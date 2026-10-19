# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Folder General + membuka folder yang terkunci
#
# Jalankan:
#   docker compose exec -T api python manage.py shell < paradise/bin/wiki-general.py
#
# Uji kering (default): tanpa WIKI_GENERAL_APPLY   |   Terapkan: WIKI_GENERAL_APPLY=1
#
# DUA HAL YANG DIKERJAKAN
#
# 1. Membuat folder General di Wiki, yaitu folder yang SIAPA PUN boleh mengisi.
#    Tidak ada mode "bebas" di model, dan memang tidak perlu ada: seluruh
#    karyawan adalah ProjectMember project Wiki, jadi menunjuk project Wiki
#    SENDIRI sebagai divisi pemilik berarti "semua anggota Wiki boleh
#    mengunggah", dievaluasi resolver yang sama tanpa satu pun cabang baru.
#
# 2. Membuka folder yang terlanjur TERKUNCI. Folder teratas tanpa satu pun baris
#    WikiFolderAccess bukan berarti bebas, melainkan tidak bisa disentuh siapa
#    pun kecuali admin project. Itu kebalikan dari dugaan orang, dan
#    `[DEMO] Contoh Lampiran Berbagai Tipe` sedang dalam keadaan itu.
#
# Idempoten: dijalankan ulang tidak menambah folder kedua dan tidak menumpuk
# baris ACL.

import os

from django.db import transaction

from plane.db.models import (
    Page,
    Project,
    ProjectMember,
    ProjectPage,
    WikiFolderAccess,
    WikiGovernedProject,
    Workspace,
)

APPLY = os.environ.get("WIKI_GENERAL_APPLY") == "1"

WORKSPACE = "pt-paradise-perkasa"
WIKI_IDENTIFIER = "WIKI"

NAMA_GENERAL = "📢 General"
KETERANGAN_GENERAL = (
    "<p>Folder terbuka. Semua karyawan boleh menaruh materi di sini. "
    "Materi yang sudah diunggah tetap hanya bisa diubah atau dihapus oleh "
    "pengunggahnya sendiri atau Super Admin.</p>"
)

# Folder yang terkunci dan memang sebaiknya dibuka untuk semua orang.
# Dicocokkan dengan `startswith`, supaya emoji atau spasi tambahan tidak
# membuat skrip ini diam-diam tidak melakukan apa-apa.
BUKA_UNTUK_SEMUA = ["[DEMO] Contoh Lampiran Berbagai Tipe"]

print("=" * 70)
print("Folder General Wiki   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

ws = Workspace.objects.get(slug=WORKSPACE)
wiki = Project.objects.get(workspace=ws, identifier=WIKI_IDENTIFIER, deleted_at__isnull=True)

if not WikiGovernedProject.objects.filter(project=wiki, deleted_at__isnull=True).exists():
    print("\n! Governance ACL folder BELUM aktif di project Wiki.")
    print("  Jalankan paradise/bin/seed-wiki-access.py lebih dulu, kalau tidak")
    print("  folder General ini tidak akan berarti apa-apa.")

# Pemilik halaman baru: admin project Wiki yang pertama, supaya folder ini tidak
# lahir tanpa pemilik. Kepemilikan halaman hanya menentukan siapa yang boleh
# mengganti nama dan menghapusnya, bukan siapa yang boleh mengisi.
# Diutamakan admin project yang BUKAN Super Admin. Super Admin punya baris
# role=20 di semua project secara otomatis, jadi mengurutkan begitu saja akan
# menjadikan folder ini milik orang yang tidak pernah mengurus Wiki.
from plane.db.superadmin import super_admin_user_ids  # noqa: E402

_admin = ProjectMember.objects.filter(project=wiki, role=20, is_active=True).select_related("member")
pemilik = (
    _admin.exclude(member_id__in=super_admin_user_ids()).order_by("created_at").first()
    or _admin.order_by("created_at").first()
)
if pemilik is None:
    raise SystemExit("Tidak ada admin project Wiki. Tidak bisa menentukan pemilik folder.")
print(f"\nPemilik folder baru: {pemilik.member.email}")

with transaction.atomic():
    print("\n1) Folder General")
    general = Page.objects.filter(
        projects=wiki, parent__isnull=True, name=NAMA_GENERAL, deleted_at__isnull=True
    ).first()

    if general:
        print(f"   ada    {NAMA_GENERAL}")
    else:
        print(f"   +      {NAMA_GENERAL}")
        general = Page.objects.create(
            name=NAMA_GENERAL,
            workspace=ws,
            owned_by=pemilik.member,
            created_by=pemilik.member,
            access=0,
            description_html=KETERANGAN_GENERAL,
        )
        ProjectPage.objects.create(
            page=general, project=wiki, workspace=ws, created_by=pemilik.member
        )

    print("\n2) Buka folder untuk semua karyawan")
    target = [general]
    for nama in BUKA_UNTUK_SEMUA:
        f = Page.objects.filter(
            projects=wiki, parent__isnull=True, name__startswith=nama, deleted_at__isnull=True
        ).first()
        if f is None:
            print(f"   ! lewat  {nama}  (folder tidak ada)")
            continue
        target.append(f)

    n_tambah = 0
    for f in target:
        sudah = WikiFolderAccess.objects.filter(
            folder=f, project=wiki, division=wiki, deleted_at__isnull=True
        ).exists()
        pemilik_lain = list(
            WikiFolderAccess.objects.filter(folder=f, project=wiki, deleted_at__isnull=True)
            .exclude(division=wiki)
            .values_list("division__identifier", flat=True)
        )
        catatan = f" (pemilik lain tetap: {' '.join(sorted(pemilik_lain))})" if pemilik_lain else ""
        if sudah:
            print(f"   =      {f.name}  sudah terbuka{catatan}")
            continue
        print(f"   +      {f.name}  dibuka untuk semua{catatan}")
        n_tambah += 1
        if APPLY:
            WikiFolderAccess.objects.create(folder=f, division=wiki, project=wiki, workspace=ws)

    # Uji kering tidak menulis apa pun, jadi tabel di bawah HARUS memproyeksikan
    # hasilnya, bukan membaca ulang keadaan lama. Laporan berjudul "sesudah"
    # yang menampilkan "sebelum" adalah laporan yang menyesatkan.
    akan_dibuka = {f.id for f in target}
    print("\n3) Keadaan seluruh folder teratas sesudah ini")
    for f in Page.objects.filter(
        projects=wiki, parent__isnull=True, deleted_at__isnull=True
    ).order_by("name"):
        divisi = sorted(
            WikiFolderAccess.objects.filter(
                folder=f, project=wiki, deleted_at__isnull=True
            ).values_list("division__identifier", flat=True)
        )
        if wiki.identifier in divisi or f.id in akan_dibuka:
            label = "TERBUKA untuk semua"
        elif divisi:
            label = " ".join(divisi)
        else:
            label = "TERKUNCI, admin project saja"
        print(f"      {f.name[:38]:<40} {label}")

    if not APPLY:
        print("\n  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 70)
print(f"  folder dibuka: {n_tambah}")
if not APPLY:
    print("  Jalankan dengan WIKI_GENERAL_APPLY=1 untuk menerapkan.")
