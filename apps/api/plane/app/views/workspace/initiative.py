# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Initiatives
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.app.permissions import WorkspaceEntityPermission, allow_permission, ROLE
from plane.app.serializers import InitiativeSerializer
from plane.db.models import Initiative, InitiativeProject, Issue, Project, Workspace


def _serialize(initiative):
    """Serialisasi + rollup progres dari seluruh project tertaut."""
    data = InitiativeSerializer(initiative).data
    project_ids = list(
        InitiativeProject.objects.filter(initiative=initiative).values_list("project_id", flat=True)
    )
    issues = Issue.issue_objects.filter(project_id__in=project_ids)
    data["project_ids"] = [str(pid) for pid in project_ids]
    data["issues_total"] = issues.count()
    data["issues_completed"] = issues.filter(state__group="completed").count()
    return data


class InitiativeViewSet(BaseViewSet):
    serializer_class = InitiativeSerializer
    model = Initiative
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        return Initiative.objects.filter(workspace__slug=self.kwargs.get("slug")).order_by("-created_at")

    def list(self, request, slug):
        data = [_serialize(i) for i in self.get_queryset()]
        return Response(data, status=status.HTTP_200_OK)

    def retrieve(self, request, slug, pk):
        return Response(_serialize(self.get_queryset().get(pk=pk)), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def create(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        serializer = InitiativeSerializer(data=request.data)
        if serializer.is_valid():
            initiative = serializer.save(workspace=workspace)
            return Response(_serialize(initiative), status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def partial_update(self, request, slug, pk):
        initiative = self.get_queryset().get(pk=pk)
        serializer = InitiativeSerializer(initiative, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(_serialize(initiative), status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def destroy(self, request, slug, pk):
        initiative = self.get_queryset().get(pk=pk)
        InitiativeProject.objects.filter(initiative=initiative).delete()
        initiative.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def link_project(self, request, slug, pk):
        initiative = self.get_queryset().get(pk=pk)
        project_id = request.data.get("project")
        project = Project.objects.filter(workspace__slug=slug, pk=project_id).first()
        if not project:
            return Response({"error": "Project tidak ditemukan."}, status=status.HTTP_400_BAD_REQUEST)
        InitiativeProject.objects.get_or_create(
            initiative=initiative, project=project, defaults={"workspace": initiative.workspace}
        )
        return Response(_serialize(initiative), status=status.HTTP_200_OK)

    @allow_permission([ROLE.ADMIN], level="WORKSPACE")
    def unlink_project(self, request, slug, pk, project_id):
        initiative = self.get_queryset().get(pk=pk)
        InitiativeProject.objects.filter(initiative=initiative, project_id=project_id).delete()
        return Response(_serialize(initiative), status=status.HTTP_200_OK)
