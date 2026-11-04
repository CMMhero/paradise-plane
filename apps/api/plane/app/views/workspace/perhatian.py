# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: endpoint widget "Needs attention" di Home
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from .. import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.utils.perhatian import susun_perhatian


class PerhatianEndpoint(BaseAPIView):
    """Ringkasan pekerjaan yang perlu perhatian user ini. Logika di `plane/utils/perhatian.py`."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        return Response(susun_perhatian(request.user, slug), status=status.HTTP_200_OK)
