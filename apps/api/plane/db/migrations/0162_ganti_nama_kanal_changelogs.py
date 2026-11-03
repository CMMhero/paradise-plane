# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kanal Changelog jadi Changelogs
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Ganti nama tampilan kanal sistem `changelog` menjadi "Changelogs".

Kuncinya (`kunci_sistem = "changelog"`) tidak berubah, jadi kode dan pesan
lama tetap cocok. Bisa dibalik.
"""

from django.db import migrations


def _ganti(apps, lama, baru):
    Ruang = apps.get_model("db", "Ruang")
    Ruang.objects.filter(kunci_sistem="changelog", nama=lama).update(nama=baru)


def _maju(apps, schema_editor):
    _ganti(apps, "Changelog", "Changelogs")


def _mundur(apps, schema_editor):
    _ganti(apps, "Changelogs", "Changelog")


class Migration(migrations.Migration):
    dependencies = [("db", "0161_kartu_tugas_lama")]

    operations = [migrations.RunPython(_maju, _mundur)]
