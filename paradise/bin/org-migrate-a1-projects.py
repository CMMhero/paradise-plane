# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian A1, buat project sub-divisi dari Org Directory
#
# Jalankan:
#   docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/org-migrate-a1-projects.py
#
# Idempotent: get_or_create semua, aman dijalankan ulang.
# Uji kering dulu:  ORG_APPLY=0 (default)  -> hanya mencetak rencana
# Terapkan:         ORG_APPLY=1
#
# Sumber: Paradise_Perkasa_Org_Directory (1).xlsx, keputusan K1-K11 di
# PP_TaskMgr/05-Task/Rencana Besar — Akses, Log & Trashbin.md
# (tanda pisah di atas bagian dari NAMA BERKAS, jangan diganti koma)
#
# TIDAK menyentuh: project lama (SALES/HRGA/INVQC tetap jadi payung per P2),
# gudang (K7), keanggotaan, maupun peran. Skrip ini HANYA membuat project.

import os

from plane.db.models import Project, ProjectMember, State, User, Workspace
from plane.db.models.state import DEFAULT_STATES

try:
    from plane.db.models import ProjectIdentifier
except ImportError:
    ProjectIdentifier = None

APPLY = os.environ.get("ORG_APPLY") == "1"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")
owner = User.objects.get(email="bintang.ramadhan@paradiseperkasa.com")

# (identifier, nama, catatan)
# Batas identifier = 12 karakter (project.py:76), unik per workspace.
BARU = [
    ("SMT1", "Sales - Team 1", "pecahan SALES"),
    ("SMT2", "Sales - Team 2", "pecahan SALES"),
    ("SMCOO", "Sales Coordinator", "pecahan SALES"),
    ("SMIND", "Sales - Independent", "pecahan SALES"),
    ("SMADM", "Admin Sales", "pecahan SALES"),
    ("INV", "Inventory", "pecahan INVQC"),
    ("QC", "Quality Control", "pecahan INVQC"),
    ("HR", "Human Resources", "pecahan HRGA"),
    ("GA", "General Affairs", "pecahan HRGA"),
    ("LEGAL", "Legal", "pecahan HRGA"),
    # SEC & OPR sengaja tetap dibuat walau anggotanya belum bisa didaftarkan:
    # ketiganya (Security 1, Security 2, Safitri) belum punya email (K5).
    # Strukturnya mengikuti file; anggotanya menyusul begitu email dari IT ada.
    ("SEC", "Security", "pecahan HRGA, anggota menunggu email (K5)"),
    ("OPR", "Operator", "pecahan HRGA, anggota menunggu email (K5)"),
    ("APAR", "AP / AR", "pecahan FIN, sebagian tertunda (K6)"),
    ("ACC", "Accounting", "pecahan FIN, sebagian tertunda (K6)"),
]

print("=" * 68)
print("A1, buat project sub-divisi   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 68)

dibuat = dilewati = 0

for identifier, nama, catatan in BARU:
    ada = Project.objects.filter(workspace=ws, identifier=identifier).first()
    if ada:
        print(f"  ada     {identifier:<7} {nama:<24} (dilewati)")
        dilewati += 1
        continue

    if not APPLY:
        print(f"  BUAT    {identifier:<7} {nama:<24} {catatan}")
        dibuat += 1
        continue

    # network=0 = private. Divisi lain tidak boleh mengintip pekerjaan divisi
    # ini; akses diberikan lewat keanggotaan project (A3).
    p = Project.objects.create(
        workspace=ws,
        identifier=identifier,
        name=nama,
        description=catatan,
        network=0,
        created_by=owner,
    )

    if ProjectIdentifier:
        ProjectIdentifier.objects.get_or_create(
            name=identifier, project=p, defaults={"workspace": ws}
        )

    # State wajib ada, kalau tidak work item tidak bisa dibuat sama sekali.
    if not State.objects.filter(project=p).exists():
        State.objects.bulk_create(
            [State(project=p, workspace=ws, created_by=owner, **s) for s in DEFAULT_STATES]
        )

    # Pembuat project harus jadi anggota, kalau tidak project-nya tidak muncul
    # di daftar siapa pun dan tidak bisa dibuka lagi untuk dikelola.
    ProjectMember.objects.get_or_create(
        project=p, member=owner, workspace=ws, defaults={"role": 20}
    )

    print(f"  DIBUAT  {identifier:<7} {nama:<24} {p.id}")
    dibuat += 1

print("-" * 68)
print(f"  dibuat/akan dibuat : {dibuat}")
print(f"  sudah ada          : {dilewati}")
print(f"  total project aktif: {Project.objects.filter(workspace=ws, deleted_at__isnull=True).count()}")
if not APPLY:
    print("\n  UJI KERING, tidak ada yang ditulis. Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
