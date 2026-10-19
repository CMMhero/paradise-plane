# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kredensial ICE/TURN
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Daftar server ICE untuk panggilan, berikut kredensial TURN berumur pendek.

KENAPA TURN DIPERLUKAN PADAHAL SATU KANTOR
Asumsi awal fitur panggilan adalah "satu LAN, kandidat host sudah cukup". Itu
runtuh di jaringan nyata. Banyak jaringan kantor menyalakan isolasi antar-klien
di WiFi, dan sebagian memblokir UDP antar-perangkat. Kalau itu terjadi, WebRTC
tidak pernah menemukan jalur langsung dan panggilan diam total: SDP bertukar
dengan mulus, status naik, tapi tidak ada satu byte media pun mengalir.

TURN menutup itu dengan merelai media lewat server. Ia infrastruktur, bukan
aplikasi tambahan: tanpa UI, tanpa akun, tanpa basis data.

KENAPA KREDENSIALNYA BERUMUR PENDEK
Kredensial statis yang dibagikan ke setiap peramban berarti siapa pun yang
membuka DevTools bisa memakai relai ini selamanya untuk lalu lintas apa pun.
Skema shared-secret coturn membuat kredensialnya dihitung dari waktu kedaluwarsa
dan hanya berlaku beberapa jam.
"""

import base64
import hashlib
import hmac
import os
import time

# Berapa lama kredensial TURN berlaku. Cukup panjang untuk menampung panggilan
# terpanjang yang masuk akal, cukup pendek supaya yang bocor tidak berguna lama.
UMUR_KREDENSIAL = 6 * 3600


def _stun_bawaan() -> list:
    """STUN publik sebagai lapisan pertama.

    Gratis dan sering sudah cukup di jaringan yang ramah. Kalau internet kantor
    mati, ini sekadar tidak menghasilkan kandidat dan ICE tetap jalan lewat
    kandidat host maupun TURN lokal.
    """
    return [{"urls": "stun:stun.l.google.com:19302"}]


def daftar_ice(user_id) -> list:
    """Server ICE untuk satu pengguna.

    Selalu mengembalikan sesuatu yang bisa dipakai. Kalau TURN belum dikonfigurasi,
    yang keluar hanya STUN, dan panggilan tetap bisa jalan di jaringan yang
    mengizinkan sambungan langsung.
    """
    server = _stun_bawaan()

    host = os.environ.get("TURN_URL", "").strip()
    rahasia = os.environ.get("TURN_SECRET", "").strip()
    if not host or not rahasia:
        return server

    # Format wajib coturn untuk `use-auth-secret`: username adalah cap waktu
    # kedaluwarsa, opsional diikuti titik dua dan penanda pemakai. Passwordnya
    # HMAC-SHA1 dari username itu, di-base64.
    kedaluwarsa = int(time.time()) + UMUR_KREDENSIAL
    username = f"{kedaluwarsa}:{user_id}"
    sandi = base64.b64encode(
        hmac.new(rahasia.encode(), username.encode(), hashlib.sha1).digest()
    ).decode()

    server.append(
        {
            # UDP lebih dulu karena jauh lebih baik untuk media. TCP disertakan
            # sebagai jalan terakhir untuk jaringan yang memblokir UDP sama
            # sekali, dan di situlah TURN paling sering menyelamatkan.
            "urls": [f"turn:{host}?transport=udp", f"turn:{host}?transport=tcp"],
            "username": username,
            "credential": sandi,
        }
    )
    return server
