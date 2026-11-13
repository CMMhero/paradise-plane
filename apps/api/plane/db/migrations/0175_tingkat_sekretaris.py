# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jenjang Sekretaris (KEP-101)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Hanya `choices` yang berubah (35 = Sekretaris): tidak ada DDL, tidak ada data.

    CATATAN URUTAN: cabang ini belum memuat 0173 dan 0174 yang sudah ada di
    origin/main (m2m through Django 5.2, sinkron departemen). Nomor 0175 sengaja
    dipilih supaya tidak bentrok dengan keduanya. Begitu origin/main digabung ke
    cabang ini, ubah dependensi di bawah menjadi `0174_sinkron_departemen_project`;
    kalau tidak, `migrate` menolak dengan "Conflicting migrations".
    """

    dependencies = [("db", "0174_sinkron_departemen_project")]

    operations = [
        migrations.AlterField(
            model_name="jabatanorganisasi",
            name="tingkat",
            field=models.PositiveSmallIntegerField(
                choices=[(10, "Member"), (20, "Supervisor"), (30, "Manager"), (35, "Sekretaris"), (40, "Direktur")]
            ),
        ),
    ]
