# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Module imports
from ..base import BaseAPIView
from plane.db.models.workspace import WorkspaceHomePreference
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import Workspace
from plane.app.serializers.workspace import WorkspaceHomePreferenceSerializer
from plane.utils.bawaan_member import susunan_widget_home

# Third party imports
from rest_framework.response import Response
from rest_framework import status


class WorkspaceHomePreferenceViewSet(BaseAPIView):
    model = WorkspaceHomePreference

    def get_serializer_class(self):
        return WorkspaceHomePreferenceSerializer

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)

        ada = set(
            WorkspaceHomePreference.objects.filter(user=request.user, workspace_id=workspace.id).values_list(
                "key", flat=True
            )
        )

        # Paradise: widget yang nyala dan urutannya dari God Mode (aturan HOME_WIDGETS,
        # bawaan per akun). Hanya baris yang BELUM ada yang dibuat, jadi pilihan
        # orangnya tidak pernah tertimpa. Widget teratas selalu 2000; sisanya diberi
        # nomor menurun seperti upstream (yang hanya menghitung baris baru).
        baru = []
        for posisi, (key, aktif) in enumerate(susunan_widget_home()):
            if key in ada:
                continue
            baru.append(
                WorkspaceHomePreference(
                    key=key,
                    user=request.user,
                    workspace=workspace,
                    is_enabled=aktif,
                    sort_order=2000 if posisi == 0 else 1000 - (len(baru) + 1),
                )
            )
        if baru:
            WorkspaceHomePreference.objects.bulk_create(baru, batch_size=10, ignore_conflicts=True)

        preference = WorkspaceHomePreference.objects.filter(user=request.user, workspace_id=workspace.id)

        return Response(
            preference.values("key", "is_enabled", "config", "sort_order"),
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def patch(self, request, slug, key):
        preference = WorkspaceHomePreference.objects.filter(key=key, workspace__slug=slug, user=request.user).first()

        if preference:
            serializer = WorkspaceHomePreferenceSerializer(preference, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Preference not found"}, status=status.HTTP_400_BAD_REQUEST)
