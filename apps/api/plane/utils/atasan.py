# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tidak ada yang bisa menugaskan atasannya
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tidak seorang pun bisa menjadikan atasannya assignee (P29 putaran 2).

Keputusan user: semua orang yang punya jenjang terikat. Penerima yang jenjangnya
di project itu LEBIH TINGGI dari jenjang pelaku tidak bisa ditugaskan olehnya.
Setingkat tidak diatur di sini; aturan rekan yang lama tetap berlaku. Admin
workspace mengikuti jenjangnya sendiri. Yang bebas hanya Super Admin dan admin
workspace yang tidak ditempatkan di mana pun. Menugaskan diri sendiri selalu boleh.

Murni perbandingan angka jenjang per project (`peta_tingkat`, KEP-93), jadi
jenjang baru di antara dua jenjang lama ikut tercakup tanpa perubahan di sini.

Sengaja tidak bergantung pada katup gerbang maupun ASSIGN_DOWN_ONLY: keduanya
mengatur tangga persetujuan dan wewenang ke bawah, sedangkan larangan ke atas ini
berlaku apa pun setelannya. Saklarnya sendiri ada di God Mode (BLOCK_ASSIGN_UPWARD).
"""

from plane.db.models import JabatanOrganisasi, Project, TINGKAT_MEMBER, WorkspaceMember
from plane.utils import aturan
from plane.utils.aturan.area_tugas import BLOCK_ASSIGN_UPWARD
from plane.utils.hierarki import _id_saja, adalah_admin_penuh, aktor_dari_context, peta_tingkat, tingkat_efektif

PESAN_ATASAN = "Anda tidak dapat menugaskan atasan Anda: jenjang penerima tugas ini di atas jenjang Anda."


def _bebas(actor, workspace_id):
    """Super Admin, atau admin workspace yang tidak ditempatkan di mana pun di workspace ini."""
    from plane.db.superadmin import is_super_admin  # noqa: PLC0415

    if is_super_admin(actor):
        return True
    return (
        adalah_admin_penuh(actor, workspace_id)
        and not JabatanOrganisasi.objects.filter(workspace_id=workspace_id, member_id=actor.id).exists()
    )


def _admin_ids(workspace_id, user_ids):
    """Id (str) di antara `user_ids` yang Super Admin atau admin workspace aktif."""
    from plane.db.superadmin import super_admin_user_ids  # noqa: PLC0415

    ids = {str(u) for u in user_ids}
    admin = WorkspaceMember.objects.filter(
        workspace_id=workspace_id, member_id__in=ids, role=20, is_active=True
    ).values_list("member_id", flat=True)
    return ({str(u) for u in admin} | {str(u) for u in super_admin_user_ids()}) & ids


def atasan_di_antara(actor, workspace_id, project_id, kandidat_ids):
    """Bagian `kandidat_ids` yang jenjangnya di project ini di atas `actor`.

    Pelaku tanpa jenjang dihitung Staf (`tingkat_efektif`); admin yang punya
    jenjang di tempat lain tetapi tidak di project ini memakai jenjang orangnya
    (yang tertinggi), sama seperti setiap keputusan wewenang KEP-93. Tanpa pelaku
    (None, mis. papan publik anonim) juga dihitung Staf: gagal ke arah aman.

    Penerima tanpa jenjang dihitung Staf, kecuali Super Admin atau admin
    workspace: mereka di atas semua jenjang, jadi hanya pelaku yang bebas yang
    bisa menugaskan mereka.
    """
    actor_id = str(getattr(actor, "id", None))
    kandidat = {_id_saja(k) for k in (kandidat_ids or []) if k is not None and str(_id_saja(k)) != actor_id}
    if not kandidat or not aturan.get_bool(BLOCK_ASSIGN_UPWARD) or (actor is not None and _bebas(actor, workspace_id)):
        return set()
    tingkat_saya = TINGKAT_MEMBER if actor is None else tingkat_efektif(actor.id, workspace_id, project_id)
    peta = {str(u): t for u, t in peta_tingkat(workspace_id, project_id).items()}
    tanpa_jenjang = [k for k in kandidat if str(k) not in peta]
    puncak = _admin_ids(workspace_id, tanpa_jenjang) if tanpa_jenjang else set()
    return {k for k in kandidat if str(k) in puncak or peta.get(str(k), TINGKAT_MEMBER) > tingkat_saya}


def galat_atasan(actor, project_id, assignee_ids, lama=()):
    """PESAN_ATASAN kalau ada penerima BARU di atas `actor`, selain itu None.

    `lama` = assignee yang sudah ada di tugas itu; mereka tidak diperiksa ulang,
    sama dengan `galat_penempatan`.
    """
    lama_set = {str(_id_saja(a)) for a in (lama or [])}
    baru = [a for a in (assignee_ids or []) if a is not None and str(_id_saja(a)) not in lama_set]
    if not baru:
        return None
    workspace_id = Project.objects.filter(pk=project_id).values_list("workspace_id", flat=True).first()
    if workspace_id is None:
        return None
    return PESAN_ATASAN if atasan_di_antara(actor, workspace_id, project_id, baru) else None


def galat_default_assignee(context, project, default_assignee):
    """PESAN_ATASAN kalau default assignee BARU sebuah project di atas penyetelnya.

    Default assignee dipakai saat tugas dibuat tanpa assignee, jadi menyetelnya
    sama dengan menugaskan orang itu nanti. `project` None = project baru: jenjang
    dibaca tanpa tempat (jenjang tertinggi tiap orang).
    """
    if default_assignee is None or str(_id_saja(default_assignee)) == str(
        getattr(project, "default_assignee_id", None)
    ):
        return None
    atasan = atasan_di_antara(
        aktor_dari_context(context), context["workspace_id"], getattr(project, "id", None), [default_assignee]
    )
    return PESAN_ATASAN if atasan else None
