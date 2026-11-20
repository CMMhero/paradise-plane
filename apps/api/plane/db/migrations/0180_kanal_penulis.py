# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penulis kanal Announcements dan email pengumuman
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Admin mengizinkan departemen (atau orang) menulis di Announcements, dan tiap
pengumuman dikirim lewat email.

`PenulisKanal`: satu baris = satu departemen ATAU satu orang (check constraint).
`pengumuman`: saklar email per orang, hidup untuk semua baris lama, termasuk
yang sudah membekukan pilihannya. Pengumuman memang dimaksudkan sampai ke semua
orang; yang tidak mau mematikannya sendiri.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0179_wiki_folder_editor")]

    operations = [
        migrations.AddField(
            model_name="usernotificationpreference",
            name="pengumuman",
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name="PenulisKanal",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "departemen",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="penulis_kanal",
                        to="db.departemen",
                    ),
                ),
                (
                    "ruang",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="penulis", to="db.ruang"
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="penulis_kanal",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="penulis_kanal", to="db.workspace"
                    ),
                ),
            ],
            options={
                "verbose_name": "Penulis Kanal",
                "verbose_name_plural": "Penulis Kanal",
                "db_table": "chat_channel_writers",
                "ordering": ("created_at",),
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("departemen__isnull", False), ("user__isnull", True)),
                            models.Q(("departemen__isnull", True), ("user__isnull", False)),
                            _connector="OR",
                        ),
                        name="penulis_kanal_satu_sasaran",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("departemen__isnull", False)),
                        fields=("ruang", "departemen"),
                        name="penulis_kanal_departemen_unik",
                    ),
                    models.UniqueConstraint(
                        condition=models.Q(("user__isnull", False)),
                        fields=("ruang", "user"),
                        name="penulis_kanal_user_unik",
                    ),
                ],
            },
        ),
    ]
