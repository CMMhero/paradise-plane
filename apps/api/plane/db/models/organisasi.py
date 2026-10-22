# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: struktur organisasi divisi -> departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Perusahaan (workspace) -> Divisi -> Departemen -> project. KEP-29.

Sebelum KEP-29, "divisi" = satu project (KEP-02). Sekarang project adalah badan
kerja DI BAWAH sebuah departemen, dan divisi/departemen adalah record sendiri.
Project tetap private: isolasi data KEP-02 tidak berubah.

## Kenapa tabel pemetaan, bukan kolom `Project.departemen`

`Project` milik upstream. Tiap kolom baru di sana dibayar di setiap upstream
sync; tabel pemetaan tidak menyentuh berkas upstream sama sekali (pola yang sama
dengan `PengawasanDivisi`, `SuperAdminTerlihatDiProject`).

## Kenapa `AksesHierarki` ada

Plane memutuskan akses lewat `ProjectMember` di puluhan tempat. Jangkauan jenjang
(supervisor = departemennya, manager = divisinya) karena itu tetap harus jadi baris
`ProjectMember`. Tabel ini menandai baris mana yang LAHIR dari hierarki, supaya
saat orangnya pindah departemen yang dicabut HANYA baris itu. Keanggotaan yang
diberi tangan (pengecualian eksplisit, KEP-29) tidak pernah disentuh.
"""

# Django imports
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel


class Divisi(BaseModel):
    """Unit organisasi teratas di bawah perusahaan, mis. Sales, HRGA, Finance."""

    workspace = models.ForeignKey("db.Workspace", related_name="divisi_organisasi", on_delete=models.CASCADE)
    kode = models.CharField(max_length=20)
    nama = models.CharField(max_length=255)

    class Meta:
        unique_together = ["workspace", "kode", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "kode"],
                condition=Q(deleted_at__isnull=True),
                name="divisi_unique_kode_aktif",
            )
        ]
        verbose_name = "Divisi"
        verbose_name_plural = "Divisi"
        db_table = "organisasi_divisi"
        ordering = ("nama",)

    def __str__(self):
        return f"{self.kode} {self.nama}"


class Departemen(BaseModel):
    """Satu departemen di satu divisi, mis. SMT1 di Sales. Bukan project."""

    workspace = models.ForeignKey("db.Workspace", related_name="departemen_organisasi", on_delete=models.CASCADE)
    divisi = models.ForeignKey(Divisi, related_name="departemen", on_delete=models.CASCADE)
    kode = models.CharField(max_length=20)
    nama = models.CharField(max_length=255)

    class Meta:
        unique_together = ["workspace", "kode", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "kode"],
                condition=Q(deleted_at__isnull=True),
                name="departemen_unique_kode_aktif",
            )
        ]
        verbose_name = "Departemen"
        verbose_name_plural = "Departemen"
        db_table = "organisasi_departemen"
        ordering = ("nama",)

    def __str__(self):
        return f"{self.kode} {self.nama}"


class DepartemenProject(BaseModel):
    """Project ini milik departemen ini. Satu project tepat satu departemen."""

    workspace = models.ForeignKey("db.Workspace", related_name="departemen_project", on_delete=models.CASCADE)
    departemen = models.ForeignKey(Departemen, related_name="project_departemen", on_delete=models.CASCADE)
    project = models.ForeignKey("db.Project", related_name="departemen_project", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["project", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=Q(deleted_at__isnull=True),
                name="departemen_project_unique_aktif",
            )
        ]
        verbose_name = "Project Departemen"
        verbose_name_plural = "Project Departemen"
        db_table = "organisasi_departemen_project"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.project_id} di {self.departemen_id}"


class AksesHierarki(BaseModel):
    """Baris `ProjectMember` (project, member) ini diberikan oleh hierarki, bukan tangan.

    Ada baris = boleh dicabut otomatis saat jangkauan orangnya berubah.
    Tidak ada baris = keanggotaan eksplisit, sinkronisasi tidak menyentuhnya.
    """

    workspace = models.ForeignKey("db.Workspace", related_name="akses_hierarki", on_delete=models.CASCADE)
    project = models.ForeignKey("db.Project", related_name="akses_hierarki", on_delete=models.CASCADE)
    member = models.ForeignKey("db.User", related_name="akses_hierarki", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["project", "member", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "member"],
                condition=Q(deleted_at__isnull=True),
                name="akses_hierarki_unique_aktif",
            )
        ]
        verbose_name = "Akses Hierarki"
        verbose_name_plural = "Akses Hierarki"
        db_table = "akses_hierarki"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["workspace", "member"], name="akses_hier_ws_member_idx"),
        ]

    def __str__(self):
        return f"{self.member_id} lewat hierarki di {self.project_id}"


class SupervisorDepartemen(BaseModel):
    """Departemen TAMBAHAN yang diawasi seorang supervisor (KEP-32).

    Satu supervisor boleh memegang beberapa departemen — mis. Fran Olnsen membawahi
    IT-SAP (utama) sekaligus IT-AI (tambahan). Penempatan utama tetap di
    `JabatanOrganisasi.departemen`; baris di sini MENAMBAH jangkauan, bukan memindahkan.

    Jangkauan supervisor = project departemen utama + project tiap baris tambahan ini
    (`jangkauan_hierarki`, `divisi_diawasi`). Hanya untuk tingkat supervisor: staf tidak
    punya wewenang lintas departemen, manager/direktur sudah tercakup divisinya.
    """

    workspace = models.ForeignKey("db.Workspace", related_name="supervisor_departemen", on_delete=models.CASCADE)
    departemen = models.ForeignKey(Departemen, related_name="supervisor_tambahan", on_delete=models.CASCADE)
    member = models.ForeignKey("db.User", related_name="supervisor_departemen", on_delete=models.CASCADE)

    class Meta:
        unique_together = ["member", "departemen", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "departemen"],
                condition=Q(deleted_at__isnull=True),
                name="supervisor_dep_unique_aktif",
            )
        ]
        verbose_name = "Supervisor Departemen"
        verbose_name_plural = "Supervisor Departemen"
        db_table = "organisasi_supervisor_departemen"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["workspace", "member"], name="supdep_ws_member_idx"),
        ]

    def __str__(self):
        return f"{self.member_id} awasi tambahan {self.departemen_id}"
