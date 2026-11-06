# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: teks isi berkas Wiki untuk pencarian
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Mengubah isi berkas Materi Wiki menjadi teks polos yang bisa dicari.

Modul ini murni: menerima bytes, mengembalikan string. Tidak ada akses jaringan
atau penyimpanan, jadi bisa diuji tanpa MinIO. Pemakai (tugas latar
`plane.bgtasks.wiki_indeks_task`) yang mengambil berkasnya.

Yang dibaca: PDF, Word (docx), Excel (xlsx), CSV/TSV, teks polos dan Markdown.
Word lama, PowerPoint, dan format OpenDocument dibaca dari PDF hasil konversi
(`WikiMaterial.pratinjau`), bukan dari berkas aslinya. Gambar dan arsip tidak
punya teks, dan itu bukan galat: hasilnya string kosong.

Hasil selalu dipotong di `TEKS_INDEKS_MAKS` dan bebas karakter NUL (PostgreSQL
menolak NUL di kolom teks, dan PDF sering membawanya).
"""

import io
import re

from plane.utils.wiki_pratinjau import (
    BERKAS_ZIP_MAKS_BYTE,
    CSV_MAKS_BYTE,
    TEKS_MAKS_BYTE,
    baca_csv,
    baca_docx,
    baca_teks,
    baca_xlsx,
    jenis_pratinjau,
)

# Karakter, bukan byte. 100 ribu karakter ~ 40 halaman teks padat: cukup untuk
# menemukan dokumen, dan menjaga indeks serta pembacaan hasil tetap kecil.
TEKS_INDEKS_MAKS = 100_000
PDF_MAKS_BYTE = 50 * 1024 * 1024
PDF_HALAMAN_MAKS = 300

# Kunci yang isinya bukan teks isi berkas (jenis blok, tautan, penanda potong).
_KUNCI_DILEWATI = {"type", "href", "kind", "level", "truncated", "sheets_truncated"}

_SPASI = re.compile(r"\s+")


def rapikan(teks):
    """Buang NUL, ratakan spasi, potong di batas indeks."""
    return _SPASI.sub(" ", (teks or "").replace("\x00", " ")).strip()[:TEKS_INDEKS_MAKS]


def _kumpulkan(nilai, keluar, batas):
    """Jalan-jalan di struktur hasil pembaca pratinjau dan kumpulkan semua string."""
    if sum(len(x) + 1 for x in keluar) >= batas:
        return
    if isinstance(nilai, str):
        if nilai:
            keluar.append(nilai)
    elif isinstance(nilai, dict):
        for kunci, isi in nilai.items():
            if kunci not in _KUNCI_DILEWATI:
                _kumpulkan(isi, keluar, batas)
    elif isinstance(nilai, (list, tuple)):
        for isi in nilai:
            _kumpulkan(isi, keluar, batas)


def _dari_struktur(hasil):
    if not hasil:
        return ""
    potongan = []
    _kumpulkan(hasil, potongan, TEKS_INDEKS_MAKS)
    return rapikan(" ".join(potongan))


def teks_pdf(data):
    """Teks sebuah PDF. String kosong untuk PDF berkata sandi, hasil pindai tanpa
    lapisan teks, atau berkas rusak."""
    if len(data) > PDF_MAKS_BYTE:
        return ""
    from pypdf import PdfReader  # noqa: PLC0415 - berat; hanya dimuat bila ada PDF

    try:
        pembaca = PdfReader(io.BytesIO(data))
        if pembaca.is_encrypted:
            return ""
        potongan, panjang = [], 0
        for halaman in pembaca.pages[:PDF_HALAMAN_MAKS]:
            try:
                isi = halaman.extract_text() or ""
            except Exception:  # noqa: BLE001 - satu halaman rusak tidak menggugurkan sisanya
                continue
            potongan.append(isi)
            panjang += len(isi)
            if panjang >= TEKS_INDEKS_MAKS:
                break
    except Exception:  # noqa: BLE001 - PDF rusak, bukan galat bagi pemanggil
        return ""
    return rapikan(" ".join(potongan))


def jenis_sumber(tipe, nama):
    """Dari mana teks sebuah berkas dibaca: 'pdf', 'xlsx', 'docx', 'csv', 'teks',
    'pratinjau' (harus lewat PDF hasil konversi), atau None (tak punya teks)."""
    jenis = jenis_pratinjau(tipe, nama)
    if jenis in ("pdf", "xlsx", "docx", "csv"):
        return jenis
    if jenis in ("text", "markdown"):
        return "teks"
    if jenis == "konversi":
        return "pratinjau"
    return None


def batas_baca(jenis):
    """Byte paling banyak yang diambil dari penyimpanan untuk jenis ini."""
    if jenis == "pdf":
        return PDF_MAKS_BYTE
    if jenis in ("xlsx", "docx"):
        return BERKAS_ZIP_MAKS_BYTE
    if jenis == "csv":
        return CSV_MAKS_BYTE
    return TEKS_MAKS_BYTE


def ekstrak_teks(data, jenis, nama=""):
    """Teks polos dari `data` untuk `jenis` hasil `jenis_sumber` (kecuali
    'pratinjau', yang pemanggil ganti dengan 'pdf' sambil membawa PDF-nya)."""
    if not data:
        return ""
    if jenis == "pdf":
        return teks_pdf(data)
    if jenis == "xlsx":
        return _dari_struktur(baca_xlsx(data))
    if jenis == "docx":
        return _dari_struktur(baca_docx(data))
    if jenis == "csv":
        hasil = baca_csv(data, nama) or baca_teks(data)
        return _dari_struktur(hasil)
    if jenis == "teks":
        return _dari_struktur(baca_teks(data))
    return ""
