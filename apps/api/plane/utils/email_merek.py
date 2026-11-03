# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: satu tata letak untuk semua email
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tata letak, warna, bahasa, dan pengiriman yang dipakai SEMUA email aplikasi.

Kenapa satu modul: sebelum ini ada 15+ salinan boilerplate koneksi SMTP dan tiga
gaya email yang berbeda (templat mail-builder upstream, div berinline Arial di
ringkasan, teks polos). Semua pengirim sekarang lewat `buat_pesan()`, jadi logo
CID, header/footer, dan bahasa tidak bisa lupa dipasang di satu jalur.

Keputusan yang mengikat:

- **Logo disisipkan sebagai CID, bukan URL.** Server produksi LAN-only di balik
  NAT; proxy gambar Gmail/Outlook.com mengambil gambar dari internet dan tidak
  pernah sampai ke `128.159.110.5`. URL absolut = logo pecah di semua kotak masuk
  luar kantor.
- **Foto profil juga CID** (dibaca dari storage saat kirim) dengan cadangan
  inisial berlatar merah merek, sama dengan `Avatar` di propel. Penyebab foto
  tidak tampil dulu: `f"{base_api}{actor.avatar_url}"` menghasilkan
  `http://hostNone` untuk orang tanpa foto (gambar pecah, bukan inisial), dan
  untuk yang punya foto, `/api/assets/v2/static/<id>/` mengalihkan ke URL MinIO
  presigned yang (a) host-nya LAN, (b) kedaluwarsa dalam hitungan jam.
- **Bahasa ikut `Profile.language` penerima** ("id" = Indonesia, lainnya =
  Inggris), sama dengan email persetujuan. Penerima tanpa akun (undangan, kode
  masuk pertama) memakai bahasa bawaan akun baru di God Mode > Members > Defaults.
- **Terang saja, tanpa varian gelap.** `color-scheme: light`: Apple Mail tidak
  membalik warna, Gmail/Outlook yang memaksa mode gelap membalik semua warna
  inline secara seragam. Varian gelap buatan sendiri membuat teks berwarna inline
  di isi (merah/hijau/abu ringkasan) gelap di atas gelap.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from email.mime.image import MIMEImage
from html import unescape
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.mail.message import SafeMIMEMultipart
from django.template.loader import render_to_string
from django.utils.html import escape
from django.utils.safestring import mark_safe


logger = logging.getLogger("plane.worker")

MEREK = "Space Paradise Perkasa"
KANTOR = "PT Paradise Perkasa"
BAHASA = ("id", "en")

# Token Bara (KEP-64) dalam hex. Sumber: packages/tailwind-config/paradise.css
# (--brand-*, merah logo #ED1F24 digelapkan ke #E40A1A supaya lolos AA) dan
# paradise-tampilan.css (--neutral-* skema bara: hue 62, chroma 0.01). Email tidak
# mengenal oklch, jadi nilainya dikonversi sekali di sini.
WARNA = {
    "kanvas": "#F6EEE9",  # neutral-300, latar kertas hangat di luar kartu
    "permukaan": "#FFFDFB",  # neutral-white, kartu
    "lapis": "#FAF4EF",  # neutral-200, blok di dalam kartu
    "garis": "#E3DAD2",  # neutral-600
    "garis_halus": "#F1E9E3",  # neutral-400
    "teks": "#221E1A",  # neutral-1200
    "teks_2": "#57514B",  # neutral-1100
    "teks_3": "#716A64",  # neutral-1000
    "teks_4": "#9B938C",  # neutral-800
    "merek": "#E40A1A",  # brand-default
    "merek_tekan": "#C10012",  # brand-900, bevel bawah tombol
    "merek_halus": "#FFF2F0",  # brand-200
    "merek_garis": "#FFD2CC",  # brand-400
    "sorot": "#EA942F",  # --highlight (amber)
    "sukses": "#016630",  # green-900
    "peringatan": "#973C00",  # amber-900
    "bahaya": "#9F0712",  # red-900
    "bahaya_halus": "#FFF2F0",
    "info_halus": "#FAF4EF",
}

# Plus Jakarta Sans = font aplikasi. Gmail tidak memuat font web, jadi cadangannya
# harus mirip: Segoe UI (Windows/Outlook), Roboto (Android), Helvetica (Apple).
FONT = "'Plus Jakarta Sans','Segoe UI',Roboto,'Helvetica Neue',Helvetica,Arial,sans-serif"
FONT_MONO = "'Geist Mono',SFMono-Regular,Consolas,'Liberation Mono',Menlo,monospace"

# ---------------------------------------------------------------- sistem gaya
#
# Satu sumber untuk jarak, ukuran huruf, dan sudut. Templat membacanya lewat
# `{{ g.* }}` / `{{ r.* }}`, penyusun Python lewat helper di bawah. Aturan yang
# membuatnya rapi di Outlook klasik (mesin Word) juga di Gmail/Apple Mail:
#
# - Jarak vertikal SELALU di bawah elemen (margin-bottom pada <p>, padding-bottom
#   pada sel pembungkus blok), tidak pernah di atas, kecuali judul bagian.
# - Elemen tingkat atas di isi kartu diberi penanda `data-j`; `_rapikan_akhir()`
#   menolkan jarak bawah elemen TERAKHIR, jadi padding kartu atas = bawah apa pun
#   penutupnya (tombol, paragraf, kotak).
# - Bingkai = "border sebagai latar": sel luar berlatar warna garis + padding 1px,
#   sel dalam berlatar permukaan. Border pada <td> kadang hilang sebagian di Word.
# - Teks berbaris banyak memakai <br> (`linebreaksbr`), bukan `white-space:pre-wrap`.

RUANG = {
    "judul": 12,  # h1 -> isi
    "paragraf": 14,  # antar paragraf
    "blok": 20,  # sesudah kartu, kotak, tabel, tombol, baris orang
    "bagian": 8,  # di atas judul bagian (ditambah jarak bawah elemen sebelumnya)
    "rapat": 8,  # baris orang -> isinya, label -> daftar
}
UKURAN = {"h1": 22, "h2": 16, "isi": 15, "isi_2": 14, "tabel": 13, "meta": 12}
# Sudut: kartu utama 12/11, blok di dalamnya 10/9 (luar/dalam bingkai), tombol 8.
SUDUT = {"kartu": 12, "kartu_dalam": 11, "blok": 10, "blok_dalam": 9, "tombol": 8}
PADDING_BLOK = "16px 18px"
JEDA_AVATAR = 10  # avatar -> nama
UKURAN_AVATAR = 28
LEBAR_KOLOM_TANGGAL = 132  # kolom kanan daftar tugas ringkasan
LEBAR_KOLOM_ANGKA = 70  # kolom angka tabel ringkasan
LEBAR_ISI = 526  # 600 - 2px bingkai - 2 x 36px padding kartu
JEDA_UBIN = 8

# Penanda blok tingkat atas; dihapus `_rapikan_akhir()` sebelum email dikirim.
PENANDA = ' data-j="1"'

_F = f"font-family:{FONT};"

# Gaya inline yang dipakai berulang (`{{ g.h1 }}`). Inline, bukan kelas: Gmail
# membuang <style> di sebagian klien dan Outlook mengabaikan kelas.
GAYA = {
    "h1": (
        f"margin:0 0 {RUANG['judul']}px;{_F}font-size:{UKURAN['h1']}px;line-height:1.3;font-weight:700;"
        f"color:{WARNA['teks']};"
    ),
    "h2": f"margin:0;{_F}font-size:{UKURAN['h2']}px;line-height:1.4;font-weight:700;color:{WARNA['teks']};",
    "p": f"margin:0 0 {RUANG['paragraf']}px;{_F}font-size:{UKURAN['isi']}px;line-height:1.6;color:{WARNA['teks']};",
    "p2": (
        f"margin:0 0 {RUANG['paragraf']}px;{_F}font-size:{UKURAN['isi_2']}px;line-height:1.6;color:{WARNA['teks_2']};"
    ),
    "kecil": (
        f"margin:0 0 {RUANG['paragraf']}px;{_F}font-size:{UKURAN['tabel']}px;line-height:1.6;color:{WARNA['teks_3']};"
    ),
    "meta": f"{_F}font-size:{UKURAN['meta']}px;line-height:1.5;font-weight:400;color:{WARNA['teks_3']};",
    "nama": f"{_F}font-size:{UKURAN['isi_2']}px;line-height:20px;font-weight:700;color:{WARNA['teks']};",
    "label": (
        f"{_F}font-size:{UKURAN['meta']}px;line-height:1.4;font-weight:700;letter-spacing:0.3px;"
        "text-transform:uppercase;"
    ),
    "label_biasa": f"{_F}font-size:{UKURAN['tabel']}px;line-height:1.4;font-weight:700;",
    "tautan": f"color:{WARNA['merek']};text-decoration:underline;word-break:break-all;",
    "tautan_aksi": f"{_F}color:{WARNA['merek']};font-size:{UKURAN['tabel']}px;font-weight:600;text-decoration:none;",
    "chip": f"font-family:{FONT_MONO};font-size:{UKURAN['meta']}px;font-weight:600;color:{WARNA['teks_3']};",
    "kode": (
        f"padding:18px 20px;font-family:{FONT_MONO};font-size:30px;line-height:1.2;font-weight:700;"
        f"letter-spacing:6px;color:{WARNA['teks']};text-align:center;"
    ),
}

LOGO_CID = "logo-paradise"
_LOGO = Path(__file__).resolve().parent.parent / "static" / "email" / "logo-paradise.png"

# Foto profil lebih besar dari ini tidak disisipkan (tanpa Pillow tidak bisa
# diperkecil); orangnya tampil sebagai inisial. Lima komentator x 2 MB = email
# 10 MB, yang ditolak sebagian server surat.
BATAS_AVATAR_BYTE = 256 * 1024


# ---------------------------------------------------------------- bahasa


def bahasa_dari_kode(kode) -> str:
    return "id" if str(kode or "").lower().startswith("id") else "en"


def bahasa_bawaan() -> str:
    """Bahasa akun baru (God Mode > Members > Defaults). Galat = Indonesia."""
    try:
        from plane.utils.bawaan_member import baca_bawaan

        return bahasa_dari_kode(baca_bawaan()["profile"]["language"])
    except Exception:  # noqa: BLE001
        return "id"


def bahasa_penerima(user) -> str:
    """'id' atau 'en' dari `Profile.language`. Tanpa profil = bahasa bawaan akun baru.

    Bahasa tinggal di `Profile` (OneToOne), BUKAN di `User` (jebakan KEP-55).
    """
    try:
        profil = getattr(user, "profile", None)
    except Exception:  # noqa: BLE001  RelatedObjectDoesNotExist
        profil = None
    kode = getattr(profil, "language", None) if profil is not None else None
    return bahasa_dari_kode(kode) if kode else bahasa_bawaan()


def bahasa_untuk_alamat(email) -> str:
    """Untuk penerima yang cuma dikenal alamatnya (undangan, kode masuk)."""
    from plane.db.models import User

    user = User.objects.filter(email__iexact=str(email or "").strip()).select_related("profile").first()
    return bahasa_penerima(user) if user else bahasa_bawaan()


_BULAN = {
    "id": ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
           "November", "Desember"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December"),
}  # fmt: skip


def tanggal(nilai, bahasa="id", pendek=False) -> str:
    """`2 November 2026` / `2 Nov 2026`. Bukan strftime: locale server selalu Inggris."""
    if not nilai:
        return ""
    if isinstance(nilai, str):
        try:
            nilai = date.fromisoformat(nilai[:10])
        except ValueError:
            return nilai
    if isinstance(nilai, datetime):
        nilai = nilai.date()
    bulan = _BULAN.get(bahasa, _BULAN["id"])[nilai.month - 1]
    return f"{nilai.day} {bulan[:3] if pendek else bulan} {nilai.year}"


# Nilai yang dihitung di lapisan data dalam bahasa Indonesia (peran, cakupan,
# jendela laporan). Teks lain lewat kamus per email.
_DATA_EN = {
    "Staf": "Staff",
    "Direktur": "Director",
    "Seluruh divisi": "All divisions",
    "Divisi Anda": "Your division",
    "Departemen Anda": "Your department",
    "Tim Anda": "Your team",
    "Project yang Anda awasi": "Projects you oversee",
    "24 jam terakhir": "last 24 hours",
    "Jumat s.d. Minggu": "Friday to Sunday",
}


def terjemah_data(teks, bahasa) -> str:
    if bahasa != "en" or not teks:
        return teks or ""
    if teks in _DATA_EN:
        return _DATA_EN[teks]
    cocok = re.fullmatch(r"(\d+) project", teks)
    return f"{cocok.group(1)} projects" if cocok else teks


# ---------------------------------------------------------------- kerangka


KERANGKA = {
    "id": {
        "otomatis": "Email otomatis dari {merek}, sistem internal {kantor}. Tidak perlu dibalas.",
        "atur": "Atur notifikasi",
        "ditujukan": "Email ini dikirim ke",
        "tautan_cadangan": "Kalau tombol tidak berfungsi, salin tautan ini ke peramban:",
    },
    "en": {
        "otomatis": "Automated email from {merek}, the internal system of {kantor}. No need to reply.",
        "atur": "Manage notifications",
        "ditujukan": "This email was sent to",
        "tautan_cadangan": "If the button doesn't work, copy this link into your browser:",
    },
}


def bungkus(
    isi,
    *,
    bahasa="id",
    judul="",
    pratajuk="",
    alasan="",
    url_preferensi="",
    email_penerima="",
) -> str:
    """Pasang header, kartu, dan footer bersama di sekeliling `isi` (HTML aman).

    `alasan` = kenapa orang ini menerima email ini. `url_preferensi` = tautan ke
    Profil > Notifikasi; kosongkan untuk email transaksional (kode masuk, undangan)
    yang memang tidak bisa dimatikan.
    """
    html = render_to_string(
        "emails/base.html",
        {
            **konteks_dasar(bahasa),
            "isi": mark_safe(isi),  # noqa: S308  isi dirakit dari partial ber-escape
            "judul": judul,
            "pratajuk": pratajuk,
            "alasan": alasan,
            "url_preferensi": url_preferensi,
            "email_penerima": email_penerima,
        },
    )
    return _rapikan_akhir(html)


_JARAK_BAWAH = re.compile(r' style="(margin|padding):(\S+) 0 \d+px')


def _rapikan_akhir(html) -> str:
    """Nolkan jarak bawah blok terakhir di isi kartu, lalu buang semua penanda.

    Tanpa ini tombol penutup (20px) + padding kartu (32px) membuat ruang bawah
    kartu jauh lebih lebar dari atasnya, dan lebarnya beda per email.
    """
    awal, akhir = html.find("<!--isi-->"), html.find("<!--/isi-->")
    if 0 <= awal < akhir:
        pos = html.rfind(PENANDA, awal, akhir)
        if pos >= 0:
            cocok = _JARAK_BAWAH.match(html, pos + len(PENANDA))
            if cocok:
                html = f'{html[: cocok.start()]} style="{cocok.group(1)}:{cocok.group(2)} 0 0{html[cocok.end() :]}'
    return html.replace(PENANDA, "").replace("<!--isi-->", "").replace("<!--/isi-->", "")


def konteks_dasar(bahasa="id") -> dict:
    """Variabel yang dibaca base.html dan semua partial."""
    k = KERANGKA.get(bahasa, KERANGKA["id"])
    return {
        "bahasa": bahasa,
        "w": WARNA,
        "font": FONT,
        "font_mono": FONT_MONO,
        "merek": MEREK,
        "kantor": KANTOR,
        "logo_src": f"cid:{LOGO_CID}",
        "g": GAYA,
        "r": RUANG,
        "sudut": SUDUT,
        "padding_blok": PADDING_BLOK,
        "ukuran_avatar": UKURAN_AVATAR,
        "jeda_avatar": JEDA_AVATAR,
        "kerangka": {kunci: nilai.format(merek=MEREK, kantor=KANTOR) for kunci, nilai in k.items()},
    }


def render_email(templat, konteks, bahasa="id"):
    """(html, teks) dari templat yang `{% extends "emails/base.html" %}`."""
    html = _rapikan_akhir(render_to_string(templat, {**konteks_dasar(bahasa), **konteks}))
    return html, teks_polos(html)


_TOMBOL_POLOS = re.compile(r'<a\b[^>]*class="em-tombol[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)


def teks_polos(html) -> str:
    """Versi teks dari HTML email bersama.

    `generate_plain_text_from_html` upstream hanya membuang tag: entitas
    (`&middot;`, `&rarr;`) tertinggal mentah, sel tabel menempel ("StatusTodo"),
    label tombol VML ikut tertulis dua kali, dan pratajuk tersembunyi ikut terbaca.
    """
    s = re.sub(r"(?is)<(head|style|title)\b.*?</\1>", "", html)
    s = re.sub(r"(?is)<!--\[if mso\]>.*?<!\[endif\]-->", "", s)
    s = re.sub(r'(?is)<div[^>]*display:none[^>]*>.*?</div>', "", s)
    s = re.sub(r'(?is)<td class="em-avatar"[^>]*>.*?</td>', "", s)  # inisial avatar, namanya sudah tertulis
    s = _TOMBOL_POLOS.sub(lambda m: f"{m.group(2)}: {m.group(1)}", s)
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</(p|h1|h2|tr|table)>", "\n", s)
    s = re.sub(r"(?i)</t[dh]>", "  ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = unescape(s).replace("\xa0", " ").replace("͏", "").replace("‌", "")
    baris, kosong = [], False
    for b in s.splitlines():
        b = re.sub(r"[ \t]+", " ", b).strip()
        if b:
            baris.append(b)
            kosong = False
        elif not kosong and baris:
            baris.append("")
            kosong = True
    return "\n".join(baris).strip() + "\n"


def url_preferensi(slug="") -> str:
    """Profil > Notifikasi. Tanpa slug workspace: halaman profil umum."""
    dasar = base_url()
    if not dasar:
        return ""
    return f"{dasar}/{slug}/settings/account/notifications/" if slug else f"{dasar}/profile/notifications"


def base_url() -> str:
    return (getattr(settings, "APP_BASE_URL", "") or os.environ.get("WEB_URL") or "").rstrip("/")


# ---------------------------------------------------------------- partial


TABEL = '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"'


def blok(isi, jarak=RUANG["blok"], atas=0) -> str:
    """Blok tingkat atas: jaraknya padding sel pembungkus (margin tabel diabaikan Word)."""
    return f'{TABEL}><tr><td{PENANDA} style="padding:{atas}px 0 {jarak}px;">{isi}</td></tr></table>'


def garis_pemisah(warna=None, colspan=1) -> str:
    """Baris pemisah 1px sebagai sel berlatar: border-bottom <td> kadang hilang di Word."""
    warna = warna or WARNA["garis_halus"]
    return (
        f'<tr><td colspan="{colspan}" height="1" bgcolor="{warna}" style="height:1px;font-size:1px;line-height:1px;'
        f'mso-line-height-rule:exactly;background-color:{warna};">&nbsp;</td></tr>'
    )


def tombol(label, url, varian="utama") -> str:
    if not url:
        return ""
    return render_to_string(
        "emails/partials/button.html", {**konteks_dasar(), "label": label, "url": url, "varian": varian}
    )


def kartu(kode="", judul="", url="", baris=(), catatan="") -> str:
    """Kartu work item: kode + judul bertautan, lalu baris (label, nilai[, warna]).

    `catatan` (teks, boleh berbaris banyak) tampil sebagai komponen catatan yang
    sama dengan `kotak()`, berlatar permukaan supaya terbaca di atas kartu.
    """
    rapi = []
    for b in baris:
        if b and b[1]:
            rapi.append({"label": b[0], "nilai": b[1], "warna": b[2] if len(b) > 2 else ""})
    catatan_html = kotak(catatan, dalam=True, latar=WARNA["permukaan"]) if catatan else ""
    return render_to_string(
        "emails/partials/card.html",
        {**konteks_dasar(), "kode": kode, "judul": judul, "url": url, "baris": rapi, "catatan_html": catatan_html},
    )


def kotak(isi_teks="", judul="", nada="info", *, butir=(), isi_html="", dalam=False, latar="") -> str:
    """Komponen catatan (garis aksen di kiri). nada: info | bahaya | sukses | peringatan.

    Satu komponen untuk semua catatan: kotak peringatan, catatan kartu, kutipan
    komentar. `isi_teks` berbaris banyak dipecah dengan <br>; `butir` = daftar
    yang tiap butirnya satu baris; `isi_html` = HTML yang SUDAH aman. `dalam`
    = bersarang di blok lain (tanpa jarak bawah dan penanda blok).
    """
    return render_to_string(
        "emails/partials/callout.html",
        {
            **konteks_dasar(),
            "isi": isi_teks,
            "isi_html": isi_html,
            "butir": list(butir),
            "judul": judul,
            "nada": nada,
            "dalam": dalam,
            "latar_ganti": latar,
        },
    )


def avatar_html(avatar, ukuran=UKURAN_AVATAR) -> str:
    return render_to_string("emails/partials/avatar.html", {**konteks_dasar(), "avatar": avatar, "ukuran": ukuran})


def baris_orang(avatar, meta="", *, jarak=None, dalam=False) -> str:
    """Avatar 28px + nama tebal + keterangan abu (`Budi · 09:12`). Selalu sesudah judul."""
    jarak = "" if jarak is None else str(jarak)
    return render_to_string(
        "emails/partials/orang.html",
        {**konteks_dasar(), "avatar": avatar, "meta": meta, "jarak": jarak, "dalam": dalam},
    )


def paragraf(teks, warna=None, ukuran=UKURAN["isi"], tebal=False, jarak=RUANG["paragraf"]) -> str:
    gaya = f"margin:0 0 {jarak}px;{_F}font-size:{ukuran}px;line-height:1.6;color:{warna or WARNA['teks']}"
    if tebal:
        gaya += ";font-weight:700"
    return f'<p{PENANDA} style="{gaya}">{escape(teks)}</p>'


def catatan_kecil(teks) -> str:
    """Keterangan kaki di dalam kartu (lampiran .ics, cara membaca pesan)."""
    return f'<p{PENANDA} style="{GAYA["kecil"]}">{escape(teks)}</p>'


def judul_html(teks) -> str:
    return f'<h1 style="{GAYA["h1"]}">{escape(teks)}</h1>'


def sapaan_html(sapaan, meta="") -> str:
    """`Halo Budi,` dan (opsional) jabatan/cakupan di bawahnya. Selalu sesudah h1."""
    bawah = f'<br><span style="{GAYA["meta"]}">{escape(meta)}</span>' if meta else ""
    return f'<p{PENANDA} style="{GAYA["p2"]}">{escape(sapaan)}{bawah}</p>'


def judul_bagian(teks) -> str:
    """h2 bergaris bawah yang membuka satu bagian (ringkasan, laporan)."""
    return (
        f'{TABEL}><tr><td style="padding:{RUANG["bagian"]}px 0 {RUANG["judul"]}px;">'
        f'{TABEL}><tr><td style="padding:0 0 8px;"><h2 style="{GAYA["h2"]}">{escape(teks)}</h2></td></tr>'
        f"{garis_pemisah(WARNA['garis'])}</table></td></tr></table>"
    )


def label_daftar(teks, warna=None, huruf_besar=True) -> str:
    """Label kecil di atas satu daftar (`TERLAMBAT (2)`, nama project)."""
    return (
        f'<p{PENANDA} style="margin:0 0 {RUANG["rapat"] - 2}px;{GAYA["label"] if huruf_besar else GAYA["label_biasa"]}'
        f'color:{warna or WARNA["teks"]};">'
        f"{escape(teks)}</p>"
    )


def daftar_tugas(baris, lainnya="") -> str:
    """Daftar tugas dua kolom: kiri kode + judul + keterangan, kanan tanggal + status.

    `baris` = [{kode, judul, url, meta, tanggal, ket, warna}]. Kolom kanan
    lebarnya tetap dan rata kanan, jadi tanggal tiap baris sejajar.
    """
    sel = f"{_F}font-size:{UKURAN['isi_2']}px;line-height:1.45;color:{WARNA['teks']};"
    isi = garis_pemisah(colspan=2)
    for b in baris:
        nama = f'<span style="{GAYA["chip"]}">{escape(b["kode"])}</span>&nbsp; {escape(b["judul"])}'
        if b.get("url"):
            nama = (
                f'<a href="{escape(b["url"])}" target="_blank" style="color:{WARNA["teks"]};text-decoration:none;">'
                f"{nama}</a>"
            )
        if b.get("meta"):
            nama += f'<br><span style="{GAYA["meta"]}">{escape(b["meta"])}</span>'
        kanan = escape(b.get("tanggal") or "")
        if b.get("ket"):
            warna = b.get("warna") or WARNA["teks_3"]
            kanan += (
                f'<br><span style="{_F}font-size:{UKURAN["meta"]}px;font-weight:600;color:{warna};">'
                f"{escape(b['ket'])}</span>"
            )
        isi += (
            f'<tr><td valign="top" style="padding:10px 12px 10px 0;{sel}">{nama}</td>'
            f'<td valign="top" align="right" width="{LEBAR_KOLOM_TANGGAL}" style="width:{LEBAR_KOLOM_TANGGAL}px;'
            f'padding:10px 0;text-align:right;white-space:nowrap;{_F}font-size:{UKURAN["tabel"]}px;line-height:1.5;'
            f'color:{WARNA["teks_2"]};">{kanan}</td></tr>' + garis_pemisah(colspan=2)
        )
    if lainnya:
        isi += (
            f'<tr><td colspan="2" style="padding:8px 0 0;{_F}font-size:{UKURAN["meta"]}px;line-height:1.5;'
            f'color:{WARNA["teks_3"]};">{escape(lainnya)}</td></tr>'
        )
    return blok(f"{TABEL}>{isi}</table>")


def tabel_angka(kepala, kolom, baris) -> str:
    """Tabel ringkasan angka (ringkasan sore/manager, laporan direktur): satu gaya.

    `kolom` = [(judul, warna)]; `baris` = [{nama, sub, angka: [..], grup, menjorok}].
    Angka nol diredam (abu, tipis), bukan tebal merah; baris `grup` berlatar lapis.
    """
    n = len(kolom) + 1
    th = f"{_F}font-size:{UKURAN['meta']}px;line-height:1.4;font-weight:600;color:{WARNA['teks_3']};"
    isi = (
        f'<tr><th align="left" style="padding:0 8px 8px 0;text-align:left;{th}">{escape(kepala)}</th>'
        + "".join(
            f'<th align="right" width="{LEBAR_KOLOM_ANGKA}" style="width:{LEBAR_KOLOM_ANGKA}px;padding:0 8px 8px 8px;'
            f'text-align:right;{th}">{escape(k)}</th>'
            for k, _ in kolom
        )
        + "</tr>"
        + garis_pemisah(WARNA["garis"], n)
    )
    for b in baris:
        latar = f'bgcolor="{WARNA["lapis"]}" ' if b.get("grup") else ""
        gaya_latar = f"background-color:{WARNA['lapis']};" if b.get("grup") else ""
        kiri = 20 if b.get("menjorok") else (8 if b.get("grup") else 0)
        nama = f"<strong>{escape(b['nama'])}</strong>" if b.get("grup") else escape(b["nama"])
        if b.get("sub"):
            nama += f'<br><span style="{GAYA["meta"]}">{escape(b["sub"])}</span>'
        sel_angka = ""
        for (_, warna), nilai in zip(kolom, b["angka"]):
            if nilai:
                gaya = f"color:{warna};font-weight:{700 if b.get('grup') else 600};"
            else:
                gaya = f"color:{WARNA['teks_4']};font-weight:400;"
            sel_angka += (
                f'<td {latar}valign="top" align="right" style="padding:9px 8px 9px 8px;text-align:right;{gaya_latar}'
                f'{_F}font-size:{UKURAN["isi_2"]}px;line-height:1.45;{gaya}">{nilai}</td>'
            )
        isi += (
            f'<tr><td {latar}valign="top" style="padding:9px 8px 9px {kiri}px;{gaya_latar}{_F}'
            f'font-size:{UKURAN["isi_2"]}px;line-height:1.45;color:{WARNA["teks"]};">{nama}</td>{sel_angka}</tr>'
            + garis_pemisah(colspan=n)
        )
    return blok(f"{TABEL}>{isi}</table>")


def ubin_angka(ubin) -> str:
    """Deretan ubin KPI berlatar lapis. `ubin` = [(label, nilai, warna, catatan)].

    Tanpa bingkai: sel berlatar selalu setinggi barisnya, jadi ubin tetap sama
    tinggi meski label membungkus dua baris. Bingkai-sebagai-latar tidak bisa.
    Angka di atas, label di bawah: label yang membungkus tidak menggeser angka.
    Lebar dalam piksel, bukan persen: Word membagi ulang kolom persen + jeda 8px
    sampai jedanya hilang dan ubin menyatu.
    """
    jeda = f'<td width="{JEDA_UBIN}" style="width:{JEDA_UBIN}px;font-size:1px;line-height:1px;">&nbsp;</td>'
    # Lebar isi sel (tanpa padding 2 x 14px), jadi jumlahnya tidak melebihi LEBAR_ISI.
    lebar = (LEBAR_ISI - JEDA_UBIN * (len(ubin) - 1)) // len(ubin) - 28
    sel = []
    for label, nilai, warna, catatan in ubin:
        bawah = (
            f'<br><span style="{_F}font-size:{UKURAN["meta"] - 1}px;line-height:1.4;color:{WARNA["teks_3"]};">'
            f"{escape(catatan)}</span>"
            if catatan
            else ""
        )
        warna = warna if nilai else WARNA["teks_4"]  # nol diredam, sama dengan tabel_angka
        sel.append(
            f'<td class="em-ubin" width="{lebar}" valign="top" bgcolor="{WARNA["lapis"]}" '
            f'style="width:{lebar}px;padding:12px 14px;'
            f'background-color:{WARNA["lapis"]};border-radius:{SUDUT["blok"]}px;{_F}">'
            f'<span style="{_F}font-size:26px;line-height:1.25;font-weight:700;color:{warna};">'
            f"{nilai}</span><br>"
            f'<span style="{_F}font-size:{UKURAN["meta"]}px;line-height:1.4;font-weight:600;color:{WARNA["teks_2"]};">'
            f"{escape(label)}</span>{bawah}</td>"
        )
    return blok(f'{TABEL} style="border-collapse:separate;"><tr>{jeda.join(sel)}</tr></table>')


# ---------------------------------------------------------------- avatar


@dataclass
class Gambar:
    """Gambar inline: dirujuk di HTML sebagai `cid:<cid>`."""

    cid: str
    data: bytes
    subtipe: str = "png"


def inisial(nama) -> str:
    kata = [k for k in re.split(r"[\s._@-]+", str(nama or "").strip()) if k]
    if not kata:
        return "?"
    return (kata[0][0] + (kata[1][0] if len(kata) > 1 else "")).upper()


def _baca_avatar(user):
    """(bytes, subtipe) foto profil dari storage, atau None. Tidak pernah melempar."""
    aset = getattr(user, "avatar_asset", None)
    if not aset or not getattr(aset, "asset", None):
        return None
    try:
        if aset.size and aset.size > BATAS_AVATAR_BYTE:
            return None
        from plane.settings.storage import S3Storage

        s3 = S3Storage()
        objek = s3.s3_client.get_object(Bucket=s3.aws_storage_bucket_name, Key=aset.asset.name)
        data = objek["Body"].read(BATAS_AVATAR_BYTE + 1)
        if len(data) > BATAS_AVATAR_BYTE:
            return None
        tipe = (objek.get("ContentType") or "image/png").split("/")[-1].split(";")[0].strip().lower()
        tipe = {"jpg": "jpeg", "svg+xml": ""}.get(tipe, tipe)
        return (data, tipe) if tipe in ("png", "jpeg", "gif", "webp") else None
    except Exception as e:  # noqa: BLE001
        logger.warning("Avatar %s tidak terbaca untuk email: %s", getattr(user, "id", "?"), e)
        return None


def avatar_untuk(user=None, nama="", gambar=None):
    """({nama, inisial, src}, Gambar | None) untuk satu orang.

    `src` kosong = partial menggambar inisial. Foto eksternal (mis. Google) dipakai
    langsung karena memang publik; foto yang diunggah ke aplikasi disisipkan CID.
    `gambar` = daftar Gambar milik pesan; foto yang sama hanya disisipkan sekali.
    """
    nama = nama or (
        (getattr(user, "display_name", "") or "")
        or " ".join(x for x in (getattr(user, "first_name", ""), getattr(user, "last_name", "")) if x)
        or getattr(user, "email", "")
    )
    hasil = {"nama": nama, "inisial": inisial(nama), "src": ""}
    if user is None:
        return hasil, None
    luar = str(getattr(user, "avatar", "") or "")
    if not getattr(user, "avatar_asset_id", None) and luar.startswith("https://"):
        hasil["src"] = luar
        return hasil, None
    cid = f"avatar-{hashlib.sha1(str(getattr(user, 'id', nama)).encode()).hexdigest()[:12]}"
    if gambar is not None and any(g.cid == cid for g in gambar):
        hasil["src"] = f"cid:{cid}"
        return hasil, None
    foto = _baca_avatar(user)
    if foto is None:
        return hasil, None
    hasil["src"] = f"cid:{cid}"
    baru = Gambar(cid, foto[0], foto[1])
    if gambar is not None:
        gambar.append(baru)
    return hasil, baru


# ---------------------------------------------------------------- kirim


def logo() -> Gambar:
    return Gambar(LOGO_CID, _LOGO.read_bytes(), "png")


class EmailBermerek(EmailMultiAlternatives):
    """EmailMultiAlternatives + gambar inline (multipart/related).

    Struktur: mixed[ related[ alternative[text, html], logo, avatar... ], lampiran ].
    Lampiran (.ics, .csv) tetap di luar `related`, jadi klien menampilkannya
    sebagai lampiran, bukan menyembunyikannya sebagai bagian HTML.
    """

    def __init__(self, *args, gambar=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.gambar = list(gambar)

    def _create_alternatives(self, msg):
        msg = super()._create_alternatives(msg)
        if not self.gambar:
            return msg
        related = SafeMIMEMultipart(_subtype="related", encoding=self.encoding)
        related.attach(msg)
        for g in self.gambar:
            bagian = MIMEImage(g.data, _subtype=g.subtipe)
            bagian.add_header("Content-ID", f"<{g.cid}>")
            bagian.add_header("Content-Disposition", "inline", filename=f"{g.cid}.{g.subtipe}")
            related.attach(bagian)
        return related


def koneksi_smtp(timeout=30):
    """(koneksi, alamat_pengirim) dari konfigurasi God Mode."""
    from plane.license.utils.instance_value import get_email_configuration

    host, user, pwd, port, use_tls, use_ssl, efrom = get_email_configuration()
    koneksi = get_connection(
        host=host,
        port=int(port or 587),
        username=user,
        password=pwd,
        use_tls=str(use_tls) == "1",
        use_ssl=str(use_ssl) == "1",
        timeout=timeout,
    )
    return koneksi, efrom


def buat_pesan(*, ke, subjek, html, teks=None, koneksi=None, dari=None, gambar=(), lampiran=()):
    """Satu pesan siap `send()`. Logo selalu ikut; `gambar` = avatar tambahan.

    `lampiran` = [(nama_berkas, isi, mimetype)].
    """
    if koneksi is None or dari is None:
        k, d = koneksi_smtp()
        koneksi = koneksi or k
        dari = dari or d
    pesan = EmailBermerek(
        subject=re.sub(r"[\x00-\x1F\x7F-\x9F]", "", subjek),
        body=teks if teks is not None else teks_polos(html),
        from_email=dari,
        to=[ke] if isinstance(ke, str) else list(ke),
        connection=koneksi,
        gambar=[logo(), *[g for g in gambar if g]],
    )
    pesan.attach_alternative(html, "text/html")
    for nama, isi, tipe in lampiran:
        pesan.attach(nama, isi, tipe)
    return pesan
