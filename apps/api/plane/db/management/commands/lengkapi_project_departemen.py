# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tiap departemen tepat satu project (KEP-32)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`python manage.py lengkapi_project_departemen [--dry-run]`

Departemen baru sudah otomatis dapat project. Perintah ini menyusulkan project
untuk departemen yang dibuat sebelum aturan itu atau yang project-nya pernah
dilepas. Project ber-identifier sama yang belum berdepartemen diadopsi; kalau
tidak ada, dibuat baru dengan Super Admin pertama sebagai pembuat. Idempoten.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.models import Departemen, DepartemenProject
from plane.license.api.views.organisasi import _workspace_utama, lengkapi_project_departemen
from plane.license.models import InstanceAdmin


class Command(BaseCommand):
    help = "Give every department without a project its own project (adopt by identifier or create)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List the departments without changing anything.")

    def handle(self, *args, **options):
        workspace = _workspace_utama()
        if workspace is None:
            raise CommandError("No workspace found.")
        tanpa = Departemen.objects.filter(workspace=workspace).exclude(
            pk__in=DepartemenProject.objects.filter(workspace=workspace).values("departemen_id")
        )
        if not tanpa.exists():
            self.stdout.write("Every department already has a project.")
            return
        for dep in tanpa.order_by("kode"):
            self.stdout.write(f"- {dep.kode} {dep.nama}")
        if options["dry_run"]:
            return

        admin = InstanceAdmin.objects.select_related("user").order_by("created_at").first()
        if admin is None:
            raise CommandError("No instance admin found to own the new projects.")
        try:
            with transaction.atomic(), tunda_sinkron():
                hasil = lengkapi_project_departemen(workspace, admin.user)
        except ValueError as e:
            raise CommandError(str(e)) from e
        sinkronkan_workspace(workspace.id)
        for project in hasil:
            self.stdout.write(self.style.SUCCESS(f"  {project.identifier} {project.name}"))
