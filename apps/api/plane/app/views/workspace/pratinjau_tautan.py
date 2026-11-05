# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: endpoint pratinjau tautan (KEP-88)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .. import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.utils.pratinjau_tautan import UrlTidakValid, pratinjau, rapikan_url


class PratinjauTautanThrottle(UserRateThrottle):
    """Kartu yang sudah di-cache tetap dihitung; 120/menit cukup untuk satu halaman penuh tautan."""

    scope = "pratinjau_tautan"
    rate = "120/minute"


class PratinjauTautanEndpoint(BaseAPIView):
    """GET ?url=... -> {url, title, description, site_name, image, favicon, kosong}.

    Hanya anggota workspace; logika & penjagaan SSRF di `plane/utils/pratinjau_tautan.py`.
    """

    permission_classes = [WorkspaceEntityPermission]
    throttle_classes = [PratinjauTautanThrottle]

    def get(self, request, slug):
        try:
            url = rapikan_url(request.query_params.get("url"))
        except UrlTidakValid:
            # Pesan tetap, bukan str(e): isi pengecualian tidak dikirim ke klien.
            return Response(
                {"error": "Only valid http and https links can be previewed."}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(pratinjau(url), status=status.HTTP_200_OK)
