# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sinkronisasi Google Calendar
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel

# Izin paling sempit yang cukup: membuat dan menyunting acara di kalender
# pengguna. BUKAN `calendar` penuh, yang juga mengizinkan membaca seluruh isi
# kalender pribadi mereka dan menghapus kalendernya. Meminta lebih dari yang
# dibutuhkan membuat layar persetujuan Google terlihat lebih menakutkan dan
# memperbesar kerugian kalau token bocor.
SCOPE_KALENDER = "https://www.googleapis.com/auth/calendar.events"


class KalenderGoogle(BaseModel):
    """Sambungan satu pengguna ke Google Calendar miliknya.

    Menyimpan refresh token, bukan access token. Access token hidup satu jam;
    menyimpannya berarti menyimpan sesuatu yang hampir selalu sudah basi saat
    dipakai. Refresh token ditukar jadi access token saat dibutuhkan.

    ⚠️ `refresh_token` dienkripsi dengan SECRET_KEY instance (Fernet, lihat
    plane/license/utils/encryption.py). Kalau database dipindah ke server
    dengan SECRET_KEY berbeda, token tidak bisa didekripsi dan sinkronisasi
    MATI SENYAP, persis seperti yang terjadi pada EMAIL_HOST_PASSWORD saat
    migrasi 7 Agustus 2026. Bawa SECRET_KEY yang sama, atau siapkan semua
    orang menyambungkan ulang.
    """

    user = models.ForeignKey(
        "db.User", related_name="google_calendars", on_delete=models.CASCADE
    )
    # Terenkripsi. Jangan pernah dikembalikan lewat API mana pun.
    refresh_token = models.TextField()
    # TIDAK ADA medan alamat email di sini, dan itu keputusan sadar. Versi
    # pertama menyimpannya supaya pengguna tahu akun MANA yang tersambung, tapi
    # medan itu selamanya kosong: scope `calendar.events` tidak memberi izin
    # membaca profil, jadi tidak ada cara mengisinya tanpa meminta izin
    # tambahan ke semua orang. Medan yang selamanya kosong lebih buruk daripada
    # tidak ada, karena ia mengundang orang berikutnya "memperbaikinya" dengan
    # memperluas scope.
    # Hampir selalu "primary". Disediakan supaya orang yang memisahkan kalender
    # kerja dari pribadi bisa mengarahkannya, tanpa perlu ubah kode.
    calendar_id = models.CharField(max_length=255, default="primary")
    terakhir_sinkron = models.DateTimeField(null=True, blank=True)
    # Diisi saat sinkronisasi gagal berturut-turut. Dipakai UI untuk memberi
    # tahu pengguna bahwa sambungannya perlu dipulihkan, alih-alih membiarkan
    # kalender diam-diam berhenti terisi.
    galat_terakhir = models.TextField(blank=True)

    class Meta:
        # deleted_at ikut dalam kunci unik, menyamai model kustom lain di repo
        # ini: tanpa itu, orang yang pernah memutus sambungan tidak akan pernah
        # bisa menyambung lagi karena baris lamanya masih memegang kuncinya.
        unique_together = ["user", "deleted_at"]
        verbose_name = "Kalender Google"
        verbose_name_plural = "Kalender Google"
        db_table = "google_calendars"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user_id} -> {self.calendar_id}"


class AcaraKalender(BaseModel):
    """Jejak satu work item yang sudah dibuatkan acara di kalender seseorang.

    Tanpa tabel ini kita tidak punya cara mengubah atau menghapus acara yang
    sudah dibuat, karena Google memberi ID acara hanya sekali saat pembuatan.
    Akibatnya tiap sinkronisasi akan membuat acara baru dan kalender orang
    dipenuhi duplikat, yang persis masalah yang dipecahkan SEQUENCE pada jalur
    lampiran .ics.

    `tenggat` menyimpan tanggal yang berlaku saat acara terakhir ditulis, jadi
    sinkronisasi berikutnya bisa melewati work item yang tidak berubah tanpa
    memanggil API Google sama sekali.
    """

    user = models.ForeignKey(
        "db.User", related_name="calendar_events", on_delete=models.CASCADE
    )
    issue = models.ForeignKey(
        "db.Issue", related_name="calendar_events", on_delete=models.CASCADE
    )
    google_event_id = models.CharField(max_length=1024)
    tenggat = models.DateField()
    # Judul yang terakhir ditulis. Ikut dibandingkan supaya penggantian nama
    # work item juga terkirim, bukan cuma perubahan tanggal.
    judul = models.TextField(blank=True)

    class Meta:
        unique_together = ["user", "issue", "deleted_at"]
        verbose_name = "Acara Kalender"
        verbose_name_plural = "Acara Kalender"
        db_table = "calendar_events"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["user", "issue"])]

    def __str__(self):
        return f"{self.issue_id} -> {self.user_id} ({self.google_event_id[:16]})"
