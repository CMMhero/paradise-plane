# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Work Item Types
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import transaction

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.app.serializers import IssueTypeSerializer
from plane.app.permissions import allow_permission, ProjectBasePermission, ROLE
from plane.db.models import IssueType, ProjectIssueType, Project


class IssueTypeViewSet(BaseViewSet):
    serializer_class = IssueTypeSerializer
    model = IssueType
    permission_classes = [ProjectBasePermission]

    def get_queryset(self):
        # Tipe yang tertaut ke project ini (lewat ProjectIssueType)
        return (
            IssueType.objects.filter(
                workspace__slug=self.kwargs.get("slug"),
                project_issue_types__project_id=self.kwargs.get("project_id"),
                project_issue_types__deleted_at__isnull=True,
            )
            .distinct()
            .order_by("level", "created_at")
        )

    def list(self, request, slug, project_id):
        serializer = IssueTypeSerializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id):
        project = Project.objects.get(pk=project_id)
        if IssueType.objects.filter(
            workspace__slug=slug,
            name__iexact=str(request.data.get("name", "")).strip(),
            project_issue_types__project_id=project_id,
            project_issue_types__deleted_at__isnull=True,
        ).exists():
            return Response(
                {"error": "Tipe dengan nama itu sudah ada di project ini."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = IssueTypeSerializer(data=request.data)
        if serializer.is_valid():
            with transaction.atomic():
                issue_type = serializer.save(workspace_id=project.workspace_id)
                ProjectIssueType.objects.create(
                    project=project,
                    workspace_id=project.workspace_id,
                    issue_type=issue_type,
                    level=issue_type.level or 0,
                    is_default=issue_type.is_default,
                )
                # Aktifkan fitur tipe di project saat tipe pertama dibuat
                if not project.is_issue_type_enabled:
                    project.is_issue_type_enabled = True
                    project.save(update_fields=["is_issue_type_enabled"])
            return Response(IssueTypeSerializer(issue_type).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def partial_update(self, request, slug, project_id, pk):
        issue_type = self.get_queryset().get(pk=pk)
        serializer = IssueTypeSerializer(issue_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, pk):
        issue_type = self.get_queryset().get(pk=pk)
        if issue_type.is_default:
            return Response(
                {"error": "Tipe default tidak bisa dihapus."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            # Bersihkan turunan tipe agar tidak yatim: nilai -> opsi -> field
            from plane.db.models import IssueProperty, IssuePropertyOption, IssuePropertyValue

            IssuePropertyValue.objects.filter(property__issue_type=issue_type).delete()
            IssuePropertyOption.objects.filter(property__issue_type=issue_type).delete()
            IssueProperty.objects.filter(issue_type=issue_type).delete()
            ProjectIssueType.objects.filter(project_id=project_id, issue_type=issue_type).delete()
            issue_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
