# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pencarian ruang DM
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu tempat untuk menjawab "di mana ruang obrolan antara A dan B".

Dulu jawabannya cuma ada di dalam view, terikat pada `request.user`. Begitu ada
penulis kedua yang bukan permintaan HTTP (tugas Celery yang mengirim penugasan
sebagai DM), menyalin logikanya berarti menyalin juga aturan "kedua pihak
langsung berlangganan". Satu salinan yang lupa membuat langganan menghasilkan
percakapan yang isinya tidak pernah terhitung sebagai belum dibaca, dan
kegagalan seperti itu tidak menimbulkan error di mana pun. Ia cuma tampak sepi.
"""

from plane.db.models import Langganan, Ruang


def ruang_dm(workspace_id, user_a_id, user_b_id):
    """Ruang DM antara dua orang, dibuat kalau belum ada.

    `get_or_create` memakai `kunci_dm` yang diurutkan di dalam model, jadi dua
    penulis yang berjalan pada detik yang sama tidak bisa menghasilkan dua ruang:
    yang kedua menabrak indeks unik lalu mengambil baris yang sudah ada.
    """
    kunci = Ruang.buat_kunci_dm(user_a_id, user_b_id)
    ruang, dibuat = Ruang.objects.get_or_create(
        kunci_dm=kunci,
        defaults={"workspace_id": workspace_id, "tipe": Ruang.Tipe.DM},
    )
    if dibuat:
        # Kedua belah pihak berlangganan sejak awal. Tanpa ini, penerima tidak
        # punya baris tempat menyimpan sudah-dibaca-sampai-mana, dan pesannya
        # tidak akan pernah terhitung sebagai belum dibaca.
        Langganan.objects.bulk_create(
            [
                Langganan(ruang=ruang, user_id=user_a_id),
                Langganan(ruang=ruang, user_id=user_b_id),
            ]
        )
    return ruang
