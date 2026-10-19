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
from plane.utils.trash import ambil, buang_permanen, kumpulkan, pulihkan


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
        buang_permanen(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)
