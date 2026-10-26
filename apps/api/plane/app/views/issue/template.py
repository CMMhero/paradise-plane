# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Templates & Recurring Work Items
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet, BaseAPIView
from plane.app.serializers import (
    IssueTemplateSerializer,
    RecurringIssueSerializer,
    IssueSerializer,
)
from plane.app.permissions import allow_permission, ProjectBasePermission, ROLE
from plane.db.models import Issue, IssueAssignee, IssueTemplate, RecurringIssue


class IssueTemplateViewSet(BaseViewSet):
    serializer_class = IssueTemplateSerializer
    model = IssueTemplate
    permission_classes = [ProjectBasePermission]

    def get_queryset(self):
        return IssueTemplate.objects.filter(
            workspace__slug=self.kwargs.get("slug"),
            project_id=self.kwargs.get("project_id"),
        ).order_by("-created_at")

    def list(self, request, slug, project_id):
        serializer = IssueTemplateSerializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id):
        serializer = IssueTemplateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project_id=project_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def partial_update(self, request, slug, project_id, pk):
        template = self.get_queryset().get(pk=pk)
        serializer = IssueTemplateSerializer(template, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, pk):
        template = self.get_queryset().get(pk=pk)
        RecurringIssue.objects.filter(template=template).delete()
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class IssueTemplateApplyEndpoint(BaseAPIView):
    """Buat work item baru dari template (anggota project)."""

    permission_classes = [ProjectBasePermission]

    def post(self, request, slug, project_id, pk):
        template = IssueTemplate.objects.filter(
            workspace__slug=slug, project_id=project_id, pk=pk
        ).first()
        if not template:
            return Response({"error": "Template tidak ditemukan."}, status=status.HTTP_404_NOT_FOUND)

        issue = Issue.objects.create(
            project=template.project,
            name=template.title,
            description_html=template.description_html or "<p></p>",
            priority=template.priority or "none",
            created_by=request.user,
        )
        if template.default_assignee_id:
            # Template ditulis admin, tapi yang menekan "apply" bisa staf — dan
            # jalur ini menulis IssueAssignee LANGSUNG tanpa serializer, jadi
            # tanpa pemeriksaan di sini ia jadi pintu pintas (prinsip #1).
            from plane.utils.hierarki import galat_penugasan  # noqa: PLC0415

            if not galat_penugasan(project_id, [template.default_assignee_id], actor=request.user):
                IssueAssignee.objects.create(
                    issue=issue,
                    assignee_id=template.default_assignee_id,
                    project=template.project,
                    workspace=template.workspace,
                    created_by=request.user,
                )
            else:
                # Ditolak = tugasnya tetap lahir TANPA assignee, bukan 400.
                # Tugas tanpa penerima tidak butuh persetujuan, jadi staf tetap
                # bisa bekerja — yang hilang cuma penugasan otomatisnya.
                pass
        return Response(IssueSerializer(issue).data, status=status.HTTP_201_CREATED)


class RecurringIssueViewSet(BaseViewSet):
    serializer_class = RecurringIssueSerializer
    model = RecurringIssue
    permission_classes = [ProjectBasePermission]

    def get_queryset(self):
        return (
            RecurringIssue.objects.filter(
                workspace__slug=self.kwargs.get("slug"),
                project_id=self.kwargs.get("project_id"),
            )
            .select_related("template")
            .order_by("next_run_at")
        )

    def list(self, request, slug, project_id):
        serializer = RecurringIssueSerializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN])
    def create(self, request, slug, project_id):
        template_id = request.data.get("template")
        if not IssueTemplate.objects.filter(
            workspace__slug=slug, project_id=project_id, pk=template_id
        ).exists():
            return Response({"error": "Template tidak valid untuk project ini."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = RecurringIssueSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(project_id=project_id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def partial_update(self, request, slug, project_id, pk):
        rec = self.get_queryset().get(pk=pk)
        serializer = RecurringIssueSerializer(rec, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN])
    def destroy(self, request, slug, project_id, pk):
        self.get_queryset().get(pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
