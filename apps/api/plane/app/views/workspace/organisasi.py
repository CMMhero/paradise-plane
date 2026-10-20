# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: struktur organisasi untuk sidebar
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`GET /api/workspaces/<slug>/struktur-organisasi/` untuk sidebar (KEP-29).

Sidebar mengelompokkan project per divisi -> departemen. Endpoint ini hanya
memberi PENGELOMPOKAN: id project yang dikirim dibatasi pada project tempat
pemanggil memang anggota aktif, jadi ia tidak membuka apa pun yang belum bisa
dilihat. Divisi/departemen yang tidak berisi project pemanggil tidak dikirim.
"""

# Third Party imports
from rest_framework.response import Response

# Module imports
from plane.app.permissions import WorkspaceEntityPermission
from plane.app.views.base import BaseAPIView
from plane.db.models import Departemen, DepartemenProject, Divisi, ProjectMember


class StrukturOrganisasiEndpoint(BaseAPIView):
    permission_classes = [WorkspaceEntityPermission]

    def get(self, request, slug):
        divisi = list(Divisi.objects.filter(workspace__slug=slug).order_by("nama"))
        if not divisi:
            return Response({"aktif": False, "divisi": []})

        milik = set(
            ProjectMember.objects.filter(
                workspace__slug=slug, member=request.user, is_active=True, project__archived_at__isnull=True
            ).values_list("project_id", flat=True)
        )
        project_per_dep = {}
        for dep_id, pid in DepartemenProject.objects.filter(workspace__slug=slug, project_id__in=milik).values_list(
            "departemen_id", "project_id"
        ):
            project_per_dep.setdefault(dep_id, []).append(str(pid))

        dep_per_divisi = {}
        for d in Departemen.objects.filter(workspace__slug=slug, id__in=project_per_dep.keys()).order_by("nama"):
            dep_per_divisi.setdefault(d.divisi_id, []).append(
                {"id": str(d.id), "kode": d.kode, "nama": d.nama, "project_ids": project_per_dep[d.id]}
            )

        return Response(
            {
                "aktif": True,
                "divisi": [
                    {"id": str(v.id), "kode": v.kode, "nama": v.nama, "departemen": dep_per_divisi[v.id]}
                    for v in divisi
                    if v.id in dep_per_divisi
                ],
            }
        )
