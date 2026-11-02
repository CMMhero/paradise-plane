# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: izin Wiki borongan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from ..base import BaseAPIView
from plane.app.permissions import allow_permission, ROLE
from plane.db.models import Divisi, Page, ProjectMember, WikiFolderAccess
from plane.utils.wiki_access import is_super_admin, is_wiki_admin, is_wiki_governed



class WikiPermissionsEndpoint(BaseAPIView):
    """Sekali tanya, semua kartu Wiki tahu apa yang boleh dilakukan pemakainya.

    Endpoint `can-edit` yang sudah ada menjawab satu halaman per permintaan.
    Itu benar untuk server Live yang memang membuka satu dokumen, tapi salah
    untuk halaman daftar: sepuluh kartu Divisi berarti sepuluh permintaan tiap
    kali orang membuka Wiki.

    Yang dikembalikan hanya bendera per folder TERATAS, bukan per halaman,
    karena resolver izin memang selalu naik ke folder teratas. Jadi klien cukup
    menelusuri satu halaman ke induknya untuk tahu haknya, tanpa menyalin satu
    pun aturan izin ke TypeScript.

    Sengaja TIDAK mengembalikan daftar orang atau divisi: ini jawaban tentang
    pemakai yang bertanya, bukan direktori.
    """

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def get(self, request, slug, project_id):
        user = request.user

        folders = list(
            Page.objects.filter(
                projects=project_id,
                parent__isnull=True,
                workspace__slug=slug,
                deleted_at__isnull=True,
            )
            .order_by("name")
            .values_list("id", "name")
        )

        owners = {}
        label = {}
        for folder_id, division_id, identifier, name in WikiFolderAccess.objects.filter(
            folder_id__in=[fid for fid, _ in folders], project_id=project_id, deleted_at__isnull=True
        ).values_list("folder_id", "division_id", "division__identifier", "division__name"):
            owners.setdefault(folder_id, set()).add(division_id)
            label[division_id] = {"id": str(division_id), "identifier": identifier, "name": name}

        super_admin = is_super_admin(user)
        # Struktur Wiki (folder, sub-topik) = admin workspace atau Super Admin.
        wiki_admin = is_wiki_admin(user, workspace_slug=slug)

        # Satu query untuk semua folder: project mana saja yang orang ini
        # anggota aktifnya (member/admin). Aturannya sama dengan
        # `can_edit_wiki_page`, hanya dievaluasi borongan.
        keanggotaan = set(
            ProjectMember.objects.filter(
                member=user,
                workspace__slug=slug,
                role__gte=ROLE.MEMBER.value,
                is_active=True,
                deleted_at__isnull=True,
            ).values_list("project_id", flat=True)
        )
        nama_divisi = set(
            Divisi.objects.filter(workspace__slug=slug, deleted_at__isnull=True).values_list("nama", flat=True)
        )

        payload = []
        for folder_id, folder_name in folders:
            division_ids = owners.get(folder_id, set())
            # Bawaan KEP-51: folder non-divisi tanpa pemilik = General.
            general = project_id in division_ids or (not division_ids and folder_name not in nama_divisi)
            pengunggah = {project_id} if general else division_ids
            payload.append(
                {
                    "id": str(folder_id),
                    # Boleh menaruh Materi baru di dalam folder ini.
                    "can_upload": wiki_admin or bool(pengunggah & keanggotaan),
                    # Boleh membereskan materi orang lain di folder ini.
                    "is_lead": wiki_admin,
                    "is_general": general,
                    # Departemen pemilik folder, diturunkan dari struktur
                    # organisasi God Mode. Terlihat oleh semua orang supaya
                    # tiap folder punya nama penanggung jawab.
                    "divisions": sorted(
                        (label[d] for d in division_ids if d in label and d != project_id),
                        key=lambda x: x["name"],
                    ),
                }
            )

        # Halaman (folder & sub-topik) yang boleh dikelola: ganti nama, ikon,
        # hapus. Struktur hanya untuk admin, jadi semua atau tidak sama sekali.
        manageable = (
            [
                str(pid)
                for pid in Page.objects.filter(
                    projects=project_id, workspace__slug=slug, deleted_at__isnull=True
                ).values_list("id", flat=True)
            ]
            if wiki_admin
            else []
        )

        return Response(
            {
                "is_governed": is_wiki_governed(project_id),
                "is_super_admin": super_admin,
                "is_project_admin": wiki_admin,
                "user_id": str(user.id),
                "folders": payload,
                "manageable_page_ids": manageable,
            },
            status=status.HTTP_200_OK,
        )
