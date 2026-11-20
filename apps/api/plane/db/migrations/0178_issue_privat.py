# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tugas privat (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Kolom `is_private` (bawaan False, jadi tidak ada tugas lama yang tersembunyi).

    Indeks parsial: saringan privat membaca "project mana yang punya tugas privat"
    di setiap daftar, dan tugas privat hanya sebagian kecil dari tabel.
    """

    dependencies = [("db", "0177_tingkat_leader")]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="is_private",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="issue",
            index=models.Index(
                condition=models.Q(is_private=True),
                fields=["workspace", "project"],
                name="issue_privat_idx",
            ),
        ),
    ]
