# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pencarian Wiki mirip + isi berkas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Tambahan murni: dua kolom baru dengan nilai bawaan, satu ekstensi, dua indeks.
# Data lama tidak berubah. Kolom `isi_teks` terisi lewat tugas latar sesudah
# unggah; materi lama diisi sekali dengan `manage.py wiki_indeks_ulang`.
#
# pg_trgm dipasang di sini (`CREATE EXTENSION IF NOT EXISTS`). Sejak PostgreSQL
# 13 ekstensi ini "trusted": pemilik database boleh memasangnya tanpa superuser.

import django.contrib.postgres.indexes
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0171_wiki_mandiri_data")]

    operations = [
        TrigramExtension(),
        migrations.AddField(
            model_name="wikimaterial",
            name="isi_teks",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="wikimaterial",
            name="diindeks_pada",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="wikimaterial",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["judul"], name="wiki_material_judul_trgm", opclasses=["gin_trgm_ops"]
            ),
        ),
        migrations.AddIndex(
            model_name="wikimaterial",
            index=django.contrib.postgres.indexes.GinIndex(
                fields=["isi_teks"], name="wiki_material_isi_trgm", opclasses=["gin_trgm_ops"]
            ),
        ),
    ]
