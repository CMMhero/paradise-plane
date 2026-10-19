# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: endpoint can-edit halaman
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from types import SimpleNamespace

# Third party imports
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

# Module imports
from ..base import BaseAPIView
from plane.app.permissions.page import ProjectPagePermission
from plane.db.models import Page


class PageCanEditEndpoint(BaseAPIView):
    """Jawab: bolehkah user ini MENGEDIT halaman ini?

    Dipakai server Live (hocuspocus) sebelum membuka koneksi kolaboratif:
    tanpa ini, siapa pun yang bisa autentikasi bisa mengetik di halaman mana
    pun lewat websocket dan melewati seluruh izin REST.

    Sengaja TIDAK menyalin aturan izin ke sini. Kita tanyakan ke penegak yang
    sama persis (`ProjectPagePermission`) dengan berpura-pura melakukan PATCH,
    supaya editor kolaboratif dan REST tidak pernah bisa berbeda pendapat.
    """

    def get(self, request, slug, project_id, page_id):
        if not Page.objects.filter(id=page_id, workspace__slug=slug).exists():
            return Response({"error": "Page not found."}, status=status.HTTP_404_NOT_FOUND)

        # PATCH = aksi "ubah isi halaman", persis yang dilakukan editor Live.
        probe_request = SimpleNamespace(user=request.user, method="PATCH", data={})
        probe_view = SimpleNamespace(
            kwargs={"slug": slug, "project_id": str(project_id), "page_id": str(page_id)}
        )

        try:
            can_edit = bool(ProjectPagePermission().has_permission(probe_request, probe_view))
        except PermissionDenied:
            # Penegaknya kini menolak dengan alasan tertulis supaya pemakai REST
            # tahu kenapa. Di sini yang ditanya cuma boleh atau tidak, dan
            # penolakan itu jawabannya, bukan galat.
            can_edit = False

        return Response({"can_edit": can_edit}, status=status.HTTP_200_OK)
