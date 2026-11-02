# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji ringkasan harian
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from plane.bgtasks.daily_digest_email import (
    BATAS_BARIS,
    BATAS_BARIS_TIM,
    GrupTim,
    Kelompok,
    Ringkasan,
    hari_ke_hari_kerja_berikutnya,
    kelompokkan,
    susun_email,
)

HARI_INI = date(2026, 10, 26)


def _tugas(selisih, nomor=1, kode="FIN"):
    return SimpleNamespace(
        target_date=HARI_INI + timedelta(days=selisih),
        name=f"Tugas {nomor}",
        sequence_id=nomor,
        id=f"id-{kode}-{nomor}",
        project_id="p",
        project=SimpleNamespace(identifier=kode),
        workspace=SimpleNamespace(slug="ws"),
    )


def _orang():
    return SimpleNamespace(display_name="Budi <b>", first_name="Budi")


@pytest.mark.unit
class TestKelompokkan:
    def test_memisah_hari_ini_tujuh_hari_dan_terlambat(self):
        tugas = [_tugas(-3, 1), _tugas(0, 2), _tugas(7, 3), _tugas(8, 4), _tugas(1, 5)]
        k = kelompokkan(tugas, HARI_INI)
        assert [t.sequence_id for t in k.hari] == [2]
        assert [t.sequence_id for t in k.depan] == [5, 3]  # terurut tenggat; hari ke-8 tidak ikut
        assert [t.sequence_id for t in k.lewat] == [1]

    def test_kosong_kalau_semua_di_luar_jendela(self):
        assert not kelompokkan([_tugas(30)], HARI_INI)


@pytest.mark.unit
class TestSusunEmailStaf:
    def test_subjek_menyebut_ketiga_hitungan(self):
        r = Ringkasan(peran="Staf", sendiri=Kelompok([_tugas(0)], [_tugas(2, 2), _tugas(3, 3)], [_tugas(-1, 4)]))
        subjek, teks, _ = susun_email(_orang(), r, HARI_INI)
        assert "1 hari ini" in subjek and "2 7 hari ke depan" in subjek and "1 terlambat" in subjek
        assert "tim:" not in subjek
        assert "TERLAMBAT (1)" in teks and "FIN-4" in teks and "Staf" in teks

    def test_html_meng_escape_nama_dan_judul(self):
        jahat = _tugas(0)
        jahat.name = "<script>x</script>"
        _, _, html = susun_email(_orang(), Ringkasan(peran="Staf", sendiri=Kelompok(hari=[jahat])), HARI_INI)
        assert "<script>" not in html and "&lt;script&gt;" in html
        assert "Budi &lt;b&gt;" in html

    def test_daftar_panjang_dipotong_dengan_sisa(self):
        banyak = [_tugas(-1, n) for n in range(BATAS_BARIS + 5)]
        _, teks, html = susun_email(_orang(), Ringkasan(peran="Staf", sendiri=Kelompok(lewat=banyak)), HARI_INI)
        assert "+5 lainnya" in teks and "+5 lainnya" in html

    def test_tugas_yang_diberikan_menyebut_penanggung_jawab(self):
        t = _tugas(-2, 9)
        r = Ringkasan(peran="Staf", diberikan=Kelompok(lewat=[t]), penanggung={t.id: ["Sari"]})
        _, teks, html = susun_email(_orang(), r, HARI_INI)
        assert "TUGAS YANG ANDA BERIKAN" in teks and "[Sari]" in teks
        assert "Tugas yang Anda berikan" in html and "Sari" in html
        assert "Tidak ada tugas Anda" in teks  # bagian pribadi kosong tetap dijelaskan


@pytest.mark.unit
class TestSusunEmailPimpinan:
    def _ringkasan(self):
        a1, a2, b1 = _tugas(-3, 1, "OPS"), _tugas(0, 2, "OPS"), _tugas(5, 3, "HRD")
        return Ringkasan(
            peran="Manager",
            cakupan="Divisi Operasional",
            judul_tim="Divisi Anda",
            tim=[
                GrupTim("Operasional", Kelompok(hari=[a2], lewat=[a1])),
                GrupTim("HRD", Kelompok(depan=[b1])),
                GrupTim("Kosong", Kelompok()),
            ],
            penanggung={a1.id: ["Rina", "Joko"]},
        )

    def test_bagian_tim_berisi_rekap_dan_rincian(self):
        subjek, teks, html = susun_email(_orang(), self._ringkasan(), HARI_INI)
        assert "tim: 1 terlambat" in subjek
        assert "Manager · Divisi Operasional" in teks
        assert "Operasional: 1 terlambat, 1 hari ini, 0 7 hari ke depan" in teks
        assert "[Rina, Joko]" in teks and "[belum ada penanggung jawab]" in teks
        assert "Divisi Anda" in html and "OPS-1" in html
        # Tugas 7 hari ke depan di tim cukup angkanya, tidak dirinci.
        assert "HRD-3" not in teks and "HRD-3" not in html
        assert "Kosong" not in teks

    def test_rincian_tim_dibatasi_per_project(self):
        banyak = [_tugas(-1, n, "OPS") for n in range(BATAS_BARIS_TIM + 2)]
        r = Ringkasan(peran="Direktur", tim=[GrupTim("Operasional", Kelompok(lewat=banyak))])
        _, teks, _ = susun_email(_orang(), r, HARI_INI)
        assert "+2 lainnya" in teks


@pytest.mark.unit
class TestBagianPilihan:
    """Keputusan user 2026-11-02: ringkasan bisa dipilih per bagian."""

    def test_subjek_hanya_menyebut_bagian_yang_hidup(self):
        r = Ringkasan(
            peran="Staf",
            sendiri=Kelompok(lewat=[_tugas(-1, 4)]),
            bagian={"digest_hari_ini": False, "digest_depan": False},
        )
        subjek, teks, _ = susun_email(_orang(), r, HARI_INI)
        assert "1 terlambat" in subjek
        assert "hari ini" not in subjek and "7 hari ke depan" not in subjek
        assert "TERLAMBAT (1)" in teks

    def test_teks_kosong_menyebut_bagian_pilihan(self):
        r = Ringkasan(peran="Staf", bagian={"digest_depan": False})
        _, teks, _ = susun_email(_orang(), r, HARI_INI)
        assert "bagian yang Anda pilih" in teks


def _beres(nomor):
    t = _tugas(0, nomor)
    t.state = SimpleNamespace(group="completed")
    return t


@pytest.mark.unit
class TestEdisiSore:
    """Keputusan user 2026-11-02: ringkasan akhir hari 17.30 WIB."""

    def test_hari_kerja_berikutnya(self):
        senin = date(2026, 10, 26)
        assert hari_ke_hari_kerja_berikutnya(senin) == 1
        assert hari_ke_hari_kerja_berikutnya(senin + timedelta(days=4)) == 3  # Jumat -> Senin
        assert hari_ke_hari_kerja_berikutnya(senin + timedelta(days=5)) == 2  # Sabtu -> Senin

    def test_subjek_dan_bagian_sore(self):
        r = Ringkasan(
            peran="Staf",
            sore=True,
            hari_ke_depan=1,
            sendiri=Kelompok(hari=[_tugas(0, 2)], depan=[_tugas(1, 3)], selesai=[_beres(1)]),
        )
        subjek, teks, html = susun_email(_orang(), r, HARI_INI)
        assert subjek.startswith("[Ringkasan sore]")
        assert "1 selesai hari ini" in subjek and "1 belum selesai" in subjek and "1 besok" in subjek
        assert "SELESAI HARI INI (1)" in teks and "(26 Okt 2026, selesai)" in teks
        assert "BELUM SELESAI, TENGGAT HARI INI (1)" in teks and "JATUH TEMPO BESOK (1)" in teks
        assert "Ringkasan akhir hari" in teks and "Selesai hari ini" in html

    def test_jumat_menyebut_senin(self):
        jumat = HARI_INI + timedelta(days=4)
        r = Ringkasan(peran="Staf", sore=True, hari_ke_depan=3, sendiri=Kelompok(lewat=[_tugas(-1)]))
        subjek, teks, _ = susun_email(_orang(), r, jumat)
        assert "0 s.d. Senin" in subjek

    def test_pagi_tetap_berawalan_pagi(self):
        r = Ringkasan(peran="Staf", sendiri=Kelompok(hari=[_tugas(0)]))
        subjek, teks, _ = susun_email(_orang(), r, HARI_INI)
        assert subjek.startswith("[Ringkasan pagi]") and "SELESAI HARI INI" not in teks

    def test_tim_sore_punya_kolom_selesai(self):
        r = Ringkasan(
            peran="Supervisor",
            sore=True,
            hari_ke_depan=1,
            tim=[GrupTim("Gudang", Kelompok(lewat=[_tugas(-1, 5)], selesai=[_beres(6)]))],
        )
        _, teks, html = susun_email(_orang(), r, HARI_INI)
        assert "Gudang: 1 selesai hari ini, 1 terlambat, 0 hari ini, 0 besok" in teks
        assert ">Selesai</th>" in html and ">Besok</th>" in html
