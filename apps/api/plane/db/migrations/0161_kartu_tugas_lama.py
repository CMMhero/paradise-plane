# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: DM penugasan lama jadi kartu
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""DM penugasan teks dari sebelum 2.2.0 dirender sebagai kartu (3 Nov 2026).

Logikanya di `plane.utils.kartu_tugas_lama` (diuji di sana). Bisa dibalik:
hanya kartu bertanda `asal = teks_lama` yang dikembalikan ke teks.
"""

from django.db import migrations

from plane.utils.kartu_tugas_lama import kembalikan_ke_teks, ubah_ke_kartu


def _maju(apps, schema_editor):
    ubah_ke_kartu(
        apps.get_model("db", "PesanLangsung"),
        apps.get_model("db", "Issue"),
        apps.get_model("db", "IssueAssignee"),
    )


def _mundur(apps, schema_editor):
    kembalikan_ke_teks(apps.get_model("db", "PesanLangsung"))


class Migration(migrations.Migration):
    dependencies = [("db", "0160_profil_kontak")]

    operations = [migrations.RunPython(_maju, _mundur)]
