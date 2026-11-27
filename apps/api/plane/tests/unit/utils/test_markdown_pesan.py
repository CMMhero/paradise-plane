# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Markdown pesan jadi teks dan HTML email
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
import re
from pathlib import Path

import pytest

from plane.utils.markdown_pesan import html_email_dari_markdown, teks_dari_markdown

# Dipakai juga tes web (`apps/web/tests/markdown-pesan.test.ts`): satu aturan, dua bahasa.
KASUS = json.loads((Path(__file__).parents[2] / "data" / "markdown_polos.json").read_text(encoding="utf-8"))


def _tanpa_atribut(html):
    return re.sub(r"<(\w+)[^>]*>", r"<\1>", html)


@pytest.mark.unit
class TestTeksPolos:
    @pytest.mark.parametrize("kasus", KASUS, ids=[k["nama"] for k in KASUS])
    def test_sintaks_hilang_teks_tetap(self, kasus):
        assert teks_dari_markdown(kasus["markdown"]) == kasus["polos"]

    def test_none(self):
        assert teks_dari_markdown(None) == ""


@pytest.mark.unit
class TestHtmlEmail:
    def test_format_dasar_dan_baris_baru(self):
        html = html_email_dari_markdown(
            "Dengan ini kami menyampaikan **selamat bergabung**.\nBaris _kedua_.\n\n## Agenda\n\n"
            "* satu\n* dua\n\n3. tiga\n\n> kutipan\n\n`kode`"
        )
        polos = _tanpa_atribut(html)
        assert "<strong>selamat bergabung</strong>.<br>" in polos
        assert "<em>kedua</em>" in polos
        assert "<h2>Agenda</h2>" in polos
        assert re.search(r"<ul>\s*<li>satu</li>\s*<li>dua</li>\s*</ul>", polos)
        assert re.search(r'<ol [^>]*start="3"', html)
        assert "<blockquote>" in polos and "<code>kode</code>" in polos
        assert "**" not in html and "##" not in html

    def test_tiap_elemen_bergaya_inline_dan_blok_terakhir_tanpa_jarak(self):
        html = html_email_dari_markdown("satu\n\ndua")
        paragraf = re.findall(r'<p style="([^"]+)">', html)
        assert len(paragraf) == 2
        assert "font-family:" in paragraf[0] and not paragraf[0].endswith("margin-bottom:0;")
        assert paragraf[1].endswith("margin-bottom:0;")

    def test_html_mentah_di_escape(self):
        html = html_email_dari_markdown(
            '<script>alert(1)</script>\n\n<img src=x onerror="alert(1)"> <a href="https://jahat.id">x</a>'
        )
        assert "<script" not in html and "<img" not in html and 'href="https://jahat.id">x</a>' not in html
        assert "&lt;script&gt;" in html and "&lt;img src=x" in html

    @pytest.mark.parametrize(
        "alamat", ["javascript:alert(1)", "JavaScript:alert(1)", "data:text/html,x", "ftp://a.id/x", "/relatif", ""]
    )
    def test_skema_selain_http_dan_mailto_tidak_jadi_tautan(self, alamat):
        html = html_email_dari_markdown(f"[klik]({alamat})")
        assert "<a" not in html and "klik" in html

    def test_tautan_yang_boleh(self):
        html = html_email_dari_markdown(
            "[@Budi](https://x.id/ws/profile/1) [surel](mailto:a@x.id) http://x.id/a_b. dan <https://y.id>"
        )
        assert re.findall(r'href="([^"]+)"', html) == [
            "https://x.id/ws/profile/1",
            "mailto:a@x.id",
            "http://x.id/a_b",
            "https://y.id",
        ]
        assert ">@Budi</a>" in html and "</a>. dan " in html

    def test_alamat_di_dalam_kode_dan_label_tautan_tidak_ditautkan_lagi(self):
        html = html_email_dari_markdown("`http://a.id`\n\n```\nhttp://b.id\n```\n\n[http://c.id](https://c.id)")
        assert re.findall(r'href="([^"]+)"', html) == ["https://c.id"]

    def test_alamat_dengan_garis_bawah_atau_diapit_penanda_tetap_utuh(self):
        html = html_email_dari_markdown("https://x.id/__init__.py **https://x.id/a** (https://x.id/b), selesai")
        assert re.findall(r'href="([^"]+)"', html) == [
            "https://x.id/__init__.py",
            "https://x.id/a",
            "https://x.id/b",
        ]
        assert "<strong>" in html

    def test_gambar_tidak_dimuat(self):
        html = html_email_dari_markdown("![denah](https://x.id/d.png)")
        assert "<img" not in html and "denah" in html

    def test_tabel_dan_blok_kode(self):
        html = html_email_dari_markdown("| a |\n| - |\n| <b> |\n\n```\n<i>\n```")
        polos = _tanpa_atribut(html)
        assert "<th>a</th>" in polos and "<td>&lt;b&gt;</td>" in polos and "<pre>&lt;i&gt;</pre>" in polos

    def test_kosong(self):
        assert html_email_dari_markdown("") == "" and html_email_dari_markdown(None) == ""
