# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian E5, pensiunkan payung gabungan + tempatkan spv SM-T1.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-e5-pensiun-payung.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: lewati yang sudah pindah/hapus, aman dijalankan ulang.
#
# KENAPA SKRIP INI
# Permintaan user 2026-10-24: project payung lama yang masih ada (IT, HRGA,
# INVQC, SALES) dihapus; kalau masih ada tugasnya, pindahkan dulu ke project
# yang sesuai. Audit 2026-10-24: hanya IT yang masih berisi (9 tugas ARSIP,
# 7 kerja SAP + 2 test). HRGA/INVQC/SALES sudah kosong (E1).
# Sekaligus: Abidin Manurau jadi supervisor Sales Tim 1 (kanon user).
#
# Arsip ikut pindah apa adanya (tetap arsip di project baru): riwayat tidak
# hilang, tapi payungnya bisa dipensiunkan.

import os

from django.db import transaction
from django.utils import timezone

from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.membership import jadikan_anggota_project
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Issue,
    IssueAssignee,
    IssueSequence,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    State,
    User,
    Workspace,
)
from plane.db.models.hierarki import TINGKAT_SUPERVISOR

APPLY = os.environ.get("ORG_APPLY") == "1"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

# (identifier payung, sequence) -> identifier tujuan / "HAPUS".
# Audit 2026-10-24: semua arsip IT adalah kerja SAP (sap3) kecuali 2 test.
PINDAH = {
    ("IT", 24): "ITSAP",
    ("IT", 31): "ITSAP",
    ("IT", 37): "ITSAP",
    ("IT", 38): "ITSAP",
    ("IT", 39): "ITSAP",
    ("IT", 41): "ITSAP",
    ("IT", 63): "HAPUS",  # "jjj" -- test
    ("IT", 66): "HAPUS",  # "kerjain ya" -- tanpa isi
    ("IT", 68): "ITSAP",  # BSD (assignee SAP)
}
PAYUNG = ["IT", "HRGA", "INVQC", "SALES"]

print("=" * 70)
print("E5, pensiunkan payung + spv SM-T1   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

n_pindah = n_hapus = n_payung = 0

with transaction.atomic():
    with tunda_sinkron():
        proj = {p.identifier: p for p in Project.objects.filter(workspace=ws, deleted_at__isnull=True)}

        def peta_state(p_tujuan):
            urut = State.objects.filter(project=p_tujuan, deleted_at__isnull=True).order_by("sequence")
            m = {}
            for s in urut:
                m.setdefault(s.group, s)
            return m, next((s for s in urut if s.default), urut.first())

        state_map = {}
        for ident in ("ITSAP", "ITAI"):
            if proj.get(ident) is not None and not proj[ident].archived_at:
                state_map[ident] = peta_state(proj[ident])

        print("\n1) Pindah sisa arsip payung IT")
        it = proj.get("IT")
        if it is None or it.deleted_at:
            print("   -    payung IT sudah tidak ada")
        else:
            sisa = list(Issue.objects.filter(
                project=it, deleted_at__isnull=True, archived_at__isnull=False
            ).select_related("state").order_by("sequence_id"))
            for i in sisa:
                t = PINDAH.get(("IT", i.sequence_id), "LEWATI")
                if t == "LEWATI":
                    print("   ??   IT-%d TANPA KEPUTUSAN, dilewati: %s" % (i.sequence_id, i.name[:50]))
                    continue
                if t == "HAPUS":
                    print("   x    IT-%d hapus (test): %s" % (i.sequence_id, i.name[:50]))
                    n_hapus += 1
                    if APPLY:
                        Issue.objects.filter(pk=i.pk).update(deleted_at=timezone.now())
                    continue
                p_tujuan = proj[t]
                m, bawaan = state_map[t]
                g = i.state.group if i.state_id else None
                print("   ->   IT-%d -> %s (tetap arsip)" % (i.sequence_id, t))
                n_pindah += 1
                if APPLY:
                    seq = IssueSequence.objects.filter(project=p_tujuan).order_by(
                        "-sequence").values_list("sequence", flat=True).first() or 0
                    Issue.objects.filter(pk=i.pk).update(
                        project=p_tujuan, sequence_id=seq + 1, state=m.get(g, bawaan))
                    IssueSequence.objects.create(issue=i, sequence=seq + 1, project=p_tujuan)
                    siapa = {i.created_by_id} | set(
                        IssueAssignee.objects.filter(
                            issue_id=i.id, deleted_at__isnull=True
                        ).values_list("assignee_id", flat=True))
                    for uid in siapa:
                        if uid is None:
                            continue
                        if not ProjectMember.objects.filter(
                                project=p_tujuan, member_id=uid, is_active=True,
                                deleted_at__isnull=True).exists():
                            asal = ProjectMember.objects.filter(
                                project=it, member_id=uid, deleted_at__isnull=True).first()
                            jadikan_anggota_project(
                                p_tujuan.pk, uid, (asal.role if asal else 15),
                                workspace_id=ws.id)

        print("\n2) Pensiunkan payung (harus kosong)")
        for ident in PAYUNG:
            p = proj.get(ident)
            if p is None or p.deleted_at:
                print("   -    %s sudah pensiun/dilewati" % ident)
                continue
            sisa = Issue.objects.filter(project=p, deleted_at__isnull=True).count()
            if sisa:
                print("   !    %s masih berisi %d tugas: TIDAK dipensiunkan" % (ident, sisa))
                continue
            print("   x    %s dipensiunkan (payung gabungan)" % ident)
            n_payung += 1
            if APPLY:
                Project.objects.filter(pk=p.pk).update(deleted_at=timezone.now())

        print("\n3) Abidin Manurau -> supervisor SM-T1")
        smt1 = Departemen.objects.filter(
            workspace=ws, kode="SM-T1", deleted_at__isnull=True).first()
        abi = User.objects.filter(email="manroe@paradiseperkasa.com", is_active=True).first()
        if smt1 is None or abi is None:
            print("   !    data tidak lengkap (dept=%s user=%s), dilewati" % (smt1, abi))
        else:
            baris = list(JabatanOrganisasi.objects.filter(
                workspace=ws, member=abi, deleted_at__isnull=True))
            if len(baris) == 1 and baris[0].tingkat == TINGKAT_SUPERVISOR and baris[0].departemen_id == smt1.id:
                print("   -    Abidin sudah spv SM-T1")
            else:
                print("   +    Abidin ditempatkan spv SM-T1 (baris %d -> 1)" % len(baris))
                if APPLY:
                    for b in baris:
                        JabatanOrganisasi.objects.filter(pk=b.pk).update(deleted_at=timezone.now())
                    JabatanOrganisasi.objects.create(
                        workspace=ws, member=abi, tingkat=TINGKAT_SUPERVISOR,
                        departemen=smt1, divisi=None, sumber="migrasi-e5",
                        catatan="Supervisor Sales Tim 1 (kanon user 2026-10-24)")

        if APPLY:
            print("\n4) Sinkron workspace")
            print("   perubahan keanggotaan: %d" % sinkronkan_workspace(ws.id))
        else:
            print("\n4) Sinkron dilewati (uji kering)")
            transaction.set_rollback(True)

print("-" * 70)
print("  pindah arsip: %d - hapus test: %d - payung pensiun: %d" % (n_pindah, n_hapus, n_payung))
if not APPLY:
    print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
