# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Dashboard Divisi + Laporan Waktu
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import csv

# Django imports
from django.db.models import Sum
from django.http import HttpResponse
from django.utils import timezone

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseAPIView
from plane.app.permissions import WorkspaceEntityPermission
from plane.db.models import Issue, IssueWorkLog, Project, ProjectMember


def _accessible_projects(user, slug):
    return (
        Project.objects.filter(
            workspace__slug=slug,
            project_projectmember__member=user,
            project_projectmember__is_active=True,
            archived_at__isnull=True,
        )
        .distinct()
        .order_by("name")
    )


class DivisionDashboardEndpoint(BaseAPIView):
    """Rekap per-divisi (project) untuk project yang bisa diakses user."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        today = timezone.now().date()
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        rows = []
        for project in _accessible_projects(request.user, slug):
            issues = Issue.issue_objects.filter(project=project)
            total = issues.count()
            completed = issues.filter(state__group="completed").count()
            overdue = (
                issues.filter(target_date__lt=today)
                .exclude(state__group__in=["completed", "cancelled"])
                .count()
            )
            worklogs = IssueWorkLog.objects.filter(project=project)
            minutes_total = worklogs.aggregate(s=Sum("duration"))["s"] or 0
            minutes_month = (
                worklogs.filter(logged_at__gte=month_start).aggregate(s=Sum("duration"))["s"] or 0
            )
            rows.append(
                {
                    "id": str(project.id),
                    "identifier": project.identifier,
                    "name": project.name,
                    "members": ProjectMember.objects.filter(project=project, is_active=True).count(),
                    "issues_total": total,
                    "issues_completed": completed,
                    "issues_open": total - completed,
                    "issues_overdue": overdue,
                    "worklog_minutes_total": minutes_total,
                    "worklog_minutes_month": minutes_month,
                }
            )

        totals = {
            "projects": len(rows),
            "issues_total": sum(r["issues_total"] for r in rows),
            "issues_open": sum(r["issues_open"] for r in rows),
            "issues_overdue": sum(r["issues_overdue"] for r in rows),
            "issues_completed": sum(r["issues_completed"] for r in rows),
            "worklog_minutes_total": sum(r["worklog_minutes_total"] for r in rows),
            "worklog_minutes_month": sum(r["worklog_minutes_month"] for r in rows),
        }
        return Response({"totals": totals, "projects": rows}, status=status.HTTP_200_OK)


class WorkLogExportEndpoint(BaseAPIView):
    """Unduh laporan waktu (CSV) dari semua project yang bisa diakses user."""

    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        project_ids = _accessible_projects(request.user, slug).values_list("id", flat=True)
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
