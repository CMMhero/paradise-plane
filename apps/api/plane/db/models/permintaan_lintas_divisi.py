# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: permintaan tugas lintas divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Catatan asal-usul satu permintaan tugas antar divisi.

Latar belakang. Divisi = project private (KEP-02), jadi anggota divisi lain
tidak bisa melihat apa pun di dalamnya. Sementara itu pekerjaan nyata sering
lahir di satu divisi tapi dikerjakan divisi lain: TENDER butuh IT menyiapkan
akun dokumen tender, SALES minta Gudang Medan mengecek stok.

Jalan yang sudah ada di sistem ini adalah **Intake** ([[Business Process]]
Alur 2): divisi peminta mengirim permintaan ke kotak masuk divisi tujuan, lalu
admin divisi tujuan menyaring terima/tolak. Yang belum ada cuma pintu masuk
internalnya -- `IntakeIssueViewSet.create`
(`plane/app/views/intake/base.py:228`) menuntut keanggotaan project tujuan.

Baris di tabel ini adalah **asal-usul** permintaan itu, dan sengaja terpisah
dari `IntakeIssue`:

* `IntakeIssue` hidup di project TUJUAN dan tunduk pada siklus triase di sana
  (diterima/ditolak/dihapus). Kalau catatan asal menumpang di situ, riwayat
  "divisi mana meminta apa" ikut hilang begitu divisi tujuan beres-beres.
* Metrik Dashboard Divisi butuh menghitung per **divisi asal** dan per
  **divisi tujuan**. `IntakeIssue` tidak menyimpan project asal sama sekali,
  dan menaruhnya di kolom JSON membuat setiap hitungan jadi kueri JSON.

TIDAK ada kunci unik di sini dengan sengaja. Tidak ada yang perlu unik pada
permintaan: divisi yang sama boleh meminta hal yang sama dua kali di hari yang
berbeda. Karena itu jebakan `unique_together` + soft-delete
([[Database & Migrasi]]) tidak berlaku di tabel ini.
"""

# Django imports
from django.conf import settings
from django.db import models

# Module imports
from .base import BaseModel


class PermintaanLintasDivisi(BaseModel):
    """Satu permintaan tugas dari satu divisi ke divisi lain."""

    workspace = models.ForeignKey("db.Workspace", related_name="permintaan_lintas_divisi", on_delete=models.CASCADE)
    asal_project = models.ForeignKey(
        "db.Project",
        related_name="permintaan_lintas_divisi_asal",
        on_delete=models.CASCADE,
    )
    tujuan_project = models.ForeignKey(
        "db.Project",
        related_name="permintaan_lintas_divisi_tujuan",
        on_delete=models.CASCADE,
    )
    # Diisi begitu work item triase di project tujuan dibuat. Boleh kosong
    # kalau suatu saat IntakeIssue-nya dihapus divisi tujuan: riwayat
    # permintaannya tetap ada, hanya tautannya yang lepas.
    intake_issue = models.ForeignKey(
        "db.IntakeIssue",
        related_name="permintaan_lintas_divisi",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    diminta_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="permintaan_lintas_divisi_dibuat",
        on_delete=models.CASCADE,
    )
    # Keterangan tambahan dari peminta (mis. nomor tender, nama barang).
    # Sengaja teks bebas dan BUKAN bagian judul: judul masuk ke papan divisi
    # tujuan, sedangkan catatan ini tidak.
    catatan = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Permintaan Lintas Divisi"
        verbose_name_plural = "Permintaan Lintas Divisi"
        db_table = "permintaan_lintas_divisi"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["workspace", "asal_project", "created_at"], name="pld_ws_asal_idx"),
            models.Index(fields=["workspace", "tujuan_project", "created_at"], name="pld_ws_tujuan_idx"),
            models.Index(fields=["diminta_oleh", "created_at"], name="pld_peminta_idx"),
        ]

    def __str__(self):
        return f"{self.asal_project.identifier} -> {self.tujuan_project.identifier} ({self.id})"
