# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes tipe MIME unggahan yang toleran
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Merapikan tipe MIME dari klien: murni teks, tanpa database."""

import pytest
from django.conf import settings

from plane.app.views.asset.v2 import IMAGE_MIME_TYPES
from plane.utils.tipe_unggahan import rapikan_tipe_unggahan, tebak_tipe_dari_nama

LAMPIRAN = settings.ATTACHMENT_MIME_TYPES


@pytest.mark.unit
class TestRapikanTipeUnggahan:
    def test_tipe_sah_dipakai_apa_adanya(self):
        assert rapikan_tipe_unggahan("a.pdf", "application/pdf", LAMPIRAN) == "application/pdf"

    def test_parameter_dan_huruf_besar_dibuang(self):
        assert rapikan_tipe_unggahan("a.txt", "Text/Plain; charset=UTF-8", LAMPIRAN) == "text/plain"

    @pytest.mark.parametrize(
        "nama,harapan",
        [
            ("catatan.md", "text/markdown"),
            ("data.CSV", "text/csv"),
            ("log.txt", "text/plain"),
            ("rekaman.mkv", "video/x-matroska"),
            ("arsip.7z", "application/x-7z-compressed"),
            ("laporan.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ],
    )
    def test_tipe_kosong_ditebak_dari_ekstensi(self, nama, harapan):
        assert rapikan_tipe_unggahan(nama, "", LAMPIRAN) == harapan
        assert rapikan_tipe_unggahan(nama, None, LAMPIRAN) == harapan
        assert rapikan_tipe_unggahan(nama, "application/octet-stream", LAMPIRAN) == harapan

    def test_ekstensi_asing_jatuh_ke_octet_stream(self):
        assert rapikan_tipe_unggahan("model.obj1", "", LAMPIRAN) == "application/octet-stream"

    def test_tipe_spesifik_tak_dikenal_tidak_diubah_jadi_sah(self):
        # penolakan yang disengaja: pemanggil yang menolaknya
        assert rapikan_tipe_unggahan("a.exe", "application/x-msdownload", LAMPIRAN) == "application/x-msdownload"
        assert "application/x-msdownload" not in LAMPIRAN

    def test_entitas_gambar_saja_tidak_dapat_octet_stream(self):
        assert rapikan_tipe_unggahan("foto.png", "", IMAGE_MIME_TYPES) == "image/png"
        assert rapikan_tipe_unggahan("dok.pdf", "", IMAGE_MIME_TYPES) == ""

    def test_tebak_tipe_dari_nama(self):
        assert tebak_tipe_dari_nama("") == ""
        assert tebak_tipe_dari_nama("tanpa-ekstensi") == ""
        assert tebak_tipe_dari_nama("A.MD") == "text/markdown"
