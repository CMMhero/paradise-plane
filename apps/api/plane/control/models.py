# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bidang kendali: catatan tentang PELANGGAN, bukan tentang kerja mereka.

KENAPA ISINYA TIDAK BOLEH BERCAMPUR DENGAN DATA PELANGGAN

Tiap perusahaan berlangganan mendapat instance dan database sendiri. Kalau
catatan langganan ikut tinggal di salah satu database itu, maka pertanyaan
sesederhana "berapa perusahaan yang menunggak" hanya bisa dijawab dengan
membuka database milik pelanggan satu per satu, dan panel pemilik jadi sesuatu
yang harus punya kunci ke seluruh data pelanggan. Itu bukan panel, itu kunci
serep.

Isolasinya TIDAK ditegakkan lewat alias database atau router. Ia datang dari
topologi yang memang sudah dipilih: panel pemilik adalah deployment tersendiri
dengan databasenya sendiri, sama seperti tiap pelanggan. Jadi yang dibutuhkan
cuma satu hal, dan itu ada di `settings/common.py`: aplikasi ini HANYA masuk
INSTALLED_APPS kalau `ENABLE_CONTROL_PLANE=1`. Di instance pelanggan tabel-tabel
di bawah bahkan tidak pernah dibuat.

Model di sini sengaja TIDAK mewarisi `plane.db.models.BaseModel`. BaseModel
menempelkan pelacakan pengguna lewat crum dan mengikat aplikasi ini ke aplikasi
`db` milik penyewa. Bidang kendali adalah konteks yang berbeda, dan konteks yang
berbeda sebaiknya tidak berbagi kelas dasar hanya demi menghemat empat kolom.
"""

import hashlib
import secrets
import uuid

from django.db import models


def _uuid():
    return uuid.uuid4()


class Waktu(models.Model):
    id = models.UUIDField(primary_key=True, default=_uuid, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(Waktu):
    """Satu perusahaan pelanggan. Baris ini lahir sebelum instance-nya ada."""

    class Status(models.TextChoices):
        TRIAL = "TRIAL", "Masa percobaan"
        ACTIVE = "ACTIVE", "Aktif"
        PAST_DUE = "PAST_DUE", "Menunggak"
        SUSPENDED = "SUSPENDED", "Ditangguhkan"
        CHURNED = "CHURNED", "Berhenti"

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64, unique=True)
    contact_email = models.EmailField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.TRIAL)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "control_companies"
        ordering = ("name",)

    def __str__(self):
        return self.slug


class Subscription(Waktu):
    """Tingkatan yang BERLAKU untuk sebuah perusahaan, beserta masa berlakunya.

    Riwayat disimpan sebagai baris, bukan sebagai kolom yang ditimpa. Pertanyaan
    "sejak kapan mereka Pro" dan "kapan mereka turun kelas" adalah pertanyaan
    penagihan yang pasti ditanyakan, dan kolom yang ditimpa tidak bisa
    menjawabnya.
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="subscriptions")
    tier = models.CharField(max_length=32)
    started_at = models.DateTimeField()
    # NULL berarti masih berjalan. Hanya boleh ada satu yang NULL per perusahaan,
    # dan itu ditegakkan constraint di bawah, bukan oleh kesopanan pemanggil.
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "control_subscriptions"
        ordering = ("-started_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                condition=models.Q(ended_at__isnull=True),
                name="satu_langganan_berjalan_per_perusahaan",
            )
        ]

    def __str__(self):
        return f"{self.company.slug}: {self.tier}"


class TenantInstance(Waktu):
    """Satu deployment milik satu perusahaan.

    RAHASIANYA DISIMPAN SEBAGAI SIDIK, BUKAN APA ADANYA. Bidang kendali yang
    menyimpan rahasia seluruh instance dalam bentuk terbaca adalah satu kebocoran
    database dari menjadi kunci ke semua pelanggan sekaligus. Nilai aslinya cuma
    ada sekali, saat dibuat, dan itu memang satu-satunya saat ia dibutuhkan
    manusia.
    """

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="instances")
    subdomain = models.CharField(max_length=63, unique=True)
    api_base_url = models.URLField(blank=True)
    secret_hash = models.CharField(max_length=64, db_index=True)
    version = models.CharField(max_length=64, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "control_tenant_instances"
        ordering = ("subdomain",)

    def __str__(self):
        return self.subdomain

    @staticmethod
    def sidik(rahasia):
        return hashlib.sha256(rahasia.encode("utf-8")).hexdigest()

    @classmethod
    def terbitkan_rahasia(cls):
        """Kembalikan (rahasia_asli, sidiknya). Yang asli TIDAK pernah disimpan."""
        rahasia = secrets.token_urlsafe(32)
        return rahasia, cls.sidik(rahasia)


class UsageSnapshot(Waktu):
    """Satu laporan pemakaian dari sebuah instance.

    Instance yang MENDORONG, bukan bidang kendali yang mengintip. Kalau bidang
    kendali yang menarik, ia harus punya kredensial baca ke tiap database
    pelanggan, dan seluruh alasan memisahkan basis data jadi hilang.

    Disimpan sebagai deret, bukan satu baris yang ditimpa, karena yang dibutuhkan
    penagihan dan perencanaan kapasitas adalah kecenderungan, bukan angka hari
    ini.
    """

    instance = models.ForeignKey(
        TenantInstance, on_delete=models.CASCADE, related_name="usage_snapshots"
    )
    taken_at = models.DateTimeField()
    workspaces = models.IntegerField(default=0)
    members = models.IntegerField(default=0)
    storage_bytes = models.BigIntegerField(default=0)

    class Meta:
        db_table = "control_usage_snapshots"
        ordering = ("-taken_at",)
        indexes = [models.Index(fields=["instance", "-taken_at"], name="usage_instance_time_idx")]

    def __str__(self):
        return f"{self.instance.subdomain} @ {self.taken_at:%Y-%m-%d}"


class Invoice(Waktu):
    """Satu tagihan untuk satu periode langganan.

    KENAPA JUMLAHNYA DISIMPAN DI SINI, BUKAN DIHITUNG ULANG SAAT DIBUTUHKAN

    Harga berubah. Kalau jumlah tagihan dihitung ulang dari tabel harga setiap
    kali dibaca, tagihan tahun lalu akan berubah angkanya begitu harga naik, dan
    catatan keuangan yang berubah sendiri bukan catatan keuangan.

    `external_id` adalah pengenal MILIK KITA yang dikirim ke penyedia pembayaran,
    dan itu yang dipakai mencocokkan webhook. Pengenal milik penyedia disimpan
    terpisah di `provider_id`. Mencampur keduanya membuat pindah penyedia berarti
    kehilangan jejak tagihan lama.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Menunggu pembayaran"
        PAID = "PAID", "Lunas"
        EXPIRED = "EXPIRED", "Kedaluwarsa"
        VOID = "VOID", "Dibatalkan"

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(
        Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name="invoices"
    )
    external_id = models.CharField(max_length=128, unique=True)
    provider = models.CharField(max_length=32, default="xendit")
    provider_id = models.CharField(max_length=128, blank=True)
    invoice_url = models.URLField(blank=True)

    tier = models.CharField(max_length=32)
    # Rupiah bulat. IDR tidak punya pecahan, jadi menyimpannya sebagai desimal
    # hanya menambah tempat bagi galat pembulatan tanpa satu pun manfaat.
    amount = models.BigIntegerField()
    currency = models.CharField(max_length=8, default="IDR")

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    due_at = models.DateTimeField()
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_amount = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "control_invoices"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["company", "-created_at"], name="invoice_company_time_idx")]

    def __str__(self):
        return f"{self.company.slug} {self.tier} {self.amount} {self.status}"
