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


# Widget yang baru ada sejak 2.13, berurutan dari atas ke bawah. Untuk akun yang sudah
# punya baris widget lain, keduanya masuk paling bawah dan Changelog (What's new) terakhir.
WIDGET_BARU_DI_BAWAH = ("announcements", "changelog")


class WorkspaceHomePreferenceViewSet(BaseAPIView):
    model = WorkspaceHomePreference

    def get_serializer_class(self):
        return WorkspaceHomePreferenceSerializer

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)

        urutan_ada = dict(
            WorkspaceHomePreference.objects.filter(user=request.user, workspace_id=workspace.id).values_list(
                "key", "sort_order"
            )
        )
        ada = set(urutan_ada)

        # Paradise: widget yang nyala dan urutannya dari God Mode (aturan HOME_WIDGETS,
        # bawaan per akun). Hanya baris yang BELUM ada yang dibuat, jadi pilihan
        # orangnya tidak pernah tertimpa. Widget teratas selalu 2000; sisanya diberi
        # nomor menurun seperti upstream (yang hanya menghitung baris baru).
        # Widget yang ditambahkan sesudah akun itu punya baris (Pengumuman dan Changelog,
        # 2.13) masuk di BAWAH widget yang sudah ada, bukan di nomor upstream yang
        # bisa jatuh di antara widget lama.
        baru = []
        susunan = susunan_widget_home()
        batas_bawah = min(urutan_ada.values(), default=None)
        di_bawah = []
        for posisi, (key, aktif) in enumerate(susunan):
            if key in ada:
                continue
            if batas_bawah is not None and key in WIDGET_BARU_DI_BAWAH:
                di_bawah.append((key, aktif))
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
        if di_bawah:
            # Di bawah SEMUA yang ada sekarang, termasuk baris yang baru dibuat di atas.
            batas_bawah = min([batas_bawah, *(b.sort_order for b in baru)])
        for key, aktif in sorted(di_bawah, key=lambda ka: WIDGET_BARU_DI_BAWAH.index(ka[0])):
            batas_bawah -= 1
            baru.append(
                WorkspaceHomePreference(
                    key=key, user=request.user, workspace=workspace, is_enabled=aktif, sort_order=batas_bawah
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
