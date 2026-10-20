# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian A3, keanggotaan & peran project
#
# Jalankan:
#   docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/org-migrate-a3-members.py
#
# Uji kering (default): tanpa ORG_APPLY   |   Terapkan: ORG_APPLY=1
#
# Rencana ini DIBEKUKAN dari Org Directory xlsx pada 2026-07-31, bukan dihitung
# ulang saat jalan, supaya yang dieksekusi persis yang sudah ditinjau.
#
# Aturan yang sudah dipatuhi saat menyusunnya:
#   P2  SALES / HRGA / INVQC tetap PAYUNG, anggotanya tidak dikeluarkan
#   K4  Orang yang tidak ada di file TIDAK dikeluarkan dari mana pun
#   K5  7 orang tanpa email dilewati (Ignatius Warsito, Security 1&2, Safitri,
#       Dani, Eko Santoso, Slamet Supriyadi)
#   K6  Akun email-bersama tetap ditempatkan, pemisahan orangnya ditunda
#   K10 HANYA peran project yang disentuh. Peran WORKSPACE sengaja TIDAK diubah
#       sampai B1 (Super Admin tersembunyi) jadi, menurunkan workspace Admin
#       sekarang akan membuat tidak ada seorang pun bisa mengelola workspace.

import os

from django.db import transaction

from plane.db.models import (
    Project, ProjectMember, ProjectUserProperty, User, Workspace,
)

APPLY = os.environ.get("ORG_APPLY") == "1"
ws = Workspace.objects.get(slug="pt-paradise-perkasa")

TAMBAH = [
    ("ACC", "andy.wijaya@paradiseperkasa.com", 20),
    ("ACC", "aristyo@paradiseperkasa.com", 20),
    ("ACC", "adminaccounting1@paradiseperkasa.com", 15),
    ("ACC", "kasir@paradiseperkasa.com", 15),
    ("ACC", "acc.stf1@paradiseperkasa.com", 15),
    ("APAR", "apteam@paradiseperkasa.com", 15),
    ("APAR", "arteam@paradiseperkasa.com", 15),
    ("GA", "ga.spv@paradiseperkasa.com", 20),
    ("GA", "ga.stf1@paradiseperkasa.com", 15),
    ("HR", "hr.spc@paradiseperkasa.com", 20),
    ("HR", "hr.stf@paradiseperkasa.com", 15),
    ("INV", "inv.stf1@paradiseperkasa.com", 20),
    ("INV", "inv.stf2@paradiseperkasa.com", 15),
    ("IT", "it.dev1@itechmandiri.com", 15),
    ("IT", "it.sap2@itechmandiri.com", 15),
    ("LEGAL", "lgl.spv@paradiseperkasa.com", 20),
    ("LEGAL", "lgl.stf2@paradiseperkasa.com", 15),
    ("LEGAL", "lgl.stf1@paradiseperkasa.com", 15),
    ("MGMT", "tan.andy@paradiseperkasa.com", 20),
    ("MGMT", "yan.tandi@paradiseperkasa.com", 20),
    ("MKT", "mkt.stf1@paradiseperkasa.com", 15),
    ("PROC", "dewi.fransisca@paradiseperkasa.com", 15),
    ("QC", "qc.stf2@paradiseperkasa.com", 15),
    ("QC", "qc.adm1@paradiseperkasa.com", 15),
    ("SMADM", "sls.adm7@paradiseperkasa.com", 15),
    ("SMADM", "sls.adm2@paradiseperkasa.com", 15),
    ("SMADM", "sls.adm1@paradiseperkasa.com", 15),
    ("SMCOO", "alex@paradiseperkasa.com", 20),
    ("SMCOO", "sls.coo2@paradiseperkasa.com", 15),
    ("SMCOO", "sls.coo1@paradiseperkasa.com", 15),
    ("SMCOO", "sls.coo12@paradiseperkasa.com", 15),
    ("SMCOO", "sls.coo3@paradiseperkasa.com", 15),
    ("SMCOO", "sls.coo9@paradiseperkasa.com", 15),
    ("SMCOO", "sls.coo6@paradiseperkasa.com", 15),
    ("SMIND", "michel@paradiseperkasa.com", 15),
    ("SMT1", "irvan@paradiseperkasa.com", 20),
    ("SMT1", "vince@paradiseperkasa.com", 15),
    ("SMT1", "ricky.sepryanto@paradiseperkasa.com", 15),
    ("SMT1", "kevin.muster@paradiseperkasa.com", 15),
    ("SMT1", "winston.cahya@paradiseperkasa.com", 15),
    ("SMT1", "evauliartha@paradiseperkasa.com", 15),
    ("SMT2", "manroe@paradiseperkasa.com", 20),
    ("SMT2", "sls.eng2@paradiseperkasa.com", 15),
    ("SMT2", "kurniawan@paradiseperkasa.com", 15),
    ("SMT2", "sls.eng1@paradiseperkasa.com", 15),
]

UBAH = [
    ("FIN", "fin.spv@paradiseperkasa.com", 15, 20),
    ("IT", "it.dev@itechmandiri.com", 15, 20),
    ("IT", "bintang.ramadhan@paradiseperkasa.com", 20, 15),
    ("LOGI", "scm.stf1@paradiseperkasa.com", 15, 20),
    ("SHIP", "shp.spv@paradiseperkasa.com", 15, 20),
]

KELUAR = [
    ("FIN", "litakomalasari@paradiseperkasa.com"),
    ("FIN", "andy.wijaya@paradiseperkasa.com"),
    ("FIN", "apteam@paradiseperkasa.com"),
    ("FIN", "arteam@paradiseperkasa.com"),
    ("FIN", "aristyo@paradiseperkasa.com"),
    ("FIN", "adminaccounting1@paradiseperkasa.com"),
    ("FIN", "acc.stf1@paradiseperkasa.com"),
    ("FIN", "bintang.ramadhan@paradiseperkasa.com"),
    ("MKT", "bintang.ramadhan@paradiseperkasa.com"),
]

print("=" * 70)
print("A3, keanggotaan & peran   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

proj = {p.identifier: p for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}
users = {u.email.lower(): u for u in User.objects.filter(is_active=True, is_bot=False)}
n_tambah = n_ubah = n_keluar = n_lewat = 0

with transaction.atomic():
    print("\n1) Tambah anggota")
    for ident, email, role in TAMBAH:
        p, u = proj.get(ident), users.get(email)
        if not p or not u:
            print(f"   ! lewat {ident:<7} {email}  (project/user tidak ada)")
            n_lewat += 1
            continue
        pm = ProjectMember.objects.filter(project=p, member=u, deleted_at__isnull=True).first()
        if pm:
            print(f"   ada    {ident:<7} {email}")
            continue
        n_tambah += 1
        print(f"   +      {ident:<7} {email:<40} {'Admin' if role == 20 else 'Member'}")
        if APPLY:
            ProjectMember.objects.create(project=p, member=u, workspace=ws, role=role)
            ProjectUserProperty.objects.get_or_create(project=p, workspace=ws, user=u)

    print("\n2) Ubah peran")
    for ident, email, lama, baru in UBAH:
        p, u = proj.get(ident), users.get(email)
        pm = ProjectMember.objects.filter(project=p, member=u, deleted_at__isnull=True).first() if p and u else None
        if not pm:
            print(f"   ! lewat {ident:<7} {email}  (bukan anggota)")
            n_lewat += 1
            continue
        if pm.role == baru:
            print(f"   ada    {ident:<7} {email:<40} sudah {baru}")
            continue
        n_ubah += 1
        print(f"   ~      {ident:<7} {email:<40} {pm.role} -> {baru}")
        if APPLY:
            pm.role = baru
            pm.save(update_fields=["role"])

    print("\n3) Pindah keluar (FIN/MKT menyesuaikan file)")
    for ident, email in KELUAR:
        p, u = proj.get(ident), users.get(email)
        pm = ProjectMember.objects.filter(project=p, member=u, deleted_at__isnull=True).first() if p and u else None
        if not pm:
            print(f"   ada    {ident:<7} {email:<40} sudah keluar")
            continue
        n_keluar += 1
        print(f"   -      {ident:<7} {email}")
        if APPLY:
            # Soft delete (konvensi Plane), bisa dipulihkan kalau salah.
            pm.delete()

    if not APPLY:
        print("\n  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 70)
print(f"  tambah {n_tambah} · ubah peran {n_ubah} · keluar {n_keluar} · dilewati {n_lewat}")
print(f"  total keanggotaan aktif: {ProjectMember.objects.filter(deleted_at__isnull=True).count()}")
if not APPLY:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
