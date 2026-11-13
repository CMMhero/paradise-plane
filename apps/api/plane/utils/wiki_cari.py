# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pencarian Wiki yang memaafkan salah ketik
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bagian pencarian Wiki yang tidak menyentuh request: memecah kueri, menilai
kemiripan judul, dan mengambil cuplikan dari isi.

Pencocokan kasarnya dikerjakan database (`icontains` untuk yang persis,
`kata_mirip` / pg_trgm untuk yang mirip, memakai indeks GIN). Modul ini hanya
mengurutkan hasilnya dan menunjukkan DI MANA kata itu muncul.
"""

import re
from contextlib import contextmanager
from difflib import SequenceMatcher, get_close_matches

from django.db import connection, transaction

_KATA = re.compile(r"\w+", re.UNICODE)

MIN_TOKEN = 2
# Di bawah ini salah ketik satu huruf sudah mengubah separuh trigram: kata
# pendek dicocokkan persis saja, supaya "sop" tidak menarik separuh Wiki.
MIN_TOKEN_MIRIP = 4
MAKS_TOKEN = 6
# Seberapa mirip dua kata sebelum dianggap salah ketik (0..1).
AMBANG_MIRIP = 0.5
AMBANG_JUDUL = 0.75
PANJANG_CUPLIKAN = 160


def pecah_kueri(kueri):
    """Kata-kata kueri: huruf kecil, unik, urutan asli, paling banyak MAKS_TOKEN."""
    hasil = []
    for kata in _KATA.findall((kueri or "").lower()):
        if len(kata) >= MIN_TOKEN and kata not in hasil:
            hasil.append(kata)
    return hasil[:MAKS_TOKEN]


@contextmanager
def ambang_mirip(nilai=AMBANG_MIRIP):
    """Atur ambang `<%` untuk satu blok. `SET LOCAL` hanya berlaku sampai
    transaksi selesai, jadi tidak bocor ke permintaan lain di koneksi yang sama."""
    with transaction.atomic():
        with connection.cursor() as kursor:
            kursor.execute("SELECT set_config('pg_trgm.word_similarity_threshold', %s, true)", [str(nilai)])
        yield


def _kemiripan(a, b):
    return SequenceMatcher(None, a, b).ratio()


def skor_judul(tokens, judul):
    """0..1: seberapa baik `judul` memenuhi semua kata kueri. Kata yang ada
    persis bernilai 1, awal kata sedikit lebih tinggi; yang salah ketik bernilai
    sebesar kemiripannya (di atas AMBANG_JUDUL), sisanya 0."""
    if not tokens:
        return 0.0
    rendah = (judul or "").lower()
    kata_judul = _KATA.findall(rendah)
    total = 0.0
    for token in tokens:
        if token in rendah:
            awal = any(k.startswith(token) for k in kata_judul)
            total += 1.0 if awal else 0.9
            continue
        terbaik = max((_kemiripan(token, k) for k in kata_judul), default=0.0)
        total += terbaik if terbaik >= AMBANG_JUDUL else 0.0
    return total / len(tokens)


def cuplikan(teks, tokens, panjang=PANJANG_CUPLIKAN):
    """(potongan teks sekitar kemunculan pertama, kata-kata yang ditemukan).

    Mencari persis dulu; kalau tidak ada, kata terdekat di teks (salah ketik).
    Kata yang ditemukan dikembalikan apa adanya dari teks supaya klien bisa
    menyorotnya, termasuk kata yang ejaannya beda dari kueri."""
    if not teks or not tokens:
        return "", []
    rendah = teks.lower()
    ditemukan, posisi = [], []
    kata_unik = None
    for token in tokens:
        i = rendah.find(token)
        if i >= 0:
            ditemukan.append(token)
            posisi.append(i)
            continue
        if len(token) < MIN_TOKEN_MIRIP:
            continue
        if kata_unik is None:
            kata_unik = list({k for k in _KATA.findall(rendah)})
        mirip = get_close_matches(token, kata_unik, n=1, cutoff=AMBANG_JUDUL)
        if mirip:
            ditemukan.append(mirip[0])
            posisi.append(rendah.find(mirip[0]))
    posisi = [p for p in posisi if p >= 0]
    if not posisi:
        return "", []
    mulai = max(0, min(posisi) - panjang // 4)
    akhir = min(len(teks), mulai + panjang)
    # Mulai dan berhenti di batas kata, supaya tidak memotong di tengah kata.
    if mulai > 0:
        geser = teks.find(" ", mulai, min(posisi))
        mulai = geser + 1 if geser >= 0 else mulai
    if akhir < len(teks):
        geser = teks.rfind(" ", max(akhir - 20, mulai), akhir)
        akhir = geser if geser > mulai else akhir
    potongan = teks[mulai:akhir].strip()
    return ("…" if mulai > 0 else "") + potongan + ("…" if akhir < len(teks) else ""), ditemukan
