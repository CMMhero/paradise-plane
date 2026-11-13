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
# Rem spam email (plane/bgtasks/email_antrean.py, plane/utils/email_utas.py,
# plane/utils/penerima_aktif.py).
# - Kumpulkan: email pembaruan work item dan persetujuan ditahan per penerima,
#   lalu dikirim sebagai SATU email sesudah EMAIL_BATCH_DELAY_MINUTES. Mati =
#   perilaku lama (satu email per work item per putaran 5 menit, persetujuan satu
#   email per kejadian).
# - Utas: semua email tentang satu work item memakai subjek tetap dan header
#   Message-ID/In-Reply-To/References yang sama, jadi Gmail dan Outlook
#   menumpuknya dalam satu percakapan.
# - Hanya member aktif: email kabar kerja dilewati untuk orang yang tidak membuka
#   aplikasi selama EMAIL_ACTIVE_DAYS. Inbox tetap ditulis. Email sistem (reset
#   sandi, undangan, kode masuk) dan ringkasan harian tidak tersentuh.
ENABLE_EMAIL_BATCH = "ENABLE_EMAIL_BATCH"
ENABLE_EMAIL_THREADING = "ENABLE_EMAIL_THREADING"
ENABLE_EMAIL_ACTIVE_ONLY = "ENABLE_EMAIL_ACTIVE_ONLY"
# Email yang HANYA diterima Super Admin (God Mode > Notifications > Super Admin
# emails, keputusan user 2026-11-06). Satu kunci per jenis email admin-saja, agar
# jenis baru tinggal menambah kunci di sini dan satu baris di layout God Mode.
# - Peringatan retensi riwayat login (`login_activity_retention`): dikirim
#   beberapa hari sebelum riwayat tertua dibuang. Mati = banner di God Mode tetap
#   muncul, hanya emailnya yang tidak dikirim; pembersihan jalan terus.
ENABLE_ADMIN_RETENTION_EMAIL = "ENABLE_ADMIN_RETENTION_EMAIL"
# Aturan kerja (KEP-83, God Mode > Work rules). Keduanya SENSITIF: mengubahnya
# lewat /api/instances/settings/ dengan frasa konfirmasi, dan tercatat di audit.
# - Penolakan persetujuan wajib beralasan (app/views/issue/persetujuan.py). 1 =
#   perilaku sebelum saklarnya ada.
# - Penugasan hanya ke jenjang yang lebih rendah (`PERIKSA_TINGKAT_PENERIMA` di
#   utils/hierarki.py, menyala sejak 2026-10-15). 1 = perilaku hari ini.
APPROVAL_REJECT_REASON_REQUIRED = "APPROVAL_REJECT_REASON_REQUIRED"
ASSIGN_DOWN_ONLY = "ASSIGN_DOWN_ONLY"
# KEP-84 (sensitif): tugas yang menunggu persetujuan selesai TIDAK dihitung
# terlambat (dashboard, merah, pengingat staf, ringkasan); pengingat lewat
# tenggatnya dikirim ke penyetuju. Penyaring bersamanya di utils/menunggu_persetujuan.py.
APPROVAL_PENDING_NOT_LATE = "APPROVAL_PENDING_NOT_LATE"

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
# Kunci -> nilai bawaan saat database maupun env tidak menyebutnya. Bawaan dipilih
# user 4 Nov 2026 (KEP-84) sesuai cara kantor memakainya: pengingat tenggat, gerbang
# hierarki, utas email, dan saringan member aktif HIDUP. Yang menulis ke luar aplikasi
# (chat email, Google Calendar) tetap mati: menyalakannya harus tindakan sadar.
SAKLAR_BAWAAN = {
    ENABLE_DEADLINE_REMINDER: "1",
    ENABLE_CHAT_EMAIL: "0",
    ENABLE_GOOGLE_CALENDAR_SYNC: "0",
    # Menulis ke dalam aplikasi saja, dan pemilik instance memintanya hidup.
    ENABLE_TUGAS_KE_DM: "1",
    HIERARKI_GERBANG_TUGAS: "1",
    AUTO_START_DATE_ON_START: "1",
    AUTO_DUE_DATE_ON_DONE: "1",
    # Kumpul MENGURANGI email, jadi hidup. Utas hidup (KEP-84): subjeknya jadi
    # tetap `[PROJ-12] Judul`, jadi peran penerima ("Perlu persetujuanmu") hilang
    # dari subjek (aturan 2.1.1); user memilih utas tetap hidup.
    # Saringan member aktif hidup (KEP-84): yang 30 hari tak membuka aplikasi cukup inbox.
    ENABLE_EMAIL_BATCH: "1",
    ENABLE_EMAIL_THREADING: "1",
    ENABLE_EMAIL_ACTIVE_ONLY: "1",
    # Hidup: peringatan retensi sudah dikirim sebelum saklarnya ada.
    ENABLE_ADMIN_RETENTION_EMAIL: "1",
    APPROVAL_REJECT_REASON_REQUIRED: "1",
    ASSIGN_DOWN_ONLY: "1",
    APPROVAL_PENDING_NOT_LATE: "1",
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
    return str(env_benih(kunci, bawaan)).strip() == "1"


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
# Jendela kumpul email (ENABLE_EMAIL_BATCH), dalam menit, dihitung dari kabar
# TERTUA yang belum terkirim untuk satu penerima. Minimal 5: penyapunya berjalan
# tiap 5 menit, angka lebih kecil tidak berarti apa-apa.
EMAIL_BATCH_DELAY_MINUTES = "EMAIL_BATCH_DELAY_MINUTES"
# Batas "aktif" untuk ENABLE_EMAIL_ACTIVE_ONLY, dalam hari sejak terakhir membuka aplikasi.
EMAIL_ACTIVE_DAYS = "EMAIL_ACTIVE_DAYS"

# --- KEP-83: setelan yang dulu terkunci di kode, sekarang di God Mode. ---
# Bawaan SETIAP kunci di bawah = perilaku sebelum kuncinya ada, jadi deploy tidak
# mengubah apa pun. Kunci baru ini TIDAK membaca env dengan namanya sendiri (env
# baru = MAJOR, KEP-48); dua di antaranya diberi benih dari env lama yang sudah ada.
#
# Ringkasan harian: berapa hari ke depan yang dimuat, dan tugas terlambat berapa
# hari yang dihitung "macet" (daily_digest_task, direktur_digest_task).
DIGEST_LOOKAHEAD_DAYS = "DIGEST_LOOKAHEAD_DAYS"
STUCK_AFTER_DAYS = "STUCK_AFTER_DAYS"
# Batas ukuran satu unggahan, dalam MiB. Benihnya env lama FILE_SIZE_LIMIT (byte).
# Maksimumnya batas body di proxy Caddy (`request_body max_size {$FILE_SIZE_LIMIT}`
# di apps/proxy/Caddyfile.*): angka lebih besar ditolak proxy sebelum sampai ke
# MinIO, jadi God Mode hanya boleh MENURUNKAN batas itu, tidak menaikkannya.
UPLOAD_MAX_MB = "UPLOAD_MAX_MB"
# Umur sesi login aplikasi, dalam hari. Benihnya env lama SESSION_COOKIE_AGE (detik).
SESSION_DAYS = "SESSION_DAYS"
# Undangan workspace kedaluwarsa sesudah sekian hari. 0 = tidak pernah (hari ini).
INVITE_EXPIRY_DAYS = "INVITE_EXPIRY_DAYS"
# Obrolan: panjang maksimum satu pesan (dulu `BATAS_ISI` di db/models/chat.py),
# jumlah lampiran per pesan (dulu `BATAS_LAMPIRAN` di app/views/chat.py), dan umur
# pesan yang masih boleh disunting pengirimnya, dalam jam (0 = tanpa batas, hari ini).
# Kolom `isi` itu TextField tanpa batas teknis; 20.000 adalah batas kewarasan.
CHAT_MESSAGE_MAX_LENGTH = "CHAT_MESSAGE_MAX_LENGTH"
CHAT_ATTACHMENTS_MAX = "CHAT_ATTACHMENTS_MAX"
CHAT_EDIT_WINDOW_HOURS = "CHAT_EDIT_WINDOW_HOURS"
# Widget "Needs attention" (utils/perhatian.py): penolakan dan sebutan sampai
# berapa hari ke belakang yang masih ditampilkan.
ATTENTION_REJECTED_DAYS = "ATTENTION_REJECTED_DAYS"
ATTENTION_MENTION_DAYS = "ATTENTION_MENTION_DAYS"

# Aturan kerja SENSITIF (pilihan, bukan angka bebas):
#
# APPROVAL_REQUIRED_BELOW_LEVEL: pemegang jenjang DI BAWAH angka ini yang
# menyelesaikan tugasnya sendiri harus menunggu persetujuan atasan. Angkanya
# jenjang di db/models/hierarki.py (10 member, 20 supervisor, 30 manager,
# 40 direktur); jenjang kosong selalu dihitung staf.
#   20 = hanya staf (member) - perilaku hari ini (`_adalah_staf` di utils/hierarki.py)
#   30 = staf dan supervisor
#   40 = semua kecuali direktur
APPROVAL_REQUIRED_BELOW_LEVEL = "APPROVAL_REQUIRED_BELOW_LEVEL"
APPROVAL_DI_BAWAH_SUPERVISOR = 20
APPROVAL_DI_BAWAH_MANAGER = 30
APPROVAL_DI_BAWAH_DIREKTUR = 40
# TASK_DELETE_RULE: siapa boleh menghapus/mengarsipkan tugas (utils/task_access.py).
#   0 = hari ini: pembuat, Super Admin, admin project; saat gerbang hierarki
#       (HIERARKI_GERBANG_TUGAS) menyala: yang boleh MENGUBAH tugas itu
#       (pembuat/assignee/atasannya) plus Super Admin
#   1 = hanya pembuat dan Super Admin
#   2 = siapa pun yang boleh mengubah tugas itu (gerbang menyala: aturan ubah
#       hierarki; gerbang mati: setiap anggota yang lolos izin project)
TASK_DELETE_RULE = "TASK_DELETE_RULE"
HAPUS_ATURAN_HARI_INI = 0
HAPUS_PEMBUAT_SAJA = 1
HAPUS_YANG_BOLEH_UBAH = 2
# DUE_DATE_CHANGE_RULE: siapa boleh menggeser Due date tugas yang sudah di papan.
#   0 = pembuat dan Super Admin (hari ini, `bisa_ganti_tenggat`)
#   1 = ditambah admin project
#   2 = siapa pun yang boleh mengubah tugas itu
# KEP-67 tetap berlaku di atas aturan ini: tugas terlambat tak pernah digeser otomatis.
DUE_DATE_CHANGE_RULE = "DUE_DATE_CHANGE_RULE"
TENGGAT_PEMBUAT_SAJA = 0
TENGGAT_PLUS_ADMIN_PROJECT = 1
TENGGAT_YANG_BOLEH_UBAH = 2
# APPROVAL_FINISH_TIME (KEP-84, sensitif): kapan tugas yang lewat persetujuan
# dihitung selesai (`completed_at`, dan Due date otomatis KEP-41/KEP-67 darinya).
#   0 = saat staf mengajukan (bawaan): atasan lambat tidak membuat staf tampak lambat
#   1 = saat atasan menyetujui (perilaku sebelum KEP-84)
APPROVAL_FINISH_TIME = "APPROVAL_FINISH_TIME"
SELESAI_SAAT_DIAJUKAN = 0
SELESAI_SAAT_DISETUJUI = 1

# --- Izin per sumber (KEP-85, God Mode > Work rules > Permissions). ---
# Siapa boleh mengubah, mengarsipkan, atau menghapus sesuatu selain work item.
# Pembacanya satu: plane/utils/izin_sumber.py. Super Admin dan admin workspace
# selalu lolos (keputusan user 4 Nov 2026), jadi pilihan di bawah hanya mengatur
# orang selain mereka.
#
# Isi (punya pemilik: pembuat/owner, plus yang ditugaskan di dalamnya):
#   0 = pemilik + atasannya di hierarki (bawaan)
#   1 = pemilik saja
#   2 = setiap anggota project (perilaku Plane asli)
IZIN_PEMILIK_ATASAN = 0
IZIN_PEMILIK_SAJA = 1
IZIN_SEMUA_ANGGOTA = 2
PERM_MODULE_EDIT = "PERM_MODULE_EDIT"
PERM_MODULE_ARCHIVE = "PERM_MODULE_ARCHIVE"
PERM_MODULE_DELETE = "PERM_MODULE_DELETE"
PERM_PAGE_EDIT = "PERM_PAGE_EDIT"
PERM_PAGE_ARCHIVE = "PERM_PAGE_ARCHIVE"
PERM_PAGE_DELETE = "PERM_PAGE_DELETE"
PERM_VIEW_EDIT = "PERM_VIEW_EDIT"
PERM_VIEW_DELETE = "PERM_VIEW_DELETE"
PERM_COMMENT_EDIT = "PERM_COMMENT_EDIT"
PERM_COMMENT_DELETE = "PERM_COMMENT_DELETE"
PERM_WIKI_EDIT = "PERM_WIKI_EDIT"
PERM_WIKI_DELETE = "PERM_WIKI_DELETE"
IZIN_ISI = (
    PERM_MODULE_EDIT,
    PERM_MODULE_ARCHIVE,
    PERM_MODULE_DELETE,
    PERM_PAGE_EDIT,
    PERM_PAGE_ARCHIVE,
    PERM_PAGE_DELETE,
    PERM_VIEW_EDIT,
    PERM_VIEW_DELETE,
    PERM_COMMENT_EDIT,
    PERM_COMMENT_DELETE,
    PERM_WIKI_EDIT,
    PERM_WIKI_DELETE,
)
# Struktur project (tak punya pemilik perorangan). Nilainya jenjang minimum yang
# boleh, dan hanya di project yang ia awasi (`divisi_diawasi`): supervisor =
# project departemennya, manager = divisinya, direktur = semua.
#   20 = supervisor ke atas (bawaan, pilihan user 4 Nov 2026)
#   30 = manager ke atas
#   40 = direktur
#   90 = hanya admin (Super Admin dan admin workspace)
STRUKTUR_SUPERVISOR = 20
STRUKTUR_MANAGER = 30
STRUKTUR_DIREKTUR = 40
STRUKTUR_ADMIN_SAJA = 90
# Detail & setelan project (nama, identifier, fitur, otomasi).
PERM_PROJECT_EDIT = "PERM_PROJECT_EDIT"
# Alur kerja project: state, label, estimate, wadah intake.
PERM_PROJECT_WORKFLOW = "PERM_PROJECT_WORKFLOW"
PERM_PROJECT_ARCHIVE = "PERM_PROJECT_ARCHIVE"
PERM_PROJECT_DELETE = "PERM_PROJECT_DELETE"
# Trash project: memulihkan dan membuang permanen barang orang lain.
PERM_TRASH_RESTORE = "PERM_TRASH_RESTORE"
PERM_TRASH_PURGE = "PERM_TRASH_PURGE"
IZIN_STRUKTUR = (
    PERM_PROJECT_EDIT,
    PERM_PROJECT_WORKFLOW,
    PERM_PROJECT_ARCHIVE,
    PERM_PROJECT_DELETE,
    PERM_TRASH_RESTORE,
    PERM_TRASH_PURGE,
)
_PILIHAN_ISI = (IZIN_PEMILIK_ATASAN, IZIN_PEMILIK_SAJA, IZIN_SEMUA_ANGGOTA)
_PILIHAN_STRUKTUR = (STRUKTUR_SUPERVISOR, STRUKTUR_MANAGER, STRUKTUR_DIREKTUR, STRUKTUR_ADMIN_SAJA)

_MIB = 1024 * 1024


_DETIK_SEHARI = 86400


def _benih_env(env: str, satuan: int, cadangan: int, minimum: int, maksimum: int) -> int:
    """Benih dari env lama berbentuk detik/byte, dibulatkan ke bawah lalu dijepit.

    Env kosong atau bukan angka = `cadangan`.
    """
    try:
        nilai = int(str(os.environ.get(env, "")).strip()) // satuan
    except ValueError:
        return cadangan
    return max(minimum, min(nilai, maksimum))


def batas_proxy_mb() -> int:
    """Batas body proxy Caddy (env FILE_SIZE_LIMIT) dalam MiB, minimal 1. Tanpa env: 5."""
    return _benih_env("FILE_SIZE_LIMIT", _MIB, 5, 1, 1 << 20)


SETELAN_ANGKA = {
    CHAT_EMAIL_QUIET_MINUTES: (10, 1, 1440),
    CHAT_EMAIL_INTERVAL_MINUTES: (60, 5, 10080),
    LOGIN_HISTORY_RETENTION_DAYS: (90, 7, 730),
    # Benih env lama HARD_DELETE_AFTER_DAYS milik upstream, supaya instance yang
    # sudah mengaturnya tidak tiba-tiba memakai angka lain.
    TRASH_RETENTION_DAYS: (int(os.environ.get("HARD_DELETE_AFTER_DAYS", 30)), 1, 3650),
    DASHBOARD_PERHATIAN_PERSEN: (5, 1, 100),
    DASHBOARD_KRITIS_PERSEN: (15, 1, 100),
    AUTO_ARCHIVE_DONE_DAYS: (90, 0, 365),
    DUE_DATE_ON_EARLY_DONE: (DUE_DATE_SIMPAN_RENCANA, DUE_DATE_SIMPAN_RENCANA, DUE_DATE_MAJU_KE_SELESAI),
    OVERDUE_GRACE_DAYS: (0, 0, 30),
    DASHBOARD_ON_TIME_WINDOW_DAYS: (30, 7, 365),
    CHAT_DELETE_WINDOW_HOURS: (24, 0, 8760),
    EMAIL_BATCH_DELAY_MINUTES: (15, 5, 1440),
    EMAIL_ACTIVE_DAYS: (30, 1, 365),
    # KEP-83
    DIGEST_LOOKAHEAD_DAYS: (7, 1, 30),
    STUCK_AFTER_DAYS: (7, 1, 90),
    UPLOAD_MAX_MB: (batas_proxy_mb(), 1, batas_proxy_mb()),
    SESSION_DAYS: (_benih_env("SESSION_COOKIE_AGE", _DETIK_SEHARI, 7, 1, 90), 1, 90),
    INVITE_EXPIRY_DAYS: (7, 0, 365),
    CHAT_MESSAGE_MAX_LENGTH: (5000, 100, 20000),
    CHAT_ATTACHMENTS_MAX: (5, 1, 20),
    CHAT_EDIT_WINDOW_HOURS: (24, 0, 8760),
    ATTENTION_REJECTED_DAYS: (14, 1, 90),
    ATTENTION_MENTION_DAYS: (7, 1, 90),
    APPROVAL_REQUIRED_BELOW_LEVEL: (
        APPROVAL_DI_BAWAH_SUPERVISOR,
        APPROVAL_DI_BAWAH_SUPERVISOR,
        APPROVAL_DI_BAWAH_DIREKTUR,
    ),
    TASK_DELETE_RULE: (HAPUS_ATURAN_HARI_INI, HAPUS_ATURAN_HARI_INI, HAPUS_YANG_BOLEH_UBAH),
    DUE_DATE_CHANGE_RULE: (TENGGAT_PEMBUAT_SAJA, TENGGAT_PEMBUAT_SAJA, TENGGAT_YANG_BOLEH_UBAH),
    APPROVAL_FINISH_TIME: (SELESAI_SAAT_DIAJUKAN, SELESAI_SAAT_DIAJUKAN, SELESAI_SAAT_DISETUJUI),
    # KEP-85
    **{k: (IZIN_PEMILIK_ATASAN, IZIN_PEMILIK_ATASAN, IZIN_SEMUA_ANGGOTA) for k in IZIN_ISI},
    **{k: (STRUKTUR_SUPERVISOR, STRUKTUR_SUPERVISOR, STRUKTUR_ADMIN_SAJA) for k in IZIN_STRUKTUR},
}

# Setelan angka yang hanya boleh salah satu nilai di daftar ini (God Mode
# menampilkannya sebagai pilihan, bukan kolom isian). PATCH menolak nilai lain;
# nilai liar yang terlanjur di database tetap dijepit ke rentang oleh `setelan_angka`.
SETELAN_PILIHAN = {
    AUTO_ARCHIVE_DONE_DAYS: (0, 7, 14, 30, 60, 90, 180, 365),
    DUE_DATE_ON_EARLY_DONE: (DUE_DATE_SIMPAN_RENCANA, DUE_DATE_MAJU_KE_SELESAI),
    APPROVAL_REQUIRED_BELOW_LEVEL: (
        APPROVAL_DI_BAWAH_SUPERVISOR,
        APPROVAL_DI_BAWAH_MANAGER,
        APPROVAL_DI_BAWAH_DIREKTUR,
    ),
    TASK_DELETE_RULE: (HAPUS_ATURAN_HARI_INI, HAPUS_PEMBUAT_SAJA, HAPUS_YANG_BOLEH_UBAH),
    DUE_DATE_CHANGE_RULE: (TENGGAT_PEMBUAT_SAJA, TENGGAT_PLUS_ADMIN_PROJECT, TENGGAT_YANG_BOLEH_UBAH),
    APPROVAL_FINISH_TIME: (SELESAI_SAAT_DIAJUKAN, SELESAI_SAAT_DISETUJUI),
    **{k: _PILIHAN_ISI for k in IZIN_ISI},
    **{k: _PILIHAN_STRUKTUR for k in IZIN_STRUKTUR},
}

# Kunci KEP-83 yang TIDAK punya env dengan namanya sendiri (KEP-48: env baru =
# MAJOR). Pembacanya melompati os.environ untuk kunci ini: baris database, lalu
# bawaan kode (yang untuk UPLOAD_MAX_MB dan SESSION_DAYS sudah berbenih env lama).
TANPA_ENV = frozenset(
    {
        APPROVAL_REJECT_REASON_REQUIRED,
        ASSIGN_DOWN_ONLY,
        DIGEST_LOOKAHEAD_DAYS,
        STUCK_AFTER_DAYS,
        UPLOAD_MAX_MB,
        SESSION_DAYS,
        INVITE_EXPIRY_DAYS,
        CHAT_MESSAGE_MAX_LENGTH,
        CHAT_ATTACHMENTS_MAX,
        CHAT_EDIT_WINDOW_HOURS,
        ATTENTION_REJECTED_DAYS,
        ATTENTION_MENTION_DAYS,
        APPROVAL_REQUIRED_BELOW_LEVEL,
        TASK_DELETE_RULE,
        DUE_DATE_CHANGE_RULE,
        APPROVAL_FINISH_TIME,
        APPROVAL_PENDING_NOT_LATE,
        *IZIN_ISI,
        *IZIN_STRUKTUR,
    }
)


def env_benih(kunci: str, cadangan=None):
    """Nilai env untuk `kunci`, atau `cadangan` untuk kunci tanpa env (`TANPA_ENV`)."""
    if kunci in TANPA_ENV:
        return cadangan
    return os.environ.get(kunci, cadangan)


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
        mentah = env_benih(kunci)
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
