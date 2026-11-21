# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi assignee tugas buatan staf (2.11)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`python manage.py isi_assignee_staf [--apply] [--termasuk-selesai]`

Tugas buatan staf yang belum punya assignee diberi assignee: pembuatnya. Logikanya
sama dengan migrasi 0186 (satu fungsi di `plane.utils.isi_assignee_staf`, aturan
pilihnya ada di sana). Bawaannya dry run: hanya menghitung. `--apply` menulis.
Idempoten, dan tidak mengirim aktivitas, notifikasi, atau email.
"""

from django.apps import apps
from django.core.management.base import BaseCommand

from plane.utils.isi_assignee_staf import isi_assignee_staf, ringkas


class Command(BaseCommand):
    help = "Assign staff-created work items that have no assignee to their creator. Dry run unless --apply."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write the assignees. Without it nothing is written.")
        parser.add_argument(
            "--termasuk-selesai",
            action="store_true",
            help="Also fill completed and cancelled work items (skipped by default: it shifts KPI and workload numbers).",
        )
        parser.add_argument("--dry-run", action="store_true", help="Count only (the default). Wins over --apply.")

    def handle(self, *args, **options):
        tulis = options["apply"] and not options["dry_run"]
        hasil = isi_assignee_staf(apps.get_model, apply=tulis, include_closed=options["termasuk_selesai"])
        self.stdout.write(ringkas(hasil))
        if tulis:
            self.stdout.write(self.style.SUCCESS("Done."))
        else:
            self.stdout.write("Dry run: nothing was written. Use --apply to write.")
