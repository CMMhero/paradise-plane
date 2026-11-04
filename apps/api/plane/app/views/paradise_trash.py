# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Trashbin per project
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from . import BaseAPIView
from plane.utils.saklar_instance import (
    PERM_MODULE_DELETE,
    PERM_PAGE_DELETE,
    PERM_TRASH_PURGE,
    PERM_TRASH_RESTORE,
    PERM_VIEW_DELETE,
    PERM_WIKI_DELETE,
    TRASH_RETENTION_DAYS,
    setelan_angka,
)
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import Issue
from plane.utils.izin_sumber import penilai_untuk, tolak_izin, tolak_izin_module
from plane.utils.task_access import bisa_hapus_tugas
from plane.utils.trash import TrashConflict, ambil, buang_permanen, kumpulkan, pulihkan
from plane.utils.wiki_access import can_manage_wiki_material

_PESAN_ISSUE = {
    "restore": "Hanya pembuat, penerima, atau atasannya yang boleh memulihkan barang ini.",
    "purge": "Hanya pembuat, penerima, atau atasannya yang boleh membuang barang ini.",
}


def _boleh_milik_sendiri(request, trash_type, obj, project_id):
    """Apakah orang ini lolos aturan HAPUS barang itu sendiri (KEP-85).

    Pemulihan barang milik sendiri (atau bawahan, menurut aturan God Mode) tidak
    butuh wewenang struktur: yang boleh menghapusnya, boleh pula mengembalikannya.
    Jenis tanpa pemilik perorangan (label, cycle, template) selalu False di sini.
    """
    if trash_type == "page":
        return (
            tolak_izin(
                request,
                PERM_PAGE_DELETE,
                workspace_id=obj.workspace_id,
                project_id=project_id,
                pemilik_id=obj.owned_by_id,
            )
            is None
        )
    if trash_type == "module":
        return tolak_izin_module(request, PERM_MODULE_DELETE, obj) is None
    if trash_type == "view":
        return (
            tolak_izin(
                request,
                PERM_VIEW_DELETE,
                workspace_id=obj.workspace_id,
                project_id=obj.project_id,
                pemilik_id=obj.owned_by_id,
            )
            is None
        )
    if trash_type == "wiki_material":
        return can_manage_wiki_material(request.user, obj, PERM_WIKI_DELETE)
    return False


def _galat_tindak_sampah(request, trash_type, obj, slug, project_id, aksi):
    """Response 403 kalau orang ini tidak boleh memulihkan/membuang `obj`, None kalau boleh.

    Work item: tetap `bisa_hapus_tugas` (pembuat, penerima, atau atasannya), sama
    dengan sebelum KEP-85; membuang permanen juga butuh wewenang struktur.
    Jenis lain (KEP-85): dulu admin project saja, sekarang
        pulihkan = PERM_TRASH_RESTORE, ATAU lolos aturan hapus barang itu sendiri
        buang    = PERM_TRASH_PURGE
    Admin project tidak lagi memberi wewenang apa pun di sini.
    """
    kunci = PERM_TRASH_RESTORE if aksi == "restore" else PERM_TRASH_PURGE
    workspace_id = obj.workspace_id
    struktur = penilai_untuk(request, workspace_id).boleh(kunci, project_id=project_id)

    if isinstance(obj, Issue):
        if not bisa_hapus_tugas(request.user, obj, slug, project_id):
            return Response({"error": _PESAN_ISSUE[aksi]}, status=status.HTTP_403_FORBIDDEN)
        if aksi == "purge" and not struktur:
            return tolak_izin(request, kunci, workspace_id=workspace_id, project_id=project_id)
        return None

    if struktur:
        return None
    if aksi == "restore" and _boleh_milik_sendiri(request, trash_type, obj, project_id):
        return None
    return tolak_izin(request, kunci, workspace_id=workspace_id, project_id=project_id)


class ProjectTrashEndpoint(BaseAPIView):
    """Tong sampah satu project, isi, pulihkan, buang permanen.

    Melihat: admin project (gerbang lama). Menindak: aturan KEP-85 di
    `_galat_tindak_sampah`. Cakupannya dikunci ke `project_id` di URL, jadi
    orang di project A tidak bisa menyentuh barang project B walau menebak
    id-nya: `ambil()` menyaring ulang berdasarkan project, bukan hanya percaya id.

    Menghapus di aplikasi ini memang sudah soft-delete sejak awal, barangnya
    tidak pernah benar-benar hilang sampai task harian membuangnya setelah
    TRASH_RETENTION_DAYS (God Mode). Endpoint ini cuma membuat yang tersembunyi itu
    terlihat dan bisa ditindak.
    """

    @allow_permission([ROLE.ADMIN])
    def get(self, request, slug, project_id):
        return Response(
            {
                "retention_days": setelan_angka(TRASH_RETENTION_DAYS),
                "results": kumpulkan(project_id=project_id, tipe=request.GET.get("type")),
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, trash_type, pk):
        """Pulihkan barang beserta anak-anak yang ikut terhapus bersamanya."""
        obj, spec = ambil(trash_type, pk, project_id=project_id)
        if not obj:
            return Response(
                {"error": "Barang tidak ada di tong sampah project ini."},
                status=status.HTTP_404_NOT_FOUND,
            )
        galat = _galat_tindak_sampah(request, trash_type, obj, slug, project_id, "restore")
        if galat is not None:
            return galat
        try:
            jumlah = pulihkan(obj, spec)
        except TrashConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {"message": "Dipulihkan.", "restored_count": jumlah},
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def delete(self, request, slug, project_id, trash_type, pk):
        """Buang permanen. Tidak bisa dibatalkan."""
        obj, _ = ambil(trash_type, pk, project_id=project_id)
        if not obj:
            return Response(
                {"error": "Barang tidak ada di tong sampah project ini."},
                status=status.HTTP_404_NOT_FOUND,
            )
        galat = _galat_tindak_sampah(request, trash_type, obj, slug, project_id, "purge")
        if galat is not None:
            return galat
        buang_permanen(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)
