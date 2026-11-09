# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes kontrak pratinjau isi Materi Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pratinjau teks, Markdown, CSV, Excel, dan Word yang dibaca server, plus tebakan
tipe saat unggah (berkas teks datang tanpa tipe dari peramban)."""

import io
import zipfile

import pytest
from openpyxl import Workbook
from rest_framework import status

from plane.db.models import FileAsset, WikiMaterial
from plane.tests.contract.app.test_wiki_mandiri_app import (  # noqa: F401 - fixture dipakai bersama
    _klien,
    _unggah,
    s3_palsu,
    wiki,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _isi_penyimpanan(s3_palsu, data):
    s3_palsu.return_value.s3_client.get_object.return_value = {"Body": io.BytesIO(data)}


def _materi_bertipe(wiki, nama, tipe=""):
    res = _unggah(_klien(wiki.staf1), wiki, wiki.f_t1, nama=nama, tipe=tipe)
    assert res.status_code == status.HTTP_200_OK, res.data
    return WikiMaterial.objects.get(id=res.data["material"]["id"])


def _pratinjau(wiki, materi):
    res = _klien(wiki.biasa).get(f"{wiki.base}materials/{materi.id}/preview/")
    assert res.status_code == status.HTTP_200_OK
    return res.data


@pytest.mark.contract
@pytest.mark.django_db
class TestUnggahTanpaTipe:
    def test_markdown_tanpa_tipe_diterima_dan_ditebak(self, wiki):
        materi = _materi_bertipe(wiki, "catatan.md", tipe="")
        assert FileAsset.objects.get(id=materi.id).attributes["type"] == "text/markdown"

    def test_csv_tanpa_tipe(self, wiki):
        materi = _materi_bertipe(wiki, "data.csv", tipe="")
        assert FileAsset.objects.get(id=materi.id).attributes["type"] == "text/csv"

    def test_tipe_tak_dikenal_tetap_ditolak(self, wiki):
        res = _unggah(_klien(wiki.staf1), wiki, wiki.f_t1, nama="a.exe", tipe="application/x-msdownload")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
@pytest.mark.django_db
class TestPratinjauIsi:
    def test_markdown(self, wiki, s3_palsu):
        materi = _materi_bertipe(wiki, "catatan.md")
        _isi_penyimpanan(s3_palsu, "# Judul\n\nisi".encode())
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "markdown"
        assert hasil["text"].startswith("# Judul")
        assert hasil["truncated"] is False
        assert hasil["url"].endswith("?disposition=inline")

    def test_csv_jadi_tabel(self, wiki, s3_palsu):
        materi = _materi_bertipe(wiki, "data.csv")
        _isi_penyimpanan(s3_palsu, b"a,b\n1,2\n")
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "table"
        assert hasil["sheets"][0]["rows"] == [["a", "b"], ["1", "2"]]

    def test_csv_ber_tipe_excel_dari_windows_tetap_tabel(self, wiki, s3_palsu):
        materi = _materi_bertipe(wiki, "data.csv", tipe="application/vnd.ms-excel")
        _isi_penyimpanan(s3_palsu, b"a;b\n1;2\n")
        assert _pratinjau(wiki, materi)["kind"] == "table"

    def test_teks_biner_ditolak_dengan_alasan(self, wiki, s3_palsu):
        materi = _materi_bertipe(wiki, "catatan.txt")
        _isi_penyimpanan(s3_palsu, b"\x00\x01\x02\x03")
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "none" and hasil["url"] is None and hasil["reason"]

    def test_teks_terlalu_besar_dipotong(self, wiki, s3_palsu, monkeypatch):
        monkeypatch.setattr("plane.app.views.wiki_berkas.TEKS_MAKS_BYTE", 10)
        materi = _materi_bertipe(wiki, "catatan.txt")
        _isi_penyimpanan(s3_palsu, b"x" * 50)
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "text" and hasil["truncated"] is True and len(hasil["text"]) == 10

    def test_xlsx_jadi_tabel_per_lembar(self, wiki, s3_palsu):
        wb = Workbook()
        wb.active.title = "Stok"
        wb.active.append(["Barang", "Qty"])
        wb.active.append(["Pipa", 4])
        buf = io.BytesIO()
        wb.save(buf)
        materi = _materi_bertipe(wiki, "stok.xlsx", tipe="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        _isi_penyimpanan(s3_palsu, buf.getvalue())
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "table"
        assert hasil["sheets"][0]["name"] == "Stok"
        assert hasil["sheets"][0]["rows"] == [["Barang", "Qty"], ["Pipa", "4"]]

    def test_xlsx_terlalu_besar_ditolak(self, wiki, s3_palsu, monkeypatch):
        monkeypatch.setattr("plane.app.views.wiki_berkas.BERKAS_ZIP_MAKS_BYTE", 10)
        materi = _materi_bertipe(wiki, "stok.xlsx", tipe="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        _isi_penyimpanan(s3_palsu, b"x" * 50)
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "none" and "too large" in hasil["reason"]

    def test_docx_tanpa_gotenberg_jatuh_ke_tampilan_sederhana(self, wiki, s3_palsu, settings):
        settings.GOTENBERG_URL = ""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(
                "word/document.xml",
                f'<w:document xmlns:w="{W}"><w:body><w:p><w:r><w:t>Halo dunia</w:t></w:r></w:p></w:body></w:document>',
            )
        materi = _materi_bertipe(
            wiki, "a.docx", tipe="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        _isi_penyimpanan(s3_palsu, buf.getvalue())
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "document" and hasil["fallback"] is True
        assert hasil["blocks"][0]["runs"] == [{"text": "Halo dunia"}]

    def test_docx_rusak_memberi_alasan(self, wiki, s3_palsu, settings):
        settings.GOTENBERG_URL = ""
        materi = _materi_bertipe(
            wiki, "a.docx", tipe="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        _isi_penyimpanan(s3_palsu, b"bukan zip")
        hasil = _pratinjau(wiki, materi)
        assert hasil["kind"] == "none" and hasil["reason"]
