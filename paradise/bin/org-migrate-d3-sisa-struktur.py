# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian D3, sisa pemetaan project + departemen baru + penempatan susulan.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-d3-sisa-struktur.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: get_or_create di mana-mana; pemetaan yang sudah ada TIDAK
# disentuh; anggota yang sudah ditempatkan dilewati (God Mode menang).
#
# KENAPA ADA SKRIP INI (bukan bagian C1/D1):
# C1 sengaja menunda project yang pemiliknya belum jelas. Audit sesudah C1
# (nama project + daftar anggotanya) memastikan pemetaan ini:
#   INVQC -> SCM-STC   (dua-duanya anak Stock Control; payungnya satu divisi)
#   SMADM -> SM-ADM    (Admin Sales; project-nya harfiah begitu)
#   SMCOO -> SM-COO    (Sales Coordinator; project-nya harfiah begitu)
#   SMIND -> SM-IND    (Sales - Independent; project-nya harfiah begitu)
#   BME   -> HRGA-GA  (Building Maintenance = urusan General Affairs)
#   ITSAP -> IT-SAP   (projectnya DIBUAT skrip ini; umbrella IT tak bisa dipecah)
#   ITAI  -> IT-AI    (idem; supervisor AI belum ada -> Manager IT + direktur)
# Departemen SM-ADM/SM-COO/SM-IND dibuat baru di bawah divisi SM (belum ada).
# Supervisor ketiganya BELUM diketahui -> tetap kosong, diisi manual di God Mode;
# sampai ada, penyetujuan naik ke Manager SM + direktur (otomatis).
#
# Yang SENGAJA tidak disentuh (keputusan, bukan kelupaan):
#   BE      : project temporer ("Revisi SOP ... 2026"), bukan unit tetap.
#   TENDER/PRICING/MGMT : pemilik lintas divisi/tidak jelas; salah taruh =
#             approver dan akses yang salah. Superadmin + direktur meng-cover.
#   RND/ANNEALINGF      : tidak ada departemen R&D di Dadap; orangnya eksternal.
#   WIKI                : dipakai bersama, jangan dimiliki satu divisi.
#   FIN/SALES/HRGA/INVQC-payung/IT : payung multi-departemen (INVQC payungnya
#             ikut SCM-STC karena anak-anaknya satu divisi semua; yang lain tidak bisa).
#   WHMDN/WHBPN : cabang luar Dadap, di luar cakupan struktur ini (lihat C1).
#
# Sesudah pemetaan, anggota yang jejaknya jadi single-departemen DITEMPATKAN
# (aturan bukti yang sama dengan D1). Di akhir: adopsi + satu sinkron.

import os
import re

from django.db import transaction

from plane.app.permissions import ROLE
from plane.app.serializers import ProjectSerializer
from plane.db.jangkauan import sinkronkan_workspace, tandai_otomatis, tunda_sinkron
from plane.db.membership import jadikan_anggota_project
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    State,
    DEFAULT_STATES,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.hierarki import jangkauan_hierarki

APPLY = os.environ.get("ORG_APPLY") == "1"
SUMBER = "migrasi-d3-sisa"
CATATAN = "Migrasi D3 2026-10-22"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

# (kode, nama, kode divisi induk). Hanya yang diputuskan di atas.
DEPT_BARU = [
    ("SM-ADM", "Admin Sales", "SM"),
    ("SM-COO", "Sales Coordinator", "SM"),
    ("SM-IND", "Sales - Independent", "SM"),
]

# Peta C1 (16) + tambahan D3 (7: INVQC, SMADM, SMCOO, SMIND, BME + ITSAP/ITAI
# yang projectnya DIBUAT skrip ini karena belum ada). Disalin agar skrip
# berdiri sendiri.
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
    "INVQC": "SCM-STC",
    "SMADM": "SM-ADM",
    "SMCOO": "SM-COO",
    "SMIND": "SM-IND",
    "BME": "HRGA-GA",
    "ITSAP": "IT-SAP",
    "ITAI": "IT-AI",
}

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
TINGKAT_MEMBER = 10

TOKEN_JENJANG = {
    "spv", "sup", "supervisor", "mgr", "manager", "direktur", "director",
    "dir", "head", "chief", "lead", "ldr", "koor", "gm", "vp", "avp",
    "svp", "evp", "kepala", "kabag", "kasi", "kasie",
}


def token_jabatan(local):
    return [t for t in re.split(r"[._-]+", (local or "").lower()) if t in TOKEN_JENJANG]


print("=" * 70)
print("D3, sisa pemetaan + departemen baru + penempatan susulan   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

divisi = {d.kode: d for d in Divisi.objects.filter(workspace=ws)}
for _kode, _nama, kodiv in DEPT_BARU:
    if kodiv not in divisi:
        print("  BERHENTI: divisi %s belum ada. Jalankan C1 dulu." % kodiv)
        raise SystemExit(1)

dept = {d.kode: d for d in Departemen.objects.filter(workspace=ws)}
proj_ident = {str(p["id"]): p["identifier"] for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True).values("id", "identifier")}
n_divisi = n_dept = n_proyek = n_petakan = n_jabatan = n_adopsi = n_lewat = 0
dilewati = []

with transaction.atomic():
    with tunda_sinkron():
        print("\n1) Departemen baru")
        for kode, nama, kodiv in DEPT_BARU:
            d = dept.get(kode)
            if d:
                print("   ada  %s (%s)" % (kode, d.nama))
                continue
            print("   BUAT %s %s (divisi %s)" % (kode, nama, kodiv))
            n_dept += 1
            d = Departemen.objects.create(workspace=ws, divisi=divisi[kodiv], kode=kode, nama=nama)
            dept[kode] = d

        print("\n1b) Project tim IT (buat kalau belum ada)")
        # Umbrella IT tidak bisa dipetakan (dipakai dua departemen). Sebagai gantinya
        # dua project kerja dibuat dari NOL -- tanpa migrasi issue lama: 195 issue
        # terbuka di payung tetap di sana (direktur meng-cover), kerja baru jalan
        # di project yang benar. Identik dengan flow "project baru" di UI
        # (serializer yang sama = validasi yang sama + state bawaan + pembuat/lead
        # jadi admin). Idempotent: ident sudah ada -> lewati (dipakai untuk
        # pemetaan kalau masih hidup, diteruskan kalau terarsip).
        PROYEK_BARU = [
            # (identifier, nama, deskripsi, email_pembuat, email_lead_atau_None)
            ("ITSAP", "SAP Support",
             "Ruang kerja tim SAP Support (dibuat skrip migrasi D3).",
             "suarno.radin@paradiseperkasa.com", "it.dev@itechmandiri.com"),
            ("ITAI", "IT AI & Infrastructure",
             "Ruang kerja tim AI & Infrastruktur (dibuat skrip migrasi D3).",
             "suarno.radin@paradiseperkasa.com", None),
        ]
        for ident, nama, deskripsi, email_pembuat, email_lead in PROYEK_BARU:
            ada = Project.all_objects.filter(workspace=ws, identifier=ident).first()
            if ada:
                print("   ada  %s (%s)%s" % (ident, ada.name, " [TERARSIP]" if ada.deleted_at else ""))
                continue
            pembuat = User.objects.filter(email=email_pembuat, is_active=True).first()
            lead = User.objects.filter(email=email_lead, is_active=True).first() if email_lead else None
            if not pembuat:
                print("   ! lewat %s: pembuat %s tidak ada" % (ident, email_pembuat))
                continue
            if email_lead and not lead:
                print("   ! lewat %s: lead %s tidak ada" % (ident, email_lead))
                continue
            data = {"name": nama, "identifier": ident, "description": deskripsi,
                    "created_by": str(pembuat.id)}
            if lead:
                data["project_lead"] = str(lead.id)
            ser = ProjectSerializer(data=data, context={"workspace_id": str(ws.id)})
            if not ser.is_valid():
                print("   ! lewat %s: validasi gagal %s" % (ident, dict(ser.errors)))
                continue
            print("   BUAT %s %s (pembuat %s%s)" % (
                ident, nama, email_pembuat, ("; lead " + email_lead) if email_lead else ""))
            n_proyek += 1
            p = ser.save()
            Project.objects.filter(pk=p.pk).update(created_by=pembuat)
            jadikan_anggota_project(p.pk, pembuat.id, ROLE.ADMIN.value)
            if lead and lead.id != pembuat.id:
                jadikan_anggota_project(p.pk, lead.id, ROLE.ADMIN.value)
            State.objects.bulk_create(
                [
                    State(
                        name=state["name"],
                        color=state["color"],
                        project=p,
                        sequence=state["sequence"],
                        workspace=ws,
                        group=state["group"],
                        default=state.get("default", False),
                        created_by=pembuat,
                    )
                    for state in DEFAULT_STATES
                ]
            )

        print("\n2) Pemetaan project tambahan")
        proj = {p.identifier: p for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}

        for ident, kode_dep in sorted(PROJECT_DEPT.items()):
            if ident in (
                "APAR", "ACC", "INV", "QC", "LOGI", "PROC", "SHIP", "WH178",
                "HR", "GA", "SEC", "OPR", "LEGAL", "SMT1", "SMT2", "MKT",
            ):
                continue  # warisan C1, sudah dipetakan
            dep = dept.get(kode_dep)
            p = proj.get(ident)
            if not dep or not p:
                print("   ! lewat %s (project/departemen tidak ada)" % ident)
                n_lewat += 1
                continue
            lama = DepartemenProject.objects.filter(project=p).first()
            if lama:
                if lama.departemen_id == dep.id:
                    print("   ada  %s -> %s" % (ident, kode_dep))
                else:
                    print("   !! %s sudah milik %s, diminta %s: DILEWATI (tidak menimpa)" % (
                        ident, lama.departemen.kode, kode_dep))
                    dilewati.append("%s: sudah terpetakan ke %s" % (ident, lama.departemen.kode))
                    n_lewat += 1
                continue
            print("   +    %s -> %s" % (ident, kode_dep))
            n_petakan += 1
            DepartemenProject.objects.create(workspace=ws, departemen=dep, project=p)

        print("\n3) Penempatan anggota yang jejaknya baru lengkap")
        users = User.objects.filter(is_active=True, is_bot=False).order_by("email")
        for u in users:
            uid, email = str(u.id), (u.email or "")
            lokal, _, domain = email.lower().partition("@")
            if not email or not domain:
                alasan = "tanpa email"
            elif domain in DOMAIN_EKSTERNAL:
                alasan = "domain eksternal (bukan staf Dadap)"
            elif JabatanOrganisasi.objects.filter(workspace=ws, member_id=uid).exists():
                alasan = "sudah punya penempatan (God Mode/C1/D1 menang)"
            elif not WorkspaceMember.objects.filter(workspace=ws, member_id=uid).exists():
                alasan = "bukan anggota workspace"
            elif token_jabatan(lokal):
                alasan = "butuh keputusan jenjang: %s" % ",".join(token_jabatan(lokal))
            else:
                alasan = None
            if alasan:
                continue
            pids = set(
                ProjectMember.objects.filter(
                    workspace=ws, member_id=uid, is_active=True, deleted_at__isnull=True
                ).values_list("project_id", flat=True)
            )
            projmap = {pid: PROJECT_DEPT.get(proj_ident.get(str(pid))) for pid in pids}
            cocok = {d for d in projmap.values() if d}
            kode_dep = None
            bukti = ""
            if len(cocok) == 1:
                kode_dep = next(iter(cocok))
                bukti = "proyek:" + kode_dep
            else:
                if cocok:
                    continue  # lintas departemen: jangan menebak (diam-diam dilewati)
                for pref, depk in PREFIX_DEPT.items():
                    if lokal.startswith(pref):
                        kode_dep = depk
                        bukti = "email:" + pref + "*"
                        break
            if not kode_dep:
                continue
            dep = dept.get(kode_dep)
            if not dep:
                continue
            baris, dibuat = JabatanOrganisasi.objects.get_or_create(
                workspace=ws,
                member_id=uid,
                defaults={
                    "tingkat": TINGKAT_MEMBER,
                    "divisi": None,
                    "departemen": dep,
                    "sumber": SUMBER,
                    "catatan": "%s; bukti %s" % (CATATAN, bukti),
                },
            )
            if not dibuat:
                continue
            print("   +    %-40s member %s [%s]" % (email, kode_dep, bukti))
            n_jabatan += 1
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
                            from plane.db.jangkauan import tandai_otomatis

                            tandai_otomatis(ws.id, pid, uid)

        print()
        print("  departemen: %d - project: %d - pemetaan: %d - ditempatkan: %d - adopsi: %d - dilewati: %d" % (
            n_dept, n_proyek, n_petakan, n_jabatan, n_adopsi, n_lewat))

        if APPLY:
            print("  Sinkron workspace (jangkauan -> keanggotaan):")
            from plane.db.jangkauan import sinkronkan_workspace

            print("  perubahan keanggotaan: %d" % sinkronkan_workspace(ws.id))
        else:
            print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
            transaction.set_rollback(True)

print("-" * 70)
if APPLY:
    print("  Diterapkan. Yang belum terpetakan tetap manual di God Mode:")
    print("  BE, TENDER, PRICING, MGMT, RND, ANNEALINGF, WIKI, payung, cabang.")
else:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
