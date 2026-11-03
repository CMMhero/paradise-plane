# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: catatan rilis ke kanal Changelog
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`python manage.py terbitkan_changelog`

Menerbitkan `plane/release_notes/<versi>.json` yang belum terbit ke kanal
Changelog setiap workspace. Idempoten. Dipanggil entrypoint API saat start;
di sana galatnya ditelan supaya start tidak pernah gagal karenanya. Dijalankan
manual, galatnya tetap muncul.
"""

from django.core.management.base import BaseCommand

from plane.utils.catatan_rilis import terbitkan, versi_berjalan


class Command(BaseCommand):
    help = "Post unposted release notes to every workspace's Changelog channel."

    def add_arguments(self, parser):
        parser.add_argument("--versi", default=None, help="Treat this as the running version (default: package.json).")

    def handle(self, *args, **options):
        versi = options.get("versi") or versi_berjalan()
        jumlah = terbitkan(versi)
        self.stdout.write(f"changelog: {jumlah} post(s) written (running version {versi or '?'})")
