# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pembersihan harian inbox
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Arsipkan atau hapus notifikasi inbox yang sudah lebih tua dari N hari.

Hari dan tindakannya diatur Super Admin di God Mode (NOTIFICATION_CLEANUP_DAYS,
bawaan 7, 0 = mati; NOTIFICATION_CLEANUP_ACTION, bawaan arsip). Umur dihitung dari
`created_at`, dibaca atau belum. Yang sedang ditunda (`snoozed_till` di depan)
dilewati: menundanya berarti "ingatkan nanti", dan membersihkannya berdasarkan
umur membatalkan itu.

Diarsipkan = hanya `archived_at` yang diisi, orangnya masih bisa membukanya di
filter Archived dan menghitung ulang badge belum-dibaca (arsip tidak dihitung).
Dihapus = baris dibuang KERAS lewat `all_objects` (queryset `objects` hanya menghapus
lunak, dan tidak ada task yang membuang baris lunak Notification).
"""

# Python imports
import logging
from datetime import timedelta

# Django imports
from django.db.models import Q
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import Notification
from plane.utils import aturan
from plane.utils.aturan.area_notifikasi import (
    NOTIFICATION_CLEANUP_ACTION,
    NOTIFICATION_CLEANUP_DAYS,
    PEMBERSIHAN_HAPUS,
)
from plane.utils.sinyal_data import siarkan_notifikasi

logger = logging.getLogger("plane.worker")

# Sekali ubah berapa baris. Satu UPDATE/DELETE raksasa mengunci tabel cukup lama
# untuk terasa di aplikasi.
UKURAN_BATCH = 2000


def _kandidat(batas, sekarang, hapus):
    """Notifikasi yang lebih tua dari `batas` dan tidak sedang ditunda.

    Arsip: yang belum diarsipkan. Hapus: semuanya, termasuk yang sudah diarsipkan
    (arsip adalah tempat tunggu, bukan pengecualian).
    """
    menu = Notification.objects.filter(created_at__lt=batas).filter(
        Q(snoozed_till__isnull=True) | Q(snoozed_till__lte=sekarang)
    )
    return menu if hapus else menu.filter(archived_at__isnull=True)


@shared_task
def bersihkan_notifikasi_lama():
    """Jalan harian lewat celery beat. Mengembalikan jumlah notifikasi yang diproses."""
    hari = aturan.get_int(NOTIFICATION_CLEANUP_DAYS)
    if hari <= 0:
        return 0
    hapus = aturan.get_choice(NOTIFICATION_CLEANUP_ACTION) == PEMBERSIHAN_HAPUS
    sekarang = timezone.now()
    batas = sekarang - timedelta(days=hari)

    diproses = 0
    terdampak = set()  # (workspace_id, receiver_id): badge dan daftar mereka harus disegarkan
    while True:
        baris = list(_kandidat(batas, sekarang, hapus).values_list("pk", "workspace_id", "receiver_id")[:UKURAN_BATCH])
        if not baris:
            break
        pks = [b[0] for b in baris]
        terdampak.update((b[1], b[2]) for b in baris)
        if hapus:
            Notification.all_objects.filter(pk__in=pks).delete()
        else:
            # `archived_at__isnull` diulang: notifikasi yang diarsipkan orangnya sendiri
            # di antara SELECT dan UPDATE tidak ditimpa waktunya.
            Notification.objects.filter(pk__in=pks, archived_at__isnull=True).update(
                archived_at=sekarang, updated_at=sekarang
            )
        diproses += len(pks)

    per_workspace = {}
    for workspace_id, receiver_id in terdampak:
        per_workspace.setdefault(workspace_id, set()).add(receiver_id)
    for workspace_id, penerima in per_workspace.items():
        siarkan_notifikasi(workspace_id, penerima)

    logger.info("Notifikasi: %s notifikasi lebih dari %s hari %s", diproses, hari, "dihapus" if hapus else "diarsipkan")
    return diproses
