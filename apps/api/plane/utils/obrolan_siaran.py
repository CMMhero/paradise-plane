# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: siaran real-time obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siarkan kejadian obrolan lewat Redis, supaya `apps/live` meneruskannya.

Django tetap SATU-SATUNYA yang menulis pesan ke database. Yang dikirim ke sini
cuma pemberitahuan "ada sesuatu terjadi di ruang X", dan peramban yang menerima
akan menarik ulang isinya sendiri. Menyiarkan isi pesan lengkap lewat Redis
berarti aturan siapa-boleh-melihat-apa harus ditegakkan di dua tempat, dan yang
kedua pasti tertinggal saat aturannya berubah.

ponytail: siaran satu arah tanpa jaminan sampai. Kalau Redis mati atau peramban
sedang tidak terhubung, tidak ada yang hilang: penarikan berkala tetap ada
sebagai jaring pengaman, cuma jadi lebih lambat. Itu sebabnya seluruh fungsi di
berkas ini menelan galatnya sendiri dan tidak pernah menggagalkan pengiriman
pesan. Pesan yang tersimpan tapi telat muncul jauh lebih baik daripada pesan
yang gagal terkirim karena Redis sedang ngambek.
"""

import json
import logging

from plane.settings.redis import redis_instance

# "plane.api", BUKAN "plane". Konfigurasi logging produksi memakai
# disable_existing_loggers dan tidak punya entri untuk "plane" polos.
logger = logging.getLogger("plane.api")

# Awalan kanal Redis. `apps/live` berlangganan dengan pola `obrolan:*`, jadi
# menambah jenis kejadian baru di sini tidak perlu mengubah apa pun di sana.
AWALAN_KANAL = "obrolan:"


def kanal_ruang(ruang_id) -> str:
    return f"{AWALAN_KANAL}{ruang_id}"


def siarkan(ruang_id, tipe: str, oleh_id=None, **tambahan) -> None:
    """Beri tahu bahwa sesuatu terjadi di sebuah ruang.

    `oleh_id` dipakai penerima untuk mengabaikan gaung kirimannya sendiri:
    pengirim sudah memperbarui layarnya sendiri saat menekan kirim, dan menarik
    ulang sekali lagi membuat pesannya berkedip.
    """
    try:
        ri = redis_instance()
        ri.publish(
            kanal_ruang(ruang_id),
            json.dumps({"tipe": tipe, "ruang": str(ruang_id), "oleh": str(oleh_id) if oleh_id else None, **tambahan}),
        )
    except Exception as e:
        # Sengaja ditelan. Lihat alasannya di docstring modul.
        logger.warning("siaran-obrolan: gagal menyiarkan %s untuk ruang %s: %s", tipe, ruang_id, e)
