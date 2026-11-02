# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan member baru di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.license.api.views.base import BaseAPIView
from plane.utils.cache import invalidate_cache
from plane.utils.bawaan_member import (
    BAGIAN_MASSAL,
    PABRIK,
    baca_bawaan,
    periksa_perubahan,
    simpan_bawaan,
    terapkan_ke_semua,
)


class InstanceMemberDefaultsEndpoint(BaseAPIView):
    """Baca/ubah setelan yang diterima akun baru (KEP-44). Hanya Super Admin.

    `PATCH` parsial per bagian (`profile`, `email`, `keanggotaan`); semua dicek
    sebelum ditulis. Balasan selalu memuat `pabrik` supaya UI bisa mengembalikan.
    """

    def _balas(self, bawaan, kode=status.HTTP_200_OK):
        return Response({**bawaan, "pabrik": PABRIK}, status=kode)

    def get(self, request):
        return self._balas(baca_bawaan())

    def patch(self, request):
        bawaan, galat = periksa_perubahan(request.data)
        if galat:
            return Response({"error": galat}, status=status.HTTP_400_BAD_REQUEST)
        simpan_bawaan(bawaan)
        return self._balas(bawaan)


class InstanceMemberDefaultsApplyEndpoint(BaseAPIView):
    """Samakan member LAMA dengan bawaan sekarang. Hanya Super Admin.

    `POST {"sections": ["navigasi", "work_items"]}`. Sengaja tombol terpisah dari
    Simpan: menimpa pilihan puluhan orang harus disengaja, bukan efek samping.
    Profil dan email tidak bisa diterapkan massal (pilihan pribadi).
    """

    def post(self, request):
        bagian = request.data.get("sections") if isinstance(request.data, dict) else None
        if not isinstance(bagian, list) or not bagian or set(bagian) - BAGIAN_MASSAL:
            return Response(
                {"error": "Sections must be a non-empty list of 'navigasi' and/or 'work_items'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"updated": terapkan_ke_semua(set(bagian))}, status=status.HTTP_200_OK)


class InstanceProjectDefaultsEndpoint(BaseAPIView):
    """Baca/ubah bawaan project baru (`plane/utils/bawaan_project.py`). Hanya Super Admin."""

    def _balas(self, bawaan):
        from plane.utils.bawaan_project import PABRIK as PABRIK_PROJECT

        return Response({**bawaan, "pabrik": PABRIK_PROJECT}, status=status.HTTP_200_OK)

    def get(self, request):
        from plane.utils.bawaan_project import baca_bawaan as baca_bawaan_project

        return self._balas(baca_bawaan_project())

    # /api/instances/ disimpan di cache 2 jam dan memuat bawaan ini untuk apps/web.
    @invalidate_cache(path="/api/instances/", user=False)
    def patch(self, request):
        from plane.utils import bawaan_project

        bawaan, galat = bawaan_project.periksa_perubahan(request.data)
        if galat:
            return Response({"error": galat}, status=status.HTTP_400_BAD_REQUEST)
        bawaan_project.simpan_bawaan(bawaan)
        return self._balas(bawaan)
