# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengecualian penyembunyian Super Admin
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel


class SuperAdminTerlihatDiProject(BaseModel):
    """Menandai bahwa seorang Super Admin adalah anggota ASLI project tertentu.

    Latar belakang. Super Admin otomatis jadi anggota SEMUA project supaya bisa
    memantau tanpa ditambahkan manual, lalu disaring keluar dari daftar anggota
    (lihat `plane/db/superadmin.py`). Masalahnya penyaringan itu semula berlaku
    di semua project sekaligus, termasuk project tempat orangnya benar-benar
    bekerja. Akibatnya tim IT tidak bisa diberi tugas di project IT sendiri:
    namanya tidak pernah muncul di daftar assignee.

    Baris di tabel ini adalah PENGECUALIAN: "orang ini bukan sekadar pengawas
    di project ini, dia memang anggotanya". Di project itu ia tampil dan
    diperlakukan seperti anggota biasa. Di project lain ia tetap tersembunyi.

    Sengaja tabel pengecualian, bukan kolom baru di ProjectMember: yang perlu
    ditandai hanya belasan baris, sedangkan menandai lewat ProjectMember berarti
    menyentuh 11 orang x 31 project = 341 baris yang seluruhnya sudah tercampur
    dan tak bisa dibedakan lagi asal-usulnya.
    """

    workspace = models.ForeignKey(
        "db.Workspace", related_name="superadmin_visibility", on_delete=models.CASCADE
    )
    project = models.ForeignKey(
        "db.Project", related_name="superadmin_visibility", on_delete=models.CASCADE
    )
    member = models.ForeignKey(
        "db.User", related_name="superadmin_visibility", on_delete=models.CASCADE
    )

    class Meta:
        # deleted_at ikut dalam kunci unik, menyamai pola WikiFolderAccess:
        # tanpa itu, sekali pengecualian dicabut (soft-delete) ia tak akan
        # pernah bisa dipasang lagi karena create() selalu IntegrityError.
        unique_together = ["project", "member", "deleted_at"]
        verbose_name = "Super Admin Terlihat di Project"
        verbose_name_plural = "Super Admin Terlihat di Project"
        db_table = "superadmin_visibility"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.member.display_name} terlihat di {self.project.identifier}"
