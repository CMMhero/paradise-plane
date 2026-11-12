# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: turunan departemen mengikuti departemennya
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Nama project mengikuti nama departemennya.

Departemen dan project-nya satu kesatuan (KEP-32): UI hanya menyebut
"departemen", project hanya mesin di belakangnya. Karena itu nama project tidak
boleh berbeda dari nama departemen, dan berubah sendiri begitu departemennya
diganti nama (2026-11-12). Folder Wiki dan kanal chat departemen sudah mengikuti
lewat `pastikan_folder_unit` dan `sinkronkan_kanal_organisasi`; folder Wiki
juga membawa ikon project-nya.

Identifier project (kode di nomor tugas, mis. FIN-12) sengaja TIDAK ikut kode
departemen: mengubahnya menulis ulang nomor semua tugas yang sudah dibagikan.

Satu sumber untuk tiga pemakai: sinkron God Mode (`license/api/views/organisasi.py`),
migrasi data 0174, dan pemeriksaan sebelum menyimpan (`nama_project_terpakai`).
"""

from plane.db.models import DepartemenProject, Project


def nama_project_terpakai(workspace_id, nama, kecuali_project_ids=()):
    """Project aktif lain yang sudah memakai `nama`, atau None.

    Nama project unik per workspace (constraint database), jadi mengganti nama
    departemen ke nama yang sudah dipakai project lain harus ditolak SEBELUM
    menyimpan, bukan gagal di tengah sinkron.
    """
    return (
        Project.objects.filter(workspace_id=workspace_id, name=nama)
        .exclude(pk__in=list(kecuali_project_ids))
        .only("id", "identifier", "name")
        .first()
    )


def samakan_project_departemen(workspace_id):
    """Nama project = nama departemennya. Mengembalikan (jumlah_diubah, bentrok).

    `bentrok` = daftar (identifier project, nama departemen) yang tidak bisa
    disamakan karena nama itu dipakai project lain; dibiarkan apa adanya.
    Idempoten: hanya menulis yang berbeda.
    """
    baris = DepartemenProject.objects.filter(
        workspace_id=workspace_id,
        departemen__deleted_at__isnull=True,
        project__deleted_at__isnull=True,
    ).select_related("departemen", "project")

    diubah, bentrok = 0, []
    for b in baris:
        nama = b.departemen.nama
        if b.project.name == nama:
            continue
        if nama_project_terpakai(workspace_id, nama, kecuali_project_ids=[b.project_id]) is not None:
            bentrok.append((b.project.identifier, nama))
            continue
        # `.update()` dengan sengaja: tidak memicu sinyal/aktivitas project, dan
        # `updated_at` diisi tangan karena update massal tidak menyentuhnya.
        from django.utils import timezone  # noqa: PLC0415

        Project.objects.filter(pk=b.project_id).update(name=nama, updated_at=timezone.now())
        diubah += 1
    return diubah, bentrok
