# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian E3, pensiunkan project tanpa departemen yang kosong/test saja.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-e3-bersih-proyek.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: lewati yang sudah pensiun, aman dijalankan ulang.
#
# KENAPA SKRIP INI
# Permintaan user 2026-10-23: project yang tidak punya departemen/divisi DAN
# kosong atau isinya cuma test dihapus saja (WHMDN, WHBPN, BE, ...). Audit
# deployment 2026-10-24 memastikan tiap kandidat: 0 tugas non-hapus, tidak
# terpetakan, tidak terarsip. Anggota tidak dicabut (project-nya saja yang
# dipensiunkan; tidak ada yang yatim -- semua anggota punya project lain).
#
# SENGAJA TIDAK DISENTUH (ada isi riil / dipakai bersama):
#   PRICING (7 tugas handbook flange), MGMT (ruang direksi), WIKI (dipakai
#   bersama 70 anggota), ANNEALINGF (1 tugas vendor eksternal).

import os

from django.db import transaction
from django.utils import timezone

from plane.db.models import DepartemenProject, Issue, Project, Workspace

APPLY = os.environ.get("ORG_APPLY") == "1"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

# Project kosong yang dipensiunkan (identifier).
PENSIUN = ["BE", "RND", "TENDER", "WHBPN", "WHMDN"]

# Tugas test yang dihapus (identifier project, sequence). Projectnya TETAP ada.
HAPUS_TUGAS = [
    ("PRICING", 2),  # "test2"
]

print("=" * 70)
print("E3, pensiunkan project tanpa departemen   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

n_proyek = n_tugas = 0

with transaction.atomic():
    print("\n1) Pensiunkan project kosong tak-terpetakan")
    for ident in PENSIUN:
        p = Project.objects.filter(workspace=ws, identifier=ident, deleted_at__isnull=True).first()
        if p is None:
            print("   -    %s sudah pensiun/dilewati" % ident)
            continue
        if p.archived_at is not None:
            print("   -    %s terarsip (bukan aktif), dilewati" % ident)
            continue
        if DepartemenProject.objects.filter(project=p, deleted_at__isnull=True).exists():
            print("   !    %s sudah terpetakan: TIDAK dipensiunkan" % ident)
            continue
        isi = Issue.objects.filter(project=p, deleted_at__isnull=True).count()
        if isi:
            print("   !    %s berisi %d tugas: TIDAK dipensiunkan" % (ident, isi))
            continue
        print("   x    %s dipensiunkan (kosong, tanpa departemen)" % ident)
        n_proyek += 1
        if APPLY:
            Project.objects.filter(pk=p.pk).update(deleted_at=timezone.now())

    print("\n2) Hapus tugas test")
    for ident, seq in HAPUS_TUGAS:
        p = Project.objects.filter(workspace=ws, identifier=ident, deleted_at__isnull=True).first()
        if p is None:
            print("   -    %s-%d: project tidak ada" % (ident, seq))
            continue
        i = Issue.objects.filter(project=p, sequence_id=seq, deleted_at__isnull=True).first()
        if i is None:
            print("   -    %s-%d: sudah dihapus/dilewati" % (ident, seq))
            continue
        print("   x    %s-%d hapus (test): %s" % (ident, seq, (i.name or "")[:60]))
        n_tugas += 1
        if APPLY:
            Issue.objects.filter(pk=i.pk).update(deleted_at=timezone.now())

    if not APPLY:
        transaction.set_rollback(True)

print("-" * 70)
print("  project pensiun: %d - tugas test hapus: %d" % (n_proyek, n_tugas))
if not APPLY:
    print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
