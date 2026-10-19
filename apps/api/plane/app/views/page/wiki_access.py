# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kelola ACL folder Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from ..base import BaseAPIView
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import Page, Project, WikiFolderAccess, WikiGovernedProject
from plane.utils.wiki_access import is_wiki_governed


def _divisions_of(folder_ids, project_id):
    """Peta folder_id -> daftar divisi pemilik, satu query untuk semua folder."""
    rows = (
        WikiFolderAccess.objects.filter(folder_id__in=folder_ids, project_id=project_id)
        .select_related("division")
        .values_list("folder_id", "division_id", "division__identifier", "division__name")
    )
    out = {}
    for folder_id, division_id, identifier, name in rows:
        # Baris aktif ganda mungkin ada (Postgres menganggap NULL berbeda, jadi
        # unique_together dgn deleted_at tidak mencegahnya). Tidak berbahaya,
        # izin dievaluasi dengan __in, tapi jangan tampilkan dobel di UI.
        bucket = out.setdefault(folder_id, {})
        bucket[division_id] = {"id": str(division_id), "identifier": identifier, "name": name}
    return {fid: list(d.values()) for fid, d in out.items()}


class WikiAccessEndpoint(BaseAPIView):
    """Baca & ubah status governance ACL folder untuk sebuah project Wiki.

    GET  -> status governance, daftar folder top-level + divisi pemiliknya,
            dan daftar project yang bisa dipilih sebagai pemilik.
    POST -> {"is_governed": true|false} menyalakan/mematikan governance.

    Admin project saja (workspace admin yang jadi anggota project juga lolos,
    lihat allow_permission).
    """

    @allow_permission([ROLE.ADMIN])
    def get(self, request, slug, project_id):
        folders = list(
            Page.objects.filter(
                projects=project_id, parent__isnull=True, workspace__slug=slug
            ).order_by("name")
        )
        owners = _divisions_of([f.id for f in folders], project_id)

        return Response(
            {
                "is_governed": is_wiki_governed(project_id),
                "folders": [
                    {
                        "id": str(f.id),
                        "name": f.name,
                        "divisions": owners.get(f.id, []),
                    }
                    for f in folders
                ],
                "available_divisions": [
                    {"id": str(p.id), "identifier": p.identifier, "name": p.name}
                    for p in Project.objects.filter(workspace__slug=slug)
                    .exclude(id=project_id)
                    .order_by("name")
                ],
                # Folder "General": semua orang boleh mengunggah.
                #
                # Tidak ada mode ketiga di model, dan memang tidak perlu ada.
                # Seluruh anggota Wiki adalah ProjectMember project Wiki, jadi
                # menunjuk project Wiki SENDIRI sebagai divisi pemilik berarti
                # "siapa pun anggota Wiki boleh mengunggah di sini", dievaluasi
                # oleh resolver yang sama tanpa satu pun cabang baru.
                #
                # Nilainya dikirim terpisah, bukan diselipkan ke
                # available_divisions, supaya UI bisa menamainya apa adanya
                # ("Semua anggota Wiki") alih-alih menampilkan project Wiki
                # sebagai kalau-kalau ia sebuah divisi.
                "general_division_id": str(project_id),
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission([ROLE.ADMIN])
    def post(self, request, slug, project_id):
        is_governed = request.data.get("is_governed")
        if not isinstance(is_governed, bool):
            return Response(
                {"error": "is_governed harus boolean."}, status=status.HTTP_400_BAD_REQUEST
            )

        already = is_wiki_governed(project_id)
        # Idempoten: menyalakan yang sudah nyala tidak menumpuk baris.
        if is_governed and not already:
            project = Project.objects.get(id=project_id, workspace__slug=slug)
            WikiGovernedProject.objects.create(project=project, workspace=project.workspace)
        elif not is_governed and already:
            WikiGovernedProject.objects.filter(project_id=project_id).delete()

        return Response({"is_governed": is_governed}, status=status.HTTP_200_OK)


class WikiFolderAccessEndpoint(BaseAPIView):
    """Set divisi pemilik satu folder top-level.

    PUT {"division_ids": [...]} MENGGANTI seluruh daftar pemilik folder itu.
    Daftar kosong = tidak ada pemilik = hanya admin project yang bisa mengedit.

    Sengaja replace, bukan tambah/hapus satuan: UI menampilkan centang per
    folder lalu simpan, dan replace membuat hasil akhir tidak bergantung urutan
    permintaan kalau dua admin menyimpan bersamaan.
    """

    @allow_permission([ROLE.ADMIN])
    def put(self, request, slug, project_id, folder_id):
        folder = Page.objects.filter(
            id=folder_id, projects=project_id, workspace__slug=slug
        ).first()
        if folder is None:
            return Response(
                {"error": "Folder tidak ditemukan di project ini."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if folder.parent_id is not None:
            # Resolver izin selalu naik ke folder teratas, jadi memberi pemilik
            # ke sub-halaman tidak akan pernah berpengaruh, tolak, jangan diam.
            return Response(
                {"error": "Hanya folder top-level yang bisa diberi pemilik."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        division_ids = request.data.get("division_ids")
        if not isinstance(division_ids, list):
            return Response(
                {"error": "division_ids harus berupa list."}, status=status.HTTP_400_BAD_REQUEST
            )

        wanted = set(map(str, division_ids))
        valid = set(
            map(
                str,
                Project.objects.filter(id__in=wanted, workspace__slug=slug).values_list(
                    "id", flat=True
                ),
            )
        )
        if wanted - valid:
            return Response(
                {"error": f"Divisi tidak dikenal: {sorted(wanted - valid)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current_qs = WikiFolderAccess.objects.filter(folder=folder, project_id=project_id)
        current = set(map(str, current_qs.values_list("division_id", flat=True)))

        removed = current - wanted
        if removed:
            current_qs.filter(division_id__in=removed).delete()

        project = Project.objects.get(id=project_id, workspace__slug=slug)
        for division_id in wanted - current:
            WikiFolderAccess.objects.create(
                folder=folder,
                division_id=division_id,
                project=project,
                workspace=project.workspace,
            )

        return Response(
            {
                "folder_id": str(folder.id),
                "divisions": _divisions_of([folder.id], project_id).get(folder.id, []),
            },
            status=status.HTTP_200_OK,
        )
