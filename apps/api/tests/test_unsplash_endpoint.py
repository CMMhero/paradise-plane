# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji jawaban endpoint Unsplash
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Endpoint Unsplash tidak boleh pernah meneruskan status milik Unsplash.

Ini menjaga satu invarian yang pernah menumbangkan aplikasi pada 20 Agustus
2026: kunci Unsplash di instance sudah tidak berlaku, Unsplash menjawab 401,
endpoint ini meneruskannya apa adanya, lalu interceptor di `api.service.ts`
menerjemahkan SETIAP 401 menjadi `window.location.replace` ke layar masuk.
Hasilnya halaman memuat ulang dirinya sendiri tiap beberapa detik dan tidak
pernah selesai terbuka.

Endpoint ini cuma perantara. Kegagalan pihak ketiga bukan kegagalan
autentikasi kita, jadi jawabannya harus tetap 200 dengan daftar kosong, sama
seperti ketika kuncinya memang belum diisi.

Murni, tanpa database, jadi tidak perlu marka `django_db`.
"""

from types import SimpleNamespace

import pytest
import requests

from plane.app.views.external import base as external_base
from plane.app.views.external.base import UnsplashEndpoint

pytestmark = pytest.mark.unit

KUNCI_PALSU = "a" * 43


class _JawabanUnsplash:
    """Tiruan `requests.Response` secukupnya untuk endpoint ini."""

    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Client Error", response=self)

    def json(self):
        return self._payload


@pytest.fixture
def kunci_terpasang(monkeypatch):
    monkeypatch.setattr(external_base, "get_configuration_value", lambda keys: (KUNCI_PALSU,))


def _panggil(monkeypatch, hasil, query=""):
    """Jalankan endpoint dengan `requests.get` yang sudah diganti.

    `hasil` boleh sebuah `_JawabanUnsplash` atau sebuah exception untuk dilempar.
    Mengembalikan `(response, kwargs_yang_diterima_requests_get)`.
    """
    terekam = {}

    def _get_palsu(**kwargs):
        terekam.update(kwargs)
        if isinstance(hasil, Exception):
            raise hasil
        return hasil

    monkeypatch.setattr(external_base.requests, "get", _get_palsu)
    request = SimpleNamespace(GET={"query": query} if query else {})
    return UnsplashEndpoint().get(request), terekam


def test_401_dari_unsplash_tidak_pernah_diteruskan(monkeypatch, kunci_terpasang):
    """Inti perbaikannya. 401 di sini yang membuat halaman berkedip tanpa henti."""
    jawaban, _ = _panggil(
        monkeypatch,
        _JawabanUnsplash(401, {"errors": ["OAuth error: The access token is invalid"]}),
    )

    assert jawaban.status_code == 200
    assert jawaban.data == []


@pytest.mark.parametrize(
    "kegagalan",
    [
        requests.Timeout("terlalu lama"),
        requests.ConnectionError("jaringan mati"),
        ValueError("badan jawaban bukan JSON"),
    ],
    ids=["timeout", "koneksi", "bukan-json"],
)
def test_kegagalan_lain_pun_dijawab_kosong(monkeypatch, kunci_terpasang, kegagalan):
    jawaban, _ = _panggil(monkeypatch, kegagalan)

    assert jawaban.status_code == 200
    assert jawaban.data == []


def test_selalu_pakai_timeout(monkeypatch, kunci_terpasang):
    """Tanpa timeout, satu panggilan Unsplash yang menggantung menahan satu worker."""
    _, terekam = _panggil(monkeypatch, _JawabanUnsplash(200, []))

    assert terekam.get("timeout"), "requests.get dipanggil tanpa timeout"


def test_jawaban_sehat_diteruskan_apa_adanya(monkeypatch, kunci_terpasang):
    foto = [{"id": "abc", "urls": {"small": "https://x/s.jpg", "regular": "https://x/r.jpg"}}]

    jawaban, _ = _panggil(monkeypatch, _JawabanUnsplash(200, foto))

    assert jawaban.status_code == 200
    assert jawaban.data == foto


def test_pencarian_juga_diteruskan(monkeypatch, kunci_terpasang):
    hasil = {"results": [{"id": "abc"}]}

    jawaban, terekam = _panggil(monkeypatch, _JawabanUnsplash(200, hasil), query="gunung")

    assert jawaban.status_code == 200
    assert jawaban.data == hasil
    assert "gunung" in terekam["url"]


def test_tanpa_kunci_tetap_kosong_dan_tidak_memanggil_unsplash(monkeypatch):
    monkeypatch.setattr(external_base, "get_configuration_value", lambda keys: ("",))

    def _jangan_dipanggil(**kwargs):
        raise AssertionError("Unsplash dipanggil walau kuncinya kosong")

    monkeypatch.setattr(external_base.requests, "get", _jangan_dipanggil)

    jawaban = UnsplashEndpoint().get(SimpleNamespace(GET={}))

    assert jawaban.status_code == 200
    assert jawaban.data == []
