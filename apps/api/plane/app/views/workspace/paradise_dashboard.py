# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Dashboard Divisi + Laporan Waktu
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import csv
from datetime import date

# Django imports
from django.http import HttpResponse
from django.utils import timezone

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseAPIView
from plane.utils.akses_privat import saring_tugas_privat
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import IssueWorkLog, Workspace
from plane.utils.kinerja import (
    LINGKUP_SAYA,
    LingkupDitolak,
    PermintaanSalah,
    hitung_kinerja,
    pilihan_lingkup,
)
from plane.utils.kinerja import PERIODE_BAWAAN as PERIODE_KINERJA_BAWAAN
from plane.utils.laporan_selesai import PERIODE_BAWAAN, PERIODE_SAH, baris_csv, susun_laporan
from plane.utils.ringkasan_divisi import hitung_ringkasan, project_terjangkau


class DivisionDashboardEndpoint(BaseAPIView):
    """Ringkasan per divisi untuk project yang bisa diakses user (KEP-60).

    Seluruh angkanya dihitung di `plane/utils/ringkasan_divisi.py`.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        return Response(hitung_ringkasan(request.user, slug), status=status.HTTP_200_OK)


class CompletedReportEndpoint(BaseAPIView):
    """Laporan tugas selesai per periode (KEP-62). `?unduh=csv` = semua baris sebagai CSV.

    Cakupan sama dengan Dashboard Divisi: hanya project yang user anggotai.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        periode = request.query_params.get("periode", PERIODE_BAWAAN)
        if periode not in PERIODE_SAH:
            return Response(
                {"error": f"periode harus salah satu dari: {', '.join(PERIODE_SAH)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.query_params.get("unduh") != "csv":
            return Response(susun_laporan(request.user, slug, periode), status=status.HTTP_200_OK)

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="laporan-selesai-{periode}-{timezone.now().date().isoformat()}.csv"'
        )
        response.write("﻿")  # BOM agar Excel membaca UTF-8 dengan benar
        writer = csv.writer(response)
        for baris in baris_csv(request.user, slug, periode):
            writer.writerow(baris)
        return response


class WorkLogExportEndpoint(BaseAPIView):
    """Unduh laporan waktu (CSV) dari semua project yang bisa diakses user."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        project_ids = project_terjangkau(request.user, slug).values_list("id", flat=True)
        logs = (
            saring_tugas_privat(
                IssueWorkLog.objects.filter(project_id__in=list(project_ids)), request.user, prefix="issue__"
            )
            .select_related("project", "issue", "logged_by")
            .order_by("project__name", "-logged_at")
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="laporan-waktu-{timezone.now().date().isoformat()}.csv"'
        )
        response.write("﻿")  # BOM agar Excel membaca UTF-8 dengan benar

        writer = csv.writer(response)
        writer.writerow(["Divisi", "Work Item", "Nomor", "Oleh", "Durasi (menit)", "Tanggal", "Keterangan"])
        for log in logs:
            writer.writerow(
                [
                    log.project.name,
                    log.issue.name,
                    f"{log.project.identifier}-{log.issue.sequence_id}",
                    log.logged_by.display_name or log.logged_by.email,
                    log.duration,
                    timezone.localtime(log.logged_at).strftime("%Y-%m-%d %H:%M"),
                    (log.description or "").replace("\n", " "),
                ]
            )
        return response


def _tanggal(teks):
    if not teks:
        return None
    try:
        return date.fromisoformat(teks)
    except ValueError as galat:
        raise PermintaanSalah("Dates must be YYYY-MM-DD.") from galat


class KinerjaEndpoint(BaseAPIView):
    """KPI satu lingkup: diri sendiri, satu orang, departemen, divisi, atau organisasi.

    Lingkup di luar jangkauan pemanggil = 403. Angkanya dihitung di `plane/utils/kinerja.py`.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        q = request.query_params
        try:
            hasil = hitung_kinerja(
                request.user,
                workspace.id,
                q.get("lingkup", LINGKUP_SAYA),
                q.get("id"),
                q.get("periode", PERIODE_KINERJA_BAWAAN),
                _tanggal(q.get("mulai")),
                _tanggal(q.get("sampai")),
            )
        except PermintaanSalah as galat:
            return Response({"error": str(galat)}, status=status.HTTP_400_BAD_REQUEST)
        except LingkupDitolak:
            return Response({"error": "This scope is outside your reach."}, status=status.HTTP_403_FORBIDDEN)
        return Response(hasil, status=status.HTTP_200_OK)


class KinerjaLingkupEndpoint(BaseAPIView):
    """Lingkup yang boleh dipilih pemanggil di halaman KPI."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        return Response(pilihan_lingkup(request.user, workspace.id), status=status.HTTP_200_OK)
