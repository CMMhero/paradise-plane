# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: izin per sumber untuk tampilan (KEP-85)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""`GET workspaces/<slug>/izin-saya/[?project_id=<uuid>]`.

Bahan bagi apps/web untuk menyembunyikan aksi ubah/arsip/hapus yang pasti ditolak
(module, page, view, komentar, materi Wiki, struktur project). Bentuknya
`ringkasan_izin()` di `plane/utils/izin_sumber.py`; penegaknya tetap di tiap endpoint.
"""

from uuid import UUID

from rest_framework.response import Response

from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseAPIView
from plane.db.models import Project, Workspace
from plane.utils.izin_sumber import ringkasan_izin


class IzinSayaEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.filter(slug=slug).only("id").first()
        if workspace is None:
            return Response({"error": "Workspace not found."}, status=404)
        project_id = request.query_params.get("project_id") or None
        if project_id is not None:
            try:
                project_id = UUID(str(project_id))
            except ValueError:
                return Response({"error": "project_id tidak sah."}, status=400)
            if not Project.objects.filter(id=project_id, workspace_id=workspace.id).exists():
                return Response({"error": "Project not found."}, status=404)
        return Response(ringkasan_izin(request.user, workspace.id, project_id))
