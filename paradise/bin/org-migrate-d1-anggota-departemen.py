# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian D1, penempatan ANGGOTA BIASA ke departemen dari BUKTI, bukan tebakan.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-d1-anggota-departemen.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
#
# Syarat: C1 sudah diterapkan (Divisi + Departemen + Project terpetakan ada).
# Kalau Divisi masih kosong, skrip berhenti dan meminta C1 dulu.
#
# Aturan penempatan (urutan penting, yang pertama cocok yang dipakai):
#   1. LEWATI kalau: tidak aktif, bot, bukan anggota workspace, SUDAH punya
#      baris JabatanOrganisasi (God Mode / C1 menang, tidak pernah ditimpa),
#      email domain eksternal (ctadvance/ohtori/qtrans/advance = perusahaan
#      lain, bukan staf Dadap), atau local-part mengandung token jabatan
#      (spv/manager/direktur/...) karena itu butuh keputusan JENJANG, bukan
#      sekadar departemen.
#   2. JEJAK PROYEK (bukti utama): semua project AKTIF miliknya dipetakan via
#      PROJECT_DEPT (salinan peta C1). Kalau semuanya jatuh di SATU departemen
#      yang sama -> tempatkan di sana sebagai member (10). Project yang tidak
#      terpetakan (WIKI, payung, lintas divisi) diabaikan, bukan dihitung.
#      Beda departemen / tidak ada yang terpetakan -> LEWATI (jangan menebak).
#   3. PREFIX EMAIL (cadangan, hanya kalau jejak proyek kosong): tabel
#      PREFIX_DEPT eksplisit di bawah, hanya untuk akun peran yang namanya
#      ADALAH jabatannya (kasir, mkt., lgl., ...). Nama orang tidak pernah
#      dipakai menebak.
#
# Semua yang ditempatkan: tingkat MEMBER (10), divisi None (ikut departemen),
# sumber + catatan diisi supaya bisa diaudit dari God Mode. Idempotent dan
# HANYA membuat baris baru -- tidak pernah mengubah baris yang sudah ada.
#
# Di akhir (saat menerapkan): adopsi keanggotaan yang cocok struktur (seperti
# C1 langkah 5) + satu sinkron workspace (seperti C1 langkah 6), supaya akses
# project staf langsung mengikuti penempatannya.

import os
import re

from django.db import transaction

from plane.db.jangkauan import sinkronkan_workspace, tandai_otomatis, tunda_sinkron
from plane.db.models import (
    Departemen,
    Divisi,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    TINGKAT_MEMBER,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.hierarki import jangkauan_hierarki

APPLY = os.environ.get("ORG_APPLY") == "1"
SUMBER = "migrasi-d1-anggota"
CATATAN = "Migrasi D1 2026-10-22"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

# Salinan peta C1 (sumber kebenaran tetap berkas C1; disalin agar skrip ini
# berdiri sendiri saat dijalankan dari stdin).
PROJECT_DEPT = {
    "APAR": "FIN-FIN",
    "ACC": "FIN-ACC",
    "INV": "SCM-STC",
    "QC": "SCM-STC",
    "LOGI": "SCM-ODF",
    "PROC": "SCM-PUR",
    "SHIP": "SCM-SHP",
    "WH178": "SCM-WH",
    "HR": "HRGA-HR",
    "GA": "HRGA-GA",
    "SEC": "HRGA-GA",
    "OPR": "HRGA-GA",
    "LEGAL": "HRGA-LGL",
    "SMT1": "SM-T1",
    "SMT2": "SM-T2",
    "MKT": "SM-MKT",
}

# Hanya akun peran (local-part ADALAH jabatan), dipakai HANYA kalau jejak
# proyek kosong. Tidak ada nama orang di sini, selamanya.
PREFIX_DEPT = {
    "it.sap": "IT-SAP",
    "mkt.": "SM-MKT",
    "lgl.": "HRGA-LGL",
    "kasir": "FIN-ACC",
    "pur.": "SCM-PUR",
    "shp.": "SCM-SHP",
    "inv.": "SCM-STC",
    "qc.": "SCM-STC",
    "whs.": "SCM-WH",
    "hr.": "HRGA-HR",
    "ga.": "HRGA-GA",
    "acc.": "FIN-ACC",
}

DOMAIN_EKSTERNAL = {"ctadvance.co.id", "ohtori.co.id", "qtrans.co.id", "advance.co.id"}

TOKEN_JENJANG = {
    "spv", "sup", "supervisor", "mgr", "manager", "direktur", "director",
    "dir", "head", "chief", "lead", "ldr", "koor", "gm", "vp", "avp",
    "svp", "evp", "kepala", "kabag", "kasi", "kasie",
}


def token_jabatan(local):
    return [t for t in re.split(r"[._-]+", (local or "").lower()) if t in TOKEN_JENJANG]


print("=" * 70)
print("D1, penempatan anggota ke departemen   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

if not Divisi.objects.filter(workspace=ws).exists():
    print("  BERHENTI: struktur divisi kosong. Jalankan C1 dulu.")
    raise SystemExit(1)

dept = {d.kode: d for d in Departemen.objects.filter(workspace=ws)}
hilang = [k for k in set(PROJECT_DEPT.values()) | set(PREFIX_DEPT.values()) if k not in dept]
if hilang:
    print(f"  BERHENTI: departemen tak dikenal di peta: {hilang}. Jalankan C1 dulu.")
    raise SystemExit(1)

proj_ident = {str(p.id): p.identifier for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}

n_tempat = n_lewat = n_adopsi = 0
dilewati = []

with transaction.atomic():
    with tunda_sinkron():
        users = (
            User.objects.filter(is_active=True, is_bot=False)
            .order_by("email")
            .values("id", "email")
        )
        for rec in users:
            uid, email = str(rec["id"]), (rec["email"] or "")
            lokal, _, domain = email.lower().partition("@")
            alasan = None
            kode_dep = None
            bukti = ""

            if not email or not domain:
                alasan = "tanpa email"
            elif domain in DOMAIN_EKSTERNAL:
                alasan = "domain eksternal (bukan staf Dadap)"
            elif JabatanOrganisasi.objects.filter(workspace=ws, member_id=uid).exists():
                alasan = "sudah punya penempatan (God Mode/C1 menang)"
            elif not WorkspaceMember.objects.filter(workspace=ws, member_id=uid).exists():
                alasan = "bukan anggota workspace"
            elif token_jabatan(lokal):
                alasan = "butuh keputusan jenjang: %s (bukan sekadar departemen)" % ",".join(
                    token_jabatan(lokal)
                )
            else:
                pids = set(
                    ProjectMember.objects.filter(
                        workspace=ws, member_id=uid, is_active=True, deleted_at__isnull=True
                    ).values_list("project_id", flat=True)
                )
                terpetakan = {PROJECT_DEPT[proj_ident[str(pid)]] for pid in pids if proj_ident.get(str(pid)) in PROJECT_DEPT}
                if len(terpetakan) == 1:
                    kode_dep = terpetakan.pop()
                    bukti = "proyek:" + kode_dep
                elif terpetakan:
                    alasan = "jejak lintas departemen (%s)" % ",".join(sorted(terpetakan))
                else:
                    cocok = [d for p, d in PREFIX_DEPT.items() if lokal.startswith(p)]
                    if len(cocok) == 1:
                        kode_dep = PREFIX_DEPT[cocok[0]]
                        bukti = "email:%s*" % cocok[0]
                    elif cocok:
                        alasan = "prefix ambigu (%s)" % ",".join(cocok)
                    else:
                        alasan = "tidak ada jejak proyek terpetakan"

            if alasan:
                print(f"   - {email:<40} LEWAT: {alasan}")
                dilewati.append((email, alasan))
                n_lewat += 1
                continue

            d = dept[kode_dep]
            baris, dibuat = JabatanOrganisasi.objects.get_or_create(
                workspace=ws,
                member_id=uid,
                defaults={
                    "tingkat": TINGKAT_MEMBER,
                    "divisi": None,
                    "departemen": d,
                    "sumber": SUMBER,
                    "catatan": "%s; bukti %s" % (CATATAN, bukti),
                },
            )
            if dibuat:
                print(f"   + {email:<40} member {kode_dep} [{bukti}]")
                n_tempat += 1
            else:
                # Seharusnya tidak terjadi (sudah disaring di atas), tapi
                # get_or_create tetap balapan-aman. Jangan timpa manual.
                print(f"   = {email:<40} sudah ada, tidak diubah")
                continue

            ingin = jangkauan_hierarki(uid, ws.id)
            if ingin:
                anggota = set(
                    ProjectMember.objects.filter(
                        workspace=ws, member_id=uid, is_active=True, deleted_at__isnull=True
                    ).values_list("project_id", flat=True)
                )
                for pid in ingin:
                    if pid in anggota:
                        n_adopsi += 1
                        if APPLY:
                            tandai_otomatis(ws.id, pid, uid)

        print()
        print(f"  ditempatkan: {n_tempat} · dilewati: {n_lewat} · adopsi: {n_adopsi}")

        if APPLY:
            print("  Sinkron workspace (jangkauan -> keanggotaan):")
            print("  perubahan keanggotaan: %s" % sinkronkan_workspace(ws.id))
        else:
            print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
            transaction.set_rollback(True)

print("-" * 70)
print("  Dilewati (%d) -- putuskan manual di God Mode:" % len(dilewati))
for email, alasan in dilewati:
    print("    - %s: %s" % (email, alasan))
if not APPLY:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
