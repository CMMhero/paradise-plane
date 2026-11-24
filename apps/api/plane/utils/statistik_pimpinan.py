# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: angka pimpinan hanya dari tugas buatan atasan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Direktur dan sekretaris hanya menghitung tugas buatan Supervisor ke atas.

Keputusan user 2026-11-20: angka terlambat, statistik, dan dashboard yang dibaca
direktur (dan sekretaris, yang jangkauannya sama) tidak memuat tugas buatan staf.
Supervisor dan manager tetap melihat angka penuh timnya. God Mode bisa mematikan
saringan ini (ORG_VIEW_LEADER_CREATED_ONLY); bawaannya menyala.

Jenjang pembuat = jenjang TERTINGGI orangnya di workspace, bukan jenjang yang
berlaku di project tugas itu (KEP-93). Manager divisi A yang duduk sebagai staf
di departemen divisi B tetap manager bagi direktur; yang ditanyakan direktur
adalah "apa yang dibuat pimpinan", bukan "siapa atasan di departemen ini".

Tugas tanpa pembuat (`created_by = NULL`) adalah permintaan lintas departemen
(`views/issue/cross_division.py`): yang dihitung jenjang PEMINTA-nya.
"""

from django.db.models import Exists, OuterRef, Q

from plane.db.models import TINGKAT_MEMBER, TINGKAT_SUPERVISOR, JabatanOrganisasi, PermintaanLintasDivisi
from plane.db.models.hierarki import menjangkau_seluruh_organisasi
from plane.utils import aturan
from plane.utils.aturan.area_visibilitas import ATTENTION_ORG_MIN_CREATOR_LEVEL, ORG_VIEW_LEADER_CREATED_ONLY
from plane.utils.hierarki import tingkat_anggota


def _berjenjang_pimpinan(ref, minimum=TINGKAT_SUPERVISOR):
    return Exists(
        JabatanOrganisasi.objects.filter(
            member_id=OuterRef(ref),
            workspace_id=OuterRef("workspace_id"),
            tingkat__gte=minimum,
            deleted_at__isnull=True,
        )
    )


def q_dibuat_pimpinan(minimum=TINGKAT_SUPERVISOR):
    """Q untuk kueri atas Issue: pembuatnya (atau peminta lintas departemennya) berjenjang `minimum` ke atas."""
    peminta_pimpinan = PermintaanLintasDivisi.objects.filter(
        intake_issue__issue_id=OuterRef("pk"), deleted_at__isnull=True
    ).filter(_berjenjang_pimpinan("diminta_oleh_id", minimum))
    return Q(_berjenjang_pimpinan("created_by_id", minimum)) | (
        Q(created_by__isnull=True) & Q(Exists(peminta_pimpinan))
    )


def q_angka_seluruh_organisasi():
    """Q untuk angka yang dibaca jangkauan seluruh organisasi (mis. laporan direktur)."""
    return q_dibuat_pimpinan() if aturan.get_bool(ORG_VIEW_LEADER_CREATED_ONLY) else Q()


def hanya_buatan_pimpinan(user, workspace_id) -> bool:
    """Apakah angka pimpinan `user` disaring ke tugas buatan Supervisor ke atas."""
    return aturan.get_bool(ORG_VIEW_LEADER_CREATED_ONLY) and menjangkau_seluruh_organisasi(
        tingkat_anggota(user.id, workspace_id)
    )


def cakupan_angka(user, workspace_id):
    """Q yang di-AND-kan ke setiap hitungan tugas di layar pimpinan `user`."""
    return q_dibuat_pimpinan() if hanya_buatan_pimpinan(user, workspace_id) else Q()


def cakupan_perhatian(user, workspace_id):
    """Q untuk kelompok "team_overdue" di widget Needs attention.

    Jangkauan seluruh organisasi (sekretaris, direktur) hanya melihat tugas buatan
    jenjang `ATTENTION_ORG_MIN_CREATOR_LEVEL` ke atas (bawaan manager, jadi
    tugas buatan supervisor dilewati). Bukan jangkauan itu: tidak disaring.
    Aturan ini berdiri sendiri dari ORG_VIEW_LEADER_CREATED_ONLY, yang tetap
    mengatur angka di dashboard dan laporan.
    """
    if not menjangkau_seluruh_organisasi(tingkat_anggota(user.id, workspace_id)):
        return Q()
    minimum = aturan.get_int(ATTENTION_ORG_MIN_CREATOR_LEVEL)
    return Q() if minimum <= TINGKAT_MEMBER else q_dibuat_pimpinan(minimum)
