# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Initiatives
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from collections import defaultdict

from django.db.models import Count, Q

# Third Party imports
from rest_framework.response import Response
from rest_framework import status

# Module imports
from .. import BaseViewSet
from plane.app.permissions import WorkspaceEntityPermission, allow_permission, ROLE
from plane.app.serializers import InitiativeSerializer
from plane.db.models import Initiative, InitiativeProject, Issue, Project, Workspace


def _serialize_banyak(initiatives):
    """Serialisasi + rollup progres dari seluruh project tertaut, untuk banyak initiative.

    Dua kueri agregat untuk seluruh daftar, bukan tiga kueri per initiative.
    Satu issue hanya milik satu project, jadi menjumlah hitungan per project
    sama dengan menghitung langsung atas gabungan project-nya.
    """
    initiatives = list(initiatives)
    project_per_initiative = defaultdict(list)
    for initiative_id, project_id in InitiativeProject.objects.filter(initiative__in=initiatives).values_list(
        "initiative_id", "project_id"
    ):
        project_per_initiative[initiative_id].append(project_id)

    semua_project = {pid for pids in project_per_initiative.values() for pid in pids}
    hitungan = {
        baris["project_id"]: baris
        for baris in Issue.issue_objects.filter(project_id__in=semua_project)
        .order_by()
        .values("project_id")
        .annotate(total=Count("id"), selesai=Count("id", filter=Q(state__group="completed")))
    }

    hasil = []
    for initiative in initiatives:
        data = InitiativeSerializer(initiative).data
        project_ids = project_per_initiative.get(initiative.id, [])
        data["project_ids"] = [str(pid) for pid in project_ids]
        data["issues_total"] = sum(hitungan.get(pid, {}).get("total", 0) for pid in project_ids)
        data["issues_completed"] = sum(hitungan.get(pid, {}).get("selesai", 0) for pid in project_ids)
        hasil.append(data)
    return hasil


def _serialize(initiative):
    return _serialize_banyak([initiative])[0]


class InitiativeViewSet(BaseViewSet):
    serializer_class = InitiativeSerializer
    model = Initiative
    permission_classes = [WorkspaceEntityPermission]

    def get_queryset(self):
        return Initiative.objects.filter(workspace__slug=self.kwargs.get("slug")).order_by("-created_at")

    def list(self, request, slug):
        data = _serialize_banyak(self.get_queryset())
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
