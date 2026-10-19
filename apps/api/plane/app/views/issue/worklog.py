# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Time Tracking
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db.models import Sum

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.app.serializers import IssueWorkLogSerializer
from plane.app.permissions import ProjectEntityPermission, ROLE
from plane.db.models import IssueWorkLog, ProjectMember


class IssueWorkLogViewSet(BaseViewSet):
    permission_classes = [ProjectEntityPermission]

    model = IssueWorkLog
    serializer_class = IssueWorkLogSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .filter(project_id=self.kwargs.get("project_id"))
            .filter(issue_id=self.kwargs.get("issue_id"))
            .filter(
                project__project_projectmember__member=self.request.user,
                project__project_projectmember__is_active=True,
                project__archived_at__isnull=True,
            )
            .select_related("logged_by")
            .order_by("-logged_at")
            .distinct()
        )

    def _is_project_admin(self, slug, project_id):
        return ProjectMember.objects.filter(
            workspace__slug=slug,
            project_id=project_id,
            member=self.request.user,
            role=ROLE.ADMIN.value,
            is_active=True,
        ).exists()

    def list(self, request, slug, project_id, issue_id):
        logs = self.get_queryset()
        total = logs.aggregate(total=Sum("duration")).get("total") or 0
        serializer = IssueWorkLogSerializer(logs, many=True)
        return Response(
            {"total_duration": total, "work_logs": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, slug, project_id, issue_id):
        serializer = IssueWorkLogSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                project_id=project_id,
                issue_id=issue_id,
                logged_by=request.user,
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, slug, project_id, issue_id, pk):
        work_log = IssueWorkLog.objects.get(
            workspace__slug=slug, project_id=project_id, issue_id=issue_id, pk=pk
        )
        # Hanya pemilik catatan atau admin project yang boleh ubah
        if work_log.logged_by_id != request.user.id and not self._is_project_admin(slug, project_id):
            return Response(
                {"error": "Kamu hanya bisa mengubah catatan waktumu sendiri."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = IssueWorkLogSerializer(work_log, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, slug, project_id, issue_id, pk):
        work_log = IssueWorkLog.objects.get(
            workspace__slug=slug, project_id=project_id, issue_id=issue_id, pk=pk
        )
        if work_log.logged_by_id != request.user.id and not self._is_project_admin(slug, project_id):
            return Response(
                {"error": "Kamu hanya bisa menghapus catatan waktumu sendiri."},
                status=status.HTTP_403_FORBIDDEN,
            )
        work_log.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
