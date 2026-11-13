# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes pratinjau isi berkas Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Parser pratinjau Wiki: murni bytes -> JSON, tanpa database atau MinIO."""

import io
import zipfile
from datetime import date, datetime

import pytest
from openpyxl import Workbook

from plane.utils import wiki_pratinjau as wp

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _docx(body_xml, rels_xml=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", f'<?xml version="1.0"?><w:document {W} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>{body_xml}</w:body></w:document>')
        if rels_xml:
            zf.writestr("word/_rels/document.xml.rels", rels_xml)
    return buf.getvalue()


@pytest.mark.unit
class TestJenis:
    @pytest.mark.parametrize(
        "mime,nama,harapan",
        [
            ("application/pdf", "a.pdf", "pdf"),
            ("image/png", "a.png", "image"),
            ("text/plain", "a.txt", "text"),
            ("text/plain", "catatan.md", "markdown"),
            ("text/markdown", "catatan.md", "markdown"),
            ("", "catatan.md", "markdown"),
            ("text/csv", "data.csv", "csv"),
            ("application/vnd.ms-excel", "data.csv", "csv"),
            ("application/vnd.ms-excel", "lama.xls", "konversi"),
            ("application/octet-stream", "data.tsv", "csv"),
            (wp.MIME_XLSX, "a.xlsx", "xlsx"),
            ("application/octet-stream", "a.xlsx", "xlsx"),
            (wp.MIME_DOCX, "a.docx", "docx"),
            ("application/msword", "a.doc", "konversi"),
            ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "a.pptx", "konversi"),
            ("video/x-matroska", "a.mkv", "none"),
            ("application/zip", "a.zip", "none"),
            ("application/octet-stream", "a.bin", "none"),
        ],
    )
    def test_jenis(self, mime, nama, harapan):
        assert wp.jenis_pratinjau(mime, nama) == harapan

    def test_tebak_mime(self):
        assert wp.tebak_mime("README.MD") == "text/markdown"
        assert wp.tebak_mime("data.csv") == "text/csv"
        assert wp.tebak_mime("catatan.txt") == "text/plain"
        assert wp.tebak_mime("aneh.xyz") == "application/octet-stream"


@pytest.mark.unit
class TestTeks:
    def test_utf8_bom_dibuang(self):
        assert wp.baca_teks("﻿halo".encode("utf-8"))["text"] == "halo"

    def test_cp1252_dipakai_bila_bukan_utf8(self):
        assert wp.baca_teks("café".encode("cp1252"))["text"] == "café"

    def test_utf16_dengan_bom(self):
        assert wp.baca_teks("halo".encode("utf-16"))["text"] == "halo"

    def test_biner_ditolak(self):
        assert wp.baca_teks(b"PK\x03\x04\x00\x00\x00") is None

    def test_karakter_putus_di_ujung_tidak_menggagalkan(self):
        data = "aé".encode("utf-8")[:-1]
        assert wp.baca_teks(data, terpotong=True) == {"text": "a", "truncated": True}


@pytest.mark.unit
class TestCsv:
    def test_koma(self):
        hasil = wp.baca_csv(b"a,b\n1,2\n", "x.csv")
        assert hasil["sheets"][0]["rows"] == [["a", "b"], ["1", "2"]]

    def test_titik_koma_dikenali(self):
        hasil = wp.baca_csv(b"a;b\n1;2\n", "x.csv")
        assert hasil["sheets"][0]["rows"][1] == ["1", "2"]

    def test_tsv(self):
        hasil = wp.baca_csv(b"a\tb\n1\t2\n", "x.tsv")
        assert hasil["sheets"][0]["rows"][0] == ["a", "b"]

    def test_kutip_dan_koma_dalam_sel(self):
        hasil = wp.baca_csv(b'a,b\n"1,5","dia ""bilang"""\n', "x.csv")
        assert hasil["sheets"][0]["rows"][1] == ["1,5", 'dia "bilang"']

    def test_baris_dipotong(self):
        data = "\n".join(f"{i},x" for i in range(wp.BARIS_MAKS + 50)).encode()
        lembar = wp.baca_csv(data, "x.csv")["sheets"][0]
        assert len(lembar["rows"]) == wp.BARIS_MAKS
        assert lembar["truncated"] is True

    def test_biner_ditolak(self):
        assert wp.baca_csv(b"\x00\x01\x02", "x.csv") is None


@pytest.mark.unit
class TestXlsx:
    def _buku(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Penjualan"
        ws.append(["Nama", "Jumlah", "Tanggal", "Aktif"])
        ws.append(["Ani", 3, date(2026, 1, 2), True])
        ws.append(["Budi", 2.5, datetime(2026, 1, 3, 10, 30), False])
        ws2 = wb.create_sheet("Kosong")
        ws2.sheet_state = "hidden"
        wb.create_sheet("Lain").append(["x"])
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def test_lembar_dan_nilai(self):
        hasil = wp.baca_xlsx(self._buku())
        nama = [s["name"] for s in hasil["sheets"]]
        assert nama == ["Penjualan", "Lain"]  # lembar tersembunyi tidak tampil
        assert hasil["sheets"][0]["rows"] == [
            ["Nama", "Jumlah", "Tanggal", "Aktif"],
            ["Ani", "3", "2026-01-02", "TRUE"],
            ["Budi", "2.5", "2026-01-03 10:30:00", "FALSE"],
        ]

    def test_berkas_rusak_ditolak(self):
        assert wp.baca_xlsx(b"bukan zip") is None

    def test_bom_zip_ditolak(self, monkeypatch):
        monkeypatch.setattr(wp, "ZIP_TERURAI_MAKS_BYTE", 10)
        assert wp.baca_xlsx(self._buku()) is None


@pytest.mark.unit
class TestDocx:
    def test_judul_paragraf_dan_gaya(self):
        isi = _docx(
            '<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>Bab</w:t></w:r></w:p>'
            "<w:p><w:r><w:rPr><w:b/><w:i/></w:rPr><w:t>Tebal miring</w:t></w:r><w:r><w:t xml:space=\"preserve\"> biasa</w:t></w:r></w:p>"  # noqa: E501
            "<w:p></w:p>"
        )
        blok = wp.baca_docx(isi)["blocks"]
        assert blok[0] == {"type": "heading", "level": 2, "runs": [{"text": "Bab"}]}
        assert blok[1]["runs"] == [{"text": "Tebal miring", "bold": True, "italic": True}, {"text": " biasa"}]
        assert len(blok) == 2  # paragraf kosong dilewati

    def test_daftar_dan_tabel(self):
        isi = _docx(
            '<w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>butir</w:t></w:r></w:p>'  # noqa: E501
            "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>a</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>b</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
        )
        blok = wp.baca_docx(isi)["blocks"]
        assert blok[0]["type"] == "list_item" and blok[0]["level"] == 1
        assert blok[1]["rows"] == [["a", "b"]]

    def test_tautan_hanya_skema_aman(self):
        rels = (
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="r1" Target="https://contoh.id/" TargetMode="External"/>'
            '<Relationship Id="r2" Target="javascript:alert(1)" TargetMode="External"/></Relationships>'
        )
        isi = _docx(
            '<w:p><w:hyperlink r:id="r1"><w:r><w:t>aman</w:t></w:r></w:hyperlink>'
            '<w:hyperlink r:id="r2"><w:r><w:t>jahat</w:t></w:r></w:hyperlink></w:p>',
            rels,
        )
        runs = wp.baca_docx(isi)["blocks"][0]["runs"]
        assert runs[0]["href"] == "https://contoh.id/"
        assert "href" not in runs[1]

    def test_entitas_xml_tidak_diurai(self):
        xml = (
            '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY x "SEKRET">]>'
            f'<w:document {W}><w:body><w:p><w:r><w:t>&x;</w:t></w:r></w:p></w:body></w:document>'
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("word/document.xml", xml)
        hasil = wp.baca_docx(buf.getvalue())
        assert hasil is None or "SEKRET" not in str(hasil)

    def test_rusak_ditolak(self):
        assert wp.baca_docx(b"bukan zip") is None
