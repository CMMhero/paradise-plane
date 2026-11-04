# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import WorkspaceUserLink, Workspace
from plane.app.serializers import WorkspaceUserLinkSerializer
from ..base import BaseViewSet
from plane.app.permissions import allow_permission, ROLE
from plane.bgtasks.quick_link_task import JENIS_PRIBADI
from plane.utils.quick_link import LogoTidakValid, isi_metadata_lama, metadata_baru


def _logo(data) -> dict:
    """Kunci `logo_props` hanya diteruskan kalau dikirim (tidak ada = tidak disentuh)."""
    return {"logo_props": data["logo_props"]} if "logo_props" in data else {}


class QuickLinkViewSet(BaseViewSet):
    model = WorkspaceUserLink
    use_read_replica = True

    def get_serializer_class(self):
        return WorkspaceUserLinkSerializer

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def create(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = WorkspaceUserLinkSerializer(data=request.data)

        if serializer.is_valid():
            # Paradise KEP-82: judul & favicon situs diambil saat link dibuat.
            try:
                metadata = metadata_baru(
                    {}, serializer.validated_data["url"], url_berubah=True, **_logo(request.data)
                )
            except LogoTidakValid as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(workspace_id=workspace.id, owner_id=request.user.id, metadata=metadata)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def partial_update(self, request, slug, pk):
        quick_link = WorkspaceUserLink.objects.filter(pk=pk, workspace__slug=slug, owner=request.user).first()

        if quick_link:
            serializer = WorkspaceUserLinkSerializer(quick_link, data=request.data, partial=True)
            if serializer.is_valid():
                url = serializer.validated_data.get("url", quick_link.url)
                try:
                    metadata = metadata_baru(
                        quick_link.metadata,
                        url,
                        url_berubah=url != quick_link.url,
                        **_logo(request.data),
                    )
                except LogoTidakValid as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
                serializer.save(metadata=metadata)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Quick link not found."}, status=status.HTTP_404_NOT_FOUND)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def retrieve(self, request, slug, pk):
        try:
            quick_link = WorkspaceUserLink.objects.get(pk=pk, workspace__slug=slug, owner=request.user)
            serializer = WorkspaceUserLinkSerializer(quick_link)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except WorkspaceUserLink.DoesNotExist:
            return Response({"error": "Quick link not found."}, status=status.HTTP_404_NOT_FOUND)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def destroy(self, request, slug, pk):
        quick_link = WorkspaceUserLink.objects.get(pk=pk, workspace__slug=slug, owner=request.user)
        quick_link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def list(self, request, slug):
        quick_links = WorkspaceUserLink.objects.filter(workspace__slug=slug, owner=request.user)
        # Paradise KEP-82: link lama diisi judul & favicon-nya di latar belakang.
        isi_metadata_lama(JENIS_PRIBADI, quick_links)

        serializer = WorkspaceUserLinkSerializer(quick_links, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
