# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import io

import pytest
from openpyxl import Workbook

from plane.utils.wiki_cari import cuplikan, pecah_kueri, skor_judul
from plane.utils.wiki_isi import TEKS_INDEKS_MAKS, ekstrak_teks, jenis_sumber, rapikan, teks_pdf


def _pdf(teks):
    """PDF satu halaman dengan satu baris teks, ditulis tangan (tanpa pustaka tulis)."""
    isi = f"BT /F1 12 Tf 72 720 Td ({teks}) Tj ET".encode()
    objek = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(isi) + isi + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    keluar, posisi = io.BytesIO(), []
    keluar.write(b"%PDF-1.4\n")
    for i, o in enumerate(objek, start=1):
        posisi.append(keluar.tell())
        keluar.write(b"%d 0 obj\n" % i + o + b"\nendobj\n")
    mulai = keluar.tell()
    keluar.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objek) + 1))
    for p in posisi:
        keluar.write(b"%010d 00000 n \n" % p)
    keluar.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objek) + 1, mulai))
    return keluar.getvalue()


@pytest.mark.unit
class TestEkstrak:
    def test_pdf_dibaca(self):
        assert "surat jalan gudang" in teks_pdf(_pdf("surat jalan gudang"))

    def test_pdf_rusak_bukan_galat(self):
        assert teks_pdf(b"%PDF-1.4 bukan pdf sungguhan") == ""
        assert teks_pdf(b"") == ""

    def test_xlsx_semua_sel_dan_nama_lembar(self):
        buku = Workbook()
        buku.active.title = "Stok"
        buku.active.append(["Barang", "Jumlah"])
        buku.active.append(["Resistor 10k", 250])
        buf = io.BytesIO()
        buku.save(buf)
        teks = ekstrak_teks(buf.getvalue(), "xlsx", "stok.xlsx")
        assert "Resistor 10k" in teks and "250" in teks and "Stok" in teks

    def test_csv_dan_teks(self):
        assert "alpha beta" in ekstrak_teks(b"a,b\nalpha beta,2\n", "csv", "x.csv")
        assert ekstrak_teks("Halo dunia".encode(), "teks", "x.txt") == "Halo dunia"

    def test_nul_dibuang_dan_dipotong(self):
        assert "\x00" not in rapikan("a\x00b")
        assert len(rapikan("x " * TEKS_INDEKS_MAKS)) == TEKS_INDEKS_MAKS

    def test_jenis_sumber(self):
        assert jenis_sumber("application/pdf", "a.pdf") == "pdf"
        assert jenis_sumber("application/msword", "a.doc") == "pratinjau"
        assert jenis_sumber("image/png", "a.png") is None


@pytest.mark.unit
class TestCari:
    def test_pecah_kueri(self):
        assert pecah_kueri("  Surat, jalan! surat a ") == ["surat", "jalan"]
        assert pecah_kueri("x") == []
        assert len(pecah_kueri("a1 b2 c3 d4 e5 f6 g7 h8")) == 6

    def test_skor_judul_persis_awalan_dan_salah_ketik(self):
        assert skor_judul(["laporan"], "Laporan Keuangan") == 1.0
        assert skor_judul(["keuangan"], "Laporan Keuangan") == 1.0
        assert skor_judul(["uangan"], "Laporan Keuangan") == 0.9  # ada, tapi bukan awal kata
        assert 0.75 <= skor_judul(["keuagan"], "Laporan Keuangan") < 1.0
        assert skor_judul(["gudang"], "Laporan Keuangan") == 0.0

    def test_cuplikan_persis(self):
        teks = "Awal. " * 30 + "Surat jalan wajib dilampirkan. " + "Akhir. " * 30
        potongan, sorot = cuplikan(teks, ["surat", "jalan"])
        assert "Surat jalan" in potongan and potongan.startswith("…") and potongan.endswith("…")
        assert sorot == ["surat", "jalan"]

    def test_cuplikan_salah_ketik_mengembalikan_ejaan_di_teks(self):
        potongan, sorot = cuplikan("Rekapitulasi pengeluaran departemen.", ["pengeluran"])
        assert sorot == ["pengeluaran"] and "pengeluaran" in potongan

    def test_cuplikan_tidak_ada(self):
        assert cuplikan("abc def", ["zzzz"]) == ("", [])
        assert cuplikan("", ["abc"]) == ("", [])
