# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pratinjau tautan & turunan konten (KEP-88)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi kartu pratinjau dari HTML, cache-nya, dan tautan/gambar yang dipetik dari teks."""

from unittest import mock

import pytest

from plane.utils import pratinjau_tautan
from plane.utils.pratinjau_tautan import UrlTidakValid, pratinjau, rapikan_url, urai_html
from plane.utils.turunan_konten import aset_dari_html, tautan_dari_html

URL = "https://example.com/post"


@pytest.mark.unit
class TestRapikanUrl:
    @pytest.mark.parametrize("url", ["", None, "javascript:alert(1)", "ftp://a.com/x", "https://", "x" * 3000])
    def test_rejects(self, url):
        with pytest.raises(UrlTidakValid):
            rapikan_url(url)

    def test_strips_whitespace(self):
        assert rapikan_url("  https://a.com/x ") == "https://a.com/x"


@pytest.mark.unit
class TestUraiHtml:
    def test_prefers_open_graph(self):
        html = """<html><head><title>Fallback</title>
            <meta property="og:title" content="OG  Title">
            <meta property="og:description" content="Desc">
            <meta property="og:site_name" content="Example">
            <meta property="og:image" content="/img.png">
            <link rel="icon" href="/fav.png"></head></html>"""
        kartu = urai_html(html, URL)
        assert kartu["title"] == "OG Title"
        assert kartu["description"] == "Desc"
        assert kartu["site_name"] == "Example"
        assert kartu["image"] == "https://example.com/img.png"
        assert kartu["favicon"] == "https://example.com/fav.png"

    def test_falls_back_to_title_tag_meta_description_and_hostname(self):
        html = '<html><head><title> Plain </title><meta name="description" content="D"></head></html>'
        kartu = urai_html(html, URL)
        assert kartu["title"] == "Plain"
        assert kartu["description"] == "D"
        assert kartu["site_name"] == "example.com"
        assert kartu["image"] is None
        assert kartu["favicon"] == "https://example.com/favicon.ico"

    def test_resolves_against_final_url_after_redirect(self):
        html = '<meta property="og:image" content="a.png">'
        assert urai_html(html, URL, "https://other.com/dir/page")["image"] == "https://other.com/dir/a.png"

    def test_truncates_long_text(self):
        kartu = urai_html(f'<meta property="og:description" content="{"a" * 1000}">', URL)
        assert len(kartu["description"]) == pratinjau_tautan.MAKS_DESKRIPSI

    def test_ignores_javascript_favicon(self):
        kartu = urai_html('<link rel="icon" href="javascript:alert(1)">', URL)
        assert kartu["favicon"] == "https://example.com/favicon.ico"


@pytest.mark.unit
class TestPratinjauCache:
    def test_fetch_failure_gives_empty_card_and_is_cached(self):
        with (
            mock.patch.object(pratinjau_tautan, "safe_get", side_effect=ValueError("private")) as ambil,
            mock.patch.object(pratinjau_tautan, "cache") as cache,
        ):
            cache.get.return_value = None
            kartu = pratinjau("https://10.0.0.1.nip.io/")
        assert kartu["kosong"] is True
        assert ambil.call_count == 1
        cache.set.assert_called_once()
        assert cache.set.call_args.args[2] == pratinjau_tautan.CACHE_GAGAL_DETIK

    def test_cached_value_skips_network(self):
        with (
            mock.patch.object(pratinjau_tautan, "safe_get") as ambil,
            mock.patch.object(pratinjau_tautan, "cache") as cache,
        ):
            cache.get.return_value = {"url": URL, "title": "T"}
            assert pratinjau(URL)["title"] == "T"
        ambil.assert_not_called()

    def test_non_html_response_is_empty(self):
        respons = mock.Mock(status_code=200, headers={"content-type": "application/pdf"}, content=b"%PDF")
        with (
            mock.patch.object(pratinjau_tautan, "safe_get", return_value=(respons, URL)),
            mock.patch.object(pratinjau_tautan, "cache") as cache,
        ):
            cache.get.return_value = None
            assert pratinjau(URL)["kosong"] is True

    def test_html_response_is_parsed(self):
        respons = mock.Mock(
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            content=b'<meta property="og:title" content="Hello">',
        )
        with (
            mock.patch.object(pratinjau_tautan, "safe_get", return_value=(respons, URL)),
            mock.patch.object(pratinjau_tautan, "cache") as cache,
        ):
            cache.get.return_value = None
            kartu = pratinjau(URL)
        assert kartu["title"] == "Hello"
        assert kartu["kosong"] is False
        assert cache.set.call_args.args[2] == pratinjau_tautan.CACHE_BERHASIL_DETIK


@pytest.mark.unit
class TestTurunanKonten:
    def test_links_keep_order_skip_duplicates_and_non_http(self):
        html = (
            '<p><a href="https://b.com">b</a> <a href="mailto:x@y.z">m</a>'
            '<a href="javascript:alert(1)">j</a><a href="https://a.com/x">a</a><a href="https://b.com">b2</a></p>'
        )
        assert tautan_dari_html(html) == ["https://b.com", "https://a.com/x"]

    def test_plain_urls_in_text_are_detected(self):
        html = (
            "<p>lihat https://a.com/x. Lalu (https://b.com/p_(1)) dan https://a.com/x lagi,"
            ' <a href="https://c.com">https://c.com</a> <code>https://skip.me</code></p>'
            "<p>ftp://nope.com dan https://d.com/q?x=1&amp;y=2!</p>"
        )
        assert tautan_dari_html(html) == [
            "https://a.com/x",
            "https://b.com/p_(1)",
            "https://c.com",
            "https://d.com/q?x=1&y=2",
        ]

    @pytest.mark.parametrize("html", [None, "", "<p></p>"])
    def test_empty_html(self, html):
        assert tautan_dari_html(html) == []
        assert aset_dari_html(html) == []

    def test_asset_ids_from_image_component_and_img(self):
        a = "0b0e6c1d-1a2b-4c3d-8e9f-0123456789ab"
        b = "1b0e6c1d-1a2b-4c3d-8e9f-0123456789ab"
        html = (
            f'<image-component src="{a}" width="100"></image-component>'
            f'<img src="/api/assets/v2/workspaces/w/projects/p/{b.upper()}/">'
            f'<image-component src="{a}"></image-component><img src="https://cdn.com/x.png">'
        )
        assert aset_dari_html(html) == [a, b]
