# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian C1, struktur Dadap: divisi -> departemen + penempatan orang
#
# Jalankan:
#   docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/org-migrate-c1-divisi-departemen.py
#
# Uji kering (default): tanpa ORG_APPLY   |   Terapkan: ORG_APPLY=1
#
# Idempotent: get_or_create semua, aman dijalankan ulang.
#
# Sumber: struktur kantor pusat Dadap dari user, 2026-10-22. Lima divisi, 15
# departemen, 1 direktur, 4 manager, 15 supervisor. Dua yang BELUM bisa diisi:
#   - HRGA - Legal belum punya manager (lowong).
#   - "Anthony" (manager Sales & Marketing) belum punya akun di sistem, jadi
#     tidak bisa ditempatkan. Begitu IT buatkan akunnya, set tingkat Manager +
#     divisi SM dari God Mode -> Struktur organisasi.
#
# Prinsip (KEP-29):
#   - Manager ditempatkan di DIVISI (divisi_id), supervisor di DEPARTEMEN
#     (departemen_id). Tidak ditebak dari keanggotaan project.
#   - Project payung (FIN/SALES/HRGA/INVQC/IT) TIDAK dipetakan otomatis dan
#     TIDAK diarsip di sini: selama belum jelas ia murni unit organisasi atau
#     masih dipakai bekerja, ia tetap hidup sebagai pengecualian. Yang dipetakan
#     hanya project sub-divisi (hasil A1) dan project yang pemiliknya jelas.
#     Sisanya tampil di God Mode sebagai "project lama" untuk diputuskan manual.
#   - Keanggotaan project yang sudah ada dan memang lahir dari struktur DIADOPSI
#     (tandai_otomatis), supaya ikut dicabut saat orangnya pindah. Yang tidak
#     cocok struktur dibiarkan sebagai pengecualian eksplisit.
#   - Sinyal sinkron ditunda selama penulisan, satu sinkron workspace di akhir.
#
# TIDAK menyentuh: akun (itu A2), keanggotaan eksplisit, peran project (itu A3),
# Super Admin (itu B1).

import os

from django.db import transaction

from plane.db.jangkauan import sinkronkan_workspace, tandai_otomatis, tunda_sinkron
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_SUPERVISOR,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.hierarki import jangkauan_hierarki

APPLY = os.environ.get("ORG_APPLY") == "1"
SUMBER = "migrasi-c1-dadap"
CATATAN = "Migrasi C1 Dadap 2026-10-22"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

# --- 1. Divisi: (kode, nama, email manager / None kalau lowong) ----------------
DIVISI = [
    ("FIN", "Financial Accounting", "litakomalasari@paradiseperkasa.com"),  # Lita Komalasari
    ("IT", "Information Technology", "suarno.radin@paradiseperkasa.com"),  # Suarno Radin
    ("SCM", "Supply Chain Management", "yan.tandi@paradiseperkasa.com"),  # Yan Tandi Raru
    ("HRGA", "HRGA - Legal", None),  # manager lowong
    # Anthony: akun placeholder dari C2 (ganti emailnya saat email asli dari IT ada).
    ("SM", "Sales & Marketing", "anthony@paradiseperkasa.com"),
]

# --- 2. Departemen: (kode, nama, kode divisi, email supervisor) ----------------
DEPARTEMEN = [
    ("FIN-FIN", "Finance", "FIN", "fin.spv@paradiseperkasa.com"),  # Lieani Christina
    ("FIN-ACC", "Accounting", "FIN", "andy.wijaya@paradiseperkasa.com"),  # Andy Wijaya Saragih
    ("IT-SAP", "SAP Support", "IT", "it.dev@itechmandiri.com"),  # Fran Olnsen
    ("IT-AI", "IT AI & Infrastructure", "IT", "it.dev@itechmandiri.com"),  # Fran Olnsen
    ("SCM-STC", "Stock Control", "SCM", "inv.stf1@paradiseperkasa.com"),  # Aranti Sisca
    ("SCM-ODF", "Order Fulfillment", "SCM", "dewi.fransisca@paradiseperkasa.com"),  # Dewi Fransisca
    ("SCM-PUR", "Purchasing & Procurement", "SCM", "pur.spv@paradiseperkasa.com"),  # Felix Yoto
    ("SCM-SHP", "Shipping", "SCM", "shp.spv@paradiseperkasa.com"),  # Frederika Linda Ekawaty
    ("SCM-WH", "Warehouse", "SCM", "ashaf.bakhia@paradiseperkasa.com"),  # Ashaf Bakhia
    ("HRGA-HR", "Human Resources", "HRGA", "hr.spc@paradiseperkasa.com"),  # Fransiska Hapsari
    ("HRGA-GA", "General Affairs", "HRGA", "ga.spv@paradiseperkasa.com"),  # Handoko
    ("HRGA-LGL", "Legal", "HRGA", "lgl.spv@paradiseperkasa.com"),  # Ismail
    ("SM-T1", "Sales Tim 1", "SM", "manroe@paradiseperkasa.com"),  # Abidin Manurung
    ("SM-T2", "Sales Tim 2", "SM", "irvan@paradiseperkasa.com"),  # Irvan Prasurya Widjaja
    ("SM-MKT", "Marketing", "SM", "octavio.susanto@paradiseperkasa.com"),  # Octavio Reinhart Susanto
]

DIREKTUR = "henry@paradiseperkasa.com"  # Henry Leo

# --- 3. Project -> departemen (hanya yang pemiliknya jelas; payung dibiarkan) --
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
    # Sengaja TIDAK dipetakan (tampil sebagai project lama di God Mode):
    # FIN/SALES/HRGA/INVQC/IT (payung, nasibnya menunggu keputusan),
    # SMCOO/SMIND/SMADM (menunggu diputuskan masuk tim mana),
    # MGMT/TENDER/BE/BME (lintas divisi / unit kerja, bukan departemen Dadap),
    # WHMDN/WHBPN (cabang Medan/Balikpapan, di luar struktur Dadap).
}

print("=" * 70)
print("C1, divisi + departemen Dadap   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

users = {u.email.lower(): u for u in User.objects.filter(is_active=True, is_bot=False)}
divisi_obj = {}
dept_obj = {}
n_divisi = n_dept = n_petakan = n_jabatan = n_adopsi = n_lewat = 0
konflik = []

with transaction.atomic():
    with tunda_sinkron():
        print("\n1) Divisi")
        for kode, nama, email_manajer in DIVISI:
            d = Divisi.objects.filter(workspace=ws, kode=kode).first()
            if d:
                if d.nama != nama:
                    print(f"   ~    {kode:<6} nama {d.nama!r} -> {nama!r}")
                    d.nama = nama
                    d.save(update_fields=["nama", "updated_at"])
                else:
                    print(f"   ada  {kode:<6} {nama}")
            else:
                # Dibuat juga saat uji kering: di dalam transaksi yang nanti
                # di-rollback, supaya langkah berikut (departemen, pemetaan,
                # jabatan) melihat id yang sama persis dengan saat diterapkan.
                print(f"   BUAT {kode:<6} {nama}")
                n_divisi += 1
                d = Divisi.objects.create(workspace=ws, kode=kode, nama=nama)
            divisi_obj[kode] = d

        print("\n2) Departemen")
        for kode, nama, kode_div, email_spv in DEPARTEMEN:
            d = Departemen.objects.filter(workspace=ws, kode=kode).first()
            induk = divisi_obj.get(kode_div)
            if d:
                ubah = []
                if d.nama != nama:
                    ubah.append(f"nama {d.nama!r} -> {nama!r}")
                if induk and d.divisi_id != induk.id:
                    ubah.append(f"divisi {d.divisi_id} -> {kode_div}")
                if ubah:
                    print(f"   ~    {kode:<9} {'; '.join(ubah)}")
                    d.nama = nama
                    if induk:
                        d.divisi = induk
                    d.save(update_fields=["nama", "divisi", "updated_at"])
                else:
                    print(f"   ada  {kode:<9} {nama} ({kode_div})")
            else:
                # Sama seperti divisi: dibuat juga saat uji kering (rollback).
                print(f"   BUAT {kode:<9} {nama} ({kode_div})")
                n_dept += 1
                d = Departemen.objects.create(workspace=ws, divisi=induk, kode=kode, nama=nama)
            dept_obj[kode] = d

        print("\n3) Project -> departemen")
        proj = {p.identifier: p for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}
        for ident, kode_dep in PROJECT_DEPT.items():
            p, dep = proj.get(ident), dept_obj.get(kode_dep)
            if not p:
                print(f"   ! lewat {ident:<7} project tidak ada")
                n_lewat += 1
                continue
            if not dep:
                print(f"   ! lewat {ident:<7} departemen {kode_dep} gagal dibuat")
                n_lewat += 1
                continue
            lama = DepartemenProject.objects.filter(project=p).first()
            if lama:
                if lama.departemen_id == dep.id:
                    print(f"   ada  {ident:<7} -> {kode_dep}")
                else:
                    msg = f"{ident} sudah milik {lama.departemen.kode}, diminta {kode_dep} — DILEWATI"
                    print(f"   !! {msg}")
                    konflik.append(msg)
                    n_lewat += 1
                continue
            print(f"   +    {ident:<7} -> {kode_dep}")
            n_petakan += 1
            DepartemenProject.objects.create(workspace=ws, departemen=dep, project=p)

        print("\n4) Jenjang + penempatan")
        # (email, tingkat, kode divisi / None, kode departemen / None, peran)
        penempatan = [(DIREKTUR, TINGKAT_DIREKTUR, None, None, "Direktur")]
        for kode, _nama, email_manajer in DIVISI:
            if email_manajer:
                penempatan.append((email_manajer, TINGKAT_MANAGER, kode, None, f"Manager {kode}"))
        # Satu orang menempati satu sel: skema hanya punya satu FK departemen
        # per orang. Duplikat (mis. Fran membawahi dua departemen IT) diisi ke
        # departemen PERTAMA, sisanya dilaporkan sebagai tanpa supervisor.
        terlihat = set()
        for kode, _nama, _div, email_spv in DEPARTEMEN:
            if email_spv in terlihat:
                msg = f"{email_spv} sudah ditempatkan, {kode} dibiarkan tanpa supervisor (satu orang satu departemen)"
                print(f"   !! {msg}")
                konflik.append(msg)
                n_lewat += 1
                continue
            terlihat.add(email_spv)
            penempatan.append((email_spv, TINGKAT_SUPERVISOR, None, kode, f"Supervisor {kode}"))
        nama_div = {d.id: d.kode for d in divisi_obj.values() if d}
        nama_dep = {d.id: d.kode for d in dept_obj.values() if d}

        for email, tingkat, kode_div, kode_dep, peran in penempatan:
            u = users.get(email)
            if not u:
                print(f"   ! lewat {email:<40} akun tidak ada ({peran})")
                konflik.append(f"{email} ({peran}): akun tidak ada")
                n_lewat += 1
                continue
            if not WorkspaceMember.objects.filter(workspace=ws, member=u).exists():
                print(f"   ! {email:<40} bukan anggota workspace ({peran})")
                konflik.append(f"{email} ({peran}): bukan anggota workspace")
            div_id = divisi_obj[kode_div].id if kode_div and divisi_obj.get(kode_div) else None
            dep_id = dept_obj[kode_dep].id if kode_dep and dept_obj.get(kode_dep) else None
            baris, dibuat = JabatanOrganisasi.objects.get_or_create(
                workspace=ws,
                member=u,
                defaults={"tingkat": tingkat, "sumber": SUMBER, "catatan": CATATAN},
            )
            sama = (
                not dibuat
                and baris.tingkat == tingkat
                and (baris.divisi_id or None) == div_id
                and (baris.departemen_id or None) == dep_id
            )
            if sama:
                print(f"   ada  {email:<40} {peran}")
                continue
            if not dibuat:
                print(
                    f"   ~    {email:<40} tingkat {baris.tingkat} -> {tingkat}, "
                    f"divisi {nama_div.get(baris.divisi_id)} -> {nama_div.get(div_id)}, "
                    f"dept {nama_dep.get(baris.departemen_id)} -> {nama_dep.get(dep_id)}"
                )
            else:
                print(f"   +    {email:<40} {peran}")
            n_jabatan += 1
            baris.tingkat = tingkat
            baris.divisi_id = div_id
            baris.departemen_id = dep_id
            baris.sumber = SUMBER
            baris.catatan = CATATAN
            baris.save()

        print("\n5) Adopsi keanggotaan lama yang lahir dari struktur")
        for email, _tingkat, _dv, _dp, _peran in penempatan:
            u = users.get(email)
            if not u:
                continue
            ingin = jangkauan_hierarki(u.id, ws.id)
            if not ingin:
                continue
            anggota = set(
                ProjectMember.objects.filter(
                    workspace=ws, member=u, is_active=True, deleted_at__isnull=True
                ).values_list("project_id", flat=True)
            )
            for pid in ingin:
                if pid in anggota:
                    n_adopsi += 1
                    if APPLY:
                        tandai_otomatis(ws.id, pid, u.id)
        print(f"   keanggotaan cocok struktur: {n_adopsi} (ditandai otomatis)")

    if APPLY:
        print("\n6) Sinkron workspace (jangkauan -> keanggotaan)")
        diubah = sinkronkan_workspace(ws.id)
        print(f"   perubahan keanggotaan: {diubah}")
    else:
        print("\n6) Sinkron dilewati (uji kering)")
        print("\n  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 70)
print(f"  divisi {n_divisi} · departemen {n_dept} · pemetaan {n_petakan} · jabatan {n_jabatan} · adopsi {n_adopsi} · dilewati {n_lewat}")
if konflik:
    print("  PERLU TINDAK LANJUT:")
    for k in konflik:
        print(f"    - {k}")
print("  BELUM DIISI (bukan galat, pengingat):")
print("    - Manager HRGA lowong; Anthony (SM) masih akun placeholder C2.")
print("    - Project payung FIN/SALES/HRGA/INVQC/IT + SMCOO/SMIND/SMADM + MGMT/TENDER/BE/BME + WHMDN/WHBPN")
print("      tetap tanpa departemen — putuskan manual di God Mode.")
if not APPLY:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
