# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapkan satu pelanggan baru: catatan di bidang kendali + berkas rahasianya.

    python manage.py provision_tenant "PT Acme" --subdomain acme --tier PRO \
        --email admin@acme.co.id --out /srv/tenants/acme.env

Dijalankan di deployment PEMILIK, bukan di instance pelanggan. Ia menuntut
`ENABLE_CONTROL_PLANE=1`.

APA YANG DIKERJAKAN DAN APA YANG SENGAJA TIDAK

Yang dikerjakan adalah bagian yang deterministik dan tidak tergantung mesin mana
pun: membuat perusahaan, langganan, dan catatan instance-nya; menerbitkan
rahasia denyut; serta menuliskan nilai-nilai yang BERBEDA per pelanggan berikut
sandi yang dibangkitkan segar.

Yang TIDAK dikerjakan adalah menyalakan containernya, membuat rekaman DNS, dan
menerbitkan sertifikat. Ketiganya bergantung pada VPS yang belum ada, dan skrip
yang menebak bentuk mesin yang belum pernah dilihat siapa pun akan salah di
detail yang hanya bisa ditemukan dengan menjalankannya. Yang dicetak perintah
ini adalah langkah berikutnya, bukan tebakan tentang mesinnya.

Bedanya nyata: tanpa perintah ini, menyiapkan pelanggan berarti seseorang
menyunting sembilan berkas .env dengan tangan pada jam dua pagi, membangkitkan
sandi sendiri, dan berharap tidak ada yang tertukar.

RAHASIA DENYUT DICETAK SEKALI, DAN HANYA SEKALI

Yang tersimpan di bidang kendali adalah sidik SHA-256-nya. Kalau nilainya hilang
sebelum sempat dipasang di instance, tidak ada yang bisa memulihkannya, dan
jalan satu-satunya adalah menerbitkan yang baru. Itu memang perilaku yang
diinginkan.
"""

import secrets
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import get_random_secret_key
from django.utils import timezone
from django.utils.text import slugify

from plane.utils.plan_limits import BATAS_TINGKATAN


class Command(BaseCommand):
    help = "Daftarkan pelanggan baru di bidang kendali dan hasilkan berkas rahasianya"

    def add_arguments(self, parser):
        parser.add_argument("nama", help='Nama perusahaan, mis. "PT Acme"')
        parser.add_argument("--subdomain", required=True)
        parser.add_argument("--email", required=True, help="Surel kontak pelanggan")
        parser.add_argument("--tier", default="PRO", choices=sorted(BATAS_TINGKATAN))
        parser.add_argument(
            "--control-url",
            default="",
            help="Alamat bidang kendali yang akan dihubungi instance, mis. https://panel.nomaden.id",
        )
        parser.add_argument("--out", required=True, help="Berkas env yang akan ditulis")
        parser.add_argument(
            "--base-domain",
            default="nomaden.id",
            help="Domain induk tempat subdomain pelanggan digantung",
        )

    def handle(self, *args, **opsi):
        if not getattr(settings, "ENABLE_CONTROL_PLANE", False):
            raise CommandError(
                "ENABLE_CONTROL_PLANE tidak menyala. Perintah ini dijalankan di "
                "deployment pemilik, bukan di instance pelanggan."
            )

        from plane.control.models import Company, Subscription, TenantInstance

        subdomain = opsi["subdomain"].strip().lower()
        slug = slugify(subdomain)
        tujuan = Path(opsi["out"])

        if tujuan.exists():
            # Menimpa berkas rahasia adalah cara kehilangan rahasia yang masih
            # dipakai instance yang sedang hidup.
            raise CommandError(f"BERHENTI. {tujuan} sudah ada, dan berkas rahasia tidak ditimpa.")

        # Menolak menulis rahasia ke dalam pohon kerja git mana pun.
        #
        # `.gitignore` sudah memuat polanya, tapi .gitignore adalah janji yang
        # bisa dilanggar satu `git add -f`, dan riwayat repo ini sudah pernah
        # dicermin ke tempat lain. Penjaga yang berjalan mengalahkan penjaga yang
        # tertulis. Ditelusuri ke atas karena `--out` bisa menunjuk ke subfolder
        # mana pun di dalam repo.
        for induk in [tujuan.parent, *tujuan.parent.parents]:
            if (induk / ".git").exists():
                raise CommandError(
                    f"BERHENTI. {tujuan} berada di dalam pohon kerja git ({induk}). "
                    "Berkas ini berisi sandi database, SECRET_KEY, dan rahasia denyut "
                    "dalam bentuk terbaca. Tulis ke luar repo."
                )
        if TenantInstance.objects.filter(subdomain=subdomain).exists():
            raise CommandError(f"BERHENTI. Subdomain '{subdomain}' sudah dipakai instance lain.")

        perusahaan, dibuat = Company.objects.get_or_create(
            slug=slug,
            defaults={
                "name": opsi["nama"],
                "contact_email": opsi["email"],
                "status": Company.Status.TRIAL,
            },
        )

        berjalan = Subscription.objects.filter(
            company=perusahaan, ended_at__isnull=True
        ).first()
        if berjalan is None:
            Subscription.objects.create(
                company=perusahaan, tier=opsi["tier"], started_at=timezone.now()
            )

        rahasia, sidik = TenantInstance.terbitkan_rahasia()
        TenantInstance.objects.create(
            company=perusahaan,
            subdomain=subdomain,
            api_base_url=f"https://{subdomain}.{opsi['base_domain']}",
            secret_hash=sidik,
        )

        # Sandi database dibangkitkan di sini, bukan diminta dari operator.
        # Sandi yang diketik manusia pada jam dua pagi adalah sandi yang dipakai
        # ulang di pelanggan berikutnya.
        sandi_db = secrets.token_urlsafe(24)
        nama_db = f"plane_{slug.replace('-', '_')}"
        alamat = f"https://{subdomain}.{opsi['base_domain']}"

        isi = f"""# Nilai KHUSUS pelanggan '{perusahaan.name}' ({subdomain}).
# Dibangkitkan {timezone.now():%Y-%m-%d %H:%M} oleh `manage.py provision_tenant`.
#
# Berkas ini BUKAN .env yang utuh. Ia hanya berisi nilai yang berbeda dari satu
# pelanggan ke pelanggan lain, dan ditumpangkan di atas .env.example. Menuliskan
# seluruh .env di sini akan membuat tiap pelanggan membawa salinan konfigurasi
# yang tidak pernah ikut diperbarui saat contohnya berubah.
#
# JANGAN commit berkas ini.

SECRET_KEY="{get_random_secret_key()}"

POSTGRES_DB="{nama_db}"
POSTGRES_USER="{nama_db}"
POSTGRES_PASSWORD="{sandi_db}"

WEB_URL="{alamat}"
ADMIN_BASE_URL="{alamat}/god-mode"
CORS_ALLOWED_ORIGINS="{alamat}"

# Instance pelanggan TIDAK pernah menjalankan bidang kendali.
ENABLE_CONTROL_PLANE=0

CONTROL_PLANE_URL="{opsi['control_url']}"
CONTROL_PLANE_SECRET="{rahasia}"
"""
        tujuan.parent.mkdir(parents=True, exist_ok=True)
        tujuan.write_text(isi, encoding="utf-8")
        try:
            tujuan.chmod(0o600)
        except OSError:
            # Windows dan sebagian volume terpasang tidak mendukungnya. Bukan
            # alasan menggagalkan, tapi cukup alasan untuk mengatakannya.
            self.stdout.write(self.style.WARNING("  Izin berkas tidak bisa disetel 600."))

        self.stdout.write("=" * 70)
        self.stdout.write(f"Perusahaan  : {perusahaan.name} ({perusahaan.slug})")
        self.stdout.write(f"              {'BARU' if dibuat else 'sudah ada, dipakai ulang'}")
        self.stdout.write(f"Tingkatan   : {opsi['tier']}")
        self.stdout.write(f"Subdomain   : {subdomain}.{opsi['base_domain']}")
        self.stdout.write(f"Berkas env  : {tujuan}")
        self.stdout.write("=" * 70)
        if not opsi["control_url"]:
            self.stdout.write(
                self.style.WARNING(
                    "CONTROL_PLANE_URL kosong. Denyut TIDAK akan berjalan sampai diisi, "
                    "jadi tingkatan pelanggan ini tidak akan pernah diperbarui dari pusat."
                )
            )
        self.stdout.write("")
        self.stdout.write("Langkah berikutnya, dan ketiganya butuh mesin yang belum tentu ada:")
        self.stdout.write(f"  1. Buat database '{nama_db}' beserta penggunanya.")
        self.stdout.write(f"  2. Arahkan {subdomain}.{opsi['base_domain']} ke host, lalu terbitkan sertifikatnya.")
        self.stdout.write("  3. Nyalakan tumpukannya dengan .env.example ditimpa berkas di atas.")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                "Rahasia denyut ada DI DALAM berkas itu dan tidak tersimpan di mana pun "
                "selain sebagai sidiknya. Kalau berkas itu hilang, terbitkan instance baru."
            )
        )
