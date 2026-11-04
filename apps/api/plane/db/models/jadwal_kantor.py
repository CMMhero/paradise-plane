# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jadwal kantor (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models


class JadwalTerlaksana(models.Model):
    """Penanda bahwa satu slot jadwal kantor sudah dijalankan pada satu tanggal kantor.

    Satu baris = satu (slot, tanggal). Kunci unik di database inilah yang membuat
    tiap slot berjalan paling banyak sekali per hari, walaupun beat berdetak dua
    kali, dua worker berebut, atau worker dimulai ulang: penanda Redis tidak cukup
    karena bisa hilang saat Redis dimulai ulang atau kehabisan memori.

    Baris ditulis SEBELUM pekerjaannya dijalankan (klaim), lalu `selesai_at` dan
    `hasil` diisi sesudahnya. Klaim yang tidak pernah selesai (worker mati di
    tengah jalan) tetap menahan slot itu sampai besok: email ringkasan yang hilang
    sehari lebih murah daripada email ganda ke seluruh kantor.

    Bukan BaseModel: tidak ada soft delete, tidak ada pembuat. Ini keadaan
    penjadwal milik instance, bukan data siapa pun.
    """

    slot = models.CharField(max_length=64)
    # Tanggal menurut OFFICE_TIMEZONE saat slot diklaim, bukan tanggal UTC.
    tanggal = models.DateField()
    diklaim_at = models.DateTimeField(auto_now_add=True)
    selesai_at = models.DateTimeField(null=True, blank=True)
    # Ringkasan hasil task (mis. {"terkirim": 12}) atau alasan dilewati.
    hasil = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["slot", "tanggal"], name="jadwal_terlaksana_slot_tanggal_unik")]
        verbose_name = "Jadwal Terlaksana"
        verbose_name_plural = "Jadwal Terlaksana"
        db_table = "office_schedule_runs"
        ordering = ("-tanggal", "slot")

    def __str__(self):
        return f"{self.slot} {self.tanggal}"
