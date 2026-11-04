# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengingat tenggat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel

# Titik pengingat, dalam hari relatif terhadap target_date.
# Negatif = sebelum tenggat, 0 = hari H, positif = sudah lewat (overdue).
#
# Sejak KEP-83 titiknya diatur di God Mode, bukan di sini:
# DEADLINE_REMINDER_EMAIL_DAYS (bawaan -7,-5,-3,-1,0,3,5,7, permintaan user
# 2026-08-11) dan DEADLINE_REMINDER_INBOX_DAYS (plane/utils/setelan_instance.py).
# Yang positif SENGAJA ada: tugas yang lewat tenggat justru paling perlu
# diingatkan, dan diam-diam membiarkannya lewat adalah cara paling halus
# membuat orang berhenti percaya pada alat pelacak tugas.
#
# `titik` di bawah polos IntegerField tanpa choices, jadi titik apa pun dalam
# -30..30 tersimpan tanpa migrasi.


class PengingatTenggat(BaseModel):
    """Catatan bahwa satu pengingat sudah dikirim, supaya tidak dobel.

    Satu baris = satu (work item, penerima, titik). Tanpa tabel ini, tugas
    harian akan mengirim ulang pengingat yang sama tiap kali ia jalan setelah
    kegagalan sebagian, atau saat jamnya digeser.

    Sengaja mencatat yang SUDAH dikirim, bukan menjadwalkan yang AKAN dikirim.
    Menjadwalkan di depan berarti setiap perubahan `target_date` harus
    membatalkan dan menjadwal ulang, dan satu jalur yang lupa memanggilnya
    membuat pengingat berbunyi untuk tanggal yang sudah tidak berlaku.
    Menghitung ulang tiap hari dari `target_date` yang berlaku saat itu tidak
    punya masalah tersebut.
    """

    workspace = models.ForeignKey(
        "db.Workspace", related_name="deadline_reminders", on_delete=models.CASCADE
    )
    project = models.ForeignKey(
        "db.Project", related_name="deadline_reminders", on_delete=models.CASCADE
    )
    issue = models.ForeignKey(
        "db.Issue", related_name="deadline_reminders", on_delete=models.CASCADE
    )
    penerima = models.ForeignKey(
        "db.User", related_name="deadline_reminders", on_delete=models.CASCADE
    )
    # Hari relatif terhadap target_date. Lihat komentar di atas kelas.
    titik = models.IntegerField()
    # Tanggal tenggat yang berlaku SAAT pengingat dikirim. Disimpan supaya kalau
    # tenggatnya digeser, kita tahu pengingat lama merujuk tanggal yang berbeda
    # dan boleh dikirim ulang untuk tanggal baru.
    tenggat = models.DateField()

    class Meta:
        # deleted_at ikut dalam kunci unik, menyamai pola model kustom lain di
        # repo ini: tanpa itu, baris yang pernah di-soft-delete membuat
        # create() berikutnya selalu IntegrityError.
        unique_together = ["issue", "penerima", "titik", "tenggat", "deleted_at"]
        verbose_name = "Pengingat Tenggat"
        verbose_name_plural = "Pengingat Tenggat"
        db_table = "deadline_reminders"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["issue", "penerima"])]

    def __str__(self):
        arah = "H" if self.titik == 0 else ("H-%d" % -self.titik if self.titik < 0 else "H+%d" % self.titik)
        return f"{self.issue_id} -> {self.penerima_id} ({arah})"
