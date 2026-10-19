# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: klien Google Calendar
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Klien tipis untuk Google Calendar API.

Sengaja memakai `requests` biasa, BUKAN google-api-python-client. SDK resmi
menarik puluhan dependensi transitif (google-auth, protobuf, httplib2, dan
seterusnya) untuk sesuatu yang di sini cuma empat panggilan REST. Ongkos
perawatan dan permukaan CVE-nya tidak sebanding.

Semua fungsi di sini MELEMPAR saat gagal. Pemanggilnya yang memutuskan apa
yang dicatat dan apa yang dilewati, karena hanya dia yang tahu apakah satu
kegagalan boleh menghentikan sisa antrean.
"""

# Python imports
import os
from datetime import timedelta

# Third party imports
import requests

# Django imports
from django.utils import timezone

# Module imports
from plane.license.utils.instance_value import get_configuration_value

TOKEN_URL = "https://oauth2.googleapis.com/token"
API_DASAR = "https://www.googleapis.com/calendar/v3"

# Tidak ada pemanggilan userinfo di sini, dan itu disengaja. Scope yang kita
# minta cuma `calendar.events`, yang TIDAK memberi izin membaca profil, jadi
# endpoint userinfo selalu menolak. Versi pertama berkas ini memanggilnya untuk
# menampilkan alamat email akun yang tersambung; panggilan itu tidak pernah
# berhasil sekali pun, hanya tidak terlihat karena dibungkus try/except.
#
# Menambah scope `userinfo.email` akan membuatnya bekerja, tapi itu berarti
# meminta izin tambahan ke 90 orang demi satu baris teks di halaman setelan.
# Tidak sebanding.

# Batas waktu tiap panggilan. Tanpa ini satu permintaan yang menggantung akan
# menahan seluruh tugas sinkronisasi sampai worker Celery-nya dianggap mati.
TIMEOUT = 20


def kredensial():
    """ID dan secret OAuth, dari God Mode lebih dulu lalu environment.

    Mengikuti pola provider OAuth login yang sudah ada di repo ini, supaya
    keduanya bisa diisi di tempat yang sama dan tidak ada yang bingung kenapa
    satu berhasil sementara yang lain tidak.
    """
    return get_configuration_value(
        [
            {
                "key": "GOOGLE_CALENDAR_CLIENT_ID",
                "default": os.environ.get("GOOGLE_CALENDAR_CLIENT_ID"),
            },
            {
                "key": "GOOGLE_CALENDAR_CLIENT_SECRET",
                "default": os.environ.get("GOOGLE_CALENDAR_CLIENT_SECRET"),
            },
        ]
    )


def tukar_kode(code, redirect_uri):
    """Tukar authorization code jadi refresh token.

    Balasannya HANYA memuat refresh_token pada persetujuan pertama. Karena itu
    URL persetujuan wajib memakai `access_type=offline` dan `prompt=consent`;
    tanpa keduanya, orang yang pernah menyetujui akan kembali tanpa refresh
    token dan sambungannya tampak berhasil padahal tidak bisa dipakai besok.
    """
    client_id, client_secret = kredensial()
    r = requests.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


def access_token(refresh_token):
    """Tukar refresh token jadi access token yang berlaku sekitar satu jam."""
    client_id, client_secret = kredensial()
    r = requests.post(
        TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
        },
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _badan_acara(judul, tenggat, deskripsi, url):
    """Susun satu acara sepanjang hari.

    `end.date` pada acara sepanjang hari bersifat EKSKLUSIF di Google Calendar,
    sama seperti DTEND di iCalendar, jadi diisi tanggal berikutnya. Diisi
    tanggal yang sama akan membuat acaranya tidak muncul sama sekali.
    """
    return {
        "summary": judul,
        "description": deskripsi + (f"\n\n{url}" if url else ""),
        "start": {"date": tenggat.strftime("%Y-%m-%d")},
        "end": {"date": (tenggat + timedelta(days=1)).strftime("%Y-%m-%d")},
        "transparency": "transparent",
        "reminders": {
            "useDefault": False,
            # Menyamai empat alarm pada lampiran .ics, supaya orang yang
            # memakai kedua jalur tidak mendapat pengingat pada waktu berbeda.
            "overrides": [
                {"method": "popup", "minutes": hari * 24 * 60} for hari in (7, 5, 3, 1)
            ],
        },
        "source": {"title": "Paradise Task Tracker", "url": url} if url else None,
    }


def buat_acara(token, calendar_id, judul, tenggat, deskripsi, url):
    """Buat acara baru, kembalikan ID-nya."""
    badan = {k: v for k, v in _badan_acara(judul, tenggat, deskripsi, url).items() if v is not None}
    r = requests.post(
        f"{API_DASAR}/calendars/{calendar_id}/events",
        headers={"Authorization": f"Bearer {token}"},
        json=badan,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["id"]


def ubah_acara(token, calendar_id, event_id, judul, tenggat, deskripsi, url):
    """Perbarui acara yang sudah ada.

    PATCH, bukan PUT: kita hanya ingin mengubah medan yang kita kelola, dan
    membiarkan apa pun yang ditambahkan pengguna sendiri pada acara itu tetap
    utuh. PUT akan menghapusnya diam-diam.
    """
    badan = {k: v for k, v in _badan_acara(judul, tenggat, deskripsi, url).items() if v is not None}
    r = requests.patch(
        f"{API_DASAR}/calendars/{calendar_id}/events/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
        json=badan,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["id"]


def hapus_acara(token, calendar_id, event_id):
    """Hapus acara. 404 dan 410 dianggap berhasil.

    Keduanya berarti acaranya memang sudah tidak ada, entah karena pengguna
    menghapusnya sendiri dari kalendernya. Menganggap itu galat akan membuat
    tugas sinkronisasi mencoba lagi selamanya untuk sesuatu yang sudah sesuai
    dengan yang kita inginkan.
    """
    r = requests.delete(
        f"{API_DASAR}/calendars/{calendar_id}/events/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=TIMEOUT,
    )
    if r.status_code in (404, 410):
        return
    r.raise_for_status()


def waktu_sekarang():
    return timezone.now()
