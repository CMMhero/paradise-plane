# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: project baru privat sejak lahir
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Hanya bawaan kolom yang berubah (2 Public -> 0 Secret).

    Django menyimpan default di Python, bukan di skema, jadi tidak ada DDL dan
    tidak ada data yang disentuh: project yang sudah ada tidak berubah
    visibilitasnya. Yang berubah adalah project yang dibuat lewat jalur yang tidak
    menyebut `network` (API v1, seed), supaya tidak lahir Public karena lupa.
    """

    dependencies = [("db", "0175_tingkat_sekretaris")]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="network",
            field=models.PositiveSmallIntegerField(choices=[(0, "Secret"), (2, "Public")], default=0),
        ),
    ]
