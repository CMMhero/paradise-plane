# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian B1, angkat tim IT jadi Super Admin & sinkronkan aksesnya
#
# Jalankan:
#   docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/org-migrate-b1-superadmin.py
#
# Uji kering (default): tanpa ORG_APPLY   |   Terapkan: ORG_APPLY=1
# Idempotent: get_or_create semua.
#
# Super Admin = instance admin (God Mode) + anggota SEMUA project, tapi
# disembunyikan dari setiap daftar anggota (plane/db/superadmin.py).
# Project baru otomatis ikut lewat signal, skrip ini hanya untuk menyusulkan
# project yang SUDAH ada saat Super Admin diangkat.

import os

from plane.db.models import Project, User
from plane.db.superadmin import sinkronkan_super_admin, super_admin_user_ids
from plane.license.models import Instance, InstanceAdmin

APPLY = os.environ.get("ORG_APPLY") == "1"

# Org Directory menandai TIGA orang sebagai "Super Admin": Henry Leo,
# Vennysia Margaretha, dan Ignatius Warsito. Ignatius belum punya email (K5),
# jadi belum bisa diangkat.
MANAJEMEN = [
    "henry@paradiseperkasa.com",
    "secre_dir@paradiseperkasa.com",
]

# K9: seluruh tim IT. Sengaja bertentangan dengan Org Directory, yang hanya
# menandai Suarno & Fran sebagai Admin, poin 9 diberikan belakangan dan
# menang. Dicatat di sini supaya tidak dikira kekeliruan.
TIM_IT = [
    "suarno.radin@paradiseperkasa.com",
    "it.dev@itechmandiri.com",
    "it.sap1@itechmandiri.com",
    "it.dev1@itechmandiri.com",
    "it.support1@itechmandiri.com",
    "it.sap3@itechmandiri.com",
    "it.spc1@itechmandiri.com",
    "it.sap2@itechmandiri.com",
    "bintang.ramadhan@paradiseperkasa.com",
    "it.support2@itechmandiri.com",
    "it.sap5@itechmandiri.com",
]

instance = Instance.objects.first()
if not instance:
    raise SystemExit("ERROR: instance belum terdaftar, jalankan setup God Mode dulu.")

print("=" * 68)
print("B1, Super Admin   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 68)

sebelum = super_admin_user_ids()
print(f"\nSuper Admin sekarang: {len(sebelum)}")

print("\n1) Angkat jadi instance admin")
tambah = 0
for email in MANAJEMEN + TIM_IT:
    u = User.objects.filter(email=email, is_active=True).first()
    if not u:
        print(f"   ! {email:<40} akun tidak ada / nonaktif, DILEWATI")
        continue
    if InstanceAdmin.objects.filter(instance=instance, user=u).exists():
        print(f"   ada  {email:<40} {u.display_name}")
        continue
    print(f"   +    {email:<40} {u.display_name}")
    tambah += 1
    if APPLY:
        InstanceAdmin.objects.create(instance=instance, user=u, role=20, is_verified=True)

print(f"\n2) Sinkronkan ke {Project.objects.filter(deleted_at__isnull=True).count()} project yang sudah ada")
if APPLY:
    dibuat = sinkronkan_super_admin()
    print(f"   keanggotaan dibuat: {dibuat}")
else:
    print("   (dilewati saat uji kering, butuh instance admin sudah tercatat)")

print("\n" + "-" * 68)
print(f"  diangkat: {tambah} · total Super Admin: {len(super_admin_user_ids())}")
if not APPLY:
    print("  UJI KERING, tidak ada yang ditulis. ORG_APPLY=1 untuk menerapkan.")
