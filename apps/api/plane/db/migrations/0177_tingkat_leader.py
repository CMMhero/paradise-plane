# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jenjang Leader (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Hanya `choices` yang berubah (12 = Leader): tidak ada DDL, tidak ada data."""

    dependencies = [("db", "0176_project_network_privat")]

    operations = [
        migrations.AlterField(
            model_name="jabatanorganisasi",
            name="tingkat",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (10, "Member"),
                    (12, "Leader"),
                    (20, "Supervisor"),
                    (30, "Manager"),
                    (35, "Sekretaris"),
                    (40, "Direktur"),
                ]
            ),
        ),
    ]
