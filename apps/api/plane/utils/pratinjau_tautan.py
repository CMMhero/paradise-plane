# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pratinjau tautan Open Graph (KEP-88)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kartu pratinjau tautan (judul, deskripsi, gambar) untuk deskripsi, komentar, dan chat.

Satu fungsi publik: `pratinjau(url)`. Tidak pernah melempar; situs mati, lambat,
atau bukan HTML menghasilkan kartu kosong (`kosong: True`) yang ikut di-cache
supaya situs yang sama tidak diketuk ulang setiap kali kartu dirender.

Pengambilan lewat `safe_get` milik upstream: IP dipatok dan divalidasi di setiap
hop, jadi URL ketikan pengguna tidak bisa dipakai menembak jaringan internal.
Gambar TIDAK diunduh server; yang dikirim cuma alamatnya, peramban memuatnya
sendiri. Mengunduh tiap og:image ke server berarti satu tautan bisa membuat
server menarik berkas besar berulang kali.
"""

# Python imports
import hashlib
import logging
import re
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

# Third party imports
from bs4 import BeautifulSoup

# Django imports
from django.core.cache import cache

# Module imports
from plane.bgtasks.work_item_link_task import find_og_image_url, safe_get

logger = logging.getLogger("plane.worker")

CACHE_BERHASIL_DETIK = 24 * 60 * 60
CACHE_GAGAL_DETIK = 60 * 60
WAKTU_TUNGGU_DETIK = 4
MAKS_PANJANG_URL = 2048
MAKS_JUDUL = 200
MAKS_DESKRIPSI = 300
MAKS_NAMA_SITUS = 80
_HEADER = {
    "User-Agent": "Mozilla/5.0 (compatible; ParadiseLinkPreview/1.0; +https://plane.so)",
    "Accept": "text/html,application/xhtml+xml",
}
_SPASI = re.compile(r"\s+")


class UrlTidakValid(ValueError):
    """URL bukan http(s), terlalu panjang, atau tanpa host."""


def rapikan_url(url: Any) -> str:
    """Validasi bentuk URL. Melempar `UrlTidakValid`; jaringan tidak disentuh di sini."""
    if not isinstance(url, str):
        raise UrlTidakValid("URL is required.")
    url = url.strip()
    if not url or len(url) > MAKS_PANJANG_URL:
        raise UrlTidakValid("URL is too long or empty.")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UrlTidakValid("Only http and https links can be previewed.")
    return url


def _kunci_cache(url: str) -> str:
    return "pratinjau_tautan:" + hashlib.sha256(url.encode("utf-8")).hexdigest()


def _teks(nilai: Optional[str], batas: int) -> Optional[str]:
    if not nilai:
        return None
    rapi = _SPASI.sub(" ", nilai).strip()
    if not rapi:
        return None
    return rapi if len(rapi) <= batas else rapi[: batas - 1].rstrip() + "…"


def _meta(soup: BeautifulSoup, *nama: str) -> Optional[str]:
    """Isi meta pertama yang cocok, lewat `property` maupun `name` (situs memakai keduanya)."""
    for dicari in nama:
        for tag in soup.find_all("meta"):
            kunci = (tag.get("property") or tag.get("name") or "").strip().lower()
            if kunci == dicari and (tag.get("content") or "").strip():
                return tag["content"]
    return None


def _favicon(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    for tag in soup.find_all("link", href=True):
        rel = tag.get("rel") or []
        rel = " ".join(rel).lower() if isinstance(rel, list) else str(rel).lower()
        if "icon" not in rel.split():
            continue
        alamat = urljoin(base_url, tag["href"])
        if urlparse(alamat).scheme in ("http", "https"):
            return alamat
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"


def urai_html(html: bytes | str, url: str, url_akhir: Optional[str] = None) -> dict[str, Any]:
    """Ubah HTML jadi isi kartu. Terpisah dari jaringan supaya bisa diuji langsung."""
    dasar = url_akhir or url
    soup = BeautifulSoup(html, "html.parser")
    judul_tag = soup.find("title")
    judul = _meta(soup, "og:title", "twitter:title") or (judul_tag.get_text() if judul_tag else None)
    deskripsi = _meta(soup, "og:description", "twitter:description", "description")
    nama_situs = _meta(soup, "og:site_name", "application-name") or urlparse(dasar).hostname
    return {
        "url": url,
        "title": _teks(judul, MAKS_JUDUL),
        "description": _teks(deskripsi, MAKS_DESKRIPSI),
        "site_name": _teks(nama_situs, MAKS_NAMA_SITUS),
        "image": find_og_image_url(soup, dasar),
        "favicon": _favicon(soup, dasar),
    }


def _kartu_kosong(url: str) -> dict[str, Any]:
    return {
        "url": url,
        "title": None,
        "description": None,
        "site_name": urlparse(url).hostname,
        "image": None,
        "favicon": None,
        "kosong": True,
    }


def _ambil(url: str) -> dict[str, Any]:
    try:
        response, url_akhir = safe_get(url, headers=_HEADER, timeout=WAKTU_TUNGGU_DETIK)
    except Exception as e:  # noqa: BLE001 - situs pihak luar, kegagalan apa pun = kartu kosong
        logger.info("Pratinjau tautan gagal diambil %s: %s", url, e)
        return _kartu_kosong(url)
    jenis = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    if response.status_code >= 400 or jenis not in ("text/html", "application/xhtml+xml"):
        return _kartu_kosong(url)
    hasil = urai_html(response.content, url, url_akhir)
    hasil["kosong"] = not (hasil["title"] or hasil["description"] or hasil["image"])
    return hasil


def pratinjau(url: str) -> dict[str, Any]:
    """Kartu pratinjau untuk `url` (sudah lewat `rapikan_url`), dari cache bila ada."""
    kunci = _kunci_cache(url)
    tersimpan = cache.get(kunci)
    if tersimpan is not None:
        return tersimpan
    hasil = _ambil(url)
    cache.set(kunci, hasil, CACHE_GAGAL_DETIK if hasil.get("kosong") else CACHE_BERHASIL_DETIK)
    return hasil


def pratinjau_tersimpan(url: str) -> Optional[dict[str, Any]]:
    """Kartu dari cache saja, tanpa menyentuh jaringan (untuk daftar yang harus cepat)."""
    try:
        return cache.get(_kunci_cache(rapikan_url(url)))
    except UrlTidakValid:
        return None
