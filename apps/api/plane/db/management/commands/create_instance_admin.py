# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.core.management.base import BaseCommand, CommandError

# Module imports
from plane.license.models import Instance, InstanceAdmin
from plane.db.models import User
from plane.db.superadmin import angkat_super_admin


class Command(BaseCommand):
    help = "Add a new instance admin"

    def add_arguments(self, parser):
        # Positional argument
        parser.add_argument("admin_email", type=str, help="Instance Admin Email")

    def handle(self, *args, **options):
        admin_email = options.get("admin_email", False)

        if not admin_email:
            raise CommandError("Please provide the email of the admin.")

        user = User.objects.filter(email=admin_email).first()
        if user is None:
            raise CommandError("User with the provided email does not exist.")

        try:
            # Get the instance
            instance = Instance.objects.last()

            # Kustomisasi Paradise: Super Admin yang pernah dicabut masih punya
            # baris soft-deleted; `get_or_create` tidak melihatnya dan INSERT-nya
            # menabrak unique (instance, user). Lihat `angkat_super_admin`.
            if InstanceAdmin.objects.filter(user=user, instance=instance).exists():
                raise CommandError("The provided email is already an instance admin.")
            angkat_super_admin(instance, user)

            self.stdout.write(self.style.SUCCESS("Successfully created the admin"))
        except Exception as e:
            print(e)
            raise CommandError("Failed to create the instance admin.")
