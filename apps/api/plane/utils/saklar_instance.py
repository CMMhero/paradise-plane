# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: saklar fitur di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Saklar fitur Paradise yang diatur Super Admin dari God Mode, bukan dari `.env`.

Nilainya tinggal di `InstanceConfiguration`, tabel yang sama dengan halaman Email,
Authentication, dan AI di God Mode, lalu dibaca ulang SETIAP kali dipanggil.
Akibatnya mengubah saklar berlaku seketika di api maupun worker Celery, tanpa
`docker compose up -d`.

Environment hanya benih: `configure_instance` menyalin nilainya ke database sekali,
saat barisnya belum ada (lihat `instance_config_variables/paradise.py`). Sesudah itu
God Mode yang menang, dan menyunting `.env` tidak berpengaruh lagi. Env baru dibaca
kalau barisnya memang belum ada (instalasi yang belum menjalankan
`configure_instance`, atau suite uji) atau `SKIP_ENV_VAR=0`.
"""

import os

from django.conf import settings

ENABLE_DEADLINE_REMINDER = "ENABLE_DEADLINE_REMINDER"
ENABLE_CHAT_EMAIL = "ENABLE_CHAT_EMAIL"
ENABLE_GOOGLE_CALENDAR_SYNC = "ENABLE_GOOGLE_CALENDAR_SYNC"
ENABLE_TUGAS_KE_DM = "ENABLE_TUGAS_KE_DM"
HIERARKI_GERBANG_TUGAS = "HIERARKI_GERBANG_TUGAS"
# Tanggal otomatis KEP-41 (lihat plane/utils/tanggal_otomatis.py). Menyala = perilaku
# sebelum saklarnya ada: masuk In Progress mengisi Start date yang kosong, masuk Done
# mengisi Due date yang kosong.
AUTO_START_DATE_ON_START = "AUTO_START_DATE_ON_START"
AUTO_DUE_DATE_ON_DONE = "AUTO_DUE_DATE_ON_DONE"

# Modul aplikasi yang bisa dimatikan Super Admin (God Mode > Features). Mati =
# menunya hilang dan halamannya menampilkan "dimatikan administrator"; data dan
# endpoint tetap utuh, jadi menyalakan ulang tidak kehilangan apa pun.
# Bawaan = perilaku sebelum saklar ini ada (Initiatives memang tersembunyi).
#
# Kunci saklarnya selalu `ENABLE_<NAMA MODUL>`, jadi nama modul di apps/web
# (`TParadiseModule`) cukup dibaca dari tabel di bawah. Cermin `BAWAAN` di
# apps/web/core/lib/paradise-modules.ts dan apps/admin .../fitur/page.tsx.
_MODUL_BAWAAN = {
    # Sidebar utama
    "inbox": "1",
    "your_work": "1",
    "stickies": "1",
    "drafts": "1",
    "quick_links": "1",
    # Menu workspace
    "dashboards": "1",
    "initiatives": "0",
    "views": "1",
    "analytics": "1",
    "chat": "1",
    "wiki": "1",
    "archives": "1",
    # Tab project
    "work_items": "1",
    # Cycles, work item types, dan templates DICABUT 2 Nov 2026 (KEP-53): bukan
    # modul lagi, jadi tak punya saklar. Barisnya yang tersisa di database tidak
    # dibaca siapa pun.
    "modules": "1",
    "pages": "1",
    "intake": "1",
    # Tab antrean persetujuan per divisi. Mematikannya hanya menyembunyikan
    # antrean; gerbang hierarki (HIERARKI_GERBANG_TUGAS) tetap berlaku.
    "approvals": "1",
    # Fitur di dalam work item & setelan project. Dimatikan 30 Okt 2026, bisa
    # dinyalakan dari God Mode.
    "time_tracking": "0",
    "estimates": "0",
}

# Nama modul (dipakai apps/web) -> kunci saklar.
MODUL_APLIKASI = {nama: f"ENABLE_{nama.upper()}" for nama in _MODUL_BAWAAN}

ENABLE_DASHBOARDS = MODUL_APLIKASI["dashboards"]
ENABLE_INITIATIVES = MODUL_APLIKASI["initiatives"]
ENABLE_VIEWS = MODUL_APLIKASI["views"]
ENABLE_ANALYTICS = MODUL_APLIKASI["analytics"]
ENABLE_ARCHIVES = MODUL_APLIKASI["archives"]

# Kunci -> nilai bawaan saat database maupun env tidak menyebutnya. Yang mengirim
# email atau menulis ke luar aplikasi MATI secara bawaan: menyalakannya harus
# tindakan sadar, bukan efek samping sebuah deploy.
SAKLAR_BAWAAN = {
    ENABLE_DEADLINE_REMINDER: "0",
    ENABLE_CHAT_EMAIL: "0",
    ENABLE_GOOGLE_CALENDAR_SYNC: "0",
    # Menulis ke dalam aplikasi saja, dan pemilik instance memintanya hidup.
    ENABLE_TUGAS_KE_DM: "1",
    HIERARKI_GERBANG_TUGAS: "0",
    AUTO_START_DATE_ON_START: "1",
    AUTO_DUE_DATE_ON_DONE: "1",
    **{MODUL_APLIKASI[nama]: bawaan for nama, bawaan in _MODUL_BAWAAN.items()},
}


def saklar_aktif(kunci: str) -> bool:
    """Apakah saklar `kunci` menyala. Kunci di luar `SAKLAR_BAWAAN` adalah bug: KeyError."""
    bawaan = SAKLAR_BAWAAN[kunci]
    if settings.SKIP_ENV_VAR:
        # Diimpor di sini: modul ini dipakai serializer yang dimuat sebelum app siap.
        from plane.license.models import InstanceConfiguration

        nilai = InstanceConfiguration.objects.filter(key=kunci).values_list("value", flat=True).first()
        if nilai is not None:
            return nilai.strip() == "1"
    return os.environ.get(kunci, bawaan).strip() == "1"


# Setelan angka: jeda, retensi, ambang. Sama seperti saklar, nilainya diatur di
# God Mode > Features dan dibaca ulang tiap dipanggil. Kunci -> (bawaan, min, maks).
# Batas min/maks dijaga di dua tempat: PATCH konfigurasi menolak nilai di luar
# rentang, dan `setelan_angka` menjepit nilai yang sudah terlanjur tersimpan
# (mis. ditulis langsung ke database) supaya retensi 0 hari tidak menghapus semua.
CHAT_EMAIL_QUIET_MINUTES = "CHAT_EMAIL_QUIET_MINUTES"
CHAT_EMAIL_INTERVAL_MINUTES = "CHAT_EMAIL_INTERVAL_MINUTES"
LOGIN_HISTORY_RETENTION_DAYS = "LOGIN_HISTORY_RETENTION_DAYS"
TRASH_RETENTION_DAYS = "TRASH_RETENTION_DAYS"
# Ambang kesehatan divisi di Dashboard Divisi: persentase tugas aktif yang lewat
# tenggat. Di atas "perhatian" = Perlu perhatian, di atas "kritis" = Kritis.
DASHBOARD_PERHATIAN_PERSEN = "DASHBOARD_PERHATIAN_PERSEN"
DASHBOARD_KRITIS_PERSEN = "DASHBOARD_KRITIS_PERSEN"
# Work item Done yang sudah sekian hari selesai diarsipkan otomatis oleh task
# harian (issue_automation_task). 0 = mati. Berlaku untuk SEMUA project, di samping
# setelan "Auto-archive" per project milik upstream yang hitungannya bulan.
AUTO_ARCHIVE_DONE_DAYS = "AUTO_ARCHIVE_DONE_DAYS"
# Due date work item yang selesai LEBIH AWAL dari rencananya. 0 = rencana dibiarkan
# (perilaku lama), 1 = Due date dimajukan ke hari selesai. Selesai TERLAMBAT tidak
# pernah menggeser Due date: itu menghapus bukti keterlambatan dari laporan.
DUE_DATE_ON_EARLY_DONE = "DUE_DATE_ON_EARLY_DONE"
DUE_DATE_SIMPAN_RENCANA = 0
DUE_DATE_MAJU_KE_SELESAI = 1
# Hari tenggang sesudah Due date sebelum work item dihitung terlambat (merah di
# aplikasi, hitungan terlambat di Dashboard Divisi & dasbor Home). 0 = sehari
# sesudah Due date sudah terlambat. Email pengingat tetap memakai tanggal kalender.
OVERDUE_GRACE_DAYS = "OVERDUE_GRACE_DAYS"
# Jendela "Selesai tepat waktu" di Dashboard Divisi, dalam hari ke belakang.
DASHBOARD_ON_TIME_WINDOW_DAYS = "DASHBOARD_ON_TIME_WINDOW_DAYS"
# Umur maksimum pesan obrolan yang masih boleh dihapus pengirimnya, dalam jam.
# Sesudahnya pesan tetap tinggal: orang sudah membaca dan menanggapinya.
# 0 = tanpa batas.
CHAT_DELETE_WINDOW_HOURS = "CHAT_DELETE_WINDOW_HOURS"

SETELAN_ANGKA = {
    CHAT_EMAIL_QUIET_MINUTES: (10, 1, 1440),
    CHAT_EMAIL_INTERVAL_MINUTES: (60, 5, 10080),
    LOGIN_HISTORY_RETENTION_DAYS: (90, 7, 730),
    # Benih env lama HARD_DELETE_AFTER_DAYS milik upstream, supaya instance yang
    # sudah mengaturnya tidak tiba-tiba memakai angka lain.
    TRASH_RETENTION_DAYS: (int(os.environ.get("HARD_DELETE_AFTER_DAYS", 60)), 1, 3650),
    DASHBOARD_PERHATIAN_PERSEN: (5, 1, 100),
    DASHBOARD_KRITIS_PERSEN: (15, 1, 100),
    AUTO_ARCHIVE_DONE_DAYS: (90, 0, 365),
    DUE_DATE_ON_EARLY_DONE: (DUE_DATE_SIMPAN_RENCANA, DUE_DATE_SIMPAN_RENCANA, DUE_DATE_MAJU_KE_SELESAI),
    OVERDUE_GRACE_DAYS: (0, 0, 30),
    DASHBOARD_ON_TIME_WINDOW_DAYS: (30, 7, 365),
    CHAT_DELETE_WINDOW_HOURS: (24, 0, 8760),
}

# Setelan angka yang hanya boleh salah satu nilai di daftar ini (God Mode
# menampilkannya sebagai pilihan, bukan kolom isian). PATCH menolak nilai lain;
# nilai liar yang terlanjur di database tetap dijepit ke rentang oleh `setelan_angka`.
SETELAN_PILIHAN = {
    AUTO_ARCHIVE_DONE_DAYS: (0, 7, 14, 30, 60, 90, 180, 365),
    DUE_DATE_ON_EARLY_DONE: (DUE_DATE_SIMPAN_RENCANA, DUE_DATE_MAJU_KE_SELESAI),
}


def nilai_angka_sah(kunci: str, nilai) -> bool:
    """Apakah `nilai` bilangan bulat di dalam rentang `kunci`."""
    _, minimum, maksimum = SETELAN_ANGKA[kunci]
    try:
        angka = int(str(nilai).strip())
    except (TypeError, ValueError):
        return False
    if kunci in SETELAN_PILIHAN:
        return angka in SETELAN_PILIHAN[kunci]
    return minimum <= angka <= maksimum


def setelan_angka(kunci: str) -> int:
    """Nilai setelan angka `kunci`, dijepit ke rentangnya. Kunci asing: KeyError."""
    bawaan, minimum, maksimum = SETELAN_ANGKA[kunci]
    mentah = None
    if settings.SKIP_ENV_VAR:
        from plane.license.models import InstanceConfiguration

        mentah = InstanceConfiguration.objects.filter(key=kunci).values_list("value", flat=True).first()
    if mentah is None:
        mentah = os.environ.get(kunci)
    try:
        angka = int(str(mentah).strip()) if mentah not in (None, "") else bawaan
    except ValueError:
        angka = bawaan
    return max(minimum, min(angka, maksimum))


def modul_aktif() -> dict:
    """{nama modul: bool} untuk seluruh MODUL_APLIKASI, dalam SATU kueri.

    Dibaca endpoint publik /api/instances/ di setiap muat halaman, jadi satu
    kueri per modul lewat `saklar_aktif` akan jadi belasan kali bolak-balik.
    """
    tersimpan = {}
    if settings.SKIP_ENV_VAR:
        from plane.license.models import InstanceConfiguration

        tersimpan = dict(
            InstanceConfiguration.objects.filter(key__in=MODUL_APLIKASI.values()).values_list("key", "value")
        )
    hasil = {}
    for nama, kunci in MODUL_APLIKASI.items():
        nilai = tersimpan.get(kunci)
        if nilai is None:
            nilai = os.environ.get(kunci, SAKLAR_BAWAAN[kunci])
        hasil[nama] = str(nilai).strip() == "1"
    return hasil
