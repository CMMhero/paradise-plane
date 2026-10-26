# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji ringkasan harian
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from plane.bgtasks.daily_digest_task import BATAS_BARIS, kelompokkan, susun_email

HARI_INI = date(2026, 10, 26)


def _tugas(selisih, nomor=1):
    return SimpleNamespace(
        target_date=HARI_INI + timedelta(days=selisih),
        name=f"Tugas {nomor}",
        sequence_id=nomor,
        id=f"id-{nomor}",
        project_id="p",
        project=SimpleNamespace(identifier="FIN"),
        workspace=SimpleNamespace(slug="ws"),
    )


@pytest.mark.unit
class TestKelompokkan:
    def test_memisah_hari_ini_tujuh_hari_dan_terlambat(self):
        tugas = [_tugas(-3, 1), _tugas(0, 2), _tugas(7, 3), _tugas(8, 4), _tugas(1, 5)]
        hari, depan, lewat = kelompokkan(tugas, HARI_INI)
        assert [t.sequence_id for t in hari] == [2]
        assert [t.sequence_id for t in depan] == [5, 3]  # terurut tenggat; hari ke-8 tidak ikut
        assert [t.sequence_id for t in lewat] == [1]

    def test_kosong_kalau_semua_di_luar_jendela(self):
        assert kelompokkan([_tugas(30)], HARI_INI) == ([], [], [])


@pytest.mark.unit
class TestSusunEmail:
    def _orang(self):
        return SimpleNamespace(display_name="Budi <b>", first_name="Budi")

    def test_subjek_menyebut_ketiga_hitungan(self):
        subjek, teks, html = susun_email(self._orang(), [_tugas(0)], [_tugas(2, 2), _tugas(3, 3)], [_tugas(-1, 4)], HARI_INI)
        assert "1 hari ini" in subjek and "2 7 hari ke depan" in subjek and "1 terlambat" in subjek
        assert "TERLAMBAT (1)" in teks and "FIN-4" in teks

    def test_html_meng_escape_nama_dan_judul(self):
        jahat = _tugas(0)
        jahat.name = "<script>x</script>"
        _, _, html = susun_email(self._orang(), [jahat], [], [], HARI_INI)
        assert "<script>" not in html and "&lt;script&gt;" in html
        assert "Budi &lt;b&gt;" in html

    def test_daftar_panjang_dipotong_dengan_sisa(self):
        banyak = [_tugas(-1, n) for n in range(BATAS_BARIS + 5)]
        _, teks, html = susun_email(self._orang(), [], [], banyak, HARI_INI)
        assert "+5 lainnya" in teks and "+5 lainnya" in html
