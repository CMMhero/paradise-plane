# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Intake menyala di setiap departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Setiap project hidup: `intake_view` menyala dan punya Intake default.

Departemen dari God Mode lahir tanpa baris `Intake` (dulu hanya jalur UPDATE
project yang membuatnya), padahal `intake_view` bawaannya True. Halaman Intake
lalu menampilkan "Error fetching the intake work items", dan departemen itu tidak
muncul sebagai tujuan permintaan lintas departemen. Keputusan pemilik produk: semua
departemen punya Intake menyala. Sejak perubahan ini setiap jalur pembuatan project
memanggil `plane.utils.intake_bawaan.ensure_default_intake`; migrasi ini menyamakan
data yang sudah ada.

Project terhapus (lunak) tidak disentuh. Berbatch dan idempoten: menjalankannya
ulang tidak menggandakan apa pun. Mundur = tidak melakukan apa pun (tidak ada
catatan mana yang dulu mati).
"""

from django.db import migrations
from django.utils import timezone

BATCH = 500
# `Intake.name` maksimal 255; akhiran harus muat.
AKHIRAN = " Intake"


def intake_bawaan(apps, schema_editor):
    Project = apps.get_model("db", "Project")
    Intake = apps.get_model("db", "Intake")

    hidup = Project._base_manager.filter(deleted_at__isnull=True)
    sekarang = timezone.now()
    while True:
        ids = list(hidup.filter(intake_view=False).values_list("id", flat=True)[:BATCH])
        if not ids:
            break
        Project._base_manager.filter(id__in=ids).update(intake_view=True, updated_at=sekarang)

    sudah = Intake._base_manager.filter(deleted_at__isnull=True, is_default=True).values("project_id")
    while True:
        tanpa = list(hidup.exclude(id__in=sudah).values_list("id", "workspace_id", "name")[:BATCH])
        if not tanpa:
            break
        Intake._base_manager.bulk_create(
            [
                Intake(
                    project_id=pid,
                    workspace_id=wid,
                    name=f"{nama[: 255 - len(AKHIRAN)]}{AKHIRAN}",
                    is_default=True,
                )
                for pid, wid, nama in tanpa
            ],
            ignore_conflicts=True,
        )
        # Nama yang sudah dipakai intake lain di project yang sama membuat barisnya
        # dilewati `ignore_conflicts`. Intake tertua project itu dijadikan default,
        # supaya putaran berikutnya tidak memilih project yang sama lagi.
        batch = [pid for pid, _, _ in tanpa]
        for pid in hidup.filter(id__in=batch).exclude(id__in=sudah).values_list("id", flat=True):
            tertua = Intake._base_manager.filter(project_id=pid, deleted_at__isnull=True).order_by("created_at").first()
            if tertua is None:
                raise RuntimeError(f"Intake untuk project {pid} gagal dibuat.")
            Intake._base_manager.filter(pk=tertua.pk).update(is_default=True)


class Migration(migrations.Migration):
    dependencies = [("db", "0184_cabang")]

    operations = [migrations.RunPython(intake_bawaan, migrations.RunPython.noop)]
