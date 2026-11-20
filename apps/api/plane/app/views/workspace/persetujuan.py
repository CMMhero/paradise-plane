# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: halaman Persetujuan workspace
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from .. import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.utils.antrean_persetujuan import susun_antrean


class AntreanPersetujuanWorkspaceEndpoint(BaseAPIView):
    """Semua yang menunggu keputusan saya. Logika di `plane/utils/antrean_persetujuan.py`."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        return Response(susun_antrean(request.user, slug), status=status.HTTP_200_OK)
