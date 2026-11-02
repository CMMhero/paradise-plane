# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Dashboard Divisi + Laporan Waktu
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import csv

# Django imports
from django.http import HttpResponse
from django.utils import timezone

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import IssueWorkLog
from plane.utils.ringkasan_divisi import hitung_ringkasan, project_terjangkau


class DivisionDashboardEndpoint(BaseAPIView):
    """Ringkasan per divisi untuk project yang bisa diakses user (KEP-60).

    Seluruh angkanya dihitung di `plane/utils/ringkasan_divisi.py`.
    """

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        return Response(hitung_ringkasan(request.user, slug), status=status.HTTP_200_OK)


class WorkLogExportEndpoint(BaseAPIView):
    """Unduh laporan waktu (CSV) dari semua project yang bisa diakses user."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        project_ids = project_terjangkau(request.user, slug).values_list("id", flat=True)
        logs = (
            IssueWorkLog.objects.filter(project_id__in=list(project_ids))
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
