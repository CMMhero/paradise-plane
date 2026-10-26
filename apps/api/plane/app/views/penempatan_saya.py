# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: anggota memilih departemennya sendiri
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Pilih departemen sendiri, untuk akun baru atau lama yang belum ditempatkan.

Keputusan user 2026-10-26: orang yang belum punya departemen diberi layar untuk
memilihnya, dan tanpa jabatan mereka dianggap STAF (member).

Batas yang disengaja:
* Hanya boleh SEKALI, dan hanya kalau belum ditempatkan. Pindah departemen atau
  naik jenjang tetap lewat God Mode.
* Yang ditulis selalu tingkat MEMBER; supervisor/manager/direktur tidak pernah
  bisa diberikan lewat endpoint ini.
* Memilih departemen = ikut jangkauan departemen itu (sinkron otomatis lewat
  signal `JabatanOrganisasi`).
"""

# Django imports
from django.db import transaction

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from . import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import Departemen, JabatanOrganisasi, TINGKAT_MEMBER, TINGKAT_SUPERVISOR, Workspace
from plane.db.superadmin import is_super_admin
from plane.utils.hierarki import struktur_aktif

SUMBER_MANDIRI = "mandiri"


def perlu_pilih_departemen(user, workspace_id):
    """True kalau struktur aktif dan orang ini belum punya departemen/divisi."""
    if not struktur_aktif(workspace_id) or is_super_admin(user):
        return False
    baris = list(JabatanOrganisasi.objects.filter(workspace_id=workspace_id, member=user))
    if not baris:
        return True
    if any(b.departemen_id or b.divisi_id for b in baris):
        return False
    # Hanya baris tanpa tempat: direktur memang begitu, staf tidak.
    return max(b.tingkat for b in baris) < TINGKAT_SUPERVISOR


class PenempatanSayaEndpoint(BaseAPIView):
    """`GET` perlukah saya memilih departemen (+ daftar pilihan); `POST` memilihnya."""

    permission_classes = [WorkspaceEntityPermission]

    def _daftar(self, workspace_id):
        return [
            {"id": str(d.id), "kode": d.kode, "nama": d.nama, "divisi": d.divisi.nama}
            for d in Departemen.objects.filter(workspace_id=workspace_id).select_related("divisi").order_by(
                "divisi__nama", "nama"
            )
        ]

    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        perlu = perlu_pilih_departemen(request.user, workspace.id)
        return Response({"perlu_pilih": perlu, "departemen": self._daftar(workspace.id) if perlu else []})

    def post(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        if not perlu_pilih_departemen(request.user, workspace.id):
            return Response(
                {"error": "Penempatan Anda sudah ada. Perubahan dilakukan admin."}, status=status.HTTP_400_BAD_REQUEST
            )
        departemen = Departemen.objects.filter(workspace_id=workspace.id, pk=request.data.get("departemen_id")).first()
        if departemen is None:
            return Response({"error": "Departemen tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # all_objects + hidupkan: baris yang pernah dicabut menempati slot unik (jebakan A21).
            baris = JabatanOrganisasi.all_objects.filter(workspace_id=workspace.id, member=request.user).first()
            if baris is None:
                JabatanOrganisasi.objects.create(
                    workspace_id=workspace.id,
                    member=request.user,
                    tingkat=TINGKAT_MEMBER,
                    sumber=SUMBER_MANDIRI,
                    departemen=departemen,
                )
            else:
                baris.deleted_at = None
                baris.tingkat = TINGKAT_MEMBER
                baris.sumber = SUMBER_MANDIRI
                baris.departemen = departemen
                baris.divisi = None
                baris.save(update_fields=["deleted_at", "tingkat", "sumber", "departemen", "divisi", "updated_at"])
        return Response({"perlu_pilih": False, "departemen": []}, status=status.HTTP_201_CREATED)
