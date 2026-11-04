# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kartu profil anggota di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""`GET members/<pk>/profile/`: isi kartu profil satu akun untuk God Mode.

Bentuknya sama dengan `ProfilAnggotaEndpoint` di apps/web supaya kartu bersama
(`@plane/propel/member-profile-card`) bisa memakai dua-duanya. Bedanya, di sini
tidak ada workspace di URL dan yang meminta pasti Super Admin, jadi kontak
selalu ikut. Penempatan diambil dari workspace tertua yang masih aktif (sama
dengan `_workspace_utama` di member.py). Hanya baca.
"""

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.views.workspace.profil_anggota import _penempatan
from plane.db.models import Profile, User, WorkspaceMember
from plane.license.api.views.base import BaseAPIView
from plane.license.api.views.member import _workspace_utama


class InstanceMemberProfileEndpoint(BaseAPIView):
    def get(self, request, pk):
        u = User.objects.filter(pk=pk, is_bot=False).first()
        if u is None:
            return Response({"error": "Account not found."}, status=status.HTTP_404_NOT_FOUND)

        ws = _workspace_utama()
        keanggotaan = (
            WorkspaceMember.objects.filter(workspace=ws, member=u, is_active=True).first() if ws else None
        )
        profil = Profile.objects.filter(user_id=u.id).values("job_title", "phone_extension").first() or {}
        return Response(
            {
                "id": str(u.id),
                "display_name": u.display_name,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "avatar_url": u.avatar_url,
                "is_active": u.is_active,
                "user_timezone": u.user_timezone,
                "workspace_role": keanggotaan.role if keanggotaan else None,
                "job_title": profil.get("job_title") or "",
                "email": u.email,
                "phone_extension": profil.get("phone_extension") or "",
                "penempatan": _penempatan(ws.id, u.id) if ws and keanggotaan else [],
            },
            status=status.HTTP_200_OK,
        )
