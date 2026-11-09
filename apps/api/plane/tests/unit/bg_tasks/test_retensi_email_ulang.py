# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jeda email peringatan retensi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Email peringatan retensi tidak boleh datang tiap hari.

Sesudah bulan ketiga selalu ada baris yang masuk jendela peringatan, jadi
`perlu_peringatan` benar setiap hari. Tanpa jeda, admin menerima email yang
sama selamanya. Yang dijaga di sini: kirim pertama, tahan sampai jeda yang
diatur Super Admin, kirim lagi kalau jeda lewat, dan kirim lebih cepat hanya
kalau jumlahnya melonjak.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.utils import timezone

from plane.bgtasks import login_activity_retention as r
from plane.license.models import InstanceConfiguration
from plane.utils.saklar_instance import (
    ADMIN_RETENTION_EMAIL_INTERVAL_DAYS,
    LOGIN_HISTORY_RETENTION_DAYS,
    SETELAN_ANGKA,
)

pytestmark = pytest.mark.unit

JEDA = 7


def _keadaan(n):
    return {"akan_dibuang": n, "perlu_peringatan": n > 0}


def _terakhir(hari_lalu, jumlah):
    return {"pada": timezone.now() - timedelta(days=hari_lalu), "jumlah": jumlah}


class TestPerluKirimEmail:
    def test_belum_pernah_kirim(self):
        assert r.perlu_kirim_email(None, _keadaan(5), jeda_hari=JEDA) is True

    def test_besoknya_ditahan(self):
        assert r.perlu_kirim_email(_terakhir(1, 5), _keadaan(5), jeda_hari=JEDA) is False

    def test_sehari_sebelum_batas_masih_ditahan(self):
        assert r.perlu_kirim_email(_terakhir(JEDA - 1, 5), _keadaan(6), jeda_hari=JEDA) is False

    def test_seminggu_lewat_kirim_lagi(self):
        assert r.perlu_kirim_email(_terakhir(JEDA, 5), _keadaan(5), jeda_hari=JEDA) is True

    def test_lonjakan_dikirim_lebih_cepat(self):
        assert r.perlu_kirim_email(_terakhir(2, 5), _keadaan(5 * r.LONJAKAN_PELIPATAN), jeda_hari=JEDA) is True

    def test_lonjakan_di_hari_yang_sama_tidak_diulang(self):
        assert r.perlu_kirim_email(_terakhir(0, 5), _keadaan(500), jeda_hari=JEDA) is False

    def test_jeda_30_hari_menahan_sampai_hari_ke_30(self):
        assert r.perlu_kirim_email(_terakhir(29, 5), _keadaan(5), jeda_hari=30) is False
        assert r.perlu_kirim_email(_terakhir(30, 5), _keadaan(5), jeda_hari=30) is True

    def test_bawaan_jeda_dari_setelan_instance(self):
        assert SETELAN_ANGKA[ADMIN_RETENTION_EMAIL_INTERVAL_DAYS][0] == 7
        assert SETELAN_ANGKA[ADMIN_RETENTION_EMAIL_INTERVAL_DAYS][1] == 0  # 0 = ikut masa retensi

    def test_jumlah_terakhir_nol_tidak_membagi_nol(self):
        assert r.perlu_kirim_email(_terakhir(2, 0), _keadaan(2), jeda_hari=JEDA) is True


@pytest.mark.django_db
class TestTaskMemakaiJeda:
    @pytest.fixture
    def cache_lokal(self):
        lokal = LocMemCache("retensi-uji", {})
        lokal.clear()  # LocMemCache berbagi penyimpanan menurut nama, antar contoh
        with mock.patch.object(r, "cache", lokal):
            yield lokal

    def _jalankan(self, kirim, keadaan):
        with (
            mock.patch.object(r, "hitung_peringatan", return_value={**keadaan, "tertua": None}),
            mock.patch.object(r, "_kirim_email_peringatan", kirim),
        ):
            return r.bersihkan_login_activity()

    def test_dua_hari_berturut_hanya_satu_email(self, cache_lokal):
        kirim = mock.Mock(return_value=2)
        keadaan = _keadaan(5)

        pertama = self._jalankan(kirim, keadaan)
        kedua = self._jalankan(kirim, keadaan)

        assert pertama["email_terkirim"] == 2
        assert kedua["email_terkirim"] == 0
        assert kirim.call_count == 1

    def test_penanda_baru_ditulis_hanya_kalau_email_benar_terkirim(self, cache_lokal):
        """SMTP mati (0 terkirim) tidak boleh menahan percobaan besok."""
        kirim = mock.Mock(return_value=0)
        self._jalankan(kirim, _keadaan(5))
        self._jalankan(kirim, _keadaan(5))

        assert kirim.call_count == 2
        assert cache_lokal.get(r.KUNCI_EMAIL_TERAKHIR) is None

    def test_seminggu_kemudian_kirim_lagi(self, cache_lokal):
        kirim = mock.Mock(return_value=1)
        cache_lokal.set(r.KUNCI_EMAIL_TERAKHIR, _terakhir(JEDA + 1, 5))

        hasil = self._jalankan(kirim, _keadaan(5))

        assert hasil["email_terkirim"] == 1
        assert cache_lokal.get(r.KUNCI_EMAIL_TERAKHIR)["jumlah"] == 5

    def test_super_admin_memperpanjang_jeda_jadi_30_hari(self, cache_lokal, settings):
        settings.SKIP_ENV_VAR = True
        InstanceConfiguration.objects.update_or_create(
            key=ADMIN_RETENTION_EMAIL_INTERVAL_DAYS, defaults={"value": "30"}
        )
        kirim = mock.Mock(return_value=1)
        cache_lokal.set(r.KUNCI_EMAIL_TERAKHIR, _terakhir(10, 5))

        ditahan = self._jalankan(kirim, _keadaan(5))
        assert ditahan["email_terkirim"] == 0

        cache_lokal.set(r.KUNCI_EMAIL_TERAKHIR, _terakhir(31, 5))
        terkirim = self._jalankan(kirim, _keadaan(5))
        assert terkirim["email_terkirim"] == 1

    def test_nol_berarti_ikut_masa_retensi(self, cache_lokal, settings):
        """Retensi 90 hari + jeda 0 = satu email per 90 hari."""
        settings.SKIP_ENV_VAR = True
        InstanceConfiguration.objects.update_or_create(key=ADMIN_RETENTION_EMAIL_INTERVAL_DAYS, defaults={"value": "0"})
        InstanceConfiguration.objects.update_or_create(key=LOGIN_HISTORY_RETENTION_DAYS, defaults={"value": "90"})
        assert r.jeda_email_hari() == 90
        kirim = mock.Mock(return_value=1)

        cache_lokal.set(r.KUNCI_EMAIL_TERAKHIR, _terakhir(89, 5))
        assert self._jalankan(kirim, _keadaan(5))["email_terkirim"] == 0

        cache_lokal.set(r.KUNCI_EMAIL_TERAKHIR, _terakhir(90, 5))
        assert self._jalankan(kirim, _keadaan(5))["email_terkirim"] == 1

    def test_jeda_mengikuti_retensi_yang_diubah(self, settings):
        settings.SKIP_ENV_VAR = True
        InstanceConfiguration.objects.update_or_create(key=ADMIN_RETENTION_EMAIL_INTERVAL_DAYS, defaults={"value": "0"})
        InstanceConfiguration.objects.update_or_create(key=LOGIN_HISTORY_RETENTION_DAYS, defaults={"value": "30"})
        assert r.jeda_email_hari() == 30
