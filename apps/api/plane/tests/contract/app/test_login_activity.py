# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pemantauan sesi & aktivitas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Riwayat login, jejak keaktifan, kick, dan retensi 3 bulan.

Yang dijaga di sini adalah hal-hal yang kalau patah **tidak menimbulkan error
apa pun**, jenis kegagalan yang paling mahal karena baru ketahuan berbulan-bulan
kemudian saat angkanya dibutuhkan:

- login/logout tidak tercatat  → dashboard menunjukkan kantor yang sepi
- middleware menulis tiap request → satu UPDATE per request ke tabel users
- kick tidak benar-benar membuang sesi → admin mengira orangnya sudah keluar
- retensi menghapus lunak → tabel tumbuh selamanya, "3 bulan" jadi bohong
- admin terakhir bisa dikunci → tak seorang pun bisa masuk God Mode lagi
"""

from datetime import timedelta

import pytest
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.authentication.utils.login import user_login
from plane.bgtasks.login_activity_retention import (
    AMBANG_PERINGATAN_HARI,
    bersihkan_login_activity,
    hitung_peringatan,
)
from plane.db.models import RETENSI_HARI, LoginActivity, Session, User
from plane.license.api.views import (
    InstanceActivityEndpoint,
    InstanceMemberSessionEndpoint,
)
from plane.license.models import Instance, InstanceAdmin
from plane.middleware.last_active import JEDA_TULIS_DETIK, LastActiveMiddleware


def _user(email):
    return User.objects.create(email=email, username=email.replace("@", "_").replace(".", "_"))


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="uji",
        instance_id="uji-aktivitas",
        current_version="uji",
        last_checked_at=timezone.now(),
    )


@pytest.fixture
def admin(instance):
    u = _user("admin@paradise.test")
    InstanceAdmin.objects.create(instance=instance, user=u, role=20)
    return u


@pytest.fixture
def anggota(db):
    return _user("anggota@paradise.test")


def _req_sesi():
    req = RequestFactory().post("/")
    req.META["HTTP_USER_AGENT"] = "uji-agent/1.0"
    req.META["REMOTE_ADDR"] = "10.9.9.9"
    SessionMiddleware(lambda r: None).process_request(req)
    return req


# --------------------------------------------------------------------------
# Perekaman
# --------------------------------------------------------------------------


def test_login_tercatat_beserta_session_key(anggota):
    """session_key harus yang FINAL, Django membuat ulang kunci saat login."""
    req = _req_sesi()
    user_login(request=req, user=anggota, is_app=True)

    a = LoginActivity.objects.get(user=anggota)
    assert a.jenis == LoginActivity.Jenis.LOGIN
    assert a.permukaan == "app"
    assert a.ip == "10.9.9.9"
    assert a.user_agent == "uji-agent/1.0"
    # Kalau ini gagal, durasi sesi tak akan pernah bisa dihitung: logout
    # menyimpan kunci lain dan pasangannya tidak pernah ketemu.
    assert a.session_key == req.session.session_key


def test_permukaan_membedakan_god_mode_dari_aplikasi(anggota):
    user_login(request=_req_sesi(), user=anggota, is_admin=True)
    assert LoginActivity.objects.get(user=anggota).permukaan == "admin"


def test_catat_tidak_pernah_melempar(anggota):
    """Jejak yang gagal tidak boleh menggagalkan orang masuk."""
    assert LoginActivity.catat(user=anggota, jenis="LOGIN", request=object()) is None
    assert LoginActivity.objects.count() == 0


# --------------------------------------------------------------------------
# Middleware keaktifan
# --------------------------------------------------------------------------


def test_last_active_ditulis_saat_basi(anggota):
    User.objects.filter(pk=anggota.pk).update(
        last_active=timezone.now() - timedelta(seconds=JEDA_TULIS_DETIK * 5)
    )
    anggota.refresh_from_db()
    lama = anggota.last_active

    req = RequestFactory().get("/")
    req.user = anggota
    LastActiveMiddleware(lambda r: "resp")(req)

    anggota.refresh_from_db()
    assert anggota.last_active > lama


def test_last_active_dilewati_saat_masih_baru(anggota):
    """Tanpa jeda ini, satu layar Plane = belasan UPDATE ke tabel users."""
    User.objects.filter(pk=anggota.pk).update(last_active=timezone.now())
    anggota.refresh_from_db()
    baru = anggota.last_active

    req = RequestFactory().get("/")
    req.user = anggota
    LastActiveMiddleware(lambda r: "resp")(req)

    anggota.refresh_from_db()
    assert anggota.last_active == baru


def test_anonim_lewat_tanpa_masalah(db):
    class Anon:
        is_authenticated = False

    req = RequestFactory().get("/")
    req.user = Anon()
    assert LastActiveMiddleware(lambda r: "resp")(req) == "resp"


# --------------------------------------------------------------------------
# Kick
# --------------------------------------------------------------------------


def _delete(admin, target, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    req = APIRequestFactory().delete(f"/api/instances/members/{target.id}/sessions/?{q}")
    force_authenticate(req, user=admin)
    return InstanceMemberSessionEndpoint.as_view()(req, pk=target.id)


def test_kick_benar_benar_membuang_sesi(admin, anggota):
    user_login(request=_req_sesi(), user=anggota, is_app=True)
    assert Session.objects.filter(user_id=str(anggota.id)).exists()

    r = _delete(admin, anggota)

    assert r.status_code == 200
    assert r.data["sesi_diputus"] == 1
    assert not Session.objects.filter(user_id=str(anggota.id)).exists()
    # Sesi ditutup rapi di riwayat, kalau tidak login-nya menggantung selamanya.
    assert LoginActivity.objects.filter(
        user=anggota, jenis=LoginActivity.Jenis.LOGOUT, permukaan="kick"
    ).exists()


def test_kick_saja_tidak_mengunci_akun(admin, anggota):
    r = _delete(admin, anggota)
    anggota.refresh_from_db()
    assert r.data["dinonaktifkan"] is False
    assert anggota.is_active is True


def test_kick_dengan_nonaktifkan_mengunci_akun(admin, anggota):
    r = _delete(admin, anggota, nonaktifkan=1)
    anggota.refresh_from_db()
    assert r.data["dinonaktifkan"] is True
    assert anggota.is_active is False


def test_admin_tidak_bisa_menendang_dirinya_sendiri(admin):
    """Satu klik di baris yang salah akan membuang sesi God Mode yang dipakai."""
    r = _delete(admin, admin)
    assert r.status_code == 400


def test_akun_baru_belum_terhitung_sedang_memakai(admin, anggota):
    """`User.last_active` ber-default `timezone.now`.

    Akun yang baru dibuat lewat God Mode karena itu punya last_active "sekarang"
    tanpa pernah login sekali pun. Kalau keaktifan diukur dari field itu saja,
    setiap karyawan baru muncul sebagai sedang memakai selama 5 menit.
    """
    assert anggota.last_active is not None  # default model, bukan bukti aktivitas

    req = APIRequestFactory().get("/api/instances/activity/?hari=30")
    force_authenticate(req, user=admin)
    r = InstanceActivityEndpoint.as_view()(req)

    assert r.data["ringkas"]["sedang_memakai"] == 0


# --------------------------------------------------------------------------
# Retensi
# --------------------------------------------------------------------------


def _peristiwa(user, hari_lalu):
    return LoginActivity.objects.create(
        user=user, jenis="LOGIN", terjadi_pada=timezone.now() - timedelta(days=hari_lalu)
    )


def test_retensi_membuang_yang_lewat_3_bulan_saja(admin, anggota):
    for h in (RETENSI_HARI + 30, RETENSI_HARI + 1, RETENSI_HARI - 1, 1):
        _peristiwa(anggota, h)

    hasil = bersihkan_login_activity()

    assert hasil["dibuang"] == 2
    # Hapus KERAS. Kalau lunak, angkanya benar tapi tabel tetap tumbuh selamanya.
    assert LoginActivity.all_objects.count() == 2


def test_peringatan_menyala_sebelum_data_hilang(anggota):
    """Peringatan pada hari penghapusan tidak memberi kesempatan mengekspor."""
    aman = hitung_peringatan()
    assert aman["perlu_peringatan"] is False

    _peristiwa(anggota, RETENSI_HARI - AMBANG_PERINGATAN_HARI + 1)
    k = hitung_peringatan()
    assert k["perlu_peringatan"] is True
    assert k["akan_dibuang"] == 1
    assert k["sudah_lewat"] == 0  # belum waktunya dihapus, baru diperingatkan


def test_dashboard_memisahkan_masih_login_dari_sedang_memakai(admin, anggota):
    """Sesi bisa hidup berhari-hari sesudah orangnya pulang."""
    user_login(request=_req_sesi(), user=anggota, is_app=True)
    User.objects.filter(pk=anggota.pk).update(last_active=timezone.now() - timedelta(hours=6))

    req = APIRequestFactory().get("/api/instances/activity/?hari=30")
    force_authenticate(req, user=admin)
    r = InstanceActivityEndpoint.as_view()(req)

    assert r.status_code == 200
    assert r.data["ringkas"]["masih_login"] == 1
    assert r.data["ringkas"]["sedang_memakai"] == 0
