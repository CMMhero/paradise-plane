# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: gambar pratinjau quick link (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""og:image: pemilihan alamat dari HTML dan pengambilan jadi data URI."""

from unittest import mock

import pytest
from bs4 import BeautifulSoup

from plane.bgtasks.work_item_link_task import find_og_image_url
from plane.utils import quick_link
from plane.utils.quick_link import MAKS_BYTE_PRATINJAU, ambil_pratinjau, perlu_diisi

BASE = "https://example.com/blog/post"


def _soup(head: str) -> BeautifulSoup:
    return BeautifulSoup(f"<html><head>{head}</head></html>", "html.parser")


@pytest.mark.unit
class TestFindOgImageUrl:
    def test_reads_og_image(self):
        soup = _soup('<meta property="og:image" content="https://cdn.example.com/a.png">')
        assert find_og_image_url(soup, BASE) == "https://cdn.example.com/a.png"

    def test_resolves_relative_path_against_page(self):
        assert find_og_image_url(_soup('<meta property="og:image" content="/img/a.png">'), BASE) == (
            "https://example.com/img/a.png"
        )
        assert find_og_image_url(_soup('<meta property="og:image" content="a.png">'), BASE) == (
            "https://example.com/blog/a.png"
        )

    def test_resolves_protocol_relative(self):
        soup = _soup('<meta property="og:image" content="//cdn.example.com/a.png">')
        assert find_og_image_url(soup, BASE) == "https://cdn.example.com/a.png"

    def test_falls_back_to_twitter_image(self):
        assert find_og_image_url(_soup('<meta name="twitter:image" content="/t.png">'), BASE) == (
            "https://example.com/t.png"
        )

    def test_og_wins_over_twitter(self):
        soup = _soup('<meta name="twitter:image" content="/t.png"><meta property="og:image" content="/o.png">')
        assert find_og_image_url(soup, BASE) == "https://example.com/o.png"

    def test_skips_empty_and_uses_next_candidate(self):
        soup = _soup('<meta property="og:image" content="  "><meta name="twitter:image" content="/t.png">')
        assert find_og_image_url(soup, BASE) == "https://example.com/t.png"

    @pytest.mark.parametrize(
        "content",
        ["data:image/png;base64,AAAA", "javascript:alert(1)", "file:///etc/passwd", "ftp://example.com/a.png"],
    )
    def test_rejects_non_http_schemes(self, content):
        assert find_og_image_url(_soup(f'<meta property="og:image" content="{content}">'), BASE) is None

    def test_none_when_absent_or_no_soup(self):
        assert find_og_image_url(_soup("<title>x</title>"), BASE) is None
        assert find_og_image_url(None, BASE) is None


def _response(body=b"\x89PNG", content_type="image/png", status=200):
    return mock.Mock(content=body, status_code=status, headers={"content-type": content_type})


@pytest.mark.unit
class TestAmbilPratinjau:
    def test_returns_data_uri(self):
        with mock.patch.object(quick_link, "safe_get", return_value=(_response(), "u")):
            assert ambil_pratinjau("https://cdn.example.com/a.png").startswith("data:image/png;base64,")

    def test_none_without_address_or_bad_scheme(self):
        with mock.patch.object(quick_link, "safe_get") as get:
            assert ambil_pratinjau(None) is None
            assert ambil_pratinjau("data:image/png;base64,AAAA") is None
            get.assert_not_called()

    @pytest.mark.parametrize(
        "response",
        [
            _response(content_type="text/html"),
            _response(content_type="image/svg+xml"),
            _response(status=404),
            _response(body=b""),
            _response(body=b"x" * (MAKS_BYTE_PRATINJAU + 1)),
        ],
    )
    def test_rejects_unusable_responses(self, response):
        with mock.patch.object(quick_link, "safe_get", return_value=(response, "u")):
            assert ambil_pratinjau("https://cdn.example.com/a") is None

    def test_network_failure_is_none(self):
        with mock.patch.object(quick_link, "safe_get", side_effect=ValueError("blocked")):
            assert ambil_pratinjau("https://internal.example/a.png") is None


@pytest.mark.unit
def test_perlu_diisi_refetches_links_stored_before_preview_existed():
    assert perlu_diisi({}) is True
    assert perlu_diisi({"diambil_pada": "2026-11-01"}) is True
    assert perlu_diisi({"diambil_pada": "2026-11-01", "og_image": None}) is False


@pytest.mark.unit
class TestRapikanLogo:
    def test_kosong_berarti_hapus(self):
        assert quick_link.rapikan_logo(None) is None
        assert quick_link.rapikan_logo({}) is None

    def test_ikon_menyimpan_kunci_dikenal_saja(self):
        nilai = {
            "in_use": "icon",
            "icon": {"name": "star_2", "color": "#fff", "background_color": "#1234abcd", "x": 1},
            "emoji": {"value": "1"},
            "lain": True,
        }
        assert quick_link.rapikan_logo(nilai) == {
            "in_use": "icon",
            "icon": {"name": "star_2", "color": "#fff", "background_color": "#1234abcd"},
        }

    def test_emoji_dengan_url(self):
        nilai = {"in_use": "emoji", "emoji": {"value": "1f600-1f3fb", "url": "https://x/y.png"}}
        assert quick_link.rapikan_logo(nilai) == nilai

    @pytest.mark.parametrize(
        "nilai",
        [
            "star",
            [],
            {"in_use": "other"},
            {"in_use": "emoji"},
            {"in_use": "emoji", "emoji": {"value": ""}},
            {"in_use": "emoji", "emoji": {"value": 5}},
            {"in_use": "emoji", "emoji": {"value": "x" * 33}},
            {"in_use": "emoji", "emoji": {"value": "1", "url": "u" * 501}},
            {"in_use": "icon", "icon": {}},
            {"in_use": "icon", "icon": {"name": "Star"}},
            {"in_use": "icon", "icon": {"name": "a" * 65}},
            {"in_use": "icon", "icon": {"name": "star\n"}},
            {"in_use": "icon", "icon": {"name": "star", "color": "red"}},
            {"in_use": "icon", "icon": {"name": "star", "background_color": 5}},
        ],
    )
    def test_tidak_valid(self, nilai):
        with pytest.raises(quick_link.LogoTidakValid):
            quick_link.rapikan_logo(nilai)

    def test_metadata_baru_sentinel_tidak_menyentuh(self):
        meta = {"diambil_pada": "x", "og_image": None, "logo_props": {"in_use": "emoji", "emoji": {"value": "1"}}}
        assert quick_link.metadata_baru(meta, "https://a.b", url_berubah=False) == meta
        assert "logo_props" not in quick_link.metadata_baru(meta, "https://a.b", url_berubah=False, logo_props=None)
