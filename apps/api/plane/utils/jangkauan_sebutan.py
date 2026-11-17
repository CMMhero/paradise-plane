# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: siapa yang dikabari saat disebut (@)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Menyebut siapa pun boleh; yang DIKABARI hanya yang berada di dalam work item itu.

Keputusan user 2026-11-17: pemilih "@" di judul, deskripsi, dan komentar
menawarkan seluruh karyawan workspace, dan sebutannya tampil sebagai nama. Tapi
notifikasi (inbox, kartu obrolan, email, pop-up) hanya untuk orang yang berada di
project/departemen/divisi work item itu. Orang di luar tidak menerima apa pun,
tidak dicatat sebagai `IssueMention`, dan tidak dijadikan subscriber diam-diam:
mereka memang tidak bisa membuka work item itu, jadi kabar untuk mereka hanya
tautan yang berakhir di 404.

## Aturan "di dalam"

Satu dari dua:

1. **Anggota project yang hidup** (`ProjectMember.is_active`). Ini wujud nyata
   jangkauan hierarki: `db/jangkauan.py` menulis `jangkauan_hierarki` (staf dan
   supervisor departemennya, manager divisinya) menjadi `ProjectMember`, dan
   keanggotaan eksplisit (tamu, pengecualian KEP-29) juga di sini. Inilah
   pengertian keanggotaan yang dipakai seluruh notifikasi lain (subscriber,
   balasan komentar, @all), jadi sebutan memakai yang sama.
2. **Jangkauan seluruh organisasi** (direktur, sekretaris;
   `menjangkau_seluruh_organisasi`) yang masih anggota aktif workspace. Mereka
   melihat semua project; baris ini menjaga mereka tetap dikabari walau
   sinkron keanggotaan belum berjalan untuk project yang baru dibuat.

Bukan dari keanggotaan WORKSPACE: itu justru "semua orang", yang ingin dibatasi.
"""

from plane.db.models import JabatanOrganisasi, ProjectMember, WorkspaceMember, menjangkau_seluruh_organisasi


def _uuid_str(nilai) -> str | None:
    from uuid import UUID  # noqa: PLC0415

    try:
        return str(UUID(str(nilai)))
    except (TypeError, ValueError, AttributeError):
        return None


def dalam_jangkauan(project_id, user_ids) -> set:
    """Subset `user_ids` (sebagai str) yang boleh dikabari karena disebut di work item `project_id`.

    Id yang bukan UUID (mis. "all" dari @all) dibuang. Paling banyak empat
    kueri, berapa pun jumlah orangnya; satu kalau semuanya anggota project.
    """
    calon = {u for u in (_uuid_str(x) for x in (user_ids or [])) if u}
    if not calon or project_id is None:
        return set()
    anggota = {
        str(u)
        for u in ProjectMember.objects.filter(project_id=project_id, member_id__in=calon, is_active=True).values_list(
            "member_id", flat=True
        )
    }
    sisa = calon - anggota
    if not sisa:
        return anggota
    from plane.db.models import Project  # noqa: PLC0415

    workspace_id = Project.objects.filter(pk=project_id).values_list("workspace_id", flat=True).first()
    if workspace_id is None:
        return anggota
    aktif = set(
        WorkspaceMember.objects.filter(workspace_id=workspace_id, member_id__in=sisa, is_active=True).values_list(
            "member_id", flat=True
        )
    )
    puncak: dict = {}
    for uid, tingkat in JabatanOrganisasi.objects.filter(workspace_id=workspace_id, member_id__in=aktif).values_list(
        "member_id", "tingkat"
    ):
        puncak[uid] = max(tingkat, puncak.get(uid, tingkat))
    return anggota | {str(uid) for uid, tingkat in puncak.items() if menjangkau_seluruh_organisasi(tingkat)}


def saring_sebutan(project_id, user_ids) -> list:
    """`user_ids` yang di dalam jangkauan, urutan dan bentuk aslinya dipertahankan."""
    sah = dalam_jangkauan(project_id, user_ids)
    return [u for u in dict.fromkeys(user_ids or []) if _uuid_str(u) in sah]
