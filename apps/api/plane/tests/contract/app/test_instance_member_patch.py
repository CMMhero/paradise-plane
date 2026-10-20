# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ubah member di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""`PATCH /api/instances/members/<pk>/`, ubah nama, email, password, hak akses.

Yang dijaga di sini bukan "apakah kolomnya tersimpan", tapi hal-hal yang kalau
patah tidak menimbulkan error apa pun:

- password lemah lolos → akun kantor dengan password 3 huruf
- sesi tidak diakhiri sesudah reset → reset password kehilangan gunanya
- email bentrok → 500 IntegrityError, bukan pesan yang bisa dibaca
- kolom yang tidak dikirim tertimpa nilai kosong → nama orang hilang
"""

import pytest
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import Session, User, Workspace, WorkspaceMember
from plane.license.api.views.member import InstanceMemberEndpoint
from plane.license.models import Instance, InstanceAdmin

PERAN_ADMIN, PERAN_MEMBER, PERAN_GUEST = 20, 15, 5


def _patch(admin, target_pk, data):
    request = APIRequestFactory().patch(f"/api/instances/members/{target_pk}/", data, format="json")
    force_authenticate(request, user=admin)
    return InstanceMemberEndpoint.as_view()(request, pk=target_pk)


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email="owner@paradise.test", username="owner_paradise_test")
    return Workspace.objects.create(name="Paradise", slug="paradise", owner=pemilik)


@pytest.fixture
def admin(db):
    u = User.objects.create(email="admin@paradise.test", username="admin_paradise_test")
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id="uji-1",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    InstanceAdmin.objects.create(instance=instance, user=u, role=20, is_verified=True)
    return u


@pytest.fixture
def target(db, workspace):
    u = User.objects.create(
        email="budi@paradise.test",
        username="budi_paradise_test",
        display_name="Budi Santoso",
        first_name="Budi",
        last_name="Santoso",
    )
    u.set_password("passwordlama")
    u.save()
    WorkspaceMember.objects.create(workspace=workspace, member=u, role=PERAN_GUEST)
    return u


def test_ubah_nama_memecah_first_dan_last_name(admin, target):
    res = _patch(admin, target.pk, {"display_name": "Budi Raharjo Santoso"})

    assert res.status_code == 200
    target.refresh_from_db()
    assert target.display_name == "Budi Raharjo Santoso"
    assert target.first_name == "Budi"
    assert target.last_name == "Raharjo Santoso"


def test_kolom_yang_tidak_dikirim_TIDAK_tertimpa(admin, target):
    """Form parsial tidak boleh mengosongkan sisanya."""
    res = _patch(admin, target.pk, {"workspace_role": PERAN_MEMBER})

    assert res.status_code == 200
    target.refresh_from_db()
    assert target.display_name == "Budi Santoso"
    assert target.email == "budi@paradise.test"
    assert target.check_password("passwordlama")


def test_password_pendek_ditolak_dan_password_lama_tetap_berlaku(admin, target):
    res = _patch(admin, target.pk, {"password": "pendek"})

    assert res.status_code == 400
    target.refresh_from_db()
    assert target.check_password("passwordlama"), "password lama harus tetap berlaku"


def test_reset_password_mengakhiri_sesi(admin, target):
    Session.objects.create(
        session_key="k1", session_data="x", expire_date="2099-01-01T00:00:00Z", user_id=str(target.id)
    )

    res = _patch(admin, target.pk, {"password": "passwordbaru123"})

    assert res.status_code == 200
    assert res.data["sessions_ended"] == 1
    assert not Session.objects.filter(user_id=str(target.id)).exists()
    target.refresh_from_db()
    assert target.check_password("passwordbaru123")
    # `True` memicu alur ganti-password paksa, admin yang mengeset password
    # bukan itu maksudnya.
    assert target.is_password_autoset is False


def test_ganti_email_ikut_memperbarui_username_dan_mengakhiri_sesi(admin, target):
    Session.objects.create(
        session_key="k2", session_data="x", expire_date="2099-01-01T00:00:00Z", user_id=str(target.id)
    )

    res = _patch(admin, target.pk, {"email": "Budi.Baru@Paradise.test"})

    assert res.status_code == 200
    assert res.data["sessions_ended"] == 1
    target.refresh_from_db()
    assert target.email == "budi.baru@paradise.test", "email harus dinormalkan ke huruf kecil"
    assert target.username == "budi_baru_paradise_test"


def test_email_yang_sudah_dipakai_akun_lain_ditolak(admin, target):
    res = _patch(admin, target.pk, {"email": "admin@paradise.test"})

    assert res.status_code == 400
    target.refresh_from_db()
    assert target.email == "budi@paradise.test"


def test_email_sama_dengan_milik_sendiri_bukan_bentrok(admin, target):
    """Menyimpan form tanpa mengubah email tidak boleh 400, dan tidak
    mengakhiri sesi, karena tidak ada yang berubah."""
    res = _patch(admin, target.pk, {"email": "budi@paradise.test", "display_name": "Budi S"})

    assert res.status_code == 200
    assert res.data["sessions_ended"] == 0


def test_hak_akses_diubah(admin, target, workspace):
    res = _patch(admin, target.pk, {"workspace_role": PERAN_ADMIN})

    assert res.status_code == 200
    assert res.data["workspace_role"] == PERAN_ADMIN
    assert WorkspaceMember.objects.get(workspace=workspace, member=target).role == PERAN_ADMIN


def test_peran_di_luar_daftar_ditolak(admin, target):
    res = _patch(admin, target.pk, {"workspace_role": 99})

    assert res.status_code == 400


def test_hak_akses_untuk_akun_yang_belum_jadi_anggota(admin, workspace, db):
    """`update_or_create`, bukan `update()`, akun tanpa WorkspaceMember harus
    ikut bisa diberi peran, kalau tidak permintaannya sukses tapi tak berefek."""
    yatim = User.objects.create(email="yatim@paradise.test", username="yatim_paradise_test")

    res = _patch(admin, yatim.pk, {"workspace_role": PERAN_MEMBER})

    assert res.status_code == 200
    assert WorkspaceMember.objects.filter(workspace=workspace, member=yatim, role=PERAN_MEMBER).exists()


def test_pindah_workspace_tanpa_ubah_peran(admin, target, workspace):
    """Dulu `workspace_slug` diabaikan kalau `workspace_role` tidak ikut dikirim."""
    lain = Workspace.objects.create(name="Lain", slug="lain", owner=admin)

    res = _patch(admin, target.pk, {"workspace_slug": "lain"})

    assert res.status_code == 200
    assert res.data["workspace_slug"] == "lain"
    assert res.data["workspace_role"] == PERAN_GUEST, "peran ikut pindah, tidak direset"
    assert WorkspaceMember.objects.get(workspace=lain, member=target).is_active
    assert not WorkspaceMember.objects.get(workspace=workspace, member=target).is_active


def test_ubah_peran_tanpa_slug_menyentuh_workspace_sendiri(admin, target):
    """Bukan workspace utama/terbaru: orang yang sudah dipindah tetap di tempatnya."""
    lain = Workspace.objects.create(name="Lain", slug="lain", owner=admin)
    _patch(admin, target.pk, {"workspace_slug": "lain"})

    res = _patch(admin, target.pk, {"workspace_role": PERAN_ADMIN})

    assert res.data["workspace_slug"] == "lain"
    assert WorkspaceMember.objects.get(workspace=lain, member=target).role == PERAN_ADMIN


def test_nonaktifkan_ikut_mengakhiri_sesi(admin, target):
    Session.objects.create(
        session_key="k3", session_data="x", expire_date="2099-01-01T00:00:00Z", user_id=str(target.id)
    )

    res = _patch(admin, target.pk, {"is_active": False})

    assert res.status_code == 200
    assert res.data["sessions_ended"] == 1


def test_nama_kosong_ditolak(admin, target):
    res = _patch(admin, target.pk, {"display_name": "   "})

    assert res.status_code == 400
    target.refresh_from_db()
    assert target.display_name == "Budi Santoso"


# --- Gerbang frasa untuk MEMBERI Super Admin -------------------------------
#
# Frasanya dari environment, bukan source, repo ini publik. `override_settings`
# di sini menirukan `SUPER_ADMIN_GRANT_PASSPHRASE` di `apps/api/.env`.

FRASA = "Frasa Uji Yang Panjang"


@override_settings(SUPER_ADMIN_GRANT_PASSPHRASE=FRASA)
def test_beri_super_admin_dengan_frasa_benar(admin, target):
    res = _patch(admin, target.pk, {"is_super_admin": True, "grant_passphrase": FRASA})

    assert res.status_code == 200
    assert res.data["is_super_admin"] is True
    assert InstanceAdmin.objects.filter(user=target).exists()


@override_settings(SUPER_ADMIN_GRANT_PASSPHRASE=FRASA)
def test_frasa_salah_menolak_dan_TIDAK_mengangkat(admin, target):
    res = _patch(admin, target.pk, {"is_super_admin": True, "grant_passphrase": "salah"})

    assert res.status_code == 403
    assert not InstanceAdmin.objects.filter(user=target).exists()


@override_settings(SUPER_ADMIN_GRANT_PASSPHRASE=FRASA)
def test_frasa_tidak_dikirim_sama_sekali_ditolak(admin, target):
    res = _patch(admin, target.pk, {"is_super_admin": True})

    assert res.status_code == 403
    assert not InstanceAdmin.objects.filter(user=target).exists()


@override_settings(SUPER_ADMIN_GRANT_PASSPHRASE="")
def test_frasa_belum_diatur_di_server_menolak(admin, target):
    """Gagal-tertutup: lebih baik menolak daripada diam-diam melewati gerbang."""
    res = _patch(admin, target.pk, {"is_super_admin": True, "grant_passphrase": "apa pun"})

    assert res.status_code == 400
    assert not InstanceAdmin.objects.filter(user=target).exists()


@override_settings(SUPER_ADMIN_GRANT_PASSPHRASE=FRASA)
def test_frasa_salah_TIDAK_ikut_menyimpan_kolom_lain(admin, target):
    """Gerbang harus diperiksa SEBELUM kolom apa pun disentuh.

    Kalau diperiksa di belakang, permintaan gabungan ini akan menyimpan password
    dan nama lalu membalas 403, balasan yang bagi pemanggilnya berarti "tidak
    terjadi apa-apa". Itu kegagalan senyap, kelas bug termahal di proyek ini.
    """
    res = _patch(
        admin,
        target.pk,
        {
            "is_super_admin": True,
            "grant_passphrase": "salah",
            "display_name": "Nama Seharusnya Tidak Tersimpan",
            "password": "passwordbaru999",
        },
    )

    assert res.status_code == 403
    target.refresh_from_db()
    assert target.display_name == "Budi Santoso", "nama tidak boleh tersimpan saat frasa salah"
    assert target.check_password("passwordlama"), "password tidak boleh berubah saat frasa salah"
    assert not InstanceAdmin.objects.filter(user=target).exists()


@override_settings(SUPER_ADMIN_GRANT_PASSPHRASE=FRASA)
def test_mencabut_TIDAK_perlu_frasa(admin, target):
    """Frasa hanya untuk MEMBERI. Mencabut sudah punya penjaganya sendiri
    (tidak bisa mencabut diri sendiri, dan Super Admin terakhir tidak bisa
    dicabut), meminta frasa di sini hanya menghalangi pencabutan darurat."""
    _patch(admin, target.pk, {"is_super_admin": True, "grant_passphrase": FRASA})
    assert InstanceAdmin.objects.filter(user=target).exists()

    res = _patch(admin, target.pk, {"is_super_admin": False})

    assert res.status_code == 200
    assert not InstanceAdmin.objects.filter(user=target).exists()


def _hapus(admin, target_pk, data):
    request = APIRequestFactory().delete(f"/api/instances/members/{target_pk}/", data, format="json")
    force_authenticate(request, user=admin)
    return InstanceMemberEndpoint.as_view()(request, pk=target_pk)


def test_hapus_akun_menonaktifkan_dan_menggosok_identitas(admin, target):
    """Hapus AMAN: nonaktif + email/nama digosok, baris User tetap ada (FK utuh)."""
    res = _hapus(admin, target.pk, {"konfirmasi": "Budi Santoso"})

    assert res.status_code == 200, getattr(res, "data", None)
    target.refresh_from_db()
    assert target.is_active is False
    assert target.display_name == "Akun dihapus"
    assert target.email != "budi@paradise.test"
    assert "@deleted.local" in target.email


def test_hapus_tanpa_konfirmasi_benar_ditolak(admin, target):
    res = _hapus(admin, target.pk, {"konfirmasi": "salah ketik"})

    assert res.status_code == 400
    target.refresh_from_db()
    assert target.is_active is True
    assert target.email == "budi@paradise.test"



@override_settings(SUPER_ADMIN_GRANT_PASSPHRASE=FRASA)
def test_hapus_super_admin_kedua_lolos_menyisakan_satu(admin, target):
    _patch(admin, target.pk, {"is_super_admin": True, "grant_passphrase": FRASA})
    assert InstanceAdmin.objects.count() == 2

    res = _hapus(admin, target.pk, {"konfirmasi": "Budi Santoso"})

    assert res.status_code == 200
    assert InstanceAdmin.objects.count() == 1
    assert not InstanceAdmin.objects.filter(user=target).exists()


def test_hapus_akun_sendiri_ditolak_walau_super_admin_terakhir(admin):
    """Satu-satunya Super Admin tidak bisa hilang lewat hapus-diri (gerbang
    diri-sendiri). Akun dan statusnya utuh sesudahnya."""
    assert InstanceAdmin.objects.count() == 1

    res = _hapus(admin, admin.pk, {"konfirmasi": admin.display_name or admin.email})

    assert res.status_code == 400
    assert InstanceAdmin.objects.filter(user=admin).exists()
    admin.refresh_from_db()
    assert admin.is_active is True
    assert admin.display_name != "Akun dihapus"
