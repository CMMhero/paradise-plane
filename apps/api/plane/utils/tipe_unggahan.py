# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tipe MIME unggahan yang toleran
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Merapikan tipe MIME yang disebut klien saat meminta URL presigned.

Kenapa ada. Tipe yang dikirim peramban (`File.type`) diisi dari registri sistem
operasi, jadi berkas yang sama bisa bertipe kosong di satu komputer dan terisi
di komputer lain (.md, .csv, .mkv, .7z, .log). Dulu yang kosong ditolak "Invalid file type" di titik unggah
lampiran, sehingga orang yang sama kadang bisa melampirkan dan kadang tidak,
tergantung mesin dan berkasnya. Klien sudah memperbaikinya sendiri
(`resolveFileMimeType` di packages/constants), tapi bundel web yang tersimpan di
service worker masih mengirim tipe lama sesudah deploy, jadi server ikut
bersikap toleran.

Aturannya: tipe yang sudah sah dipakai apa adanya. Kalau KOSONG (atau generik
`application/octet-stream`), ditebak dari ekstensi; kalau tebakannya tidak ada,
pakai `application/octet-stream` bila diizinkan untuk entitas itu. Tipe yang
disebut klien dan tidak dikenal (mis. `application/x-msdownload`) TIDAK diubah
jadi sah: itu penolakan yang disengaja (lihat tes Wiki), dan pemanggil menolaknya.
Entitas yang hanya menerima gambar tidak punya `application/octet-stream`,
jadi tipe kosong dengan ekstensi bukan gambar tetap ditolak.

Daftar tipe lampiran (`TIPE_LAMPIRAN`, dulu settings.ATTACHMENT_MIME_TYPES)
tinggal di sini karena registri aturan God Mode membutuhkannya sebagai pilihan
UPLOAD_BLOCKED_FILE_TYPES, dan berkas area aturan tidak boleh memuat Django.
God Mode hanya bisa MENCORET tipe dari daftar ini, tidak pernah menambah.
"""

import mimetypes
import posixpath

from django.conf import settings

OCTET_STREAM = "application/octet-stream"

# Plafon tipe lampiran (Wiki, Obrolan, isi halaman, lampiran task, API publik).
# Kembar di daftar lama (text/markdown, x-compressed-tar-zip) dibuang: isinya sama.
TIPE_LAMPIRAN = (
    # Images
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/svg+xml",
    "image/webp",
    "image/tiff",
    "image/bmp",
    # Documents
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "text/markdown",
    "application/rtf",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.presentation",
    "application/vnd.oasis.opendocument.graphics",
    # Microsoft Visio
    "application/vnd.visio",
    # Netpbm format
    "image/x-portable-graymap",
    "image/x-portable-bitmap",
    "image/x-portable-pixmap",
    # Open Office Base
    "application/vnd.oasis.opendocument.database",
    # Audio
    "audio/mpeg",
    "audio/wav",
    "audio/ogg",
    "audio/midi",
    "audio/x-midi",
    "audio/aac",
    "audio/flac",
    "audio/x-m4a",
    # Video
    "video/mp4",
    "video/mpeg",
    "video/ogg",
    "video/webm",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-ms-wmv",
    # Keluaran bawaan OBS. Peramban tidak bisa memutarnya, jadi ia sengaja
    # TIDAK diberi pemutar sebaris di editor dan jatuh ke kartu unduh. Tetap
    # diterima karena pemilik instance meminta semua tipe berkas boleh masuk,
    # dan menolaknya di server berarti orang kehilangan rekamannya, bukan
    # sekadar kehilangan pratinjaunya.
    "video/x-matroska",
    # Archives
    "application/zip",
    "application/x-rar",
    "application/x-rar-compressed",
    "application/x-tar",
    "application/gzip",
    "application/x-zip",
    "application/x-zip-compressed",
    "application/x-7z-compressed",
    "application/x-compressed",
    "application/x-compressed-tar",
    "application/x-compressed-tar-gz",
    "application/x-compressed-tar-bz2",
    "application/x-compressed-tar-zip",
    "application/x-compressed-tar-7z",
    "application/x-compressed-tar-rar",
    # 3D Models
    "model/gltf-binary",
    "model/gltf+json",
    OCTET_STREAM,  # for .obj files, but be cautious
    # Fonts
    "font/ttf",
    "font/otf",
    "font/woff",
    "font/woff2",
    # Other
    "text/css",
    "text/javascript",
    "application/json",
    "text/xml",
    "text/csv",
    "application/xml",
    # SQL
    "application/x-sql",
    # Gzip
    "application/x-gzip",
)

# Tipe yang dijalankan peramban atau sistem operasi. Tidak pernah boleh masuk
# TIPE_LAMPIRAN, apa pun yang diminta: impor modul ini gagal kalau ada yang
# menambahkannya. SVG, JS, dan XML yang sudah ada sejak upstream tetap diterima
# tapi selalu disajikan sebagai unduhan (settings.SCRIPT_CAPABLE_MIME_TYPES).
TIPE_TIDAK_PERNAH_BOLEH = frozenset(
    {
        "text/html",
        "application/xhtml+xml",
        "application/javascript",
        "application/x-javascript",
        "application/ecmascript",
        "text/ecmascript",
        "text/vbscript",
        "application/hta",
        "application/x-msdownload",
        "application/x-msdos-program",
        "application/x-dosexec",
        "application/vnd.microsoft.portable-executable",
        "application/x-executable",
        "application/x-elf",
        "application/x-mach-binary",
        "application/x-msi",
        "application/x-ms-installer",
        "application/x-ms-shortcut",
        "application/x-sh",
        "application/x-csh",
        "application/x-shellscript",
        "application/x-bat",
        "application/x-powershell",
        "application/x-httpd-php",
        "application/x-php",
        "text/x-php",
        "application/java-archive",
        "application/x-java-archive",
    }
)

_TERLARANG_DI_DAFTAR = sorted(TIPE_TIDAK_PERNAH_BOLEH.intersection(TIPE_LAMPIRAN))
if _TERLARANG_DI_DAFTAR:
    raise ValueError(f"Tipe terlarang masuk TIPE_LAMPIRAN: {', '.join(_TERLARANG_DI_DAFTAR)}")


def tipe_lampiran_diizinkan() -> tuple:
    """TIPE_LAMPIRAN dikurangi yang dicoret Super Admin (UPLOAD_BLOCKED_FILE_TYPES), per permintaan."""
    from plane.utils import aturan
    from plane.utils.aturan.area_keamanan import UPLOAD_BLOCKED_FILE_TYPES

    dicoret = set(aturan.get_list(UPLOAD_BLOCKED_FILE_TYPES))
    if not dicoret:
        return TIPE_LAMPIRAN
    return tuple(t for t in TIPE_LAMPIRAN if t not in dicoret)


# Tebakan dari ekstensi untuk yang tidak dikenal `mimetypes` di semua platform
# (tabelnya bergantung registri OS pada Windows). Nilainya semua ada di
# TIPE_LAMPIRAN.
_TIPE_EKSTENSI = {
    ".txt": "text/plain",
    ".log": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".csv": "text/csv",
    ".json": "application/json",
    ".xml": "application/xml",
    ".css": "text/css",
    ".js": "text/javascript",
    ".sql": "application/x-sql",
    ".rtf": "application/rtf",
    ".mkv": "video/x-matroska",
    ".7z": "application/x-7z-compressed",
    ".rar": "application/x-rar-compressed",
    ".tgz": "application/gzip",
    ".gz": "application/gzip",
    ".m4a": "audio/x-m4a",
    ".flac": "audio/flac",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".odp": "application/vnd.oasis.opendocument.presentation",
}


def _bersihkan(tipe):
    """`text/plain; charset=utf-8` menjadi `text/plain`, huruf kecil."""
    if not isinstance(tipe, str):
        return ""
    return tipe.split(";")[0].strip().lower()


def tebak_tipe_dari_nama(nama):
    """Tipe dari ekstensi nama berkas, atau "" kalau tidak ketahuan."""
    ekstensi = posixpath.splitext((nama or "").lower())[1]
    if not ekstensi:
        return ""
    return _TIPE_EKSTENSI.get(ekstensi) or mimetypes.guess_type(f"x{ekstensi}")[0] or ""


def rapikan_tipe_unggahan(nama, tipe, diizinkan):
    """Tipe yang dipakai untuk presign.

    `diizinkan` adalah daftar tipe sah untuk entitasnya. Mengembalikan tipe yang
    bersih yang disebut klien kalau ia sudah berisi tipe spesifik (sah atau
    tidak; pemanggil yang menolak), dan tebakan dari ekstensi kalau kosong atau
    generik.
    """
    bersih = _bersihkan(tipe)
    if bersih not in ("", OCTET_STREAM):
        return bersih
    tebakan = tebak_tipe_dari_nama(nama)
    if tebakan and tebakan in diizinkan:
        return tebakan
    if OCTET_STREAM in diizinkan:
        return OCTET_STREAM
    return bersih


# Tipe yang boleh disajikan `inline` (pratinjau di <iframe>, <img>, <video>).
# Daftar positif, bukan daftar larangan: tipe yang tak disebut di sini selalu
# jadi unduhan, jadi tipe baru yang bisa menjalankan skrip (HTML, SVG, XML apa
# pun yang memuat XHTML) tidak pernah lolos hanya karena lupa dicoret.
_PREFIKS_INLINE = ("image/", "video/", "audio/")
_TIPE_INLINE = frozenset({"application/pdf", "text/plain", "application/json"})


def disposisi_sajian(tipe, diminta):
    """"inline" hanya bila diminta DAN tipenya aman ditampilkan; selain itu "attachment"."""
    if diminta != "inline":
        return "attachment"
    bersih = _bersihkan(tipe)
    if bersih in settings.SCRIPT_CAPABLE_MIME_TYPES:
        return "attachment"
    if bersih in _TIPE_INLINE or bersih.startswith(_PREFIKS_INLINE):
        return "inline"
    return "attachment"

