# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: anggota baru otomatis ikut kanal sistem
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Anggota workspace baru (atau yang diaktifkan lagi) langsung ikut kanal sistem.

Signal ini tidak menangkap `bulk_create` (dipakai saat menerima undangan), jadi
`ChatConversationsEndpoint` punya jaring kedua yang malas. Keduanya memanggil
fungsi yang sama di `plane/utils/kanal_sistem.py`.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="db.WorkspaceMember")
def anggota_workspace_ikut_kanal_sistem(sender, instance, created, **kwargs):
    from plane.utils.kanal_organisasi import sinkronkan_kanal_organisasi  # noqa: PLC0415
    from plane.utils.kanal_sistem import ikutkan_aman, ikutkan_jika_belum  # noqa: PLC0415

    workspace_id, member_id = instance.workspace_id, instance.member_id
    # Kanal divisi/departemen: keluar dari workspace = keluar dari kanalnya, masuk
    # (lagi) = ikut kanal sesuai penempatan yang mungkin sudah diisi lebih dulu.
    # Tiap simpan, bukan cuma `created`: pengaktifan ulang juga simpan biasa.
    # Biayanya beberapa kueri kecil, dan WorkspaceMember jarang disimpan.
    transaction.on_commit(lambda: sinkronkan_kanal_organisasi(workspace_id, member_id))
    if not instance.is_active:
        return
    # Simpan ulang biasa (preferensi tampilan, dsb.) cukup satu COUNT; yang baru
    # dibuat atau diaktifkan lagi diikutkan penuh. Sesudah commit: anggota dari
    # transaksi yang lalu dibatalkan tidak boleh meninggalkan langganan.
    if created:
        transaction.on_commit(lambda: ikutkan_aman(workspace_id, [member_id]))
    else:
        transaction.on_commit(lambda: ikutkan_jika_belum(workspace_id, member_id))
