# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian E1, pecah project payung per departemen (KEP-32 1:1).
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-e1-pecah-payung.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: get_or_create / get-or-skip di mana-mana, aman dijalankan ulang.
# Menulis lewat queryset.update()/bulk_create supaya tidak memicu sinyal
# aktivitas/notifikasi Issue (pindahan massal bukan aktivitas pengguna).
#
# KENAPA SKRIP INI
# Permintaan user 2026-10-23: tiap departemen punya project-nya sendiri, bukan
# berbagi payung gabungan. Tugas ikut orangnya (pembuat/assignee), manager divisi
# tetap melihat semua project departemen di bawahnya (lewat sinkron jangkauan).
#
# Cakupan (hasil audit deployment 2026-10-23):
#   IT (194 tugas terbuka) -> ITAI (IT-AI) + ITSAP (IT-SAP), ikut bukti orang.
#   HRGA (3 tugas) -> GA 2 tugas, 1 hapus (test). Payung diarsipkan.
#   INVQC (1 tugas "iii") -> hapus (test). Payung diarsipkan.
#   FIN (kosong) -> ganti nama "Finance" (project FIN-FIN). APAR dipensiunkan.
#   SALES (kosong) -> diarsipkan.
#   IT (sesudah pindah) -> diarsipkan (riwayat 9 tugas arsip tetap di dalam).
#
# TIDAK disentuh: PRICING/TENDER/MGMT/RND/WIKI/BE/cabang (keputusan D3),
# SMADM/SMCOO/SMIND + departemen non-kanon (wilayah D4), tugas arsip di payung.

import os

from django.db import transaction
from django.utils import timezone

from plane.app.permissions import ROLE
from plane.app.serializers import ProjectSerializer
from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.membership import jadikan_anggota_project
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Issue,
    IssueLabel,
    IssueSequence,
    JabatanOrganisasi,
    Label,
    Module,
    ModuleIssue,
    ModuleMember,
    Project,
    ProjectMember,
    State,
    DEFAULT_STATES,
    User,
    Workspace,
)

APPLY = os.environ.get("ORG_APPLY") == "1"
SUMBER = "migrasi-e1-pecah"
CATATAN = "Migrasi E1 pecah payung 2026-10-23"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

IT_SAP = "IT-SAP"
IT_AI = "IT-AI"

# (identifier_lama, sequence) -> identifier_tujuan, atau "HAPUS" (tugas test).
OVERRIDE = {
    ("IT", 33): "HAPUS",  # "Testing Calender" -- test
    ("IT", 71): "ITSAP",  # Sign-off Go Live, assignee SAP mayoritas
    ("IT", 79): "ITAI",  # Sosialisasi Space, tanpa bukti -> AI (infrastruktur aplikasi)
    ("IT", 97): "ITSAP",  # FU Prodor GI-GR (SAP MM)
    ("IT", 118): "ITAI",  # Network Improvement (infrastruktur)
    ("HRGA", 5): "HAPUS",  # "test"
    ("INVQC", 1): "HAPUS",  # "iii"
}

HAPUS_TEST = {k for k, v in OVERRIDE.items() if v == "HAPUS"}
PINDAH_MANUAL = {k: v for k, v in OVERRIDE.items() if v != "HAPUS"}

MODUL_SAP = {"IT SAP - FICO", "IT SAP - MM", "IT SAP - SD", "IT SAP - QM", "IT SAP - WM"}
MODUL_AI = {"IT AI"}


def dept_utama(user_id):
    j = JabatanOrganisasi.objects.filter(
        workspace=ws, member_id=user_id, deleted_at__isnull=True
    ).first()
    if j is None or j.departemen_id is None:
        return None
    return j.departemen.kode


def dept_assignee_tunggal(issue_id):
    from plane.db.models import IssueAssignee

    deps = set()
    for a in IssueAssignee.objects.filter(issue_id=issue_id, deleted_at__isnull=True):
        k = dept_utama(a.assignee_id)
        if k in (IT_SAP, IT_AI):
            deps.add(k)
    if len(deps) == 1:
        return next(iter(deps))
    return None


def rute_it(issue, modul_nama):
    key = ("IT", issue.sequence_id)
    if key in OVERRIDE:
        return OVERRIDE[key]
    if modul_nama in MODUL_SAP:
        return "ITSAP"
    if modul_nama in MODUL_AI:
        return "ITAI"
    tunggal = dept_assignee_tunggal(issue.id)
    if tunggal == IT_SAP:
        return "ITSAP"
    if tunggal == IT_AI:
        return "ITAI"
    pembuat = dept_utama(issue.created_by_id)
    if pembuat == IT_SAP:
        return "ITSAP"
    if pembuat == IT_AI:
        return "ITAI"
    return "LEWATI"


print("=" * 70)
print("E1, pecah payung per departemen   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

n_pindah = n_hapus = n_modul = n_label = n_lewat = 0
peta_seq = {}  # (ident_lama, seq_lama) -> issue id (untuk modul)

with transaction.atomic():
    with tunda_sinkron():
        print("\n1) Project baru tim IT (buat kalau belum ada)")
        proj = {p.identifier: p for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}
        BARU = [
            ("ITSAP", "IT SAP Support Project",
             "Ruang kerja tim SAP Support (dibuat skrip migrasi E1).",
             "suarno.radin@paradiseperkasa.com", "it.dev@itechmandiri.com"),
            ("ITAI", "IT AI dan Infrastruktur",
             "Ruang kerja tim AI dan Infrastruktur (dibuat skrip migrasi E1).",
             "suarno.radin@paradiseperkasa.com", "it.dev@itechmandiri.com"),
        ]
        for ident, nama, deskripsi, email_pembuat, email_lead in BARU:
            ada = Project.all_objects.filter(workspace=ws, identifier=ident).first()
            if ada is not None and ada.deleted_at is None:
                print("   ada  %s (%s)%s" % (ident, ada.name, " [TERARSIP]" if ada.archived_at else ""))
                proj[ident] = ada
                continue
            if ada is not None:
                print("   HIDUPKAN %s (%s, tadinya terhapus)" % (ident, ada.name))
            else:
                print("   BUAT %s %s" % (ident, nama))
            pembuat = User.objects.filter(email=email_pembuat, is_active=True).first()
            lead = User.objects.filter(email=email_lead, is_active=True).first()
            if not APPLY:
                continue
            if ada is not None:
                # Pernah dibuat lalu dihapus: hidupkan lagi. State/anggota lama
                # yang masih ada dipakai lagi; yang hilang dilengkapi di bawah.
                # Pakai all_objects: manager biasa tidak melihat baris terhapus
                # sehingga update() lewat sana tidak kena apa-apa.
                Project.all_objects.filter(pk=ada.pk).update(
                    deleted_at=None, archived_at=None)
                p = Project.objects.get(pk=ada.pk)
            else:
                data = {"name": nama, "identifier": ident, "description": deskripsi,
                        "created_by": str(pembuat.id), "project_lead": str(lead.id)}
                ser = ProjectSerializer(data=data, context={"workspace_id": str(ws.id)})
                if not ser.is_valid():
                    print("   ! lewat %s: validasi gagal %s" % (ident, dict(ser.errors)))
                    continue
                p = ser.save()
                Project.objects.filter(pk=p.pk).update(created_by=pembuat)
            jadikan_anggota_project(p.pk, pembuat.id, ROLE.ADMIN.value, workspace_id=ws.id)
            jadikan_anggota_project(p.pk, lead.id, ROLE.ADMIN.value, workspace_id=ws.id)
            if not State.objects.filter(
                    project=p, deleted_at__isnull=True).exists():
                State.objects.bulk_create(
                    [State(project=p, workspace=ws, created_by=pembuat, **s) for s in DEFAULT_STATES]
                )
            proj[ident] = Project.objects.get(pk=p.pk)

        print("\n1b) Pemetaan project baru ke departemen")
        dept = {d.kode: d for d in Departemen.objects.filter(workspace=ws, deleted_at__isnull=True)}
        for ident, kode_dep in (("ITSAP", IT_SAP), ("ITAI", IT_AI)):
            p = proj.get(ident)
            if p is None or p.deleted_at:
                print("   ! lewat %s (project tidak ada)" % ident)
                continue
            lama = DepartemenProject.objects.filter(project=p).first()
            if lama and lama.deleted_at is None:
                print("   ada  %s -> %s" % (ident, lama.departemen.kode))
                continue
            print("   +    %s -> %s" % (ident, kode_dep))
            if APPLY:
                DepartemenProject.objects.create(
                    workspace=ws, departemen=dept[kode_dep], project=p)

        # State per project tujuan, dikelompokkan group -> state pertama.
        def peta_state(project):
            urut = State.objects.filter(
                project=project, deleted_at__isnull=True).order_by("sequence")
            m, bawaan = {}, None
            for s in urut:
                m.setdefault(s.group, s)
                if s.default:
                    bawaan = s
            return m, (bawaan or urut.first())

        state_map = {ident: peta_state(proj[ident]) for ident in
                     ("ITSAP", "ITAI", "GA") if proj.get(ident) is not None}

        def pindahkan(issue, ident_tujuan, modul_nama=""):
            from plane.db.models import IssueAssignee
            p_tujuan = proj[ident_tujuan]
            m, bawaan = state_map[ident_tujuan]
            g = issue.state.group if issue.state_id else None
            s_baru = m.get(g, bawaan)
            if APPLY:
                seq = IssueSequence.objects.filter(project=p_tujuan).order_by(
                    "-sequence").values_list("sequence", flat=True).first() or 0
                seq = max(seq, pindahkan.cnt.get(ident_tujuan, 0)) + 1
                pindahkan.cnt[ident_tujuan] = seq
                Issue.objects.filter(pk=issue.pk).update(
                    project=p_tujuan, sequence_id=seq, state=s_baru)
                IssueSequence.objects.create(issue=issue, sequence=seq, project=p_tujuan)
            # Label: salin per nama ke project tujuan, taut ulang.
            for il in IssueLabel.objects.filter(issue=issue, deleted_at__isnull=True
                                               ).select_related("label"):
                lab = il.label
                if APPLY:
                    bantu = None
                    if lab.parent_id:
                        lp = lab.parent
                        bantu, _ = Label.objects.get_or_create(
                            project=p_tujuan, name=lp.name,
                            defaults={"workspace": ws, "color": lp.color or ""})
                    baru, _ = Label.objects.get_or_create(
                        project=p_tujuan, name=lab.name,
                        defaults={"workspace": ws, "color": lab.color or "",
                                  "parent": bantu})
                    IssueLabel.objects.filter(pk=il.pk).update(deleted_at=timezone.now())
                    IssueLabel.objects.create(issue=issue, label=baru)
            # Anggota: pembuat + assignee aktif jadi anggota eksplisit tujuan.
            siapa = {issue.created_by_id} | set(
                IssueAssignee.objects.filter(
                    issue_id=issue.id, deleted_at__isnull=True
                ).values_list("assignee_id", flat=True))
            for uid in siapa:
                if uid is None:
                    continue
                if APPLY:
                    sudah = ProjectMember.objects.filter(
                        project=p_tujuan, member_id=uid, is_active=True,
                        deleted_at__isnull=True).first()
                    if sudah is None:
                        asal = ProjectMember.objects.filter(
                            project=issue.project,
                            member_id=uid, deleted_at__isnull=True).first()
                        jadikan_anggota_project(
                            p_tujuan.pk, uid,
                            (asal.role if asal else 15), workspace_id=ws.id)
            if APPLY:
                peta_seq[(issue.project.identifier, issue.sequence_id)] = issue.id

        pindahkan.cnt = {}
        # Muat ulang counter dari DB supaya idempotent antar-jalankan.
        if APPLY:
            for ident in ("ITSAP", "ITAI", "GA"):
                if proj.get(ident) is not None:
                    pindahkan.cnt[ident] = IssueSequence.objects.filter(
                        project=proj[ident]).order_by(
                        "-sequence").values_list("sequence", flat=True).first() or 0

        print("\n2) Pindah tugas IT (ikut bukti orang)")
        it = proj["IT"]
        anak = {}
        semua = list(Issue.objects.filter(
            project=it, deleted_at__isnull=True, archived_at__isnull=True
        ).select_related("state").order_by("sequence_id"))
        by_id = {str(i.id): i for i in semua}
        for i in semua:
            if i.parent_id and str(i.parent_id) in by_id:
                anak.setdefault(str(i.parent_id), []).append(i)
        modul_of = {}
        for mi in ModuleIssue.objects.filter(
                issue__project=it, deleted_at__isnull=True).select_related("module"):
            modul_of.setdefault(str(mi.issue_id), []).append(mi.module.name)
        target_of = {}
        for i in semua:
            mods = modul_of.get(str(i.id), [])
            m1 = mods[0] if len(mods) == 1 else ""
            t = rute_it(i, m1)
            if len(mods) > 1:
                print("   !    IT-%d multi-modul %s: ikut aturan orang" % (
                    i.sequence_id, ",".join(mods)))
                t = rute_it(i, "")
            # Konflik modul vs orang dilaporkan (modul menang, kecuali Development).
            if m1 in MODUL_SAP or m1 in MODUL_AI:
                t_orang = rute_it(i, "")
                if (("IT", i.sequence_id) not in OVERRIDE
                        and t_orang not in ("LEWATI",)
                        and ((m1 in MODUL_SAP and t_orang != "ITSAP") or
                             (m1 in MODUL_AI and t_orang != "ITAI"))):
                    print("   !    IT-%d konflik modul %s vs orang %s: ikut modul" % (
                        i.sequence_id, m1, t_orang))
            target_of[str(i.id)] = t
        # Anak ikut induk teratas.
        for i in semua:
            t = target_of[str(i.id)]
            p = i
            while p.parent_id and str(p.parent_id) in by_id:
                p = by_id[str(p.parent_id)]
            tp = target_of[str(p.id)]
            if t != tp:
                print("   ~    IT-%d ikut induk IT-%d -> %s" % (i.sequence_id, p.sequence_id, tp))
                target_of[str(i.id)] = tp
        for i in semua:
            t = target_of[str(i.id)]
            if t == "LEWATI":
                print("   ??   IT-%d TANPA BUKTI, dilewati: %s" % (i.sequence_id, i.name[:60]))
                n_lewat += 1
                continue
            if t == "HAPUS":
                print("   x    IT-%d hapus (test): %s" % (i.sequence_id, i.name[:60]))
                n_hapus += 1
                if APPLY:
                    Issue.objects.filter(pk=i.pk).update(deleted_at=timezone.now())
                continue
            mods = modul_of.get(str(i.id), [])
            print("   ->   IT-%d -> %s %s" % (
                i.sequence_id, t, ("[modul %s]" % mods[0] if mods else "")))
            n_pindah += 1
            if APPLY:
                issue_sebelum = Issue.objects.filter(pk=i.pk).values_list(
                    "project__identifier", flat=True).first()
                pindahkan(i, t, mods[0] if mods else "")
                peta_seq[(issue_sebelum, i.sequence_id)] = i.id

        print("\n3) HRGA + INVQC")
        for ident, tujuan in (("HRGA", "GA"),):
            p_lama = proj.get(ident)
            if p_lama is None:
                continue
            for i in Issue.objects.filter(
                    project=p_lama, deleted_at__isnull=True,
                    archived_at__isnull=True).order_by("sequence_id"):
                key = (ident, i.sequence_id)
                if key in HAPUS_TEST:
                    print("   x    %s-%d hapus (test): %s" % (ident, i.sequence_id, i.name[:60]))
                    n_hapus += 1
                    if APPLY:
                        Issue.objects.filter(pk=i.pk).update(deleted_at=timezone.now())
                    continue
                t = PINDAH_MANUAL.get(key, tujuan)
                print("   ->   %s-%d -> %s" % (ident, i.sequence_id, t))
                n_pindah += 1
                if APPLY:
                    pindahkan(i, t)
                    peta_seq[(ident, i.sequence_id)] = i.id
        p_inv = proj.get("INVQC")
        if p_inv is not None:
            for i in Issue.objects.filter(
                    project=p_inv, deleted_at__isnull=True,
                    archived_at__isnull=True).order_by("sequence_id"):
                print("   x    INVQC-%d hapus (test): %s" % (i.sequence_id, i.name[:60]))
                n_hapus += 1
                if APPLY:
                    Issue.objects.filter(pk=i.pk).update(deleted_at=timezone.now())

        print("\n4) Modul: bangun ulang per project tujuan")
        rencana_modul = {}
        for mi in ModuleIssue.objects.filter(
                issue__project=it, deleted_at__isnull=True).select_related("module"):
            issue = mi.issue
            if APPLY:
                baru = Issue.objects.filter(pk=issue.pk).first()
            else:
                baru = None
            tujuan_issue = None
            if baru is not None and baru.project.identifier in ("ITSAP", "ITAI"):
                tujuan_issue = baru.project.identifier
            else:
                # Uji kering: tebak dari target_of.
                t = target_of.get(str(issue.id))
                tujuan_issue = t if t in ("ITSAP", "ITAI") else None
            if tujuan_issue is None:
                # Tautan milik tugas arsip/hapus/tertahan: JANGAN disentuh.
                continue
            rencana_modul.setdefault((mi.module.name, tujuan_issue), []).append(
                (issue.sequence_id, mi))
        for (nama_mod, tujuan_issue), daftar in sorted(rencana_modul.items()):
            print("   %s modul %-18s -> %-5s <- %d tugas" % (
                "+" if APPLY else "rencana", nama_mod, tujuan_issue, len(daftar)))
            n_modul += len(daftar)
            if APPLY:
                mod_baru, dibuat = Module.objects.get_or_create(
                    project=proj[tujuan_issue], name=nama_mod,
                    defaults={"workspace": ws})
                if dibuat:
                    asal = Module.objects.filter(
                        project=it, name=nama_mod, deleted_at__isnull=True).first()
                    if asal is not None:
                        Module.objects.filter(pk=mod_baru.pk).update(
                            description=asal.description or "",
                            start_date=asal.start_date, target_date=asal.target_date,
                            status=asal.status, lead=asal.lead,
                            view_props=asal.view_props or {})
                        for mm in ModuleMember.objects.filter(
                                module=asal, deleted_at__isnull=True):
                            ModuleMember.objects.get_or_create(
                                module=mod_baru, member=mm.member)
                for _seq, mi in daftar:
                    baru_issue = Issue.objects.filter(pk=mi.issue_id).first()
                    ModuleIssue.objects.filter(pk=mi.pk).update(
                        deleted_at=timezone.now())
                    if baru_issue is not None:
                        ModuleIssue.objects.get_or_create(
                            module=mod_baru, issue=baru_issue)

        print("\n5) Bereskan payung kosong + FIN")
        for ident in ("IT", "HRGA", "INVQC", "SALES"):
            p = proj.get(ident)
            if p is None or p.deleted_at or p.archived_at:
                print("   -    %s sudah beres/dilewati" % ident)
                continue
            sisa = Issue.objects.filter(
                project=p, deleted_at__isnull=True, archived_at__isnull=True).count()
            if sisa:
                print("   !    %s masih berisi %d tugas: TIDAK diarsipkan" % (ident, sisa))
                continue
            print("   A    %s diarsipkan (kosong)" % ident)
            if APPLY:
                Project.objects.filter(pk=p.pk).update(archived_at=timezone.now())
        fin = proj.get("FIN")
        if fin is not None and not fin.deleted_at and fin.name != "Finance":
            print("   =    FIN diganti nama jadi 'Finance' (project FIN-FIN)")
            if APPLY:
                Project.objects.filter(pk=fin.pk).update(name="Finance")
        apar = proj.get("APAR")
        if apar is not None and not apar.deleted_at:
            isi = Issue.objects.filter(
                project=apar, deleted_at__isnull=True).count()
            if isi == 0:
                print("   x    APAR dipensiunkan (kosong, duplikat FIN-FIN)")
                if APPLY:
                    DepartemenProject.objects.filter(project=apar).update(
                        deleted_at=timezone.now())
                    Project.objects.filter(pk=apar.pk).update(deleted_at=timezone.now())
            else:
                print("   !    APAR berisi %d tugas: dibiarkan" % isi)

        if APPLY:
            print("\n6) Sinkron workspace (manager/divisi/direktur ikut project baru)")
            print("   perubahan keanggotaan: %d" % sinkronkan_workspace(ws.id))
        else:
            print("\n6) Sinkron dilewati (uji kering)")
            transaction.set_rollback(True)

print("-" * 70)
print("  pindah: %d - hapus(test): %d - modul: %d - tanpa bukti: %d" % (
    n_pindah, n_hapus, n_modul, n_lewat))
if not APPLY:
    print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
