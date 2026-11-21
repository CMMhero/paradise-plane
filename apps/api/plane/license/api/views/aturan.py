# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: registri aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""/api/instances/rules/: daftar, ubah, dan kembalikan aturan registri `plane.utils.aturan`.

- GET: semua aturan registri (nilai, bawaan, `changed`, metadata) ditambah setelan
  registri lama sebagai baris baca-saja (`source: "legacy"`).
- PATCH `{"values": {KEY: nilai}, "confirm"?: "CHANGE RULES"}`: semua atau tidak
  sama sekali. Aturan `risk: high` yang berubah wajib membawa frasa konfirmasi,
  sama dengan kunci SENSITIF di /api/instances/settings/.
- POST reset/ `{"keys": [KEY, ...], "confirm"?}`: kembali ke bawaan, aturan yang sama.

Setiap kunci yang berubah meninggalkan satu entri di Logs > Audit log (lama -> baru).
Kunci registri lama ditolak di sini; ia tetap diubah lewat /api/instances/settings/.
"""

from rest_framework import status
from rest_framework.response import Response

from plane.license.api.views.base import BaseAPIView
from plane.license.audit_godmode import catat_godmode
from plane.utils.aturan.daftar import daftar_aturan
from plane.utils.aturan.jenis import ke_teks
from plane.utils.aturan.tulis import butuh_frasa, perubahan, terapkan, validasi
from plane.utils.cache import invalidate_cache
from plane.utils.setelan_instance import FRASA_KONFIRMASI

GALAT_KONFIRMASI = "confirm_required"


def _pencatat(request, reset: bool):
    def catat(rule, lama, baru, pk):
        teks_lama, teks_baru = ke_teks(rule, lama), ke_teks(rule, baru)
        catat_godmode(
            request,
            kind="rule",
            label=f"Rule: {rule.key}",
            changes={"value": [teks_lama, teks_baru]},
            object_pk=pk,
            detail=f"{rule.key}: {teks_lama} -> {teks_baru}{' (reset to default)' if reset else ''}",
            extra={"key": rule.key, "risk": rule.risk, "area": rule.area, "reset": reset},
        )

    return catat


def _tolak_tanpa_frasa(request, daftar):
    kunci = butuh_frasa(daftar)
    if kunci and request.data.get("confirm") != FRASA_KONFIRMASI:
        return Response({"error": GALAT_KONFIRMASI, "keys": kunci}, status=status.HTTP_400_BAD_REQUEST)
    return None


class InstanceRulesEndpoint(BaseAPIView):
    """Hanya instance admin (`BaseAPIView` God Mode sudah memasang izinnya)."""

    def get(self, request):
        return Response(daftar_aturan(), status=status.HTTP_200_OK)

    # /api/instances/ (cache 2 jam) memuat `paradise_rules`.
    @invalidate_cache(path="/api/instances/", user=False)
    def patch(self, request):
        nilai = request.data.get("values") if hasattr(request.data, "get") else None
        if not isinstance(nilai, dict) or not nilai:
            return Response(
                {"error": 'Body must be {"values": {KEY: value, ...}}.'}, status=status.HTTP_400_BAD_REQUEST
            )

        baru, galat = validasi(nilai)
        if galat:
            return Response({"errors": galat}, status=status.HTTP_400_BAD_REQUEST)

        daftar = perubahan(baru)
        tolak = _tolak_tanpa_frasa(request, daftar)
        if tolak is not None:
            return tolak

        terapkan(daftar, catat=_pencatat(request, reset=False))
        return Response(daftar_aturan(), status=status.HTTP_200_OK)


class InstanceRulesResetEndpoint(BaseAPIView):
    @invalidate_cache(path="/api/instances/", user=False)
    def post(self, request):
        from plane.utils.aturan import REGISTRI

        kunci = request.data.get("keys") if hasattr(request.data, "get") else None
        if not isinstance(kunci, list) or not kunci or not all(isinstance(k, str) for k in kunci):
            return Response({"error": 'Body must be {"keys": [KEY, ...]}.'}, status=status.HTTP_400_BAD_REQUEST)
        asing = sorted({k for k in kunci if k not in REGISTRI})
        if asing:
            return Response({"errors": dict.fromkeys(asing, "Unknown rule.")}, status=status.HTTP_400_BAD_REQUEST)

        daftar = perubahan({k: REGISTRI[k].default for k in kunci})
        tolak = _tolak_tanpa_frasa(request, daftar)
        if tolak is not None:
            return tolak

        terapkan(daftar, kembalikan=True, catat=_pencatat(request, reset=True))
        return Response(daftar_aturan(), status=status.HTTP_200_OK)
