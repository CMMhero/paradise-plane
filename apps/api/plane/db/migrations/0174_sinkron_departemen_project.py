# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: nama project dan ikon folder Wiki mengikuti departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Data saja, tanpa skema. Sejak perubahan ini nama project selalu sama dengan
# departemennya dan folder Wiki departemen membawa ikon project-nya; migrasi ini
# menyamakan data yang sudah ada sebelum aturannya berlaku:
#
# - Project.name = Departemen.nama untuk tiap pasangan DepartemenProject yang
#   hidup. Nama yang sudah dipakai project lain (nama project unik per
#   workspace) dilewati dan dibiarkan apa adanya; sinkron berikutnya di God Mode
#   mencatatnya ke log.
# - WikiFolder.logo_props (folder departemen) = Project.logo_props.
#
# Mundur tidak memulihkan nama atau ikon lama: tidak ada catatan nilai sebelumnya,
# dan nilai yang disamakan di sini adalah nilai yang benar.

from django.db import migrations
from django.utils import timezone


def samakan(apps, schema_editor):
    DepartemenProject = apps.get_model("db", "DepartemenProject")
    Project = apps.get_model("db", "Project")
    WikiFolder = apps.get_model("db", "WikiFolder")

    baris = DepartemenProject.objects.filter(
        departemen__deleted_at__isnull=True, project__deleted_at__isnull=True
    ).select_related("departemen", "project")
    sekarang = timezone.now()
    for b in baris:
        nama, project = b.departemen.nama, b.project
        if project.name != nama:
            bentrok = (
                Project.objects.filter(workspace_id=project.workspace_id, name=nama, deleted_at__isnull=True)
                .exclude(pk=project.pk)
                .exists()
            )
            if not bentrok:
                Project.objects.filter(pk=project.pk).update(name=nama, updated_at=sekarang)
        logo = project.logo_props if isinstance(project.logo_props, dict) else {}
        WikiFolder.objects.filter(departemen_id=b.departemen_id, deleted_at__isnull=True).exclude(
            logo_props=logo
        ).update(logo_props=logo, updated_at=sekarang)


class Migration(migrations.Migration):
    dependencies = [("db", "0173_m2m_through_fields_django52")]

    operations = [migrations.RunPython(samakan, migrations.RunPython.noop)]
