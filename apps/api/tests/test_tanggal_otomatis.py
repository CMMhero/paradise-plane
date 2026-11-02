# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji tanggal mulai & selesai otomatis
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Aturan isi tanggal otomatis (KEP-41), murni tanpa database.

Yang dijaga: sistem HANYA mengisi yang kosong, dan tidak pernah melahirkan
pasangan mulai > selesai yang akan ditolak serializer pada suntingan berikutnya.
"""

from datetime import date, datetime, timezone as tz

import pytest

from plane.utils.tanggal_otomatis import mulai_otomatis, selesai_otomatis, tanggal_lokal

HARI_INI = date(2026, 10, 30)


@pytest.mark.unit
class TestMulaiOtomatis:
    def test_kosong_diisi_hari_ini(self):
        assert mulai_otomatis(None, None, HARI_INI) == HARI_INI

    def test_tanggal_rencana_TIDAK_ditimpa(self):
        assert mulai_otomatis(date(2026, 11, 5), None, HARI_INI) is None

    def test_tenggat_masih_depan_tetap_diisi(self):
        assert mulai_otomatis(None, date(2026, 11, 2), HARI_INI) == HARI_INI

    def test_mulai_tepat_di_hari_tenggat_boleh(self):
        assert mulai_otomatis(None, HARI_INI, HARI_INI) == HARI_INI

    def test_tenggat_sudah_lewat_DILEWATI(self):
        assert mulai_otomatis(None, date(2026, 10, 29), HARI_INI) is None


@pytest.mark.unit
class TestSelesaiOtomatis:
    def test_kosong_diisi_hari_selesai(self):
        assert selesai_otomatis(None, None, HARI_INI) == HARI_INI

    def test_tenggat_yang_ada_TIDAK_ditimpa(self):
        assert selesai_otomatis(None, date(2026, 10, 1), HARI_INI) is None

    def test_selesai_sesudah_mulai_diisi(self):
        assert selesai_otomatis(date(2026, 10, 20), None, HARI_INI) == HARI_INI

    def test_selesai_sebelum_rencana_mulai_DILEWATI(self):
        assert selesai_otomatis(date(2026, 11, 5), None, HARI_INI) is None


@pytest.mark.unit
class TestTanggalLokal:
    def test_pagi_wib_bukan_kemarin(self):
        # 23.30 UTC tanggal 29 = 06.30 WIB tanggal 30.
        saat = datetime(2026, 10, 29, 23, 30, tzinfo=tz.utc)
        assert tanggal_lokal(saat, "Asia/Jakarta") == HARI_INI
        assert tanggal_lokal(saat, "UTC") == date(2026, 10, 29)

    def test_zona_tak_dikenal_jatuh_ke_utc(self):
        saat = datetime(2026, 10, 29, 23, 30, tzinfo=tz.utc)
        assert tanggal_lokal(saat, "Bukan/Zona") == date(2026, 10, 29)
        assert tanggal_lokal(saat, None) == date(2026, 10, 29)
