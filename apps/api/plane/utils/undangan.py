# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: masa berlaku undangan (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Undangan workspace & project kedaluwarsa sesudah INVITE_EXPIRY_DAYS hari.

0 (bawaan) = tidak pernah kedaluwarsa, perilaku sebelum setelan ini ada.
Umurnya dihitung dari `created_at` undangan. Undangan kedaluwarsa TIDAK dihapus:
daftar undangan tetap menampilkannya (dengan tanda `is_expired`) supaya admin
bisa mengirim ulang atau membuangnya; yang ditolak hanya menerimanya.
"""

from datetime import timedelta

from django.utils import timezone

# Kode galat untuk klien. Pesannya bahasa Inggris seperti galat undangan upstream.
KODE_KEDALUWARSA = "INVITE_EXPIRED"
PESAN_KEDALUWARSA = "This invitation has expired. Ask the workspace admin to send a new one."


def hari_berlaku() -> int:
    """Umur undangan dalam hari; 0 = tidak pernah kedaluwarsa."""
    from plane.utils.saklar_instance import INVITE_EXPIRY_DAYS, setelan_angka  # noqa: PLC0415

    return setelan_angka(INVITE_EXPIRY_DAYS)


def batas_dibuat(hari=None, sekarang=None):
    """Undangan yang dibuat SEBELUM waktu ini sudah kedaluwarsa. None = tidak ada batas."""
    hari = hari_berlaku() if hari is None else hari
    if not hari:
        return None
    return (sekarang or timezone.now()) - timedelta(days=hari)


def kedaluwarsa(undangan, batas=...) -> bool:
    """Apakah undangan ini sudah kedaluwarsa. `batas` boleh dihitung sekali oleh pemanggil."""
    if batas is ...:
        batas = batas_dibuat()
    if batas is None or undangan.created_at is None:
        return False
    return undangan.created_at < batas


def saring_berlaku(queryset):
    """Queryset undangan yang masih berlaku (belum kedaluwarsa)."""
    batas = batas_dibuat()
    if batas is None:
        return queryset
    return queryset.filter(created_at__gte=batas)


def tanda_kedaluwarsa(serializer, undangan) -> bool:
    """Isi `is_expired` di serializer undangan; batasnya dihitung sekali per balasan."""
    akar = serializer.root
    if not hasattr(akar, "_batas_undangan"):
        akar._batas_undangan = batas_dibuat()
    return kedaluwarsa(undangan, batas=akar._batas_undangan)


def balasan_kedaluwarsa():
    """Response 400 baku untuk undangan kedaluwarsa."""
    from rest_framework import status  # noqa: PLC0415
    from rest_framework.response import Response  # noqa: PLC0415

    return Response(
        {"error": PESAN_KEDALUWARSA, "error_code": KODE_KEDALUWARSA},
        status=status.HTTP_400_BAD_REQUEST,
    )
