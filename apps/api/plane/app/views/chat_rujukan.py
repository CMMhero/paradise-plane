# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: rujukan #kanal dan #PRJ-12 (KEP-91)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Saran dan keterangan rujukan untuk kotak tulis obrolan dan editor teks kaya.

Dua endpoint, dipakai bersama obrolan, deskripsi work item, dan komentar:

- `rujukan/` menjawab "#ap..." saat orang mengetik: kanal dan work item yang
  BOLEH ia rujuk, tidak lebih.
- `rujukan/info/` menjawab "chip ini menunjuk apa" saat teks dirender. Id yang
  tidak dikenal atau tidak boleh dilihat dijawab `boleh: false` TANPA nama atau
  judul, supaya id yang bocor tidak bisa dipakai untuk mengintip.

Aturan siapa boleh melihat apa ada di `utils/rujukan_obrolan.py`, satu tempat
untuk endpoint ini, pengiriman pesan, dan penyamaran saat dibaca.
"""

import re

from django.db.models import Case, Count, IntegerField, Q, Value, When
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import IssueAssignee, Workspace
from plane.utils.rujukan_obrolan import kanal_terlihat, nomor_tugas, tugas_terlihat, urai_uuid

from .base import BaseAPIView

# Jumlah saran bawaan dan batasnya. Kotak saran yang lebih panjang dari ini
# tidak dibaca, cuma digulir.
SARAN_BAWAAN = 6
SARAN_MAKS = 20
# Penanggung jawab yang disebut namanya di kartu pratinjau; sisanya jadi "+N".
PRATINJAU_ASSIGNEE = 3
# Batas id per jenis di satu permintaan info. Satu deskripsi panjang jarang
# merujuk lebih dari ini; lebih dari itu dipotong, bukan ditolak.
INFO_MAKS = 50

# `PRJ-12`, `prj-12`, atau `PRJ-` yang belum selesai diketik.
POLA_NOMOR = re.compile(r"^([A-Za-z0-9]+)-(\d*)$")


def _jumlah(request) -> int:
    try:
        n = int(request.query_params.get("count") or SARAN_BAWAAN)
    except (TypeError, ValueError):
        n = SARAN_BAWAAN
    return max(1, min(n, SARAN_MAKS))


def _bentuk_tugas(issue) -> dict:
    return {
        "id": str(issue.id),
        "nomor": nomor_tugas(issue),
        "judul": issue.name,
        "project_id": str(issue.project_id),
        "state_group": issue.state.group if issue.state_id else None,
    }


def _peta_assignee(tugas_ids) -> dict:
    """{id tugas: [nama tampilan...]} untuk kartu pratinjau, SATU kueri untuk semua tugas."""
    peta = {}
    baris = (
        IssueAssignee.objects.filter(issue_id__in=tugas_ids, assignee__is_bot=False)
        .order_by("created_at")
        .values_list("issue_id", "assignee__display_name")
    )
    for issue_id, nama in baris:
        peta.setdefault(str(issue_id), []).append(nama)
    return peta


def _pratinjau_tugas(issue, assignee) -> dict:
    """Ringkasan kecil untuk kartu hover: cukup untuk memutuskan perlu dibuka atau tidak."""
    return {
        "project_nama": issue.project.name,
        "state_nama": issue.state.name if issue.state_id else None,
        "prioritas": issue.priority or "none",
        "tenggat": issue.target_date.isoformat() if issue.target_date else None,
        "assignee": assignee[:PRATINJAU_ASSIGNEE],
        "assignee_jumlah": len(assignee),
    }


def _saring_tugas_q(q) -> Q:
    """Syarat pencarian work item: judul, identifier project, nomor urut, atau `PRJ-12`."""
    cocok = POLA_NOMOR.match(q)
    if cocok:
        kode, angka = cocok.groups()
        syarat = Q(project__identifier__iexact=kode)
        if angka:
            syarat &= Q(sequence_id=int(angka))
        return syarat | Q(name__icontains=q)
    syarat = Q(name__icontains=q) | Q(project__identifier__icontains=q)
    if q.isdigit():
        syarat |= Q(sequence_id=int(q))
    return syarat


class ChatRujukanEndpoint(BaseAPIView):
    """Saran #kanal dan #work item untuk kotak tulis."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.filter(slug=slug).first()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)
        q = (request.query_params.get("q") or "").strip().lstrip("#")
        n = _jumlah(request)

        kanal = kanal_terlihat(request.user.id, workspace.id)
        tugas = tugas_terlihat(request.user.id, workspace.id).select_related("project", "state")
        if q:
            kanal = kanal.filter(nama__icontains=q).annotate(
                awal=Case(When(nama__istartswith=q, then=Value(0)), default=Value(1), output_field=IntegerField())
            )
            kanal = kanal.order_by("awal", "nama")
            tugas = tugas.filter(_saring_tugas_q(q)).annotate(
                awal=Case(When(name__istartswith=q, then=Value(0)), default=Value(1), output_field=IntegerField())
            )
            tugas = tugas.order_by("awal", "-updated_at")
        else:
            kanal = kanal.order_by("nama")
            tugas = tugas.order_by("-updated_at")

        return Response(
            {
                "kanal": [{"id": str(r.id), "nama": r.nama or "", "tipe": r.tipe} for r in kanal[:n]],
                "tugas": [_bentuk_tugas(i) for i in tugas[:n]],
            },
            status=status.HTTP_200_OK,
        )


def _daftar_id(request, kunci) -> list:
    """Id mentah dari `?kunci=a,b,c`, tanpa kosong dan kembar, paling banyak INFO_MAKS."""
    hasil = []
    for nilai in (request.query_params.get(kunci) or "").split(","):
        nilai = nilai.strip()
        if nilai and nilai not in hasil:
            hasil.append(nilai)
        if len(hasil) >= INFO_MAKS:
            break
    return hasil


class ChatRujukanInfoEndpoint(BaseAPIView):
    """Keterangan chip rujukan: nama kanal / nomor dan judul work item, kalau boleh."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.filter(slug=slug).first()
        if workspace is None:
            return Response({"error": "Workspace tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        mentah_kanal = _daftar_id(request, "kanal")
        mentah_tugas = _daftar_id(request, "tugas")

        kanal_ids = urai_uuid(mentah_kanal, INFO_MAKS)
        tugas_ids = urai_uuid(mentah_tugas, INFO_MAKS)
        kanal = (
            {
                str(r.id): r
                for r in kanal_terlihat(request.user.id, workspace.id)
                .filter(id__in=kanal_ids)
                .annotate(jumlah_anggota=Count("langganan", filter=Q(langganan__deleted_at__isnull=True)))
            }
            if kanal_ids
            else {}
        )
        tugas = (
            {
                str(i.id): i
                for i in tugas_terlihat(request.user.id, workspace.id)
                .filter(id__in=tugas_ids)
                .select_related("project", "state")
            }
            if tugas_ids
            else {}
        )

        peta_assignee = _peta_assignee(list(tugas.keys())) if tugas else {}

        def _kunci(nilai):
            # Kunci jawaban = id dalam bentuk baku kalau sah, mentah kalau tidak.
            sah = urai_uuid([nilai], 1)
            return str(sah[0]) if sah else nilai

        jawab_kanal = {}
        for nilai in mentah_kanal:
            k = _kunci(nilai)
            r = kanal.get(k)
            jawab_kanal[k] = (
                {
                    "id": k,
                    "boleh": True,
                    "nama": r.nama or "",
                    "tipe": r.tipe,
                    "topik": r.topik or "",
                    "jumlah_anggota": r.jumlah_anggota,
                }
                if r
                else {"id": k, "boleh": False}
            )
        jawab_tugas = {}
        for nilai in mentah_tugas:
            k = _kunci(nilai)
            i = tugas.get(k)
            jawab_tugas[k] = (
                {**_bentuk_tugas(i), **_pratinjau_tugas(i, peta_assignee.get(k, [])), "boleh": True}
                if i
                else {"id": k, "boleh": False}
            )

        return Response({"kanal": jawab_kanal, "tugas": jawab_tugas}, status=status.HTTP_200_OK)
