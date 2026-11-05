# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: TPA (Tempat Pembuangan Akhir) di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.license.audit_godmode import catat_godmode
from plane.utils.saklar_instance import TRASH_RETENTION_DAYS, setelan_angka
from plane.license.api.views.base import BaseAPIView
from plane.utils.trash import TrashConflict, ambil, buang_permanen, kumpulkan, pulihkan


class InstanceTrashEndpoint(BaseAPIView):
    """TPA, tong sampah seluruh instance, lintas project.

    Membaca data yang SAMA dengan Trashbin per project; yang berbeda hanya
    cakupan dan siapa yang boleh menyentuhnya. Karena itu logikanya dipakai
    bersama lewat `plane.utils.trash`, bukan disalin, kalau disalin, cepat
    atau lambat keduanya akan berbeda pendapat soal isi tong sampah.

    Izin datang dari `BaseAPIView` God Mode (`InstanceAdminPermission`), jadi
    tidak ada dekorator tambahan di sini.

    Berbeda dengan Trashbin, TPA TIDAK dibatasi project: Super Admin bisa
    memulihkan atau membuang apa pun, termasuk barang milik project yang admin
    project-nya sendiri sudah membuangnya permanen dari pandangannya.
    """

    def get(self, request):
        return Response(
            {
                "retention_days": setelan_angka(TRASH_RETENTION_DAYS),
                "results": kumpulkan(project_id=None, tipe=request.GET.get("type")),
            },
            status=status.HTTP_200_OK,
        )

    def post(self, request, trash_type, pk):
        obj, spec = ambil(trash_type, pk)
        if not obj:
            return Response({"error": "Item not found in trash."}, status=status.HTTP_404_NOT_FOUND)
        try:
            jumlah = pulihkan(obj, spec)
        except TrashConflict as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        catat_godmode(request, kind="trash", label=f"Trash {trash_type}: restored", object_pk=str(pk), action=1)
        return Response({"message": "Restored.", "restored_count": jumlah}, status=status.HTTP_200_OK)

    def delete(self, request, trash_type, pk):
        obj, _ = ambil(trash_type, pk)
        if not obj:
            return Response({"error": "Item not found in trash."}, status=status.HTTP_404_NOT_FOUND)
        buang_permanen(obj)
        catat_godmode(
            request, kind="trash", label=f"Trash {trash_type}: deleted permanently", object_pk=str(pk), action=2
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
