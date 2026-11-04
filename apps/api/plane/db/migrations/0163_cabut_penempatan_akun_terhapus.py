# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: cabut penempatan akun yang sudah terhapus
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Akun yang dihapus sebelum 2.3.0 masih punya baris penempatan organisasi.

Barisnya membuat "Deleted account" muncul di departemen/divisi God Mode, tidak bisa
dicabut dari sana, dan memblokir penghapusan departemennya. Sejak 2.3.0 penghapusan
akun mencabutnya sendiri; migrasi ini merapikan sisa yang lama. Soft delete dengan
`deleted_at` = waktu potret akun, jadi memulihkan akun dari Trash ikut
mengembalikannya (lihat `_pulihkan_akun`).
"""

from django.db import migrations
from django.utils import timezone


def cabut(apps, schema_editor):
    JabatanOrganisasi = apps.get_model("db", "JabatanOrganisasi")
    AkunTerhapus = apps.get_model("db", "AkunTerhapus")
    for snap in AkunTerhapus.objects.all().only("user_id", "dihapus_pada"):
        JabatanOrganisasi.objects.filter(member_id=snap.user_id, deleted_at__isnull=True).update(
            deleted_at=snap.dihapus_pada
        )
    # Akun yang terhapus sebelum ada potret (sebelum KEP-50) tidak bisa dipulihkan,
    # jadi barisnya cukup dicabut sekarang.
    JabatanOrganisasi.objects.filter(
        member__email__endswith="@deleted.local", deleted_at__isnull=True
    ).update(deleted_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [("db", "0162_ganti_nama_kanal_changelogs")]

    operations = [migrations.RunPython(cabut, migrations.RunPython.noop)]
