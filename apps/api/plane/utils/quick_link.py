# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: judul & favicon otomatis quick link (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Judul & ikon quick link, plus siapa yang melihat quick link bersama.

Tampilan satu link (dihitung di web, aturannya di sini supaya satu sumber):

    judul = title (manual) -> metadata.title (dari situs) -> url
    ikon  = metadata.logo_props (emoji, ikon, atau gambar dari URL yang diunduh server) -> metadata.favicon (dari situs)
            -> metadata.logo_cadangan (ikon bawaan saat dibuat, mis. link impor portal)

"Pakai bawaan lagi" = kosongkan `title` dan kirim `logo_props: null`. Nilai otomatis
tidak pernah ditimpa oleh nilai manual, jadi selalu bisa kembali.

Semua pengambilan lewat `safe_get` milik upstream (IP dipatok & divalidasi tiap
hop), jadi URL buatan pengguna tidak bisa dipakai menembak jaringan internal.
"""

# Python imports
import base64
import logging
import re
import time
from typing import Any
from urllib.parse import urljoin, urlsplit

# Django imports
from django.utils import timezone

# Module imports
from plane.bgtasks.work_item_link_task import crawl_work_item_link_title_and_favicon, safe_get
from plane.utils.url_security import pinned_fetch

logger = logging.getLogger("plane.worker")

# Ikon disimpan sebagai data URI di JSON baris itu dan ikut di setiap respons daftar,
# jadi dibatasi. Favicon nyata jarang di atas 50 KB.
MAKS_BYTE_IKON = 200 * 1024
MAKS_JUDUL = 255
# Gambar pratinjau (og:image) ikut disimpan sebagai data URI di JSON baris, jadi
# dibatasi: lebih besar = tanpa pratinjau, dan kartu jatuh ke favicon.
MAKS_BYTE_PRATINJAU = 150 * 1024
KUNCI_DIAMBIL = "diambil_pada"
KUNCI_PRATINJAU = "og_image"
_HEADER = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
}


_TIDAK_DISENTUH: Any = object()
_NAMA_IKON = re.compile(r"^[a-z0-9_]{1,64}$")
_WARNA = re.compile(r"^#[0-9a-fA-F]{3,8}$")
MAKS_EMOJI = 32
MAKS_URL_EMOJI = 500
MAKS_URL_GAMBAR = 2000
# Gambar ikon dari URL pengguna: sama dengan batas pratinjau, karena ikut disimpan
# sebagai data URI di JSON baris. Tanpa Pillow di image API, jadi yang lebih besar
# ditolak, bukan dikecilkan.
MAKS_BYTE_GAMBAR = MAKS_BYTE_PRATINJAU
MAKS_REDIRECT_GAMBAR = 3
# `timeout` requests berlaku per pembacaan soket, jadi server yang menetes 1 byte tiap
# 4 detik bisa menahan worker tanpa batas. Batas total ini mencakup semua hop dan badan.
MAKS_DETIK_GAMBAR = 8
_DETIK_PER_HOP = 5
_REDIRECT = {301, 302, 303, 307, 308}
_PESAN_LOGO = "Pick an icon from the list."
_PESAN_GAMBAR = "Use a public https link to a PNG, JPEG, WebP or GIF image under 150 KB."
_DATA_GAMBAR = re.compile(r"^data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/]+={0,2})$")


class LogoTidakValid(ValueError):
    """`logo_props` tidak sesuai bentuk TLogoProps yang dikenal."""


def _jenis_dari_isi(isi: bytes) -> str | None:
    """Jenis gambar dari byte pertamanya, bukan dari header server (bisa berbohong)."""
    if isi.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if isi.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if isi[:4] == b"RIFF" and isi[8:12] == b"WEBP":
        return "image/webp"
    if isi[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return None


def _punya_userinfo(url: str) -> bool:
    try:
        return "@" in urlsplit(url).netloc
    except ValueError:
        return True


def _url_untuk_log(url: str) -> str:
    """URL tanpa userinfo dan query, supaya kredensial tidak masuk log."""
    try:
        bagian = urlsplit(url)
        host = bagian.hostname or ""
        port = f":{bagian.port}" if bagian.port else ""
        return f"{bagian.scheme}://{host}{port}{bagian.path}"
    except ValueError:
        return "<url tidak valid>"


def _url_gambar_aman(url: Any) -> str:
    if (
        not isinstance(url, str)
        or len(url) > MAKS_URL_GAMBAR
        or not url.startswith("https://")
        or _punya_userinfo(url)
    ):
        raise LogoTidakValid(_PESAN_GAMBAR)
    return url


def _ambil_gambar(url: str, batas: float):
    """Ikuti redirect manual: tiap hop harus https tanpa userinfo dan masih dalam batas waktu."""
    sekarang_url = url
    for hop in range(MAKS_REDIRECT_GAMBAR + 1):
        sisa = batas - time.monotonic()
        if sisa <= 0:
            raise TimeoutError("batas waktu total terlampaui")
        response = pinned_fetch(
            "GET", sekarang_url, headers=_HEADER, timeout=min(_DETIK_PER_HOP, sisa), stream=True
        )
        lokasi = response.headers.get("Location")
        if response.status_code not in _REDIRECT or not lokasi:
            return response
        response.close()
        if hop >= MAKS_REDIRECT_GAMBAR:
            break
        sekarang_url = urljoin(sekarang_url, lokasi)
        if not sekarang_url.startswith("https://") or _punya_userinfo(sekarang_url):
            raise ValueError("redirect ke URL yang bukan https")
    raise ValueError("terlalu banyak redirect")


def _unduh_gambar(url: str) -> str:
    """Unduh gambar ikon jadi data URI. Hanya raster; SVG dan jenis lain ditolak.

    Lewat pengambil yang sama dengan favicon (IP dipatok dan divalidasi tiap hop, jadi
    host privat, loopback, link-local, dan redirect ke sana ditolak). Badan dibaca
    bertahap supaya batas ukuran benar-benar membatasi memori.
    """
    batas = time.monotonic() + MAKS_DETIK_GAMBAR
    try:
        response = _ambil_gambar(url, batas)
    except Exception as e:  # noqa: BLE001 - host pihak luar; ValueError = host terlarang
        logger.warning("Gambar ikon quick link gagal diambil %s: %s", _url_untuk_log(url), e)
        raise LogoTidakValid(_PESAN_GAMBAR) from e
    try:
        if response.status_code != 200:
            raise LogoTidakValid(_PESAN_GAMBAR)
        panjang = response.headers.get("content-length")
        if panjang and panjang.isdigit() and int(panjang) > MAKS_BYTE_GAMBAR:
            raise LogoTidakValid(_PESAN_GAMBAR)
        isi = bytearray()
        for potongan in response.iter_content(chunk_size=16 * 1024):
            isi.extend(potongan)
            if len(isi) > MAKS_BYTE_GAMBAR or time.monotonic() > batas:
                raise LogoTidakValid(_PESAN_GAMBAR)
    except LogoTidakValid:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("Gambar ikon quick link gagal dibaca %s: %s", _url_untuk_log(url), e)
        raise LogoTidakValid(_PESAN_GAMBAR) from e
    finally:
        response.close()
    jenis = _jenis_dari_isi(bytes(isi))
    if jenis is None:
        raise LogoTidakValid(_PESAN_GAMBAR)
    return f"data:{jenis};base64,{base64.b64encode(bytes(isi)).decode('ascii')}"


def _data_gambar_valid(data: Any) -> str:
    """Data URI gambar yang sudah tersimpan (dikirim balik saat edit): periksa ulang, jangan percaya."""
    if not isinstance(data, str) or len(data) > MAKS_BYTE_GAMBAR * 4 // 3 + 100:
        raise LogoTidakValid(_PESAN_GAMBAR)
    cocok = _DATA_GAMBAR.fullmatch(data)
    if cocok is None:
        raise LogoTidakValid(_PESAN_GAMBAR)
    try:
        isi = base64.b64decode(cocok.group(2), validate=True)
    except ValueError as e:
        raise LogoTidakValid(_PESAN_GAMBAR) from e
    if len(isi) > MAKS_BYTE_GAMBAR or _jenis_dari_isi(isi) != cocok.group(1):
        raise LogoTidakValid(_PESAN_GAMBAR)
    return data


def rapikan_logo(nilai: Any) -> dict[str, Any] | None:
    """Rapikan `logo_props` kiriman klien. None / {} = hapus; selain itu lempar `LogoTidakValid`.

    Hanya kunci yang dikenal yang disimpan, sisanya dibuang.
    """
    if nilai is None or nilai == {}:
        return None
    if not isinstance(nilai, dict):
        raise LogoTidakValid(_PESAN_LOGO)
    pakai = nilai.get("in_use")
    if pakai == "emoji":
        emoji = nilai.get("emoji")
        if not isinstance(emoji, dict):
            raise LogoTidakValid(_PESAN_LOGO)
        value = emoji.get("value")
        if not isinstance(value, str) or not value or len(value) > MAKS_EMOJI:
            raise LogoTidakValid(_PESAN_LOGO)
        bersih: dict[str, Any] = {"value": value}
        url = emoji.get("url")
        if url is not None:
            if (
                not isinstance(url, str)
                or len(url) > MAKS_URL_EMOJI
                or not url.startswith(("https://", "data:image/"))
            ):
                raise LogoTidakValid(_PESAN_LOGO)
            bersih["url"] = url
        return {"in_use": "emoji", "emoji": bersih}
    if pakai == "image":
        gambar = nilai.get("image")
        if not isinstance(gambar, dict):
            raise LogoTidakValid(_PESAN_GAMBAR)
        url = gambar.get("url")
        if gambar.get("data") is not None:
            # Sudah diunduh sebelumnya: periksa ulang isinya, tanpa mengunduh lagi.
            hasil: dict[str, Any] = {"data": _data_gambar_valid(gambar["data"])}
            if url is not None:
                hasil["url"] = _url_gambar_aman(url)
            return {"in_use": "image", "image": hasil}
        url = _url_gambar_aman(url)
        return {"in_use": "image", "image": {"url": url, "data": _unduh_gambar(url)}}
    if pakai == "icon":
        ikon = nilai.get("icon")
        if not isinstance(ikon, dict):
            raise LogoTidakValid(_PESAN_LOGO)
        nama = ikon.get("name")
        if not isinstance(nama, str) or not _NAMA_IKON.fullmatch(nama):
            raise LogoTidakValid(_PESAN_LOGO)
        bersih = {"name": nama}
        for kunci in ("color", "background_color"):
            warna = ikon.get(kunci)
            if warna is None:
                continue
            if not isinstance(warna, str) or not _WARNA.fullmatch(warna):
                raise LogoTidakValid(_PESAN_LOGO)
            bersih[kunci] = warna
        return {"in_use": "icon", "icon": bersih}
    raise LogoTidakValid(_PESAN_LOGO)


def _rapikan_judul(judul: str | None) -> str | None:
    if not judul:
        return None
    rapi = re.sub(r"\s+", " ", judul).strip()
    return rapi[:MAKS_JUDUL] or None


def _favicon_layak(favicon: str | None, favicon_url: str | None) -> str | None:
    """Favicon upstream jatuh ke SVG garis `currentColor` saat situs tak punya ikon.

    Sebagai <img> itu tampil hitam, lebih jelek dari ikon bawaan web, jadi dibuang.
    Data URI di atas batas juga dibuang (base64 ~ 4/3 ukuran asli).
    """
    if not favicon or not favicon_url or not favicon.startswith("data:image/"):
        return None
    if len(favicon) > MAKS_BYTE_IKON * 4 // 3 + 100:
        return None
    return favicon


def ambil_pratinjau(url_gambar: str | None) -> str | None:
    """Unduh gambar pratinjau jadi data URI. Tidak pernah melempar: gagal = None."""
    if not url_gambar or not url_gambar.startswith(("http://", "https://")):
        return None
    try:
        response, _ = safe_get(url_gambar, headers=_HEADER, timeout=5)
    except Exception as e:  # noqa: BLE001 - situs pihak luar
        logger.warning("Gambar pratinjau quick link gagal diambil %s: %s", _url_untuk_log(url_gambar), e)
        return None
    jenis = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
    # SVG dilewati: favicon sudah jadi cadangan dan isinya tak bisa dijamin.
    if response.status_code != 200 or not jenis.startswith("image/") or jenis == "image/svg+xml":
        return None
    if not response.content or len(response.content) > MAKS_BYTE_PRATINJAU:
        return None
    return f"data:{jenis};base64,{base64.b64encode(response.content).decode('ascii')}"


def ambil_dari_situs(url: str) -> dict[str, Any]:
    """Judul & favicon situs. Tidak pernah melempar: situs mati = nilai kosong."""
    try:
        hasil = crawl_work_item_link_title_and_favicon(url) or {}
    except Exception as e:  # noqa: BLE001 - situs pihak luar, kegagalan apa pun = tanpa metadata
        logger.warning("Quick link metadata gagal diambil untuk %s: %s", _url_untuk_log(url), e)
        hasil = {}
    return {
        "title": _rapikan_judul(hasil.get("title")),
        "favicon": _favicon_layak(hasil.get("favicon"), hasil.get("favicon_url")),
        "favicon_url": hasil.get("favicon_url"),
        # Selalu ada (None kalau situs tak punya), supaya `perlu_diisi` tidak mengulang.
        KUNCI_PRATINJAU: ambil_pratinjau(hasil.get("og_image_url")),
        KUNCI_DIAMBIL: timezone.now().isoformat(),
    }


def metadata_baru(
    metadata: dict[str, Any] | None,
    url: str,
    *,
    url_berubah: bool,
    logo_props: Any = _TIDAK_DISENTUH,
) -> dict[str, Any]:
    """Metadata baru (salinan) sesudah URL dan/atau ikon pilihan berubah.

    `logo_props`: tidak diberikan = tidak disentuh, None / {} = hapus (tampil favicon
    situs), objek = disimpan di `metadata["logo_props"]` setelah dirapikan.
    Melempar `LogoTidakValid` kalau bentuknya salah, sebelum ada yang diambil dari situs.
    Sisa `ikon_kustom*` dari versi lama ikut dibuang pada setiap tulis.
    """
    hasil = dict(metadata or {})
    ubah_logo = logo_props is not _TIDAK_DISENTUH
    bersih = rapikan_logo(logo_props) if ubah_logo else None
    if url_berubah or perlu_diisi(hasil):
        hasil.update(ambil_dari_situs(url))
    if ubah_logo:
        if bersih is None:
            hasil.pop("logo_props", None)
        else:
            hasil["logo_props"] = bersih
    hasil.pop("ikon_kustom", None)
    hasil.pop("ikon_kustom_url", None)
    return hasil


def perlu_diisi(metadata: dict[str, Any] | None) -> bool:
    """Link yang belum pernah diambil judul, ikon, atau gambar pratinjaunya.

    Link dari sebelum pratinjau ada punya `diambil_pada` tapi tanpa kunci `og_image`,
    jadi terisi pada pemuatan daftar berikutnya.
    """
    isi = metadata or {}
    return KUNCI_DIAMBIL not in isi or KUNCI_PRATINJAU not in isi


def isi_metadata_lama(jenis: str, links) -> None:
    """Antrekan pengisian judul & favicon untuk link yang belum pernah diambil.

    Broker mati tidak boleh membuat daftar quick link gagal dimuat: link tetap tampil
    dengan ikon bawaan, dan dicoba lagi pada pemuatan berikutnya.
    """
    from plane.bgtasks.quick_link_task import isi_metadata_quick_link  # noqa: PLC0415

    ids = [str(link.id) for link in links if perlu_diisi(link.metadata)]
    if not ids:
        return
    try:
        isi_metadata_quick_link.delay(jenis, ids)
    except Exception as e:  # noqa: BLE001
        logger.warning("Antrean metadata quick link gagal: %s", e)


def boleh_kelola_bersama(user, workspace_id) -> bool:
    """Super Admin atau admin workspace (role 20) boleh mengatur quick link bersama.

    God Mode (QUICK_LINK_SHARED_MANAGERS) bisa menambah jenjang di atas itu; bawaannya hanya admin.
    """
    from plane.db.models import WorkspaceMember  # noqa: PLC0415
    from plane.db.superadmin import is_super_admin  # noqa: PLC0415
    from plane.utils import aturan  # noqa: PLC0415
    from plane.utils.aturan.area_obrolan import QUICK_LINK_SHARED_MANAGERS  # noqa: PLC0415
    from plane.utils.jenjang_aturan import lolos_jenjang  # noqa: PLC0415

    if is_super_admin(user):
        return True
    if WorkspaceMember.objects.filter(workspace_id=workspace_id, member=user, role=20, is_active=True).exists():
        return True
    return lolos_jenjang(user, workspace_id, aturan.get_choice(QUICK_LINK_SHARED_MANAGERS), admin=False)


def sasaran_pengguna(user_id, workspace_id) -> tuple[set, set]:
    """(departemen_ids, divisi_ids) yang dicakup penempatan orang ini.

    Staf/supervisor di departemen X juga masuk divisi induk X. Manager divisi Y juga
    melihat link untuk setiap departemen di Y (ia memimpin mereka). Direktur tanpa
    penempatan hanya melihat link untuk semua orang.
    """
    from plane.db.models import Departemen  # noqa: PLC0415
    from plane.utils.hierarki import penempatan_semua  # noqa: PLC0415

    baris = penempatan_semua(user_id, workspace_id)
    departemen_ids = {dep for _, dep, _ in baris if dep}
    divisi_ids = {div for _, _, div in baris if div}
    if departemen_ids:
        divisi_ids |= set(Departemen.objects.filter(id__in=departemen_ids).values_list("divisi_id", flat=True))
    if divisi_ids:
        departemen_ids |= set(Departemen.objects.filter(divisi_id__in=divisi_ids).values_list("id", flat=True))
    return departemen_ids, divisi_ids


def berlaku_untuk(link, departemen_ids: set, divisi_ids: set) -> bool:
    """Link bersama ini tampil untuk orang dengan sasaran tersebut?

    Butuh `prefetch_related("departemen", "divisi")` supaya tidak N+1.
    """
    from plane.db.models import CAKUPAN_QUICK_LINK_SEMUA  # noqa: PLC0415

    if link.cakupan == CAKUPAN_QUICK_LINK_SEMUA:
        return True
    return any(d.id in departemen_ids for d in link.departemen.all()) or any(
        v.id in divisi_ids for v in link.divisi.all()
    )
