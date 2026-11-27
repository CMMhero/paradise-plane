# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jenjang Asisten Manager (P215)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Hanya `choices` yang berubah (25 = Asisten Manager): tidak ada DDL, tidak ada data."""

    dependencies = [("db", "0186_isi_assignee_staf")]

    operations = [
        migrations.AlterField(
            model_name="jabatanorganisasi",
            name="tingkat",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (10, "Member"),
                    (12, "Leader"),
                    (20, "Supervisor"),
                    (25, "Asisten Manager"),
                    (30, "Manager"),
                    (33, "Direktur Cabang"),
                    (35, "Sekretaris"),
                    (40, "Direktur"),
                ]
            ),
        ),
    ]
