# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email pemberitahuan pesan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penyusun dan pengirim satu email rangkuman pesan yang belum dibaca."""

from django.utils.html import escape

from plane.utils.email_merek import (
    FONT,
    GAYA,
    JEDA_AVATAR,
    RUANG,
    TABEL,
    UKURAN_AVATAR,
    WARNA,
    avatar_untuk,
    bahasa_penerima,
    base_url,
    baris_orang,
    blok,
    bungkus,
    buat_pesan,
    catatan_kecil,
    garis_pemisah,
    judul_html,
    sapaan_html,
    tombol,
    url_preferensi,
)

FONT_SEL = f"font-family:{FONT};"

# Panjang cuplikan isi pesan di dalam email. Cukup untuk tahu ini soal apa,
# pendek supaya email tidak jadi tempat membaca seluruh percakapan. Membacanya
# tetap di aplikasi, supaya status terbaca ikut tercatat.
PANJANG_CUPLIKAN = 120

TEKS = {
    "id": {
        "subjek_satu": "[Obrolan] {n} pesan baru dari {nama}",
        "subjek_banyak": "[Obrolan] {n} pesan baru dari {orang} orang",
        "sapaan": "Halo {nama},",
        "judul": "Ada pesan yang belum Anda baca",
        "jumlah": "{n} pesan",
        "buka": "Buka percakapan",
        "buka_teks": "Buka: {url}",
        "tombol": "Buka obrolan",
        "catatan": "Pesan ditandai terbaca saat Anda membukanya di aplikasi.",
        "alasan": "Anda menerima email ini karena email obrolan Anda menyala.",
    },
    "en": {
        "subjek_satu": "[Chat] {n} new messages from {nama}",
        "subjek_banyak": "[Chat] {n} new messages from {orang} people",
        "sapaan": "Hi {nama},",
        "judul": "You have unread messages",
        "jumlah": "{n} messages",
        "buka": "Open conversation",
        "buka_teks": "Open: {url}",
        "tombol": "Open chat",
        "catatan": "Messages are marked as read when you open them in the app.",
        "alasan": "You received this email because chat emails are turned on for you.",
    },
}


def _cuplik(teks: str) -> str:
    satu_baris = " ".join((teks or "").split())
    if len(satu_baris) <= PANJANG_CUPLIKAN:
        return satu_baris
    return satu_baris[: PANJANG_CUPLIKAN - 1] + "…"


def _nama(orang) -> str:
    return orang.display_name or orang.first_name or orang.email


def susun_email_pesan(penerima, slug: str, ringkasan: list, bahasa="id", gambar=None):
    """(subjek, teks, html). `gambar` = daftar Gambar pesan; foto pengirim masuk ke sana."""
    s = TEKS.get(bahasa, TEKS["id"])
    total = sum(jumlah for _, jumlah, _ in ringkasan)
    if len(ringkasan) == 1:
        subjek = s["subjek_satu"].format(n=total, nama=_nama(ringkasan[0][0]))
    else:
        subjek = s["subjek_banyak"].format(n=total, orang=len(ringkasan))

    url = base_url()
    sapaan = s["sapaan"].format(nama=penerima.display_name or penerima.first_name or "").replace(" ,", ",")
    baris_teks = [sapaan, "", s["judul"], ""]
    baris_html = []
    for pengirim, jumlah, isi_terakhir in ringkasan:
        nama = _nama(pengirim)
        tautan = f"{url}/{slug}/chat?dengan={pengirim.id}" if url else ""
        baris_teks += [f"  {nama} ({s['jumlah'].format(n=jumlah)})", f"    {_cuplik(isi_terakhir)}"]
        if tautan:
            baris_teks.append("    " + s["buka_teks"].format(url=tautan))
        baris_teks.append("")
        av, _ = avatar_untuk(pengirim, gambar=gambar)
        buka = (
            f'<br><a href="{escape(tautan)}" target="_blank" style="{GAYA["tautan_aksi"]}">'
            f"{escape(s['buka'])} &rarr;</a>"
            if tautan
            else ""
        )
        # Isi pesan orang lain masuk ke HTML, jadi WAJIB di-escape. Tanpa ini
        # siapa pun bisa menyuntikkan markup ke kotak masuk rekannya hanya
        # dengan mengetiknya di obrolan.
        baris_html.append(
            baris_orang(av, s["jumlah"].format(n=jumlah), jarak=4, dalam=True)
            + f'{TABEL}><tr><td style="padding:0 0 0 {UKURAN_AVATAR + JEDA_AVATAR}px;{FONT_SEL}'
            f'font-size:14px;line-height:1.5;color:{WARNA["teks_2"]};">{escape(_cuplik(isi_terakhir))}{buka}</td></tr></table>'
        )
    baris_teks += [s["catatan"], ""]

    # Pemisah HANYA di antara orang: garis terakhir yang menempel ke tombol
    # membuat tombol terlihat seperti bagian baris terakhir.
    pemisah = f'</td></tr>{garis_pemisah()}<tr><td style="padding:14px 0;">'
    daftar = f'{TABEL}><tr><td style="padding:0 0 14px;">{pemisah.join(baris_html)}</td></tr></table>'

    isi = (
        judul_html(s["judul"])
        + sapaan_html(sapaan)
        + blok(daftar, jarak=RUANG["blok"] - 14)
        + tombol(s["tombol"], f"{url}/{slug}/chat" if url else "")
        + catatan_kecil(s["catatan"])
    )
    html = bungkus(
        isi,
        bahasa=bahasa,
        judul=subjek,
        pratajuk=s["judul"],
        alasan=s["alasan"],
        url_preferensi=url_preferensi(slug),
        email_penerima=penerima.email,
    )
    return subjek, "\n".join(baris_teks), html


def kirim_email_pesan(penerima, slug: str, ringkasan: list) -> None:
    """Kirim satu email berisi seluruh pesan belum dibaca milik satu orang.

    `ringkasan` berisi tuple (pengirim, jumlah, isi_terakhir), satu per lawan
    bicara. Melempar kalau gagal, biar pemanggil yang mencatat.
    """
    gambar = []
    subjek, teks, html = susun_email_pesan(penerima, slug, ringkasan, bahasa_penerima(penerima), gambar)
    buat_pesan(ke=penerima.email, subjek=subjek, html=html, teks=teks, gambar=gambar).send(fail_silently=False)
