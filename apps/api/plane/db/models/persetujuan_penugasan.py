# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: persetujuan penugasan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu permintaan persetujuan untuk satu penugasan.

Keputusan user 2026-10-15 (verbatim di `.herdr/hierarki-desain.md` §12):

* Yang **butuh persetujuan hanya jabatan member**, dan hanya karena member hanya boleh
  menugaskan ke dirinya sendiri. Supervisor/manager/direktur tidak butuh persetujuan.
* Yang menyetujui adalah **atasan pembuat di divisinya** -- boleh supervisor, manager,
  atau direktur (siapa pun yang tingkatnya lebih tinggi di divisi itu).
* Tugasnya **tetap muncul** (tidak disembunyikan) tapi belum disetujui, **dengan
  indikator** -- jadi baris di tabel ini yang menjadi indikator itu.

## Kenapa tabel sendiri, bukan kolom di `Issue`

Satu tugas bisa berpindah penugasan berkali-kali, dan tiap penugasan butuh persetujuan
sendiri. Kolom di `Issue` hanya bisa menyimpan keadaan TERAKHIR, sehingga riwayat "siapa
menyetujui apa, kapan, dengan alasan apa" hilang begitu penugasan berubah -- persis pola
yang sudah dipakai `PermintaanLintasDivisi` (catatan asal-usul terpisah dari objeknya).

## Kenapa "tidak ada atasan" TIDAK disimpan sebagai status

Keadaan itu dihitung ulang setiap kali dibaca (`plane/utils/hierarki.py:calon_penyetuju`).
Kalau disimpan, ia jadi beku: begitu God Mode mengisi jenjang orangnya, baris lama tetap
berkata "tanpa atasan" dan tidak ada yang tahu kapan ia sudah usang. Yang tersimpan hanya
keputusan manusia (menunggu/disetujui/ditolak).
"""

# Django imports
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel

STATUS_MENUNGGU = "menunggu"
STATUS_DISETUJUI = "disetujui"
STATUS_DITOLAK = "ditolak"

STATUS_CHOICES = (
    (STATUS_MENUNGGU, "Menunggu"),
    (STATUS_DISETUJUI, "Disetujui"),
    (STATUS_DITOLAK, "Ditolak"),
)


class PersetujuanPenugasan(BaseModel):
    """Keputusan yang ditunggu (atau sudah diambil) atas satu penugasan."""

    workspace = models.ForeignKey(
        "db.Workspace", related_name="persetujuan_penugasan", on_delete=models.CASCADE
    )
    project = models.ForeignKey("db.Project", related_name="persetujuan_penugasan", on_delete=models.CASCADE)
    issue = models.ForeignKey(
        "db.Issue", related_name="persetujuan_penugasan", on_delete=models.CASCADE
    )
    # Pembuat tugas = penerima tugas (member hanya boleh menugaskan ke dirinya sendiri).
    # Disimpan eksplisit supaya kalau kelak aturannya melonggar, yang berubah cuma
    # penjaganya, bukan bentuk datanya.
    pemohon = models.ForeignKey("db.User", related_name="persetujuan_penugasan_diminta", on_delete=models.CASCADE)
    penerima = models.ForeignKey(
        "db.User", related_name="persetujuan_penugasan_diterima", on_delete=models.CASCADE
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_MENUNGGU)
    diputuskan_oleh = models.ForeignKey(
        "db.User",
        related_name="persetujuan_penugasan_diputuskan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    diputuskan_pada = models.DateTimeField(null=True, blank=True)
    # Wajib diisi saat menolak (dijaga di view): penolakan tanpa alasan memaksa orang
    # menebak, dan tebakan atas alasan orang lain adalah cara termurah kehilangan kepercayaan.
    alasan = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Persetujuan Penugasan"
        verbose_name_plural = "Persetujuan Penugasan"
        db_table = "persetujuan_penugasan"
        ordering = ("-created_at",)
        # Satu tugas hanya boleh punya SATU permintaan yang masih menunggu. Tanpa ini,
        # dua kali menyimpan tugas dengan cepat menghasilkan dua baris menunggu, dan
        # penyetuju bisa menekan "setujui" pada baris yang salah (yang lain tetap
        # menggantung selamanya).
        constraints = [
            models.UniqueConstraint(
                fields=["issue"],
                condition=Q(status="menunggu", deleted_at__isnull=True),
                name="persetujuan_satu_menunggu_per_tugas",
            )
        ]
        indexes = [
            models.Index(fields=["project", "status", "created_at"], name="persetujuan_proyek_status_idx"),
            models.Index(fields=["pemohon", "status"], name="persetujuan_pemohon_idx"),
        ]

    def __str__(self):
        return f"{self.issue_id} {self.status} ({self.pemohon_id})"
