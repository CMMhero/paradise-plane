# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kredensial ICE/TURN
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kredensial TURN: bentuknya harus persis, kalau tidak coturn menolak diam-diam.

Skema `use-auth-secret` menuntut username berupa cap waktu kedaluwarsa dan
password berupa HMAC-SHA1 dari username itu, di-base64. Salah satu huruf saja
membuat coturn menolak alokasi relai, dan penolakannya tidak muncul di peramban
sebagai error: panggilan sekadar tidak pernah tersambung.

Yang paling ingin dijaga di sini justru sifat kedua: daftar ini TIDAK PERNAH
kosong. Kalau TURN belum dikonfigurasi, panggilan harus tetap mungkin di
jaringan yang mengizinkan sambungan langsung, bukan mati total.
"""

import base64
import hashlib
import hmac
import time
from unittest.mock import patch

from plane.utils.ice import UMUR_KREDENSIAL, daftar_ice


def test_tanpa_turn_masih_mengembalikan_stun():
    with patch.dict("os.environ", {"TURN_URL": "", "TURN_SECRET": ""}):
        hasil = daftar_ice("u1")
    assert len(hasil) == 1
    assert "stun:" in hasil[0]["urls"]


def test_turn_setengah_dikonfigurasi_diabaikan():
    """Alamat tanpa rahasia (atau sebaliknya) tidak akan pernah bisa dipakai.
    Mengirimkannya ke peramban hanya menambah kandidat yang pasti gagal."""
    with patch.dict("os.environ", {"TURN_URL": "host:3478", "TURN_SECRET": ""}):
        assert len(daftar_ice("u1")) == 1
    with patch.dict("os.environ", {"TURN_URL": "", "TURN_SECRET": "rahasia"}):
        assert len(daftar_ice("u1")) == 1


def test_kredensial_cocok_dengan_skema_coturn():
    rahasia = "rahasia-uji"
    with patch.dict("os.environ", {"TURN_URL": "128.159.110.5:3478", "TURN_SECRET": rahasia}):
        hasil = daftar_ice("u1")

    turn = hasil[-1]
    kedaluwarsa, penanda = turn["username"].split(":")

    assert penanda == "u1"
    assert int(kedaluwarsa) > time.time(), "kredensial tidak boleh lahir sudah kedaluwarsa"
    assert int(kedaluwarsa) <= time.time() + UMUR_KREDENSIAL + 5

    # Dihitung ulang di sini dengan cara yang sama seperti coturn, bukan
    # dibandingkan dengan nilai yang disalin dari implementasinya.
    harapan = base64.b64encode(
        hmac.new(rahasia.encode(), turn["username"].encode(), hashlib.sha1).digest()
    ).decode()
    assert turn["credential"] == harapan


def test_udp_dan_tcp_keduanya_ditawarkan():
    """UDP untuk kualitas, TCP sebagai jalan terakhir di jaringan yang memblokir
    UDP sama sekali. Justru di jaringan seperti itu TURN paling dibutuhkan."""
    with patch.dict("os.environ", {"TURN_URL": "host:3478", "TURN_SECRET": "s"}):
        turn = daftar_ice("u1")[-1]

    gabung = " ".join(turn["urls"])
    assert "transport=udp" in gabung
    assert "transport=tcp" in gabung


def test_stun_tetap_didahulukan():
    """ICE mencoba semua berbarengan, tapi urutannya tetap menyatakan niat:
    jalur langsung dulu, relai belakangan. Relai menambah hop dan latensi."""
    with patch.dict("os.environ", {"TURN_URL": "host:3478", "TURN_SECRET": "s"}):
        hasil = daftar_ice("u1")

    assert "stun:" in str(hasil[0]["urls"])
    assert "turn:" in str(hasil[1]["urls"])


def test_tiap_pengguna_dapat_kredensial_berbeda():
    """Penanda pemakai ikut di username supaya penyalahgunaan bisa dilacak ke
    satu akun, bukan ke seluruh kantor."""
    with patch.dict("os.environ", {"TURN_URL": "host:3478", "TURN_SECRET": "s"}):
        a = daftar_ice("user-a")[-1]["username"]
        b = daftar_ice("user-b")[-1]["username"]

    assert a.endswith(":user-a")
    assert b.endswith(":user-b")
