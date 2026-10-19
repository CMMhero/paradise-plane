# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: riwayat login/logout
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models
from django.utils import timezone

# Module imports
from .base import BaseModel

# Retensi riwayat. Permintaan kantor: bisa ditelusuri mundur sampai 3 bulan.
RETENSI_HARI = 90

# Ambang "sedang aktif". Sesi boleh hidup berhari-hari, jadi keberadaan baris di
# tabel `sessions` hanya berarti MASIH LOGIN, bukan sedang memakai. Yang
# menentukan "sedang memakai" adalah User.last_active, diperbarui middleware.
AMBANG_AKTIF_MENIT = 5


class LoginActivity(BaseModel):
    """Satu baris per peristiwa login atau logout.

    Kenapa tabel sendiri dan bukan mengandalkan `User.last_login_time`: kolom itu
    **satu nilai yang ditimpa** tiap login. Dari sana mustahil menjawab "berapa
    sering orang ini keluar-masuk" atau "berapa lama biasanya dia memakai",
    riwayatnya tidak pernah ada, bukan sekadar tidak ditampilkan.

    `BaseModel` membawa soft-delete, tapi retensi WAJIB menghapus keras
    (`.delete(soft=False)` atau `queryset.delete()` lewat `all_objects`). Baris
    ini murni jejak dan tidak dirujuk apa pun; kalau dihapus lunak, tabel tumbuh
    selamanya padahal seluruh gunanya adalah dibuang setelah 3 bulan, dan
    `soft_delete_related_objects.delay()` akan mengantre satu task Celery per
    baris, yang untuk pembersihan puluhan ribu baris berarti membanjiri worker.
    """

    class Jenis(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        LOGOUT = "LOGOUT", "Logout"

    user = models.ForeignKey(
        "db.User", related_name="login_activities", on_delete=models.CASCADE
    )
    jenis = models.CharField(max_length=10, choices=Jenis.choices)
    terjadi_pada = models.DateTimeField(default=timezone.now, db_index=True)

    # Dari mana. Diambil dari request yang sama dengan yang mengisi device_info
    # sesi, jadi nilainya konsisten dengan yang terlihat di daftar sesi.
    ip = models.CharField(max_length=255, blank=True)
    user_agent = models.TextField(blank=True)
    # "email", "magic-code", "google", dst. Kosong untuk logout.
    medium = models.CharField(max_length=20, blank=True)
    # Permukaan tempat peristiwa terjadi: app / admin / space. Membedakan orang
    # yang login ke God Mode dari yang memakai aplikasi biasa.
    permukaan = models.CharField(max_length=10, blank=True)

    # Menautkan LOGIN ke sesinya. Dipakai memasangkan logout dengan login-nya
    # untuk menghitung durasi. Tidak ForeignKey: baris `sessions` dihapus saat
    # logout/kick, sementara jejak ini harus tetap ada sesudahnya.
    session_key = models.CharField(max_length=128, blank=True, db_index=True)

    class Meta:
        verbose_name = "Login Activity"
        verbose_name_plural = "Login Activities"
        db_table = "login_activities"
        ordering = ("-terjadi_pada",)
        indexes = [
            # Dua pola baca yang benar-benar dipakai dashboard: riwayat satu
            # orang, dan seluruh peristiwa dalam rentang waktu.
            models.Index(fields=["user", "-terjadi_pada"], name="loginact_user_waktu_idx"),
            models.Index(fields=["jenis", "-terjadi_pada"], name="loginact_jenis_waktu_idx"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.jenis} {self.terjadi_pada:%Y-%m-%d %H:%M}"

    @classmethod
    def catat(cls, *, user, jenis, request=None, medium="", permukaan="", session_key=""):
        """Catat satu peristiwa. TIDAK PERNAH melempar exception.

        Dipanggil dari jalur login dan logout. Kegagalan mencatat jejak tidak
        boleh membuat orang gagal masuk atau gagal keluar, jejak yang hilang
        itu merepotkan, pintu yang macet itu menghentikan pekerjaan.
        """
        try:
            ip, ua = "", ""
            if request is not None:
                # Impor lokal: modul ini dimuat saat app registry disusun, dan
                # plane.utils.ip_address menarik settings.
                from plane.utils.ip_address import get_client_ip

                ip = get_client_ip(request=request) or ""
                ua = request.META.get("HTTP_USER_AGENT", "") or ""
            return cls.objects.create(
                user=user,
                jenis=jenis,
                ip=ip,
                user_agent=ua,
                medium=medium or "",
                permukaan=permukaan or "",
                session_key=session_key or "",
            )
        except Exception:
            import logging

            logging.getLogger("plane").exception("Gagal mencatat LoginActivity")
            return None
