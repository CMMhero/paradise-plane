# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian E2, tegakkan 1 project per departemen.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-e2-satu-project.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: get-or-skip, aman dijalankan ulang. Menulis lewat queryset.update()
# supaya tidak memicu sinyal aktivitas/notifikasi.
#
# KENAPA SKRIP INI
# Permintaan user 2026-10-23: tiap departemen tepat satu project. Audit pasca-E1
# menemukan dua pelanggar (sisanya sudah 1:1):
#   SCM-STC : INV + QC (keduanya kosong) -> QC dipensiunkan, INV jadi "Stock Control".
#   HRGA-GA : GA + SEC + OPR + BME (1 tugas di BME) -> tugas pindah ke GA,
#             SEC/OPR/BME dipensiunkan (semuanya kosong sesudah pindah).
# Keputusan user yang TIDAK diubah skrip ini: tidak ada divisi/departemen baru
# (MGMT tetap pengecualian lintas-divisi; Security/Operator tetap fungsi GA),
# payung arsip/legacy dan project tak-terpetakan lain dibiarkan.

import os

from django.db import transaction
from django.utils import timezone

from plane.db.jangkauan import sinkronkan_workspace, tunda_sinkron
from plane.db.membership import jadikan_anggota_project
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Issue,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    State,
    Workspace,
)
from plane.db.models.hierarki import TINGKAT_MANAGER

APPLY = os.environ.get("ORG_APPLY") == "1"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

print("=" * 70)
print("E2, satu project per departemen   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

n_pindah = n_pensiun = 0

with transaction.atomic():
    with tunda_sinkron():
        proj = {p.identifier: p for p in Project.objects.filter(
            workspace=ws, deleted_at__isnull=True)}

        def isi(p):
            return Issue.objects.filter(project=p, deleted_at__isnull=True).count()

        def terbuka(p):
            return Issue.objects.filter(
                project=p, deleted_at__isnull=True, archived_at__isnull=True).count()

        def pensiunkan(ident, alasan):
            global n_pensiun
            p = proj.get(ident)
            if p is None or p.deleted_at:
                print("   -    %s sudah pensiun/dilewati" % ident)
                return
            total, buka = isi(p), terbuka(p)
            if total or buka:
                print("   !    %s berisi %d tugas (%d terbuka): TIDAK dipensiunkan" % (
                    ident, total, buka))
                return
            print("   x    %s dipensiunkan (%s)" % (ident, alasan))
            n_pensiun += 1
            if APPLY:
                DepartemenProject.objects.filter(project=p).update(
                    deleted_at=timezone.now())
                Project.objects.filter(pk=p.pk).update(deleted_at=timezone.now())

        print("\n1) SCM-STC -> satu project Stock Control")
        inv = proj.get("INV")
        if inv is not None and inv.name != "Stock Control":
            print("   =    INV diganti nama jadi 'Stock Control'")
            if APPLY:
                Project.objects.filter(pk=inv.pk).update(name="Stock Control")
        else:
            print("   -    INV sudah bernama Stock Control/dilewati")
        pensiunkan("QC", "kosong, duplikat SCM-STC")

        print("\n2) HRGA-GA -> satu project General Affairs")
        ga = proj.get("GA")
        bme = proj.get("BME")
        if ga is not None and bme is not None and not ga.deleted_at and not bme.deleted_at:
            states = list(State.objects.filter(
                project=ga, deleted_at__isnull=True).order_by("sequence"))
            if not states:
                print("   !    GA tidak punya state: pindahan BME ditahan")
                states = None
            peta = {}
            for s in states:
                peta.setdefault(s.group, s)
            for i in Issue.objects.filter(
                    project=bme, deleted_at__isnull=True,
                    archived_at__isnull=True).order_by("sequence_id"):
                g = i.state.group if i.state_id else None
                print("   ->   BME-%d -> GA" % i.sequence_id)
                n_pindah += 1
                if APPLY and states:
                    from plane.db.models import IssueAssignee
                    Issue.objects.filter(pk=i.pk).update(
                        project=ga, state=peta.get(g, states[0]))
                    siapa = {i.created_by_id} | set(
                        IssueAssignee.objects.filter(
                            issue_id=i.id, deleted_at__isnull=True
                        ).values_list("assignee_id", flat=True))
                    for uid in siapa:
                        if uid is None:
                            continue
                        if not ProjectMember.objects.filter(
                                project=ga, member_id=uid, is_active=True,
                                deleted_at__isnull=True).exists():
                            asal = ProjectMember.objects.filter(
                                project=bme, member_id=uid,
                                deleted_at__isnull=True).first()
                            jadikan_anggota_project(
                                ga.pk, uid, (asal.role if asal else 15),
                                workspace_id=ws.id)
        pensiunkan("SEC", "kosong, fungsi GA")
        pensiunkan("OPR", "kosong, fungsi GA")
        pensiunkan("BME", "kosong sesudah pindah, fungsi GA")

        print("\n2b) Sales legacy: SMADM/SMCOO/SMIND + departemen non-kanon")
        # Kanon user: SM-T1/SM-T2/SM-MKT. Tiga pecahan admin/koordinator/
        # independen tidak ada di kanon, kosong, tanpa anggota -> pensiunkan
        # projectnya dan hapus departemennya (lembut, bisa dikembalikan).
        pensiunkan("SMADM", "kosong, di luar kanon")
        pensiunkan("SMCOO", "kosong, di luar kanon")
        pensiunkan("SMIND", "kosong, di luar kanon")
        for kode in ("SM-ADM", "SM-COO", "SM-IND"):
            d = Departemen.objects.filter(
                workspace=ws, kode=kode, deleted_at__isnull=True).first()
            if d is None:
                print("   -    dept %s sudah tidak ada" % kode)
                continue
            berpenghuni = JabatanOrganisasi.objects.filter(
                workspace=ws, departemen=d, deleted_at__isnull=True).count()
            if berpenghuni:
                print("   !    dept %s masih berisi %d penempatan: TIDAK dihapus" % (
                    kode, berpenghuni))
                continue
            print("   x    dept %s dihapus (kosong, di luar kanon)" % kode)
            if APPLY:
                Departemen.objects.filter(pk=d.pk).update(
                    deleted_at=timezone.now())

        print("\n3) Verifikasi 1:1 (project aktif tak-terarsip per departemen)")
        semua_ok = True
        for d in sorted(ws.departemen_organisasi.filter(
                deleted_at__isnull=True), key=lambda x: x.kode):
            ada = [m.project for m in DepartemenProject.objects.filter(
                departemen=d, deleted_at__isnull=True
            ).select_related("project") if not m.project.deleted_at
                and not m.project.archived_at]
            tandai = "OK " if len(ada) <= 1 else "LEBIH"
            if len(ada) > 1:
                semua_ok = False
            print("   %s %-9s %d: %s" % (
                tandai, d.kode, len(ada), ",".join(p.identifier for p in ada)))
        print("   1:1 %s" % ("TERPENUHI" if semua_ok else "BELUM (lihat LEBIH)"))

        print("\n3b) Manager divisi vs kanon user (laporan)")
        from plane.db.models import User
        for nama, kodiv in (
                ("lita komalasari", "FIN"), ("suarno radin", "IT"),
                ("yan tandi raru", "SCM"), ("anthony", "SM")):
            kunci = nama.split()[0]
            calon = list(User.objects.filter(is_active=True))
            cocok = [u for u in calon
                     if kunci in (u.email or "").lower()
                     or kunci in (u.first_name or "").lower()
                     or kunci in (u.display_name or "").lower()]
            if len(cocok) != 1:
                print("   ??   %-16s calon: %s" % (
                    nama, ", ".join(u.email for u in cocok) or "-"))
                continue
            u = cocok[0]
            j = JabatanOrganisasi.objects.filter(
                workspace=ws, member=u, deleted_at__isnull=True).first()
            sudah = (j is not None and j.tingkat == TINGKAT_MANAGER
                     and j.divisi is not None and j.divisi.kode == kodiv)
            print("   %s %-16s %s (tingkat=%s divisi=%s)" % (
                "OK  " if sudah else "CEK  ", nama, u.email,
                j.tingkat if j else "-",
                j.divisi.kode if j and j.divisi else "-"))

        if APPLY:
            print("\n4) Sinkron workspace")
            print("   perubahan keanggotaan: %d" % sinkronkan_workspace(ws.id))
        else:
            print("\n4) Sinkron dilewati (uji kering)")
            transaction.set_rollback(True)

print("-" * 70)
print("  pindah: %d - pensiun: %d" % (n_pindah, n_pensiun))
if not APPLY:
    print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
