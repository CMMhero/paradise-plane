# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models

# Module imports
from .base import BaseModel


class WorkspacePlan(BaseModel):
    """Tingkatan langganan sebuah workspace, beserta keadaan tidurnya.

    KENAPA MENEMPEL DI WORKSPACE, BUKAN DI INSTANCE

    Ada tiga topologi yang harus dilayani satu jalur penegakan yang sama:

        kolam gratis       banyak Workspace dalam satu deployment
        instance berbayar  satu Workspace, tingkatannya disetel bidang kendali
        pasang sendiri     tingkatannya disetel berkas lisensi

    `Instance` adalah singleton (`Instance.objects.first()` dipakai di mana-mana
    di `plane/license/`). Menempelkan tingkatan di sana akan merusak kolam gratis
    seketika: satu Instance untuk ribuan pemakai gratis berarti satu tingkatan
    untuk semuanya, dan penegakan terpaksa lahir dua kali dengan aturan kembar
    yang cepat atau lambat berbeda pendapat.

    Menempel di Workspace juga membuat naik kelas jadi PEMINDAHAN DATA, bukan
    penulisan ulang: satu workspace gratis yang berlangganan tinggal dipindahkan
    ke instance barunya, membawa barisnya.

    BARIS INI BOLEH TIDAK ADA. Workspace tanpa baris dianggap `FREE`, lihat
    `plane.utils.plan_limits.plan_for`. Jadi tidak ada backfill yang wajib, dan
    instance pasang-sendiri yang tidak peduli tingkatan tetap jalan apa adanya.
    """

    class Tier(models.TextChoices):
        FREE = "FREE", "Gratis"
        PRO = "PRO", "Pro"
        EXPERT = "EXPERT", "Expert"
        ENTERPRISE = "ENTERPRISE", "Enterprise"

    workspace = models.ForeignKey(
        "db.Workspace", related_name="plan", on_delete=models.CASCADE
    )
    tier = models.CharField(max_length=32, choices=Tier.choices, default=Tier.FREE)

    # Batas per baris. NULL berarti "pakai angka bawaan tingkatannya", dan angka
    # bawaan itu hidup di `plane.utils.plan_limits.BATAS_TINGKATAN`, bukan
    # disalin ke tiap baris. Membiarkannya NULL berarti mengubah kuota Pro cukup
    # satu tempat, bukan migrasi data. Kolom ini ada demi Enterprise, yang di
    # rencana produk memang "khusus" dan dinegosiasikan satu per satu.
    max_members = models.IntegerField(null=True, blank=True)
    max_storage_bytes = models.BigIntegerField(null=True, blank=True)
    max_workspaces_per_owner = models.IntegerField(null=True, blank=True)

    # --- Keadaan tidur -------------------------------------------------------
    #
    # Empat kolom, bukan satu kolom status, karena yang dibutuhkan operator
    # bukan "sekarang di tahap mana" melainkan "kapan tiap tahap terjadi".
    # Tanggal bisa menjawab keduanya, status hanya menjawab yang pertama.
    last_activity_at = models.DateTimeField(null=True, blank=True)
    dormant_warned_at = models.DateTimeField(null=True, blank=True)
    uploads_frozen_at = models.DateTimeField(null=True, blank=True)
    # Ditandai, TIDAK dieksekusi. Menghapus data pelanggan lewat timer adalah
    # tindakan tak bisa dibatalkan yang tidak pantas dijalankan tanpa manusia.
    pending_deletion_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Menyertakan deleted_at, bukan OneToOneField. OneToOneField meng-unique-kan
        # workspace_id saja dan mengabaikan soft-delete, jadi sekali baris ini
        # dihapus lunak, membuat yang baru selalu IntegrityError. Pola yang sama
        # dipakai WikiGovernedProject, dan alasannya sudah terbukti di sana.
        unique_together = ["workspace", "deleted_at"]
        verbose_name = "Workspace Plan"
        verbose_name_plural = "Workspace Plans"
        db_table = "workspace_plans"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.workspace.slug}: {self.tier}"
