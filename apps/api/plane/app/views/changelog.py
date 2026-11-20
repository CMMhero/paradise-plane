# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: catatan rilis untuk widget Home
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Daftar catatan rilis workspace, dibaca widget Changelog di Home.

Datanya tetap kartu `jenis=changelog` di ruang sistem Changelog yang diisi
`terbitkan_changelog`. Ruang itu tidak lagi diikuti anggota dan tidak tampil di
Obrolan; jalur ini membacanya langsung, tanpa langganan, karena catatan rilis
milik seluruh workspace dan tidak punya status belum-dibaca.
"""

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseAPIView
from plane.db.models import KUNCI_CHANGELOG, JenisPesan, PesanLangsung
from plane.utils.catatan_rilis import JENIS_ENTRI, urai_versi

BATAS_BAWAAN = 10
BATAS_MAKS = 50


def _entri(muatan) -> list:
    mentah = muatan.get("entri") if isinstance(muatan, dict) else None
    return [
        {"type": e["type"], "text": str(e["text"])}
        for e in (mentah if isinstance(mentah, list) else [])
        if isinstance(e, dict) and e.get("type") in JENIS_ENTRI and str(e.get("text") or "").strip()
    ]


class ChangelogEndpoint(BaseAPIView):
    """Catatan rilis terbaru dulu, urut versi (bukan waktu tulis)."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        try:
            batas = int(request.query_params.get("batas", BATAS_BAWAAN))
        except ValueError:
            batas = BATAS_BAWAAN
        batas = max(1, min(batas, BATAS_MAKS))

        kartu = PesanLangsung.objects.filter(
            workspace__slug=slug,
            ruang__kunci_sistem=KUNCI_CHANGELOG,
            jenis=JenisPesan.CHANGELOG,
        ).values("id", "muatan")

        hasil = []
        for k in kartu:
            muatan = k["muatan"] if isinstance(k["muatan"], dict) else {}
            versi = str(muatan.get("versi") or "")
            entri = _entri(muatan)
            if not urai_versi(versi) or not entri:
                continue
            hasil.append(
                {"id": str(k["id"]), "versi": versi, "tanggal": str(muatan.get("tanggal") or ""), "entri": entri}
            )
        hasil.sort(key=lambda c: urai_versi(c["versi"]), reverse=True)
        return Response(hasil[:batas], status=status.HTTP_200_OK)
