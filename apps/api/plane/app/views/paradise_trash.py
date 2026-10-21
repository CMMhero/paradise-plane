# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Trashbin per project
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.conf import settings

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from . import BaseAPIView
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import Issue
from plane.utils.task_access import bisa_hapus_tugas
from plane.utils.trash import ambil, buang_permanen, kumpulkan, pulihkan


def _boleh_tindak_sampah(user, obj, slug, project_id):
    """Aturan kepemilikan untuk isi tong sampah, SAMA dengan ubah/hapus.

    Tong sampah project boleh DILIHAT semua admin project, tapi menindak (pulihkan
    atau buang permanen) work item milik orang lain sama saja menghapusnya: hanya
    pembuat, penerima, atau atasannya yang boleh -- persis `bisa_hapus_tugas`.
    Tipe selain work item tetap ikut aturan admin project seperti semula.
    """
    if isinstance(obj, Issue) and not bisa_hapus_tugas(user, obj, slug, project_id):
        return False
    return True


class ProjectTrashEndpoint(BaseAPIView):
    """Tong sampah satu project, isi, pulihkan, buang permanen.

    Admin project saja. Cakupannya dikunci ke `project_id` di URL, jadi admin
    project A tidak bisa menyentuh barang project B walau menebak id-nya:
    `ambil()` menyaring ulang berdasarkan project, bukan hanya percaya id.

    Menghapus di aplikasi ini memang sudah soft-delete sejak awal, barangnya
    tidak pernah benar-benar hilang sampai task harian membuangnya setelah
    HARD_DELETE_AFTER_DAYS. Endpoint ini cuma membuat yang tersembunyi itu
    terlihat dan bisa ditindak.
    """

    @allow_permission([ROLE.ADMIN])
    def get(self, request, slug, project_id):
        return Response(
            {
                "retention_days": settings.HARD_DELETE_AFTER_DAYS,
                "results": kumpulkan(project_id=project_id, tipe=request.GET.get("type")),
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN])
    def post(self, request, slug, project_id, trash_type, pk):
        """Pulihkan barang beserta anak-anak yang ikut terhapus bersamanya."""
        obj, _ = ambil(trash_type, pk, project_id=project_id)
        if not obj:
            return Response(
                {"error": "Barang tidak ada di tong sampah project ini."},
                status=status.HTTP_404_NOT_FOUND,
            )
        from plane.utils.hierarki import galat_terkunci, gerbang_aktif  # noqa: PLC0415

        if gerbang_aktif():
            kunci = galat_terkunci([obj.pk], request.user)
            if kunci:
                return Response({"error": kunci}, status=status.HTTP_403_FORBIDDEN)
        if not _boleh_tindak_sampah(request.user, obj, slug, project_id):
            return Response(
                {"error": "Hanya pembuat, penerima, atau atasannya yang boleh memulihkan barang ini."},
                status=status.HTTP_403_FORBIDDEN,
            )
        jumlah = pulihkan(obj)
        return Response(
            {"message": "Dipulihkan.", "restored_count": jumlah},
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN])
    def delete(self, request, slug, project_id, trash_type, pk):
        """Buang permanen. Tidak bisa dibatalkan."""
        obj, _ = ambil(trash_type, pk, project_id=project_id)
        if not obj:
            return Response(
                {"error": "Barang tidak ada di tong sampah project ini."},
                status=status.HTTP_404_NOT_FOUND,
            )
        from plane.utils.hierarki import galat_terkunci, gerbang_aktif  # noqa: PLC0415

        if gerbang_aktif():
            kunci = galat_terkunci([obj.pk], request.user)
            if kunci:
                return Response({"error": kunci}, status=status.HTTP_403_FORBIDDEN)
        if not _boleh_tindak_sampah(request.user, obj, slug, project_id):
            return Response(
                {"error": "Hanya pembuat, penerima, atau atasannya yang boleh membuang barang ini."},
                status=status.HTTP_403_FORBIDDEN,
            )
        buang_permanen(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)
