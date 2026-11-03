# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kontak kantor di profil anggota
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`Profile.job_title` + `Profile.phone_extension` untuk kartu profil anggota.

Additive, ber-default string kosong: baris lama tetap sah dan tidak ada data
yang dipindah.
"""

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0159_obrolan_kartu_sistem")]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="job_title",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="profile",
            name="phone_extension",
            field=models.CharField(
                blank=True,
                default="",
                max_length=20,
                validators=[
                    django.core.validators.RegexValidator(
                        "^[0-9+()#*\\-\\s]*$", "Only digits, spaces and + ( ) - # * are allowed."
                    )
                ],
            ),
        ),
    ]
