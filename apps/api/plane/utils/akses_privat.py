# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tugas privat (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapa yang boleh MELIHAT tugas privat.

Keputusan user (P29 #8): tugas privat hanya terlihat oleh assignee-nya,
pembuatnya, atasan langsung assignee-nya, dan Super Admin. Admin workspace
TIDAK termasuk, kecuali ia sendiri masuk salah satu kelompok itu. Atasan si
pembuat tidak ikut melihat hanya karena pembuatnya bawahannya.

"Atasan langsung" = orang yang memiliki salah satu assignee di
`_bawahan_ids(viewer, workspace, project)`. Itu helper yang sama dengan gerbang
penugasan, jadi jenjang baru (Leader, KEP u3) ikut tanpa menyentuh berkas ini.

Dua pintu, satu aturan:

- `saring_tugas_privat(qs, user)` untuk daftar. Satu kueri tambahan untuk
  mencari project yang punya tugas privat, lalu syaratnya masuk ke WHERE sebagai
  subkueri `EXISTS`. Tidak ada Python per baris.
- `boleh_lihat_tugas(issue, user)` untuk satu objek. Detail yang tak boleh
  dilihat dijawab 404, bukan 403: 403 membocorkan bahwa tugasnya ada.

Agregat (KPI, total Dashboard Divisi) sengaja TIDAK memakai saringan ini.
"""

import uuid

from django.db.models import Exists, OuterRef, Q

from plane.db.models import Issue, IssueAssignee
from plane.db.superadmin import is_super_admin


def _anonim(user):
    return user is None or getattr(user, "is_anonymous", True)


def _assignee_di(user_ids, issue_ref="pk"):
    return Exists(
        IssueAssignee.objects.filter(
            issue_id=OuterRef(issue_ref),
            assignee_id__in=user_ids,
            deleted_at__isnull=True,
        )
    )


def _bawahan_per_project(user):
    """{project_id: {bawahan}} untuk project yang punya tugas privat dan user punya bawahan di sana."""
    from plane.utils.hierarki import TINGKAT_LEADER, _bawahan_ids, penempatan_semua  # noqa: PLC0415

    privat = Issue.all_objects.filter(is_private=True, deleted_at__isnull=True)
    per_workspace = {}
    for ws_id, pid in privat.values_list("workspace_id", "project_id").distinct():
        per_workspace.setdefault(ws_id, set()).add(pid)

    hasil = {}
    for ws_id, pids in per_workspace.items():
        # Leader sampai Direktur punya bawahan; `_bawahan_ids` sendiri yang menentukan
        # cakupannya per project, sama dengan `boleh_lihat_tugas`.
        if max((t for t, _, _ in penempatan_semua(user.id, ws_id)), default=0) < TINGKAT_LEADER:
            continue
        for pid in pids:
            bawahan = _bawahan_ids(user.id, ws_id, pid)
            if bawahan:
                hasil[pid] = bawahan
    return hasil


def syarat_tugas_terlihat(user, prefix=""):
    """`Q` yang benar untuk tugas yang boleh dilihat user, atau None kalau tanpa batas.

    `prefix` untuk queryset model lain yang menunjuk tugas, mis. `"issue__"` di
    IssueActivity. Baris yang tidak menunjuk tugas apa pun ikut lolos.
    """
    if not _anonim(user) and is_super_admin(user):
        return None
    syarat = Q(**{f"{prefix}is_private": False})
    if prefix:
        syarat |= Q(**{f"{prefix[:-2]}__isnull": True})
    if _anonim(user):
        return syarat
    ref = f"{prefix[:-2]}_id" if prefix else "pk"
    syarat |= Q(**{f"{prefix}created_by_id": user.id}) | Q(_assignee_di([user.id], ref))
    for pid, bawahan in _bawahan_per_project(user).items():
        syarat |= Q(**{f"{prefix}project_id": pid}) & Q(_assignee_di(bawahan, ref))
    return syarat


def saring_tugas_privat(qs, user, prefix=""):
    """Queryset tanpa tugas privat yang tak boleh dilihat user."""
    syarat = syarat_tugas_terlihat(user, prefix)
    return qs if syarat is None else qs.filter(syarat)


def boleh_lihat_tugas(issue, user):
    if issue is None or not issue.is_private:
        return True
    if _anonim(user):
        return False
    if issue.created_by_id == user.id or is_super_admin(user):
        return True
    from plane.utils.hierarki import _bawahan_ids  # noqa: PLC0415

    assignee = set(
        IssueAssignee.objects.filter(issue_id=issue.id, deleted_at__isnull=True).values_list("assignee_id", flat=True)
    )
    if user.id in assignee:
        return True
    return bool(assignee) and bool(assignee & _bawahan_ids(user.id, issue.workspace_id, issue.project_id))


def tugas_tersembunyi_ids(issue_ids, user):
    """Id dari `issue_ids` yang privat dan tak boleh dilihat user. Satu kueri kalau tak ada yang privat."""
    if not issue_ids:
        return set()
    return {
        issue.id
        for issue in Issue.all_objects.filter(id__in=issue_ids, is_private=True)
        if not boleh_lihat_tugas(issue, user)
    }


def penonton_tugas_ids(issue, kandidat_ids):
    """Bagian dari `kandidat_ids` yang boleh melihat tugas ini (untuk notifikasi, kartu, email).

    Urutan dan bentuk id (str atau UUID) dari pemanggil dipertahankan.
    """
    kandidat = list(dict.fromkeys(kandidat_ids))
    if not issue.is_private:
        return kandidat
    from plane.db.superadmin import super_admin_user_ids  # noqa: PLC0415
    from plane.utils.hierarki import _bawahan_ids  # noqa: PLC0415

    assignee = {
        str(a)
        for a in IssueAssignee.objects.filter(issue_id=issue.id, deleted_at__isnull=True).values_list(
            "assignee_id", flat=True
        )
    }
    langsung = assignee | {str(issue.created_by_id)} | {str(u) for u in super_admin_user_ids()}

    def boleh(uid):
        if str(uid) in langsung:
            return True
        if not assignee:
            return False
        bawahan = _bawahan_ids(uuid.UUID(str(uid)), issue.workspace_id, issue.project_id)
        return bool(assignee & {str(b) for b in bawahan})

    return [uid for uid in kandidat if boleh(uid)]


def tugas_privat_tersembunyi(user):
    """Subkueri id tugas privat yang tak boleh dilihat user, atau None kalau tak ada batas."""
    syarat = syarat_tugas_terlihat(user)
    if syarat is None:
        return None
    return Issue.all_objects.filter(is_private=True).exclude(syarat).values("id")


def saring_kabar_privat(qs, user):
    """Notifikasi tanpa yang menunjuk tugas privat yang (sudah) tak boleh dilihat user.

    Fan-out tidak mengirim ke mereka sejak awal; ini untuk notifikasi lama, mis.
    orang yang sudah dilepas dari assignee tugas privat.
    """
    tersembunyi = tugas_privat_tersembunyi(user)
    if tersembunyi is None:
        return qs
    return qs.exclude(entity_name="issue", entity_identifier__in=tersembunyi)


PESAN_TOLAK_PRIVAT = "Only the creator and people who can edit this work item can change whether it is private."


def galat_ubah_privat(issue, actor, data):
    """Pesan 403 kalau `data` mengubah `is_private` dan actor tak berhak, selain itu None.

    Berhak = pembuatnya, atau yang boleh mengubah tugas menurut `galat_ubah_tugas`.
    Katup gerbang hierarki sengaja diabaikan: mematikan gerbang membuka edit untuk
    semua anggota, tapi tidak boleh membuat semua anggota bisa membuka tugas privat.
    """
    if "is_private" not in data or bool(data.get("is_private")) == issue.is_private:
        return None
    if issue.created_by_id == actor.id:
        return None
    from plane.utils.hierarki import galat_ubah_tugas  # noqa: PLC0415

    if galat_ubah_tugas(issue.project_id, issue, actor=actor, abaikan_katup=True) is None:
        return None
    return PESAN_TOLAK_PRIVAT
