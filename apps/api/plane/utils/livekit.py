# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: token panggilan LiveKit
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Token akses LiveKit untuk panggilan suara dan video.

KENAPA PINDAH KE LIVEKIT
Versi pertama panggilan ditulis langsung di atas RTCPeerConnection, peer ke peer.
Secara teori itu cukup untuk dua orang di satu kantor. Dalam praktik ia gagal
berulang kali, dan yang paling menentukan: peer ke peer menuntut kedua KOMPUTER
bisa saling menghubungi langsung. Banyak jaringan kantor tidak mengizinkan itu,
dan tidak ada yang bisa diperbaiki dari sisi kode untuk melawannya.

LiveKit membalik arahnya. Ia SFU: kedua peramban menyambung ke SERVER, lalu
server yang meneruskan media. Jalur komputer ke server sudah pasti terbuka,
karena aplikasinya sendiri berjalan lewat jalur itu.

Yang ikut hilang bersama peer ke peer: negosiasi yang harus kita tulis sendiri,
penanganan glare saat dua orang menelepon bersamaan, rollback, sambung ulang
saat jaringan berkedip, dan perakitan track jauh. Semua itu sudah dikerjakan
klien LiveKit, dan tiap satunya pernah jadi bug di versi buatan sendiri.

TOKENNYA JWT BIASA, jadi tidak perlu menambah dependensi Python. Cukup PyJWT
yang sudah ada. Bentuk klaimnya mengikuti dokumentasi LiveKit: `sub` identitas
peserta, `iss` kunci API, dan klaim `video` berisi izin ruangnya.
"""

import os
import time

import jwt

# Token hanya dipakai sekali untuk masuk ruang, dan sambungannya bertahan sendiri
# sesudah itu. Umur pendek membatasi kerusakan kalau ia bocor dari log peramban.
UMUR_TOKEN = 900


def konfigurasi_ada() -> bool:
    return bool(os.environ.get("LIVEKIT_API_KEY") and os.environ.get("LIVEKIT_API_SECRET"))


def url_livekit() -> str:
    """Alamat yang DIHUBUNGI PERAMBAN, bukan nama container.

    Peramban berjalan di komputer karyawan dan tidak mengenal jaringan Docker.
    Salah mengisi ini membuat sambungan gagal tanpa pesan yang menunjuk sebabnya.
    """
    return os.environ.get("LIVEKIT_URL", "").strip()


def nama_ruang(ruang_id) -> str:
    """Nama ruang LiveKit diturunkan dari id Ruang obrolan.

    Diturunkan, bukan disimpan: dengan begitu tidak ada keadaan kedua yang bisa
    melenceng dari ruang obrolannya, dan tidak ada tabel yang harus dibersihkan
    saat panggilan berakhir.
    """
    return f"obrolan-{ruang_id}"


def token_panggilan(user, ruang_id) -> str:
    """Token masuk untuk satu orang ke satu ruang panggilan.

    Izinnya sengaja sempit: hanya boleh masuk ruang INI. Token yang berlaku untuk
    ruang mana pun berarti satu kebocoran cukup untuk menyadap panggilan siapa
    pun di kantor.
    """
    sekarang = int(time.time())
    klaim = {
        "iss": os.environ["LIVEKIT_API_KEY"],
        "sub": str(user.id),
        "nbf": sekarang,
        "exp": sekarang + UMUR_TOKEN,
        "name": user.display_name or user.email,
        "video": {
            "roomJoin": True,
            "room": nama_ruang(ruang_id),
            "canPublish": True,
            "canSubscribe": True,
            # Tidak perlu, dan mematikannya menutup satu jalur kirim data yang
            # tidak kita awasi sama sekali.
            "canPublishData": False,
        },
    }
    return jwt.encode(klaim, os.environ["LIVEKIT_API_SECRET"], algorithm="HS256")
