# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: edisi sore ringkasan harian
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Saklar `daily_digest_sore` (ringkasan 17.30 WIB, keputusan user 2026-11-02).

Orang yang masih ikut bawaan jabatan tidak membaca kolom ini: nilainya datang
dari tabel bawaan (hidup untuk semua jabatan). Orang yang sudah membekukan
pilihannya (`ikut_bawaan_jabatan=False`) mewarisi pilihan ringkasan paginya:
yang mematikan ringkasan pagi tidak tiba-tiba menerima ringkasan sore, yang
menyalakannya ikut menerima keduanya.
"""

from django.db import migrations, models
from django.db.models import F


def _warisi_pagi(apps, schema_editor):
    Pref = apps.get_model("db", "UserNotificationPreference")
    Pref.objects.filter(ikut_bawaan_jabatan=False).update(daily_digest_sore=F("daily_digest"))


class Migration(migrations.Migration):
    dependencies = [("db", "0157_log_persetujuan_lama")]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="daily_digest_sore",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(_warisi_pagi, migrations.RunPython.noop),
    ]
