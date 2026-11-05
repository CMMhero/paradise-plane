# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sematkan pesan obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kolom sematan di pesan obrolan.

Skema saja, tanpa pembaruan data: kedua kolom lahir kosong, jadi tidak ada baris
lama yang perlu diisi. Mencampur ALTER dengan UPDATE dalam satu migrasi memicu
`pending trigger events` saat dimundurkan.

AddIndex SENGAJA sesudah kedua AddField. `makemigrations` kadang menaruhnya lebih
dulu, lalu indeks dibuat untuk kolom yang belum ada.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0166_quick_link_portal"),
    ]

    operations = [
        migrations.AddField(
            model_name="pesanlangsung",
            name="disematkan_pada",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pesanlangsung",
            name="disematkan_oleh",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pesan_disematkan",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="pesanlangsung",
            index=models.Index(
                condition=models.Q(("disematkan_pada__isnull", False)),
                fields=["ruang", "disematkan_pada"],
                name="dm_ruang_disematkan_idx",
            ),
        ),
    ]
