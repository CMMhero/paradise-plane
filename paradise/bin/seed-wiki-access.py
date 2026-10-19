# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Pemilik folder Wiki, dibekukan jadi kode
#
# Jalankan:
#   docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/seed-wiki-access.py
#
# Uji kering (default): tanpa WIKI_ACCESS_APPLY   |   Terapkan: WIKI_ACCESS_APPLY=1
#
# KENAPA BERKAS INI ADA
#
# Sampai 21 Agustus 2026, satu-satunya salinan pemetaan "folder Wiki ini milik
# divisi mana" ada di tabel `wiki_folder_access` di database produksi. Ke-16
# barisnya diklik satu per satu lewat UI dan tidak pernah ditulis di mana pun.
# `seed-wiki.py` tidak menyentuh governance maupun ACL sama sekali. Jadi kalau
# database di-restore dari cadangan yang lebih tua, seluruh aturan siapa boleh
# mengunggah ke folder mana hilang tanpa jejak, dan Wiki langsung terkunci untuk
# semua orang kecuali admin (folder tanpa pemilik bukan berarti bebas).
#
# Angka di bawah ini DIBEKUKAN dari produksi pada 21 Agustus 2026, bukan
# dihitung ulang saat jalan, supaya yang dieksekusi persis yang sudah ditinjau.
#
# SEMANTIKNYA REPLACE, SAMA DENGAN ENDPOINT PUT
#
# Daftar divisi untuk sebuah folder adalah KEADAAN AKHIR yang diinginkan, bukan
# tambahan. Divisi yang ada di database tapi tidak ada di sini akan dicabut.
# Ini disengaja: kalau dua sumber kebenaran boleh berbeda, yang menang adalah
# yang paling terakhir diklik orang, dan itu bukan sumber kebenaran namanya.
#
# Folder yang TIDAK disebut di sini sama sekali tidak disentuh.

import os

from django.db import transaction

from plane.db.models import (
    Page,
    Project,
    WikiFolderAccess,
    WikiGovernedProject,
    Workspace,
)

APPLY = os.environ.get("WIKI_ACCESS_APPLY") == "1"

WORKSPACE = "pt-paradise-perkasa"
WIKI_IDENTIFIER = "WIKI"

# Nama folder tepat seperti di judul halaman, termasuk emoji-nya. Judul halaman
# hidup di Yjs dan didorong balik oleh server Live, jadi mengganti nama folder
# lewat SQL akan terbalik sendiri; kalau nama di bawah tidak lagi cocok, ganti
# namanya lewat editor DULU, baru perbarui berkas ini.
#
# "GENERAL" adalah penanda khusus, bukan identifier project: ia berarti project
# Wiki itu sendiri jadi pemiliknya, dan karena seluruh anggota Wiki adalah
# ProjectMember Wiki, artinya siapa pun boleh mengunggah di folder itu.
PEMILIK_FOLDER = {
    "📋 SOP & Kebijakan": ["MGMT"],
    "📖 Panduan Perusahaan": ["MGMT", "HRGA"],
    "🧭 Onboarding Karyawan Baru": ["HRGA"],
    "📚 Wiki Sales & Marketing": ["SALES", "MKT"],
    "📚 Wiki SCM & Procurement": ["PROC"],
    "📚 Wiki Finance & Accounting": ["FIN"],
    "📚 Wiki HRGA & Legal": ["HRGA"],
    "📚 Wiki IT": ["IT"],
    "📚 Wiki Warehouse & Logistik": [
        "LOGI",
        "SHIP",
        "INVQC",
        "WH178",
        "WHMDN",
        "WHBPN",
    ],
}

PENANDA_GENERAL = "GENERAL"

print("=" * 70)
print("Pemilik folder Wiki   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

ws = Workspace.objects.get(slug=WORKSPACE)
wiki = Project.objects.get(workspace=ws, identifier=WIKI_IDENTIFIER, deleted_at__isnull=True)
divisi = {
    p.identifier: p
    for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)
}
divisi[PENANDA_GENERAL] = wiki
nama_divisi = {p.id: p.identifier for p in divisi.values()}

folder_rows = Page.objects.filter(
    projects=wiki, parent__isnull=True, deleted_at__isnull=True
).order_by("name")
folder = {f.name: f for f in folder_rows}

n_tambah = n_cabut = n_tetap = 0
hilang = []

with transaction.atomic():
    sudah_governed = WikiGovernedProject.objects.filter(
        project=wiki, deleted_at__isnull=True
    ).exists()
    print(f"\n1) Governance ACL folder: {'sudah aktif' if sudah_governed else 'BELUM aktif'}")
    if not sudah_governed:
        print("   + menyalakan governance untuk project Wiki")
        if APPLY:
            WikiGovernedProject.objects.create(project=wiki, workspace=ws)

    print("\n2) Pemilik per folder")
    for nama, identifiers in PEMILIK_FOLDER.items():
        f = folder.get(nama)
        if f is None:
            hilang.append(nama)
            print(f"   ! lewat  {nama}  (folder tidak ada di Wiki)")
            continue

        diminta = {}
        for ident in identifiers:
            p = divisi.get(ident)
            if p is None:
                hilang.append(f"{nama} -> {ident}")
                print(f"   ! lewat  {nama}  (divisi {ident} tidak ada)")
                continue
            diminta[p.id] = ident

        sekarang_qs = WikiFolderAccess.objects.filter(
            folder=f, project=wiki, deleted_at__isnull=True
        )
        sekarang = set(sekarang_qs.values_list("division_id", flat=True))

        cabut = sekarang - set(diminta)
        tambah = set(diminta) - sekarang
        tetap = sekarang & set(diminta)
        n_cabut += len(cabut)
        n_tambah += len(tambah)
        n_tetap += len(tetap)

        label = " ".join(sorted(diminta.values())) or "(tanpa pemilik)"
        tanda = "=" if not cabut and not tambah else "~"
        print(f"   {tanda}  {nama:<32} {label}")
        for division_id in tambah:
            print(f"        + {diminta[division_id]}")
        for division_id in cabut:
            print(f"        - {nama_divisi.get(division_id, division_id)}  (tidak ada di berkas ini)")

        if APPLY:
            if cabut:
                sekarang_qs.filter(division_id__in=cabut).delete()
            for division_id in tambah:
                WikiFolderAccess.objects.create(
                    folder=f, division_id=division_id, project=wiki, workspace=ws
                )

    tak_disebut = sorted(set(folder) - set(PEMILIK_FOLDER))
    if tak_disebut:
        print("\n3) Folder yang TIDAK disebut berkas ini (tidak disentuh)")
        for nama in tak_disebut:
            punya = WikiFolderAccess.objects.filter(
                folder=folder[nama], project=wiki, deleted_at__isnull=True
            ).count()
            catatan = f"{punya} pemilik" if punya else "tanpa pemilik, terkunci kecuali admin"
            print(f"      {nama:<32} {catatan}")

    if not APPLY:
        print("\n  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 70)
print(f"  tambah {n_tambah} · cabut {n_cabut} · sudah benar {n_tetap}")
if hilang:
    print(f"  ! {len(hilang)} entri dilewati: {hilang}")
print(
    "  total baris ACL aktif: "
    f"{WikiFolderAccess.objects.filter(project=wiki, deleted_at__isnull=True).count()}"
)
if not APPLY:
    print("  Jalankan dengan WIKI_ACCESS_APPLY=1 untuk menerapkan.")
