# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tugas yang menunggu persetujuan selesai
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu penyaring untuk "tugas ini sedang menunggu persetujuan selesai" (KEP-84).

Staf yang menggeser tugasnya ke selesai tidak memindahkan statusnya (KEP-55): tugas
tetap In Progress sampai atasan memutuskan. Tanpa penyaring ini tugas itu tampak
terlambat di mana-mana selama atasan belum sempat, padahal pekerjaannya sudah
diserahkan. Saklar APPROVAL_PENDING_NOT_LATE (bawaan hidup) mengatur apakah
tugas seperti itu dikeluarkan dari hitungan terlambat.

Setiap pemakai hitungan terlambat (Dashboard Divisi, widget Needs attention,
dasbor Home, pengingat tenggat, ringkasan harian dan direktur) memakai fungsi di
sini, supaya definisinya tidak berbeda antar layar.
"""

# Django imports
from django.db.models import Exists, OuterRef, Q

# Module imports
from plane.utils.saklar_instance import APPROVAL_PENDING_NOT_LATE, saklar_aktif


def menunggu_tidak_terlambat() -> bool:
    """Apakah tugas yang menunggu persetujuan dikecualikan dari hitungan terlambat."""
    return saklar_aktif(APPROVAL_PENDING_NOT_LATE)


def q_menunggu_persetujuan(ref: str = "pk") -> Q:
    """Q: tugas (`OuterRef(ref)` = id Issue) punya pengajuan selesai yang masih menunggu.

    `ref="pk"` untuk kueri atas Issue; `ref="issue_id"` untuk kueri atas model yang
    menunjuk Issue (mis. IssueAssignee).
    """
    from plane.db.models import STATUS_PERSETUJUAN_MENUNGGU, PersetujuanPenugasan  # noqa: PLC0415

    return Q(
        Exists(
            PersetujuanPenugasan.objects.filter(
                issue_id=OuterRef(ref),
                status=STATUS_PERSETUJUAN_MENUNGGU,
                deleted_at__isnull=True,
            )
        )
    )


def q_bisa_terlambat(ref: str = "pk") -> Q:
    """Q yang di-AND-kan ke setiap syarat "terlambat"/"segera jatuh tempo".

    Saklar mati: `Q()` (tanpa saringan, perilaku sebelum KEP-84). Saklar hidup:
    tugas yang menunggu persetujuan dikeluarkan.
    """
    if not menunggu_tidak_terlambat():
        return Q()
    return ~q_menunggu_persetujuan(ref)


def issue_ids_menunggu(issue_ids) -> set:
    """Id tugas (dari `issue_ids`) yang pengajuan selesainya masih menunggu."""
    from plane.db.models import STATUS_PERSETUJUAN_MENUNGGU, PersetujuanPenugasan  # noqa: PLC0415

    ids = list(issue_ids)
    if not ids:
        return set()
    return set(
        PersetujuanPenugasan.objects.filter(
            issue_id__in=ids, status=STATUS_PERSETUJUAN_MENUNGGU, deleted_at__isnull=True
        ).values_list("issue_id", flat=True)
    )
