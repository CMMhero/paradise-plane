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
from plane.db.models import Page, Project, ProjectMember, WikiFolderAccess
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
            .values_list("id", flat=True)
        )

        owners = {}
        label = {}
        for folder_id, division_id, identifier, name in WikiFolderAccess.objects.filter(
            folder_id__in=folders, project_id=project_id, deleted_at__isnull=True
        ).values_list("folder_id", "division_id", "division__identifier", "division__name"):
            owners.setdefault(folder_id, set()).add(division_id)
            label[division_id] = {"id": str(division_id), "identifier": identifier, "name": name}

        super_admin = is_super_admin(user)
        # Hak tulis Wiki = admin workspace atau Super Admin saja (2026-10-26).
        wiki_admin = is_wiki_admin(user, workspace_slug=slug)
        project_admin = wiki_admin

        payload = []
        for folder_id in folders:
            division_ids = owners.get(folder_id, set())
            payload.append(
                {
                    "id": str(folder_id),
                    # Boleh menaruh Topik/Materi baru di dalam folder ini.
                    "can_upload": wiki_admin,
                    # Boleh membereskan materi orang lain di folder ini.
                    "is_lead": wiki_admin,
                    # Folder "General": pemiliknya project Wiki itu sendiri,
                    # jadi seluruh anggota Wiki boleh mengunggah ke sini.
                    "is_general": project_id in division_ids,
                    # Siapa yang mengurus folder ini. Sengaja terlihat oleh semua
                    # orang, bukan cuma admin: folder yang tidak punya nama
                    # penanggung jawab adalah folder yang pelan-pelan jadi tong
                    # sampah, dan itu pola yang sudah terdokumentasi di mana-mana.
                    "divisions": sorted(
                        (
                            label[d]
                            for d in division_ids
                            if d in label and d != project_id
                        ),
                        key=lambda x: x["name"],
                    ),
                }
            )

        # Halaman mana saja yang boleh DIKELOLA orang ini: ganti nama, ganti
        # ikon, hapus. Dihitung server dalam satu sapuan, bukan disalin jadi
        # aturan kembar di TypeScript, karena aturan izin yang hidup di dua
        # bahasa cepat atau lambat berbeda pendapat.
        #
        # Aturannya sama persis dengan halaman: pengunggahnya, kepala divisi
        # pemilik folder teratas, atau Super Admin.
        semua = Page.objects.filter(
            projects=project_id, workspace__slug=slug, deleted_at__isnull=True
        ).values_list("id", "parent_id", "owned_by_id")
        induk = {pid: parent for pid, parent, _ in semua}

        def teratas(page_id):
            kini = page_id
            for _ in range(20):
                orang_tua = induk.get(kini)
                if orang_tua is None:
                    return kini
                kini = orang_tua
            return kini

        manageable = [
            str(pid)
            for pid, _, owner in semua
            if wiki_admin
        ]

        return Response(
            {
                "is_governed": is_wiki_governed(project_id),
                "is_super_admin": super_admin,
                "is_project_admin": project_admin,
                "user_id": str(user.id),
                "folders": payload,
                "manageable_page_ids": manageable,
                # Bahan untuk panel "Kelola" di dalam Wiki, supaya mengatur
                # divisi pemilik tidak lagi harus lewat Setelan project yang
                # sejak Wiki punya rute sendiri tidak ada jalannya lagi.
                #
                # Hanya dikirim ke admin project. Daftar seluruh project adalah
                # informasi struktur organisasi, dan tidak ada alasan setiap
                # anggota Wiki menerimanya hanya untuk melihat kartu.
                "general_division_id": str(project_id) if project_admin else None,
                "available_divisions": (
                    [
                        {"id": str(p.id), "identifier": p.identifier, "name": p.name}
                        for p in Project.objects.filter(workspace__slug=slug)
                        .exclude(id=project_id)
                        .order_by("name")
                    ]
                    if project_admin
                    else []
                ),
            },
            status=status.HTTP_200_OK,
        )
