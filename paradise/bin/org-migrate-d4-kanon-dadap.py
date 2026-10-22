# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian D4, kanon Dadap 15 departemen (KEP-32).
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-d4-kanon-dadap.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: get_or_create / get-or-skip di mana-mana, aman dijalankan ulang.
#
# KENAPA ADA SKRIP INI
# Kanon user 2026-10-22: 5 divisi, 15 departemen (Dadap). Tiga departemen D3
# (SM-ADM, SM-COO, SM-IND) TIDAK ada di kanon -> dihapus di sini (D3 sudah
# dineutralkan supaya tidak membuatnya lagi). Project payung gabungan yang
# KOSONG (tanpa tugas terbuka) diarsipkan; yang masih punya tugas dilaporkan
# untuk dipindahkan manual dulu -- mengarsipkan project berisi tugas
# menyembunyikan pekerjaan orang tanpa jejak di papan.
#
# TIDAK menyentuh: MGMT/TENDER/PRICING/BE/RND/WIKI/cabang (pemilik lintas
# divisi/tidak jelas, keputusan D3 tetap berlaku), project kerja yang sudah
# terpetakan (walau satu departemen menampung >1 project -- itu dirapikan
# manual di God Mode, skrip ini hanya MELAPORKAN).
#
# KEP-32 yang ditegakkan skrip ini di sisi DATA:
#   - tiap departemen tepat satu project (dilaporkan kalau belum),
#   - supervisor boleh multi-departemen (Fran Olnsen: IT-SAP utama + IT-AI tambahan).

import os

from django.db import transaction
from django.utils import timezone

from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    JabatanOrganisasi,
    Project,
    SupervisorDepartemen,
    TINGKAT_SUPERVISOR,
    User,
    Workspace,
)

APPLY = os.environ.get("ORG_APPLY") == "1"
SUMBER = "migrasi-d4-kanon"
CATATAN = "Migrasi D4 kanon Dadap 2026-10-22 (KEP-32)"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

# Kanon user: (kode, nama, kode divisi). Harus sudah ada (dibuat C1); skrip ini
# TIDAK membuatnya -- kalau ada yang hilang, berarti C1 belum diterapkan.
KANON = [
    ("FIN-FIN", "Finance", "FIN"),
    ("FIN-ACC", "Accounting", "FIN"),
    ("IT-SAP", "SAP Support", "IT"),
    ("IT-AI", "IT AI & Infrastructure", "IT"),
    ("SCM-STC", "Stock Control", "SCM"),
    ("SCM-ODF", "Order Fulfillment", "SCM"),
    ("SCM-PUR", "Purchasing & Procurement", "SCM"),
    ("SCM-SHP", "Shipping", "SCM"),
    ("SCM-WH", "Warehouse", "SCM"),
    ("HRGA-HR", "Human Resources", "HRGA"),
    ("HRGA-GA", "General Affairs", "HRGA"),
    ("HRGA-LGL", "Legal", "HRGA"),
    ("SM-T1", "Sales Tim 1", "SM"),
    ("SM-T2", "Sales Tim 2", "SM"),
    ("SM-MKT", "Marketing", "SM"),
]

# Departemen D3 yang tidak ada di kanon -> hapus (projectnya jadi legacy, anggotanya
# jadi belum-ditempatkan; keduanya bisa dirapikan manual di God Mode).
DEPT_HAPUS = ["SM-ADM", "SM-COO", "SM-IND"]

# Project payung gabungan yang boleh diarsipkan: HANYA kalau tanpa pemetaan
# departemen DAN tanpa tugas terbuka. Yang masih berisi tugas dilaporkan.
PAYUNG = ["FIN", "SALES", "HRGA", "IT"]

# Supervisor multi-departemen kanon: (email, kode utama, [kode tambahan]).
EKSTRA = [
    ("it.dev@itechmandiri.com", "IT-SAP", ["IT-AI"]),  # Fran Olnsen membawahi dua tim IT
]


def tugas_terbuka(project):
    return Issue.objects.filter(project=project, deleted_at__isnull=True, archived_at__isnull=True).count()


print("=" * 70)
print("D4, kanon Dadap 15 departemen (KEP-32)   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

dept = {d.kode: d for d in Departemen.objects.filter(workspace=ws)}
hilang = [k for k, _n, _dv in KANON if k not in dept]
if hilang:
    print("  BERHENTI: departemen kanon belum ada: %s. Jalankan C1 dulu." % ", ".join(hilang))
    raise SystemExit(1)

n_hapus_dep = n_unmap = n_arsip = n_ekstra = 0

with transaction.atomic():
    with tunda_sinkron():
        print("\n1) Hapus departemen di luar kanon")
        for kode in DEPT_HAPUS:
            d = dept.get(kode)
            if d is None:
                print("   -    %s tidak ada, dilewati" % kode)
                continue
            dipetakan = list(DepartemenProject.objects.filter(departemen=d))
            anggota = JabatanOrganisasi.objects.filter(workspace=ws, departemen=d).count()
            ekstra = SupervisorDepartemen.objects.filter(workspace=ws, departemen=d).count()
            print("   x    %s (%d project dipetakan, %d anggota utama, %d ekstra)" % (kode, len(dipetakan), anggota, ekstra))
            for baris in dipetakan:
                print("        project %s jadi tanpa departemen (legacy)" % baris.project.identifier)
                n_unmap += 1
                if APPLY:
                    baris.delete(soft=False)
            if APPLY:
                d.delete()
            n_hapus_dep += 1

        print("\n2) Arsipkan project payung gabungan yang kosong")
        proj = {p.identifier: p for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}
        for ident in PAYUNG:
            p = proj.get(ident)
            if p is None:
                print("   -    %s tidak ada, dilewati" % ident)
                continue
            if DepartemenProject.objects.filter(project=p).exists():
                print("   -    %s sudah berdepartemen (project kerja), dilewati" % ident)
                continue
            n = tugas_terbuka(p)
            if n:
                print("   !    %s masih punya %d tugas terbuka: PINDAHKAN MANUAL dulu, tidak diarsipkan" % (ident, n))
                continue
            print("   A    %s diarsipkan (kosong)" % ident)
            n_arsip += 1
            if APPLY:
                Project.objects.filter(pk=p.pk).update(archived_at=timezone.now())

        print("\n3) Departemen tambahan supervisor (multi-departemen)")
        for email, utama_kode, tambahan in EKSTRA:
            u = User.objects.filter(email=email, is_active=True).first()
            if u is None:
                print("   !    %s: akun tidak ada, dilewati" % email)
                continue
            j = JabatanOrganisasi.objects.filter(workspace=ws, member=u).first()
            if j is None or j.tingkat != TINGKAT_SUPERVISOR:
                print("   !    %s: bukan supervisor berpenempatan, dilewati" % email)
                continue
            for kode in tambahan:
                d = dept.get(kode)
                if d is None:
                    print("   !    %s: departemen %s tidak ada" % (email, kode))
                    continue
                if str(j.departemen_id) == str(d.id):
                    print("   -    %s sudah utama di %s" % (email, kode))
                    continue
                lama = SupervisorDepartemen.all_objects.filter(workspace=ws, member=u, departemen=d).first()
                if lama is not None and lama.deleted_at is None:
                    print("   ada  %s ekstra %s" % (email, kode))
                    continue
                print("   +    %s ekstra %s" % (email, kode))
                n_ekstra += 1
                if APPLY:
                    if lama is None:
                        SupervisorDepartemen.objects.create(workspace=ws, member=u, departemen=d)
                    else:
                        SupervisorDepartemen.all_objects.filter(pk=lama.pk).update(deleted_at=None)

        print("\n4) Audit 1:1 project per departemen (laporan, bukan tindakan)")
        for kode, _nama, _div in KANON:
            d = dept[kode]
            isi = [
                (b.project.identifier, tugas_terbuka(b.project))
                for b in DepartemenProject.objects.filter(departemen=d).select_related("project")
            ]
            if len(isi) == 1:
                continue
            if not isi:
                print("   !    %s: BELUM punya project (buat di God Mode: project mengikuti departemen)" % kode)
            else:
                print("   !    %s: %d project %s -- pilih satu di God Mode, arsipkan sisanya" % (
                    kode, len(isi), ", ".join("%s(%d tugas)" % t for t in isi)))

        print("\n5) Audit penempatan vs kanon user (laporan)")
        for kode, _nama, _div in KANON:
            d = dept[kode]
            sup = [
                "%s <%s>" % (j.member.display_name or j.member.email, j.member.email)
                for j in JabatanOrganisasi.objects.filter(
                    workspace=ws, departemen=d, tingkat=TINGKAT_SUPERVISOR
                ).select_related("member")
            ]
            eks = [
                "%s <%s>" % (s.member.display_name or s.member.email, s.member.email)
                for s in SupervisorDepartemen.objects.filter(workspace=ws, departemen=d).select_related("member")
            ]
            print("   %-9s supervisor: %s%s" % (kode, ", ".join(sup) or "(kosong)", " +ekstra %s" % ", ".join(eks) if eks else ""))
        print("   manager/divisi + direktur: cek di God Mode -> Struktur organisasi.")

        if APPLY:
            print("\n6) Sinkron workspace (jangkauan -> keanggotaan)")
            print("   perubahan keanggotaan: %d" % sinkronkan_workspace(ws.id))
        else:
            print("\n6) Sinkron dilewati (uji kering)")
            print("\n  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
            transaction.set_rollback(True)

print("-" * 70)
print("  departemen dihapus %d - unmap %d - payung diarsipkan %d - ekstra %d" % (
    n_hapus_dep, n_unmap, n_arsip, n_ekstra))
if not APPLY:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
