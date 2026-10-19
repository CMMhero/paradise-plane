# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Granular Access Control Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel


class WikiGovernedProject(BaseModel):
    """Menandai sebuah project sebagai Wiki ber-ACL folder.

    Di project bertanda ini, hak EDIT halaman ditentukan oleh kepemilikan
    folder per-divisi (lihat WikiFolderAccess), bukan oleh peran project biasa.
    Project TANPA baris ini memakai izin halaman Plane normal, tak tersentuh.
    """

    workspace = models.ForeignKey(
        "db.Workspace", related_name="wiki_governed_projects", on_delete=models.CASCADE
    )
    # ForeignKey + unique_together yang MENYERTAKAN deleted_at, bukan OneToOneField.
    # OneToOneField meng-unique-kan project_id saja dan mengabaikan soft-delete, jadi
    # sekali governance dimatikan (soft-delete) project itu tak akan pernah bisa
    # dinyalakan lagi, create() selalu IntegrityError. Pola ini menyamai
    # WikiFolderAccess di bawah.
    project = models.ForeignKey(
        "db.Project", related_name="wiki_governance", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["project", "deleted_at"]
        verbose_name = "Wiki Governed Project"
        verbose_name_plural = "Wiki Governed Projects"
        db_table = "wiki_governed_projects"
        ordering = ("-created_at",)

    def __str__(self):
        return f"wiki-governed: {self.project.name}"


class WikiFolderAccess(BaseModel):
    """Memberi hak EDIT satu folder Wiki (halaman top-level) kepada satu divisi.

    Semua anggota Wiki tetap bisa VIEW. Sub-halaman mewarisi folder top-level-nya.
    Satu folder boleh ditautkan ke beberapa divisi (beberapa baris) → gabungan
    hak edit. Folder tanpa baris apa pun = hanya admin yang boleh edit.
    """

    workspace = models.ForeignKey(
        "db.Workspace", related_name="wiki_folder_access", on_delete=models.CASCADE
    )
    # Project Wiki tempat folder ini berada (untuk scoping/kelola)
    project = models.ForeignKey(
        "db.Project", related_name="wiki_folder_access", on_delete=models.CASCADE
    )
    # Halaman folder top-level yang diatur
    folder = models.ForeignKey(
        "db.Page", related_name="wiki_folder_access", on_delete=models.CASCADE
    )
    # Divisi (project) yang anggotanya boleh mengedit folder ini
    division = models.ForeignKey(
        "db.Project", related_name="wiki_division_access", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ["folder", "division", "deleted_at"]
        verbose_name = "Wiki Folder Access"
        verbose_name_plural = "Wiki Folder Access"
        db_table = "wiki_folder_access"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.folder.name} → {self.division.name}"
