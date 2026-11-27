# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode area F (berkas, sesi, keamanan)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Aturan area F: bawaan sama dengan perilaku lama, nilai lain berlaku, dan pagar.

Pagar yang dibuktikan di sini, bukan hanya di teks bantuan:

- Endpoint menolak angka di luar lantai/plafon dengan pesan yang bisa dibaca.
- Nilai yang lolos ke database tanpa validasi (ditulis tangan) tetap jatuh ke
  bawaan lewat pembaca, jadi pemeriksa tidak pernah memakai laju 0 atau sandi lemah.
- Daftar tipe unggahan hanya bisa dicoret dan tidak pernah memuat tipe terlarang.
"""

from datetime import datetime, timedelta
from importlib import import_module
from unittest import mock
from uuid import uuid4

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.api.rate_limit import ApiKeyRateThrottle
from plane.app.views.asset.v2 import IMAGE_MIME_TYPES, allowed_mime_types
from plane.authentication.adapter.error import AUTHENTICATION_ERROR_CODES, AuthenticationException
from plane.authentication.middleware.session import SessionMiddleware
from plane.authentication.provider.credentials.magic_code import MagicCodeProvider
from plane.authentication.rate_limit import AuthenticationThrottle, EmailVerificationThrottle
from plane.authentication.utils.kata_sandi import TokenResetSandi, sandi_cukup_kuat
from plane.bgtasks.exporter_expired_task import delete_old_s3_link
from plane.bgtasks.magic_link_code_task import susun_magic_link
from plane.db.models import ExporterHistory, User
from plane.license.api.views.aturan import InstanceRulesEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.settings.redis import redis_instance
from plane.utils import aturan
from plane.utils.aturan import area_keamanan as f
from plane.utils.aturan.jenis import INT, TINGGI, NilaiTidakSah, normalkan
from plane.utils.setelan_instance import FRASA_KONFIRMASI
from plane.utils.tipe_unggahan import TIPE_LAMPIRAN, TIPE_TIDAK_PERNAH_BOLEH, tipe_lampiran_diizinkan

AREA_F = [r for r in aturan.REGISTRI.values() if r.area == "keamanan"]
SANDI_SKOR_3 = "Tracker#9988"
SANDI_SKOR_4 = "kuda-lari-cepat"


def _setel(kunci, nilai):
    """Tulis baris langsung, TANPA validasi endpoint (seperti suntingan tangan di database)."""
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": str(nilai), "category": "PARADISE", "is_encrypted": False}
    )


def _user(prefix="f"):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-f-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    cache.clear()
    yield user
    cache.clear()


def _patch(aktor, nilai, frasa=FRASA_KONFIRMASI):
    request = APIRequestFactory().patch("/api/instances/rules/", {"values": nilai, "confirm": frasa}, format="json")
    force_authenticate(request, user=aktor)
    return InstanceRulesEndpoint.as_view()(request)


# ---------------------------------------------------------------------------
# Deklarasi dan pagar statis
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestDeklarasi:
    def test_area_lengkap_dan_semua_berisiko_tinggi(self):
        assert {r.key for r in AREA_F} == {
            f.UPLOAD_BLOCKED_FILE_TYPES,
            f.EXPORT_FILE_KEEP_DAYS,
            f.PASSWORD_MIN_STRENGTH,
            f.LOGIN_ATTEMPTS_PER_MINUTE,
            f.EMAIL_CHANGE_CODES_PER_HOUR,
            f.SIGN_IN_CODE_MINUTES,
            f.SIGN_IN_CODE_WRONG_TRIES,
            f.SIGN_IN_CODE_RESENDS,
            f.PASSWORD_RESET_LINK_MINUTES,
            f.GOD_MODE_SESSION_MINUTES,
            f.APP_SESSION_SLIDING,
            f.API_KEY_REQUESTS_PER_MINUTE,
        }
        for rule in AREA_F:
            assert rule.risk == TINGGI, rule.key
            assert rule.applies != aturan.RESTART, rule.key
            assert not rule.web, rule.key

    @pytest.mark.parametrize("rule", [r for r in AREA_F if r.kind == INT], ids=lambda r: r.key)
    def test_setiap_angka_punya_lantai_di_atas_nol(self, rule):
        assert rule.min >= 1
        with pytest.raises(NilaiTidakSah):
            normalkan(rule, 0)
        with pytest.raises(NilaiTidakSah):
            normalkan(rule, rule.max + 1)

    def test_lantai_dan_plafon_yang_dijanjikan(self):
        batas = {r.key: (r.min, r.max) for r in AREA_F if r.kind == INT}
        assert batas[f.LOGIN_ATTEMPTS_PER_MINUTE] == (3, 60)
        assert batas[f.API_KEY_REQUESTS_PER_MINUTE] == (10, 600)
        assert batas[f.EMAIL_CHANGE_CODES_PER_HOUR] == (1, 10)
        assert batas[f.SIGN_IN_CODE_MINUTES] == (5, 30)
        assert batas[f.SIGN_IN_CODE_WRONG_TRIES] == (3, 10)
        assert batas[f.SIGN_IN_CODE_RESENDS] == (1, 5)
        assert batas[f.PASSWORD_RESET_LINK_MINUTES] == (10, 1440)
        assert batas[f.GOD_MODE_SESSION_MINUTES] == (5, 480)

    def test_kekuatan_sandi_bawaan_panjang_saja(self):
        rule = aturan.REGISTRI[f.PASSWORD_MIN_STRENGTH]
        assert rule.default == 0
        assert rule.nilai_pilihan == (0, 3, 4)
        for lemah in (1, 2, "2"):
            with pytest.raises(NilaiTidakSah):
                normalkan(rule, lemah)

    def test_daftar_unggahan_hanya_bisa_mencoret(self):
        rule = aturan.REGISTRI[f.UPLOAD_BLOCKED_FILE_TYPES]
        assert rule.default == ()
        assert rule.nilai_pilihan == TIPE_LAMPIRAN
        assert not TIPE_TIDAK_PERNAH_BOLEH.intersection(TIPE_LAMPIRAN)
        with pytest.raises(NilaiTidakSah):
            normalkan(rule, ["text/html"])

    @pytest.mark.parametrize(
        "env,harapan",
        [
            (None, 10),
            ("10/minute", 10),
            ("20/min", 20),
            ("600/hour", 10),
            ("1/second", 60),
            ("1000/minute", 60),
            ("0/minute", 3),
            ("rusak", 10),
            ("", 10),
        ],
    )
    def test_benih_laju_dari_env_lama_dijepit(self, monkeypatch, env, harapan):
        if env is None:
            monkeypatch.delenv("AUTHENTICATION_RATE_LIMIT", raising=False)
        else:
            monkeypatch.setenv("AUTHENTICATION_RATE_LIMIT", env)
        assert f._benih_laju_per_menit("AUTHENTICATION_RATE_LIMIT", 10, 3, 60) == harapan

    @pytest.mark.parametrize(
        "env,harapan", [(None, 60), ("3600", 60), ("7200", 120), ("60", 5), ("99999", 480), ("x", 60)]
    )
    def test_benih_sesi_god_mode_dari_env_lama(self, monkeypatch, env, harapan):
        if env is None:
            monkeypatch.delenv("ADMIN_SESSION_COOKIE_AGE", raising=False)
        else:
            monkeypatch.setenv("ADMIN_SESSION_COOKIE_AGE", env)
        assert f._benih_menit("ADMIN_SESSION_COOKIE_AGE", 60, 5, 480) == harapan


# ---------------------------------------------------------------------------
# Endpoint menolak nilai di luar pagar; nilai rusak di database jatuh ke bawaan
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestPagarEndpoint:
    @pytest.mark.parametrize(
        "kunci,nilai,pesan",
        [
            (f.LOGIN_ATTEMPTS_PER_MINUTE, 0, "Must be between 3 and 60."),
            (f.LOGIN_ATTEMPTS_PER_MINUTE, 100000, "Must be between 3 and 60."),
            (f.API_KEY_REQUESTS_PER_MINUTE, 0, "Must be between 10 and 600."),
            (f.EMAIL_CHANGE_CODES_PER_HOUR, 0, "Must be between 1 and 10."),
            (f.SIGN_IN_CODE_WRONG_TRIES, 1000, "Must be between 3 and 10."),
            (f.SIGN_IN_CODE_RESENDS, 0, "Must be between 1 and 5."),
            (f.SIGN_IN_CODE_MINUTES, 1440, "Must be between 5 and 30."),
            (f.PASSWORD_RESET_LINK_MINUTES, 100000, "Must be between 10 and 1440."),
            (f.GOD_MODE_SESSION_MINUTES, 0, "Must be between 5 and 480."),
            (f.EXPORT_FILE_KEEP_DAYS, 0, "Must be between 1 and 30."),
            (f.PASSWORD_MIN_STRENGTH, 2, "Must be one of: Length only, Strong, Very strong."),
            (f.UPLOAD_BLOCKED_FILE_TYPES, ["text/html"], "Unknown items: text/html."),
        ],
    )
    def test_di_luar_pagar_ditolak_dengan_pesan(self, super_admin, kunci, nilai, pesan):
        res = _patch(super_admin, {kunci: nilai})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data["errors"] == {kunci: pesan}
        assert not InstanceConfiguration.objects.filter(key=kunci).exists()

    @pytest.mark.parametrize(
        "kunci,mentah",
        [
            (f.LOGIN_ATTEMPTS_PER_MINUTE, "0"),
            (f.LOGIN_ATTEMPTS_PER_MINUTE, "999999"),
            (f.API_KEY_REQUESTS_PER_MINUTE, "-1"),
            (f.EMAIL_CHANGE_CODES_PER_HOUR, "0"),
            (f.SIGN_IN_CODE_WRONG_TRIES, "1000"),
            (f.SIGN_IN_CODE_RESENDS, "99"),
            (f.SIGN_IN_CODE_MINUTES, "100000"),
            (f.PASSWORD_RESET_LINK_MINUTES, "525600"),
            (f.GOD_MODE_SESSION_MINUTES, "0"),
            (f.PASSWORD_MIN_STRENGTH, "1"),
            (f.APP_SESSION_SLIDING, "mungkin"),
            (f.UPLOAD_BLOCKED_FILE_TYPES, "text/html,application/pdf"),
        ],
    )
    def test_nilai_lolos_ke_database_jatuh_ke_bawaan(self, kunci, mentah):
        _setel(kunci, mentah)
        assert aturan.get(kunci) == aturan.REGISTRI[kunci].default

    def test_pembaca_tidak_pernah_memakai_laju_dari_baris_rusak(self):
        _setel(f.LOGIN_ATTEMPTS_PER_MINUTE, "0")
        _setel(f.API_KEY_REQUESTS_PER_MINUTE, "0")
        _setel(f.PASSWORD_MIN_STRENGTH, "1")
        assert AuthenticationThrottle().rate == f"{aturan.REGISTRI[f.LOGIN_ATTEMPTS_PER_MINUTE].default}/minute"
        assert ApiKeyRateThrottle().rate == f"{aturan.REGISTRI[f.API_KEY_REQUESTS_PER_MINUTE].default}/minute"
        assert sandi_cukup_kuat("password123")

    def test_perubahan_tercatat_di_audit(self, super_admin):
        from auditlog.models import LogEntry

        res = _patch(super_admin, {f.LOGIN_ATTEMPTS_PER_MINUTE: 5})
        assert res.status_code == status.HTTP_200_OK
        assert LogEntry.objects.filter(object_repr=f"Rule: {f.LOGIN_ATTEMPTS_PER_MINUTE}").count() == 1


# ---------------------------------------------------------------------------
# Batas laju
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestBatasLaju:
    def test_bawaan_sama_dengan_hari_ini(self):
        assert AuthenticationThrottle().rate == f"{aturan.REGISTRI[f.LOGIN_ATTEMPTS_PER_MINUTE].default}/minute"
        assert EmailVerificationThrottle().rate == "3/hour"
        assert ApiKeyRateThrottle().rate == f"{aturan.REGISTRI[f.API_KEY_REQUESTS_PER_MINUTE].default}/minute"

    def test_tanpa_env_bawaannya_angka_kode_lama(self):
        import os

        if "AUTHENTICATION_RATE_LIMIT" not in os.environ:
            assert aturan.REGISTRI[f.LOGIN_ATTEMPTS_PER_MINUTE].default == 10
        if "API_KEY_RATE_LIMIT" not in os.environ or os.environ["API_KEY_RATE_LIMIT"] == "60/minute":
            assert aturan.REGISTRI[f.API_KEY_REQUESTS_PER_MINUTE].default == 60

    def test_nilai_god_mode_berlaku_tanpa_restart(self):
        _setel(f.LOGIN_ATTEMPTS_PER_MINUTE, 5)
        _setel(f.EMAIL_CHANGE_CODES_PER_HOUR, 7)
        _setel(f.API_KEY_REQUESTS_PER_MINUTE, 120)
        assert AuthenticationThrottle().rate == "5/minute"
        assert AuthenticationThrottle().num_requests == 5
        assert EmailVerificationThrottle().rate == "7/hour"
        assert ApiKeyRateThrottle().rate == "120/minute"

    def test_throttle_menolak_sesudah_batas_god_mode(self):
        cache.clear()
        _setel(f.LOGIN_ATTEMPTS_PER_MINUTE, 3)
        pabrik = RequestFactory()
        hasil = []
        for _ in range(4):
            request = pabrik.post("/auth/magic-sign-in/", REMOTE_ADDR="10.9.8.7")
            request.user = AnonymousUser()
            hasil.append(AuthenticationThrottle().allow_request(request, None))
        cache.clear()
        assert hasil == [True, True, True, False]


# ---------------------------------------------------------------------------
# Kekuatan sandi dan tautan reset
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestSandi:
    @pytest.mark.parametrize("sandi", ["12345678", "password", "kucing123"])
    def test_bawaan_menerima_delapan_karakter_apa_saja(self, sandi):
        assert sandi_cukup_kuat(sandi)

    @pytest.mark.parametrize("sandi", ["", "1234567", "Ab#1", None, 12345678])
    def test_bawaan_menolak_yang_pendek_atau_bukan_teks(self, sandi):
        assert not sandi_cukup_kuat(sandi)

    def test_strong_menolak_yang_mudah_ditebak(self):
        _setel(f.PASSWORD_MIN_STRENGTH, 3)
        assert sandi_cukup_kuat(SANDI_SKOR_3)
        assert not sandi_cukup_kuat("password123")

    def test_very_strong_menolak_skor_tiga(self):
        _setel(f.PASSWORD_MIN_STRENGTH, 4)
        assert not sandi_cukup_kuat(SANDI_SKOR_3)
        assert sandi_cukup_kuat(SANDI_SKOR_4)

    def test_endpoint_ganti_sandi_mengikuti_aturan(self, session_client, create_user):
        create_user.set_password("lama-Sekali#123")
        create_user.save()
        url = "/auth/change-password/"
        _setel(f.PASSWORD_MIN_STRENGTH, 4)
        res = session_client.post(url, {"old_password": "lama-Sekali#123", "new_password": SANDI_SKOR_3}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data["error_code"] == AUTHENTICATION_ERROR_CODES["PASSWORD_TOO_WEAK"]

    @pytest.mark.parametrize("baru,kode", [("kucing123", 200), ("kucing1", 400)])
    def test_endpoint_ganti_sandi_bawaan(self, session_client, create_user, baru, kode):
        create_user.set_password("lama-Sekali#123")
        create_user.save()
        res = session_client.post(
            "/auth/change-password/", {"old_password": "lama-Sekali#123", "new_password": baru}, format="json"
        )
        assert res.status_code == kode

    def _token_pada(self, menit_lalu, user):
        awal = datetime(2026, 11, 1, 8, 0, 0)
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=awal):
            token = TokenResetSandi().make_token(user)
        with mock.patch.object(PasswordResetTokenGenerator, "_now", return_value=awal + timedelta(minutes=menit_lalu)):
            return TokenResetSandi().check_token(user, token)

    def test_tautan_reset_bawaan_satu_jam(self):
        user = _user()
        assert self._token_pada(59, user)
        assert not self._token_pada(61, user)

    def test_tautan_reset_mengikuti_god_mode(self):
        user = _user()
        _setel(f.PASSWORD_RESET_LINK_MINUTES, 120)
        assert self._token_pada(119, user)
        assert not self._token_pada(121, user)
        _setel(f.PASSWORD_RESET_LINK_MINUTES, 10)
        assert not self._token_pada(11, user)

    def test_token_palsu_tetap_ditolak(self):
        user = _user()
        _setel(f.PASSWORD_RESET_LINK_MINUTES, 1440)
        token = TokenResetSandi().make_token(user)
        assert not TokenResetSandi().check_token(user, token[:-1] + ("0" if token[-1] != "0" else "1"))
        assert not TokenResetSandi().check_token(_user(), token)


# ---------------------------------------------------------------------------
# Kode masuk lewat email
# ---------------------------------------------------------------------------


def _penyedia(email, kode=None):
    """MagicCodeProvider tanpa __init__ (yang memeriksa SMTP): yang diuji initiate/set_user_data."""
    penyedia = MagicCodeProvider.__new__(MagicCodeProvider)
    penyedia.key = email
    penyedia.code = kode
    return penyedia


@pytest.mark.contract
@pytest.mark.django_db
class TestKodeMasuk:
    @pytest.fixture(autouse=True)
    def _bersih(self):
        self.email = f"kode-{uuid4().hex[:8]}@uji.id"
        yield
        ri = redis_instance()
        ri.delete(f"magic_{self.email}")
        ri.delete(f"magic_{self.email}:verify_attempts")

    def _kirim(self):
        return _penyedia(self.email).initiate()

    def test_bawaan_umur_sepuluh_menit_dan_tiga_kirim_ulang(self):
        kunci, _ = self._kirim()
        assert 590 <= redis_instance().ttl(kunci) <= 600
        for _ in range(3):
            self._kirim()
        with pytest.raises(AuthenticationException) as e:
            self._kirim()
        assert e.value.error_code == AUTHENTICATION_ERROR_CODES["EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP"]

    def test_umur_dan_kirim_ulang_dari_god_mode(self):
        _setel(f.SIGN_IN_CODE_MINUTES, 15)
        _setel(f.SIGN_IN_CODE_RESENDS, 1)
        kunci, _ = self._kirim()
        assert 890 <= redis_instance().ttl(kunci) <= 900
        self._kirim()
        with pytest.raises(AuthenticationException):
            self._kirim()

    def _salah(self, kunci):
        with pytest.raises(AuthenticationException) as e:
            _penyedia(kunci, "000000").set_user_data()
        return e.value.error_code

    def test_salah_kode_bawaan_lima(self):
        kunci, _ = self._kirim()
        kode = [self._salah(kunci) for _ in range(5)]
        habis = AUTHENTICATION_ERROR_CODES["EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP"]
        assert kode[:4] == [AUTHENTICATION_ERROR_CODES["INVALID_MAGIC_CODE_SIGN_UP"]] * 4
        assert kode[4] == habis

    def test_salah_kode_dari_god_mode(self):
        _setel(f.SIGN_IN_CODE_WRONG_TRIES, 3)
        kunci, _ = self._kirim()
        kode = [self._salah(kunci) for _ in range(3)]
        assert kode[2] == AUTHENTICATION_ERROR_CODES["EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP"]
        assert not redis_instance().exists(kunci)

    def test_email_menyebut_umur_kode(self):
        _, _, polos = susun_magic_link("a@uji.id", "123456", "en")
        assert "valid for 10 minutes" in polos
        _, _, polos = susun_magic_link("a@uji.id", "123456", "en", menit=25)
        assert "valid for 25 minutes" in polos
        _, _, polos = susun_magic_link("a@uji.id", "123456", "id", grup="ganti_email", menit=25)
        assert "berlaku 25 menit" in polos

    def test_pengirim_mengisi_umur_dari_god_mode(self):
        from plane.bgtasks.magic_link_code_task import menit_kode

        assert menit_kode() == 10
        _setel(f.SIGN_IN_CODE_MINUTES, 20)
        assert menit_kode() == 20


# ---------------------------------------------------------------------------
# Sesi
# ---------------------------------------------------------------------------

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


def _lewat_middleware(path, nama_cookie, umur):
    sesi = SessionStore()
    sesi["isi"] = 1
    sesi.set_expiry(umur)
    sesi.save()
    request = RequestFactory().get(path)
    request.COOKIES[nama_cookie] = sesi.session_key
    respons = SessionMiddleware(lambda r: HttpResponse())(request)
    return respons, sesi.session_key


@pytest.mark.contract
@pytest.mark.django_db
class TestSesi:
    def test_sesi_aplikasi_tidak_menggeser_secara_bawaan(self):
        respons, _ = _lewat_middleware("/api/users/me/", settings.SESSION_COOKIE_NAME, 86400)
        assert settings.SESSION_COOKIE_NAME not in respons.cookies

    def test_sesi_aplikasi_menggeser_kalau_dinyalakan(self):
        _setel(f.APP_SESSION_SLIDING, "1")
        respons, _ = _lewat_middleware("/api/users/me/", settings.SESSION_COOKIE_NAME, 86400)
        assert respons.cookies[settings.SESSION_COOKIE_NAME]["max-age"] == 86400

    def test_sesi_god_mode_bawaan_satu_jam(self):
        from plane.authentication.utils.login import user_login

        request = RequestFactory().post("/api/instances/admins/sign-in/", HTTP_USER_AGENT="pytest")
        request.session = SessionStore()
        request.user = AnonymousUser()
        user_login(request=request, user=_user("admin"), is_admin=True)
        assert request.session.get_expiry_age() == aturan.REGISTRI[f.GOD_MODE_SESSION_MINUTES].default * 60

    def test_sesi_god_mode_berlaku_untuk_sesi_yang_sedang_jalan(self):
        _setel(f.GOD_MODE_SESSION_MINUTES, 30)
        respons, kunci = _lewat_middleware("/api/instances/admins/me/", settings.ADMIN_SESSION_COOKIE_NAME, 3600)
        assert respons.cookies[settings.ADMIN_SESSION_COOKIE_NAME]["max-age"] == 1800
        assert SessionStore(kunci).get_expiry_age() == 1800


# ---------------------------------------------------------------------------
# Berkas
# ---------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestBerkas:
    def test_bawaan_semua_tipe_lampiran(self):
        assert tipe_lampiran_diizinkan() == TIPE_LAMPIRAN
        assert allowed_mime_types("WIKI_MATERIAL") == TIPE_LAMPIRAN

    def test_tipe_yang_dicoret_ditolak_dan_gambar_profil_tidak_terpengaruh(self):
        _setel(f.UPLOAD_BLOCKED_FILE_TYPES, "image/svg+xml,application/pdf,image/png")
        diizinkan = tipe_lampiran_diizinkan()
        assert "image/svg+xml" not in diizinkan and "application/pdf" not in diizinkan
        assert set(diizinkan) == set(TIPE_LAMPIRAN) - {"image/svg+xml", "application/pdf", "image/png"}
        assert allowed_mime_types("COMMENT_DESCRIPTION") == IMAGE_MIME_TYPES

    def test_endpoint_unggah_menolak_tipe_yang_dicoret(self, session_client, workspace):
        _setel(f.UPLOAD_BLOCKED_FILE_TYPES, "application/pdf")
        with mock.patch("plane.app.views.asset.v2.S3Storage"):
            res = session_client.post(
                f"/api/assets/v2/workspaces/{workspace.slug}/",
                {"name": "a.pdf", "type": "application/pdf", "size": 1024, "entity_type": "CHAT_ATTACHMENT"},
                format="json",
            )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid file type" in res.data["error"]

    def _ekspor(self, workspace, user, hari_lalu):
        ekspor = ExporterHistory.objects.create(
            workspace=workspace,
            provider="csv",
            key=f"k-{uuid4().hex[:6]}",
            url="https://minio.example/x",
            initiated_by=user,
        )
        ExporterHistory.objects.filter(pk=ekspor.pk).update(created_at=timezone.now() - timedelta(days=hari_lalu))
        return ekspor

    def test_berkas_ekspor_dihapus_mengikuti_god_mode(self, workspace, create_user):
        ekspor = self._ekspor(workspace, create_user, 5)
        with mock.patch("plane.bgtasks.exporter_expired_task.boto3"):
            delete_old_s3_link()
            ekspor.refresh_from_db()
            assert ekspor.url is not None
            _setel(f.EXPORT_FILE_KEEP_DAYS, 3)
            delete_old_s3_link()
        ekspor.refresh_from_db()
        assert ekspor.url is None
