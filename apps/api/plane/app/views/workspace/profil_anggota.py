# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kartu profil anggota
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""`GET` profil satu anggota workspace untuk kartu/halaman profil di apps/web.

Yang boleh dilihat: siapa pun yang anggota aktif workspace ini. Yang dilihat:
hanya anggota aktif workspace yang sama, bukan bot, bukan akun terhapus (KEP-50).
Selain itu 404, supaya endpoint ini tidak bisa dipakai menebak siapa yang
punya akun di instance.

Super Admin TIDAK disembunyikan di sini: ini direktori karyawan workspace, sama
dengan daftar anggota workspace (lihat `plane/db/superadmin.py`). Penyembunyian
Super Admin hanya berlaku di daftar anggota project.

Kontak (email, ekstensi) hanya untuk peminta berperan Member/Admin. Guest tidak
melihat email anggota lain di Plane, dan kartu ini tidak boleh jadi jalan
pintasnya.
"""

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseAPIView
from plane.db.models import (
    DOMAIN_AKUN_TERHAPUS,
    JabatanOrganisasi,
    Profile,
    WorkspaceMember,
)

PERAN_BOLEH_KONTAK = 15


def _penempatan(workspace_id, user_id) -> list[dict]:
    """Penempatan God Mode (KEP-29) orang ini, tanpa departemen/divisi terhapus."""
    hasil = []
    baris = (
        JabatanOrganisasi.objects.filter(workspace_id=workspace_id, member_id=user_id)
        .select_related("departemen__divisi", "divisi")
        .order_by("-tingkat", "created_at")
    )
    for b in baris:
        dep = b.departemen if b.departemen and b.departemen.deleted_at is None else None
        div = b.divisi if b.divisi and b.divisi.deleted_at is None else None
        if div is None and dep is not None and dep.divisi.deleted_at is None:
            div = dep.divisi
        if (b.departemen_id and dep is None) or (b.divisi_id and div is None):
            continue  # tempatnya sudah dihapus: jangan tampilkan penempatan basi
        hasil.append(
            {
                "tingkat": b.tingkat,
                "departemen": {"id": str(dep.id), "kode": dep.kode, "nama": dep.nama} if dep else None,
                "divisi": {"id": str(div.id), "kode": div.kode, "nama": div.nama} if div else None,
            }
        )
    return hasil


class ProfilAnggotaEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug, user_id):
        keanggotaan = (
            WorkspaceMember.objects.filter(
                workspace__slug=slug,
                member_id=user_id,
                is_active=True,
                member__is_bot=False,
            )
            .exclude(member__email__endswith=f"@{DOMAIN_AKUN_TERHAPUS}")
            .select_related("member", "member__avatar_asset", "workspace")
            .first()
        )
        if keanggotaan is None:
            return Response({"error": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

        peminta = WorkspaceMember.objects.filter(
            workspace__slug=slug, member=request.user, is_active=True
        ).values_list("role", flat=True).first()
        boleh_kontak = request.user.id == keanggotaan.member_id or (peminta or 0) >= PERAN_BOLEH_KONTAK

        user = keanggotaan.member
        profil = Profile.objects.filter(user_id=user.id).values("job_title", "phone_extension").first() or {}
        return Response(
            {
                "id": str(user.id),
                "display_name": user.display_name,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "avatar_url": user.avatar_url,
                "is_active": user.is_active,
                "user_timezone": user.user_timezone,
                "workspace_role": keanggotaan.role,
                "job_title": profil.get("job_title") or "",
                "email": user.email if boleh_kontak else None,
                "phone_extension": (profil.get("phone_extension") or "") if boleh_kontak else None,
                "penempatan": _penempatan(keanggotaan.workspace_id, user.id),
            },
            status=status.HTTP_200_OK,
        )
