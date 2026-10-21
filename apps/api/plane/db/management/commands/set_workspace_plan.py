# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Setel tingkatan sebuah workspace dari baris perintah.

Ada supaya tingkatan bisa diubah TANPA bidang kendali. Kolam gratis, instance
pasang-sendiri, dan mesin pengembang semuanya tidak punya pusat yang menjawab
denyut, dan tanpa perintah ini satu-satunya cara menaikkan tingkatan di sana
adalah menulis SQL langsung ke tabel. SQL langsung ke tabel adalah cara yang
paling sering salah ketik dan paling tidak meninggalkan jejak.

    python manage.py set_workspace_plan acme --tier PRO
    python manage.py set_workspace_plan acme --tier ENTERPRISE --storage-gib 500
    python manage.py set_workspace_plan acme --tier FREE --bangunkan
"""

from django.core.management.base import BaseCommand, CommandError

from plane.db.models import Workspace, WorkspacePlan
from plane.utils.plan_limits import BATAS_TINGKATAN, GIB


class Command(BaseCommand):
    help = "Setel tingkatan dan batas sebuah workspace"

    def add_arguments(self, parser):
        parser.add_argument("slug", help="Slug workspace")
        parser.add_argument("--tier", required=True, choices=sorted(BATAS_TINGKATAN))
        parser.add_argument(
            "--storage-gib",
            type=float,
            default=None,
            help="Kuota penyimpanan khusus dalam GiB. Kosongkan untuk memakai bawaan tingkatannya.",
        )
        parser.add_argument(
            "--max-members",
            type=int,
            default=None,
            help="Batas anggota khusus. Kosongkan untuk memakai bawaan tingkatannya.",
        )
        parser.add_argument(
            "--bangunkan",
            action="store_true",
            help="Cabut sekaligus status tidur: peringatan, pembekuan, dan tanda hapus.",
        )

    def handle(self, *args, **opsi):
        workspace = Workspace.objects.filter(
            slug=opsi["slug"], deleted_at__isnull=True
        ).first()
        if workspace is None:
            raise CommandError(f"Workspace '{opsi['slug']}' tidak ada.")

        baris, dibuat = WorkspacePlan.objects.get_or_create(
            workspace=workspace, deleted_at__isnull=True, defaults={"tier": opsi["tier"]}
        )
        baris.tier = opsi["tier"]
        ubah = ["tier"]

        if opsi["storage_gib"] is not None:
            baris.max_storage_bytes = int(opsi["storage_gib"] * GIB)
            ubah.append("max_storage_bytes")
        if opsi["max_members"] is not None:
            baris.max_members = opsi["max_members"]
            ubah.append("max_members")
        if opsi["bangunkan"]:
            baris.dormant_warned_at = None
            baris.uploads_frozen_at = None
            baris.pending_deletion_at = None
            ubah += ["dormant_warned_at", "uploads_frozen_at", "pending_deletion_at"]

        # Tanpa disable_auto_set_user, BaseModel.save() akan menolkan created_by
        # baris yang sudah ada, karena management command tidak punya request.
        baris.save(update_fields=ubah, disable_auto_set_user=True)

        kata = "DIBUAT" if dibuat else "diperbarui"
        self.stdout.write(f"{kata}: {workspace.slug} -> {baris.tier}")
        self.stdout.write(
            "  penyimpanan: "
            + (
                f"{baris.max_storage_bytes / GIB:.1f} GiB (khusus)"
                if baris.max_storage_bytes is not None
                else f"bawaan tingkatan {baris.tier}"
            )
        )
        if opsi["bangunkan"]:
            self.stdout.write("  status tidur dicabut")
