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
"""

import mimetypes
import posixpath

OCTET_STREAM = "application/octet-stream"

# Tebakan dari ekstensi untuk yang tidak dikenal `mimetypes` di semua platform
# (tabelnya bergantung registri OS pada Windows). Nilainya semua ada di
# settings.ATTACHMENT_MIME_TYPES.
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
