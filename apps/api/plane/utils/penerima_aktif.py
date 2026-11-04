# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: email hanya untuk member yang aktif
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Apakah seseorang masih cukup aktif untuk dikirimi email kabar kerja.

Saklar God Mode `ENABLE_EMAIL_ACTIVE_ONLY` + angka `EMAIL_ACTIVE_DAYS`. Saat
menyala, email kabar kerja (pembaruan work item, persetujuan, penyebutan,
penugasan, pengingat tenggat, pesan obrolan belum dibaca) dilewati untuk orang
yang terakhir membuka aplikasi lebih dari N hari lalu. Inbox di dalam aplikasi
tetap ditulis, jadi begitu orangnya kembali, kabarnya masih ada.

Sengaja TIDAK dipakai untuk:
- email sistem: reset sandi, kode masuk, undangan, aktivasi, ganti email. Itu
  dipicu orangnya sendiri atau justru jalan masuk kembali ke aplikasi.
- ringkasan harian dan laporan direktur. Itu ringkasan yang dipilih sendiri, dan
  direktur (KEP-59) memang membaca kabar lewat email, bukan lewat aplikasi.

"Aktif" = nilai terbaru dari `User.last_active` (dipelihara middleware tiap
request) dan `User.last_login_time`. Akun yang keduanya kosong dianggap tidak aktif.
"""

from datetime import datetime, timedelta

from django.utils import timezone

from plane.utils.saklar_instance import EMAIL_ACTIVE_DAYS, ENABLE_EMAIL_ACTIVE_ONLY, saklar_aktif, setelan_angka


def batas_aktif(sekarang: datetime | None = None) -> datetime | None:
    """Waktu paling lama yang masih dihitung aktif. None = saklarnya mati (semua lolos)."""
    if not saklar_aktif(ENABLE_EMAIL_ACTIVE_ONLY):
        return None
    return (sekarang or timezone.now()) - timedelta(days=setelan_angka(EMAIL_ACTIVE_DAYS))


def terakhir_aktif(user) -> datetime | None:
    waktu = [w for w in (getattr(user, "last_active", None), getattr(user, "last_login_time", None)) if w]
    return max(waktu) if waktu else None


def aktif_sejak(user, batas: datetime | None) -> bool:
    """Murni: lolos kalau `batas` None, atau aktivitas terakhirnya tidak lebih tua dari `batas`."""
    if batas is None:
        return True
    terakhir = terakhir_aktif(user)
    return terakhir is not None and terakhir >= batas


def penerima_aktif(user) -> bool:
    """Satu orang. Untuk banyak orang, hitung `batas_aktif()` sekali lalu pakai `aktif_sejak`."""
    return aktif_sejak(user, batas_aktif())
