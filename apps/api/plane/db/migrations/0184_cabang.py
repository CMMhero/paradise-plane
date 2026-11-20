# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: cabang dan Direktur Cabang (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0183_nav_kinerja'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cabang',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Last Modified At')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True)),
                ('kode', models.CharField(max_length=20)),
                ('nama', models.CharField(max_length=255)),
            ],
            options={
                'verbose_name': 'Cabang',
                'verbose_name_plural': 'Cabang',
                'db_table': 'organisasi_cabang',
                'ordering': ('nama',),
            },
        ),
        migrations.RemoveConstraint(
            model_name='jabatanorganisasi',
            name='jabatan_organisasi_unique_tanpa_tempat_aktif',
        ),
        migrations.AlterField(
            model_name='jabatanorganisasi',
            name='tingkat',
            field=models.PositiveSmallIntegerField(choices=[(10, 'Member'), (12, 'Leader'), (20, 'Supervisor'), (30, 'Manager'), (33, 'Direktur Cabang'), (35, 'Sekretaris'), (40, 'Direktur')]),
        ),
        migrations.AddField(
            model_name='cabang',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_created_by', to=settings.AUTH_USER_MODEL, verbose_name='Created By'),
        ),
        migrations.AddField(
            model_name='cabang',
            name='updated_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_updated_by', to=settings.AUTH_USER_MODEL, verbose_name='Last Modified By'),
        ),
        migrations.AddField(
            model_name='cabang',
            name='workspace',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cabang_organisasi', to='db.workspace'),
        ),
        migrations.AddField(
            model_name='divisi',
            name='cabang',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='divisi', to='db.cabang'),
        ),
        migrations.AddField(
            model_name='jabatanorganisasi',
            name='cabang',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='penempatan_direktur', to='db.cabang'),
        ),
        migrations.AddConstraint(
            model_name='jabatanorganisasi',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('workspace', 'member', 'cabang'), name='jabatan_organisasi_unique_cabang_aktif'),
        ),
        migrations.AddConstraint(
            model_name='jabatanorganisasi',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True), ('departemen__isnull', True), ('divisi__isnull', True), ('cabang__isnull', True)), fields=('workspace', 'member'), name='jabatan_organisasi_unique_tanpa_tempat_aktif'),
        ),
        migrations.AddConstraint(
            model_name='cabang',
            constraint=models.UniqueConstraint(condition=models.Q(('deleted_at__isnull', True)), fields=('workspace', 'kode'), name='cabang_unique_kode_aktif'),
        ),
        migrations.AlterUniqueTogether(
            name='cabang',
            unique_together={('workspace', 'kode', 'deleted_at')},
        ),
    ]
