# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penulis kanal Announcements
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Admin mengatur siapa, selain admin, yang boleh menulis di Announcements.

Hanya kanal Announcements yang punya daftar penulis: Changelog ditulis sistem,
dan kanal lain bebas ditulis anggotanya. Yang boleh mengatur: admin workspace
dan Super Admin, sama dengan yang selalu boleh menulis di sana.
"""

import logging

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import KUNCI_PENGUMUMAN, Departemen, PenulisKanal, Ruang, WorkspaceMember
from plane.utils.kanal_sistem import adalah_admin_workspace
from plane.utils.rujukan_obrolan import urai_uuid

from .base import BaseAPIView

logger = logging.getLogger("plane.api")


def _bentuk(penulis) -> dict:
    dept = penulis.departemen
    return {
        "id": str(penulis.id),
        "departemen": {"id": str(dept.id), "kode": dept.kode, "nama": dept.nama} if dept else None,
        "user": str(penulis.user_id) if penulis.user_id else None,
    }


class ChatPenulisKanalEndpoint(BaseAPIView):
    """GET daftar izin + pilihan departemen, POST beri izin, DELETE cabut izin."""

    permission_classes = [WorkspaceEntityPermission]

    def _kanal(self, request, slug, ruang_id):
        """(ruang, respons_galat). Hanya Announcements, hanya untuk admin."""
        ruang = Ruang.objects.filter(id=ruang_id, workspace__slug=slug, kunci_sistem=KUNCI_PENGUMUMAN).first()
        if ruang is None:
            return None, Response({"error": "Kanal tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        if not adalah_admin_workspace(request.user, ruang.workspace_id):
            return None, Response(
                {"error": "Hanya admin yang bisa mengatur penulis pengumuman."}, status=status.HTTP_403_FORBIDDEN
            )
        return ruang, None

    def get(self, request, slug, ruang_id):
        ruang, galat = self._kanal(request, slug, ruang_id)
        if galat:
            return galat
        penulis = PenulisKanal.objects.filter(ruang=ruang).select_related("departemen")
        departemen = Departemen.objects.filter(workspace_id=ruang.workspace_id).select_related("divisi")
        return Response(
            {
                "penulis": [_bentuk(p) for p in penulis],
                "departemen": [
                    {"id": str(d.id), "kode": d.kode, "nama": d.nama, "divisi": d.divisi.nama} for d in departemen
                ],
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, slug, ruang_id):
        ruang, galat = self._kanal(request, slug, ruang_id)
        if galat:
            return galat
        departemen_id = next(iter(urai_uuid([request.data.get("departemen_id")], 1)), None)
        user_id = next(iter(urai_uuid([request.data.get("user_id")], 1)), None)
        if bool(departemen_id) == bool(user_id):
            return Response(
                {"error": "Isi tepat satu: departemen_id atau user_id."}, status=status.HTTP_400_BAD_REQUEST
            )
        if departemen_id:
            sah = Departemen.objects.filter(id=departemen_id, workspace_id=ruang.workspace_id).exists()
            sasaran = {"departemen_id": departemen_id}
        else:
            sah = WorkspaceMember.objects.filter(
                workspace_id=ruang.workspace_id, member_id=user_id, is_active=True
            ).exists()
            sasaran = {"user_id": user_id}
        if not sah:
            return Response({"error": "Departemen atau orang tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

        penulis, dibuat = PenulisKanal.objects.get_or_create(ruang=ruang, workspace_id=ruang.workspace_id, **sasaran)
        logger.info("penulis-kanal: %s mengizinkan %s menulis di %s", request.user.email, sasaran, ruang.id)
        return Response(_bentuk(penulis), status=status.HTTP_201_CREATED if dibuat else status.HTTP_200_OK)

    def delete(self, request, slug, ruang_id, penulis_id):
        ruang, galat = self._kanal(request, slug, ruang_id)
        if galat:
            return galat
        jumlah, _ = PenulisKanal.objects.filter(id=penulis_id, ruang=ruang).delete(soft=False)
        if not jumlah:
            return Response({"error": "Izin tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        logger.info("penulis-kanal: %s mencabut izin %s di %s", request.user.email, penulis_id, ruang.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
