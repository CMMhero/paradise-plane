# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Tandai project "rumah" tiap Super Admin
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/seed-superadmin-visibility.py
#
# Uji kering (default): tanpa ORG_APPLY   |   Terapkan: ORG_APPLY=1
# Idempotent: get_or_create.
#
# LATAR BELAKANG
# Super Admin otomatis jadi anggota SEMUA project supaya bisa memantau, lalu
# disaring keluar dari daftar anggota. Semula penyaringan itu berlaku di semua
# project sekaligus, termasuk project tempat orangnya benar-benar bekerja.
# Akibatnya tim IT tak bisa diberi tugas di project IT sendiri: namanya tidak
# pernah muncul di daftar assignee.
#
# Skrip ini mengisi pengecualian: "orang ini anggota ASLI di project ini".
# Di project itu ia tampil normal; di 30 project lain ia tetap tersembunyi.

import os

from plane.db.models import Project, SuperAdminTerlihatDiProject, User
from plane.license.models import InstanceAdmin

APPLY = os.environ.get("ORG_APPLY") == "1"

# Pemetaan orang -> project rumahnya.
# Tim IT (domain itechmandiri.com) + Bintang bekerja di project IT.
# Manajemen bekerja di project MGMT. Keputusan user 2026-08-11: manajemen
# diperlakukan dengan aturan yang sama seperti IT.
RUMAH = {
    "IT": [
        "it.support1@itechmandiri.com",
        "it.support2@itechmandiri.com",
        "it.sap1@itechmandiri.com",
        "it.sap2@itechmandiri.com",
        "it.sap5@itechmandiri.com",
        "it.spc1@itechmandiri.com",
        "it.dev@itechmandiri.com",
        "bintang.ramadhan@paradiseperkasa.com",
    ],
    "MGMT": [
        "henry@paradiseperkasa.com",
        "suarno.radin@paradiseperkasa.com",
        "secre_dir@paradiseperkasa.com",
    ],
}

super_admin_ids = set(InstanceAdmin.objects.filter(deleted_at__isnull=True).values_list("user_id", flat=True))
print(f"Super Admin terdaftar: {len(super_admin_ids)}")
print(f"Mode: {'TERAPKAN' if APPLY else 'UJI KERING (set ORG_APPLY=1 untuk menerapkan)'}")
print()

dibuat = dilewati = 0
tak_ketemu = []

for identifier, emails in RUMAH.items():
    project = Project.objects.filter(identifier=identifier, deleted_at__isnull=True).first()
    if project is None:
        print(f"!! project {identifier} tidak ditemukan, dilewati")
        continue

    print(f"--- {identifier} ({project.name}) ---")
    for email in emails:
        user = User.objects.filter(email=email).first()
        if user is None:
            tak_ketemu.append(email)
            print(f"   !! {email} tidak ada di database")
            continue
        # Hanya masuk akal untuk Super Admin. Orang biasa memang sudah terlihat,
        # jadi barisnya akan jadi sampah yang membingungkan pembaca berikutnya.
        if user.id not in super_admin_ids:
            print(f"   -  {user.display_name} bukan Super Admin, tidak perlu pengecualian")
            continue

        ada = SuperAdminTerlihatDiProject.objects.filter(project=project, member=user).exists()
        if ada:
            dilewati += 1
            print(f"   =  {user.display_name} sudah ditandai")
            continue

        if APPLY:
            SuperAdminTerlihatDiProject.objects.create(
                workspace_id=project.workspace_id, project=project, member=user
            )
        dibuat += 1
        print(f"   +  {user.display_name}")

print()
print(f"Ditandai baru : {dibuat}")
print(f"Sudah ada     : {dilewati}")
if tak_ketemu:
    print(f"Email tak ketemu: {tak_ketemu}")
if not APPLY:
    print("\nUji kering. Tidak ada yang ditulis. Ulangi dengan ORG_APPLY=1.")
