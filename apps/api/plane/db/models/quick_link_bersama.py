# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: quick link bersama (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Quick link yang dipasang admin untuk banyak orang sekaligus.

Quick link pribadi (`WorkspaceUserLink`) tetap milik satu orang. Baris di sini
tampil di Home dan halaman Quick links setiap orang yang masuk sasarannya, dan
hanya Super Admin / admin workspace yang boleh mengubahnya.

Sasaran dibaca dari `cakupan`, BUKAN dari kosong-tidaknya daftar departemen/divisi:
departemen yang dihapus (soft delete) menghilang dari relasi M2M, dan link yang
tadinya untuk satu departemen tidak boleh diam-diam berubah jadi untuk semua orang.
"""

from django.db import models

from .base import BaseModel

CAKUPAN_SEMUA = "semua"
CAKUPAN_ORGANISASI = "organisasi"
CAKUPAN_CHOICES = (
    (CAKUPAN_SEMUA, "Everyone"),
    (CAKUPAN_ORGANISASI, "Selected divisions and departments"),
)


class QuickLinkBersama(BaseModel):
    workspace = models.ForeignKey("db.Workspace", related_name="quick_link_bersama", on_delete=models.CASCADE)
    url = models.TextField()
    # Judul manual. Kosong = pakai judul situs yang diambil otomatis (metadata.title).
    title = models.CharField(max_length=255, null=True, blank=True)
    # {title, favicon, favicon_url, og_image, logo_props, diambil_pada}
    metadata = models.JSONField(default=dict)
    cakupan = models.CharField(max_length=20, choices=CAKUPAN_CHOICES, default=CAKUPAN_SEMUA)
    departemen = models.ManyToManyField("db.Departemen", related_name="quick_link_bersama", blank=True)
    divisi = models.ManyToManyField("db.Divisi", related_name="quick_link_bersama", blank=True)
    sort_order = models.FloatField(default=65535)

    class Meta:
        verbose_name = "Quick Link Bersama"
        verbose_name_plural = "Quick Link Bersama"
        db_table = "quick_link_bersama"
        ordering = ("sort_order", "created_at")

    def __str__(self):
        return f"{self.workspace_id} {self.url}"
