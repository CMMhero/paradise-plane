# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from typing import Any
from django.core.management import BaseCommand, CommandError

# Module imports
from plane.db.membership import jadikan_anggota_project
from plane.db.models import (
    User,
    WorkspaceMember,
    Project,
    ProjectUserProperty,
)


class Command(BaseCommand):
    help = "Add a member to a project. If present in the workspace"

    def add_arguments(self, parser):
        # Positional argument
        parser.add_argument("--project_id", type=str, nargs="?", help="Project ID")
        parser.add_argument("--user_email", type=str, nargs="?", help="User Email")
        parser.add_argument("--role", type=int, nargs="?", help="Role of the user in the project")

    def handle(self, *args: Any, **options: Any):
        try:
            if not options["project_id"]:
                raise CommandError("Project ID is required")
            if not options["user_email"]:
                raise CommandError("User Email is required")

            project_id = options["project_id"]
            user_email = options["user_email"]
            role = options.get("role", 20)

            print(f"Role: {role}")

            user = User.objects.filter(email=user_email).first()
            if not user:
                raise CommandError("User not found")

            # Check if the project exists
            project = Project.objects.filter(pk=project_id).first()
            if not project:
                raise CommandError("Project not found")

            # Check if the user exists in the workspace
            if not WorkspaceMember.objects.filter(workspace=project.workspace, member=user, is_active=True).exists():
                raise CommandError("User not member in workspace")


            # Keanggotaan lewat `jadikan_anggota_project`, bukan
            # `ProjectMember.objects.create()` telanjang. Pemeriksaan lama di
            # sini memakai manager bawaan, yang tidak melihat baris
            # ter-soft-delete, jadi `create()` untuk pasangan yang pernah
            # dicabut menabrak constraint unik `ProjectUserProperty` milik baris
            # lama yang masih hidup — dan gagalnya traceback, bukan CommandError.
            jadikan_anggota_project(project.id, user.id, role, workspace_id=project.workspace_id)

            # Issue Property
            ProjectUserProperty.objects.get_or_create(user=user, project=project)

            # Success message
            self.stdout.write(self.style.SUCCESS(f"User {user_email} added to project {project_id}"))
            return
        except CommandError as e:
            self.stdout.write(self.style.ERROR(e))
            return
