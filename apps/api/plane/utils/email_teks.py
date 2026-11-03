# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: teks email id/en
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kamus teks untuk email yang memakai templat Django.

Pola yang sama dengan `_STRINGS_APPROVAL_*`: teks di Python, bukan di templat,
supaya satu templat melayani dua bahasa dan logikanya tidak bercabang di HTML.
Nilai diformat di sini lalu di-escape otomatis oleh templat, jadi nama orang dan
nama workspace yang berisi `<` tetap aman.

Email ringkasan, pengingat, penugasan, dan obrolan dirakit di modulnya sendiri
(`plane/bgtasks/*_email.py`) dengan kamus masing-masing.
"""

from plane.utils.email_merek import MEREK

TEKS = {
    "magic": {
        "id": {
            "subjek": "Kode masuk {merek}: {kode}",
            "judul": "Kode masuk Anda",
            "intro": "Masukkan kode ini di halaman masuk {merek}. Kode berlaku 10 menit.",
            "abaikan": "Kalau Anda tidak sedang mencoba masuk, abaikan email ini. Akun Anda tetap aman.",
        },
        "en": {
            "subjek": "Your {merek} sign-in code: {kode}",
            "judul": "Your sign-in code",
            "intro": "Enter this code on the {merek} sign-in page. It is valid for 10 minutes.",
            "abaikan": "If you weren't trying to sign in, ignore this email. Your account is still safe.",
        },
    },
    "ganti_email": {
        "id": {
            "subjek": "Verifikasi alamat email baru Anda di {merek}",
            "judul": "Verifikasi email baru",
            "intro": "Masukkan kode ini untuk memastikan alamat ini milik Anda. Kode berlaku 10 menit.",
            "abaikan": "Kalau Anda tidak sedang mengganti alamat email, abaikan email ini.",
        },
        "en": {
            "subjek": "Verify your new email address on {merek}",
            "judul": "Verify your new email",
            "intro": "Enter this code to confirm this address belongs to you. It is valid for 10 minutes.",
            "abaikan": "If you aren't changing your email address, ignore this email.",
        },
    },
    "lupa_sandi": {
        "id": {
            "subjek": "Atur ulang kata sandi {merek} Anda",
            "judul": "Atur ulang kata sandi",
            "intro": "Kami menerima permintaan untuk mengatur ulang kata sandi akun {email}. Klik tombol di bawah untuk membuat kata sandi baru.",
            "tombol": "Buat kata sandi baru",
            "abaikan": "Kalau Anda tidak memintanya, abaikan email ini. Kata sandi lama tetap berlaku.",
        },
        "en": {
            "subjek": "Reset your {merek} password",
            "judul": "Reset your password",
            "intro": "We received a request to reset the password for {email}. Click the button below to choose a new one.",
            "tombol": "Choose a new password",
            "abaikan": "If you didn't ask for this, ignore this email. Your current password still works.",
        },
    },
    "undangan_workspace": {
        "id": {
            "subjek": "{pengundang} mengundang Anda ke {workspace} di {merek}",
            "judul": "Bergabung ke {workspace}",
            "intro": "{pengundang} mengundang Anda bekerja bersama di workspace {workspace}.",
            "tombol": "Terima undangan",
            "abaikan": "Kalau Anda tidak menunggu undangan ini, abaikan saja email ini.",
        },
        "en": {
            "subjek": "{pengundang} invited you to {workspace} on {merek}",
            "judul": "Join {workspace}",
            "intro": "{pengundang} invited you to work together in the {workspace} workspace.",
            "tombol": "Accept invitation",
            "abaikan": "If you weren't expecting this invitation, you can ignore this email.",
        },
    },
    "undangan_project": {
        "id": {
            "subjek": "{pengundang} mengundang Anda ke project {project} di {merek}",
            "judul": "Bergabung ke project {project}",
            "intro": "{pengundang} mengundang Anda bergabung ke project {project}.",
            "tombol": "Terima undangan",
            "abaikan": "Kalau Anda tidak menunggu undangan ini, abaikan saja email ini.",
        },
        "en": {
            "subjek": "{pengundang} invited you to the {project} project on {merek}",
            "judul": "Join the {project} project",
            "intro": "{pengundang} invited you to join the {project} project.",
            "tombol": "Accept invitation",
            "abaikan": "If you weren't expecting this invitation, you can ignore this email.",
        },
    },
    "tambah_project": {
        "id": {
            "subjek": "Anda ditambahkan ke project {project} di {merek}",
            "judul": "Anda sekarang anggota {project}",
            "intro": "{pengundang} menambahkan Anda ke project {project} di workspace {workspace}. Tugas dan diskusinya sudah bisa Anda buka.",
            "tombol": "Buka project",
        },
        "en": {
            "subjek": "You were added to the {project} project on {merek}",
            "judul": "You're now a member of {project}",
            "intro": "{pengundang} added you to the {project} project in the {workspace} workspace. Its work items and discussions are open to you now.",
            "tombol": "Open project",
        },
    },
    "email_diubah": {
        "id": {
            "subjek": "Alamat email {merek} Anda sudah diganti",
            "judul": "Alamat email diganti",
            "intro": "Mulai sekarang Anda masuk ke {merek} dengan alamat {email}.",
            "abaikan": "Kalau bukan Anda yang menggantinya, segera hubungi tim IT.",
        },
        "en": {
            "subjek": "Your {merek} email address was changed",
            "judul": "Email address changed",
            "intro": "From now on you sign in to {merek} with {email}.",
            "abaikan": "If you didn't make this change, contact the IT team right away.",
        },
    },
    "aktivasi": {
        "id": {
            "subjek": "Akun {merek} Anda aktif kembali",
            "judul": "Selamat datang kembali",
            "intro": "Akun Anda sudah aktif lagi. Tugas dan data Anda bisa dibuka seperti sebelumnya, selama project-nya masih aktif.",
            "tombol": "Buka {merek}",
        },
        "en": {
            "subjek": "Your {merek} account is active again",
            "judul": "Welcome back",
            "intro": "Your account is active again. Your work items and data are available as before, as long as their projects are still active.",
            "tombol": "Open {merek}",
        },
    },
    "deaktivasi": {
        "id": {
            "subjek": "Akun {merek} Anda dinonaktifkan",
            "judul": "Akun dinonaktifkan",
            "intro": "Akun Anda sudah dinonaktifkan. Tugas dan data project Anda tetap tersimpan dan bisa dibuka anggota lain.",
            "tombol": "Aktifkan akun",
            "abaikan": "Kalau bukan Anda yang menonaktifkannya, segera hubungi tim IT.",
        },
        "en": {
            "subjek": "Your {merek} account was deactivated",
            "judul": "Account deactivated",
            "intro": "Your account has been deactivated. Your work items and project data are kept and stay available to other members.",
            "tombol": "Reactivate account",
            "abaikan": "If you didn't do this, contact the IT team right away.",
        },
    },
    "ekspor": {
        "id": {
            "subjek": "Ekspor analitik {merek} Anda sudah siap",
            "judul": "Ekspor analitik siap",
            "intro": "Data analitik yang Anda minta terlampir sebagai berkas CSV.",
            "catatan": "Buka berkasnya di Excel, Google Sheets, atau alat BI apa pun.",
        },
        "en": {
            "subjek": "Your {merek} analytics export is ready",
            "judul": "Analytics export ready",
            "intro": "The analytics data you requested is attached as a CSV file.",
            "catatan": "Open it in Excel, Google Sheets, or any BI tool.",
        },
    },
    "webhook": {
        "id": {
            "subjek": "Webhook dinonaktifkan",
            "judul": "Webhook dinonaktifkan",
            "intro": "Webhook {url} dimatikan otomatis karena permintaannya berulang kali gagal.",
            "tombol": "Lihat webhook",
            "alasan": "Anda menerima email ini karena Anda admin workspace pemilik webhook ini.",
        },
        "en": {
            "subjek": "Webhook deactivated",
            "judul": "Webhook deactivated",
            "intro": "Webhook {url} was turned off automatically because its requests kept failing.",
            "tombol": "View webhook",
            "alasan": "You received this email because you administer the workspace that owns this webhook.",
        },
    },
    "uji": {
        "id": {
            "subjek": "Email uji dari {merek}",
            "judul": "Pengaturan SMTP berfungsi",
            "intro": "Email ini dikirim untuk memastikan pengaturan email di {merek} bekerja. Kalau Anda membacanya, server surat sudah tersambung.",
        },
        "en": {
            "subjek": "Test email from {merek}",
            "judul": "Your SMTP settings work",
            "intro": "This email checks that the email settings in {merek} work. If you can read it, the mail server is connected.",
        },
    },
    "pembaruan": {
        "id": {
            "judul_satu": "{aktor} memperbarui tugas ini",
            "judul_banyak": "{n} orang memperbarui tugas ini",
            "komentar": "Komentar",
            "tombol": "Buka tugas",
            "alasan": "Anda menerima email ini karena Anda mengikuti tugas ini.",
            "kosong": "(kosong)",
            "diubah": "diubah",
        },
        "en": {
            "judul_satu": "{aktor} updated this work item",
            "judul_banyak": "{n} people updated this work item",
            "komentar": "Comment",
            "tombol": "Open work item",
            "alasan": "You received this email because you follow this work item.",
            "kosong": "(empty)",
            "diubah": "changed",
        },
    },
}

# Nama kolom di aktivitas work item -> label. Kolom yang tidak dikenal tampil
# apa adanya, bukan disembunyikan: lebih baik "estimate_point" daripada hilang.
KOLOM = {
    "id": {
        "name": "Judul",
        "state": "Status",
        "priority": "Prioritas",
        "assignees": "Penanggung jawab",
        "labels": "Label",
        "target_date": "Tenggat",
        "start_date": "Mulai",
        "description": "Deskripsi",
        "parent": "Induk",
        "duplicate": "Duplikat",
        "blocking": "Menghalangi",
        "blocked_by": "Dihalangi oleh",
        "relates_to": "Terkait",
        "link": "Tautan",
        "attachment": "Lampiran",
        "modules": "Modul",
        "estimate_point": "Estimasi",
        "archived_at": "Diarsipkan",
    },
    "en": {
        "name": "Title",
        "state": "State",
        "priority": "Priority",
        "assignees": "Assignees",
        "labels": "Labels",
        "target_date": "Due date",
        "start_date": "Start date",
        "description": "Description",
        "parent": "Parent",
        "duplicate": "Duplicate of",
        "blocking": "Blocking",
        "blocked_by": "Blocked by",
        "relates_to": "Relates to",
        "link": "Link",
        "attachment": "Attachment",
        "modules": "Modules",
        "estimate_point": "Estimate",
        "archived_at": "Archived",
    },
}

PRIORITAS = {
    "id": {"urgent": "Mendesak", "high": "Tinggi", "medium": "Sedang", "low": "Rendah", "none": "Belum diatur"},
    "en": {"urgent": "Urgent", "high": "High", "medium": "Medium", "low": "Low", "none": "None"},
}


class _Aman(dict):
    """`str.format_map` yang membiarkan placeholder tak dikenal apa adanya."""

    def __missing__(self, kunci):
        return "{" + kunci + "}"


def teks(grup, bahasa="id", **nilai) -> dict:
    """Semua teks satu email, sudah diformat. Bahasa tak dikenal = Indonesia."""
    kamus = TEKS[grup].get(bahasa) or TEKS[grup]["id"]
    isian = _Aman(merek=MEREK, **{k: ("" if v is None else v) for k, v in nilai.items()})
    return {kunci: s.format_map(isian) for kunci, s in kamus.items()}
