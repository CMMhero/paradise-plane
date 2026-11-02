# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: akun yang dihapus dari God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Potret identitas akun yang dihapus, supaya bisa dipulihkan dari Trash.

Menghapus akun tidak pernah menghapus baris User: `User.delete()` merambat
CASCADE ke halaman, view, vote, dan perangkat, jadi data orang lain ikut
hilang. Yang terjadi adalah penggosokan: email, nama, dan username diganti
placeholder, akun dinonaktifkan. Semua rujukan (assignee, pembuat, audit,
worklog) tetap utuh dan tampil sebagai "Deleted account".

Sebelum tabel ini ada, penggosokan itu final. Sekarang nilai aslinya disimpan
di sini sampai masa simpan Trash habis atau Super Admin membuangnya permanen;
sesudah itu yang tersisa hanya placeholder.

Sengaja `models.Model` biasa, bukan `BaseModel`: tidak punya `deleted_at`,
jadi sapuan generik `hard_delete` tidak menyentuhnya, dan tidak ikut disaring
manager soft-delete. Masa simpannya diurus eksplisit di `hard_delete`.
"""

import uuid

# Django imports
from django.db import models
from django.utils import timezone

# Domain placeholder email akun terhapus. Satu-satunya definisi: penanda
# `is_deleted` di serializer dan penyaringan daftar member membaca ini.
DOMAIN_AKUN_TERHAPUS = "deleted.local"
NAMA_AKUN_TERHAPUS = "Deleted account"


def email_akun_terhapus(user_id):
    return f"terhapus-{str(user_id)[:8]}@{DOMAIN_AKUN_TERHAPUS}"


def adalah_akun_terhapus(email):
    return bool(email) and email.endswith(f"@{DOMAIN_AKUN_TERHAPUS}")


class AkunTerhapus(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    user = models.OneToOneField("db.User", related_name="akun_terhapus", on_delete=models.CASCADE)
    email = models.CharField(max_length=255)
    username = models.CharField(max_length=128)
    display_name = models.CharField(max_length=255, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    # Dicatat, tapi TIDAK dipulihkan otomatis: memberi Super Admin selalu lewat
    # konfirmasi ketik-ulang di editor member, Trash bukan jalan pintasnya.
    was_super_admin = models.BooleanField(default=False)
    # WorkspaceMember yang AKTIF saat dihapus. Yang memang sudah nonaktif
    # sebelumnya tidak boleh ikut hidup lagi saat dipulihkan.
    workspace_member_ids = models.JSONField(default=list)
    dihapus_pada = models.DateTimeField(default=timezone.now, db_index=True)
    dihapus_oleh = models.ForeignKey(
        "db.User", related_name="+", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        db_table = "akun_terhapus"
        verbose_name = "Akun Terhapus"
        verbose_name_plural = "Akun Terhapus"
        ordering = ("-dihapus_pada",)

    def __str__(self):
        return f"{self.display_name} <{self.email}>"
