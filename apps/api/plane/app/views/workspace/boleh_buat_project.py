# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bolehkah saya membuat project
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""`GET workspaces/<slug>/boleh-buat-project/` -> `{"boleh": bool}`.

apps/web membacanya untuk menyembunyikan tombol "Create project" dari staf.
Penegak sebenarnya tetap di endpoint create (`plane/utils/izin_buat_project.py`);
ini hanya supaya tombol yang pasti ditolak tidak tampil.
"""

# Third party imports
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseAPIView
from plane.db.models import Workspace
from plane.utils.izin_buat_project import boleh_buat_project


class BolehBuatProjectEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.filter(slug=slug).only("id").first()
        if workspace is None:
            return Response({"error": "Workspace not found."}, status=404)
        return Response({"boleh": boleh_buat_project(request.user, workspace.id)})
