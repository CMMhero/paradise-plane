# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian E1b, susulan E1: modul ikut pindah ke project baru.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-e1b-modul.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: get_or_create di mana-mana, aman dijalankan ulang.
#
# KENAPA SKRIP INI
# E1 memindahkan 195 tugas IT ke ITSAP/ITAI, TAPI loop modul-nya membaca tautan
# ModuleIssue lewat filter issue__project=<payung lama> SESUDAH tugasnya pindah
# -- hasilnya kosong, modul tidak tersalin dan tautan lama tetap aktif menunjuk
# ke modul milik payung yang kini terarsip. Skrip ini membereskannya: untuk
# setiap tautan aktif yang issue-nya sudah di project BARU sementara modulnya
# masih di project LAMA (terarsip), modul disalin ke project baru (nama sama,
# anggota + lead + tanggal ikut), tautan dipindah, tautan lama dinonaktifkan.

import os

from django.db import transaction
from django.utils import timezone

from plane.db.models import Module, ModuleIssue, ModuleMember, Workspace

APPLY = os.environ.get("ORG_APPLY") == "1"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

print("=" * 70)
print("E1b, modul ikut pindah   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

n_modul = n_taut = 0

with transaction.atomic():
    # Tautan aktif yang issue-nya sudah pindah tapi modulnya tertinggal.
    aneh = list(
        ModuleIssue.objects.filter(deleted_at__isnull=True)
        .select_related("module", "issue", "issue__project", "module__project")
    )
    aneh = [
        mi
        for mi in aneh
        if mi.issue.deleted_at is None
        and mi.issue.project_id != mi.module.project_id
        and mi.issue.project.workspace_id == ws.id
    ]
    print("\nTautan modul nyasar: %d" % len(aneh))
    by_modul = {}
    for mi in aneh:
        by_modul.setdefault(
            (mi.module.name, str(mi.module.project.identifier),
             str(mi.issue.project.identifier)), []).append(mi)
    for (nama, asal, tujuan), daftar in sorted(by_modul.items()):
        print("   %s %s (%s) -> %s: %d tugas" % (
            "+" if APPLY else "rencana", nama, asal, tujuan, len(daftar)))
        if not APPLY:
            n_modul += 1
            n_taut += len(daftar)
            continue
        p_tujuan = daftar[0].issue.project
        mod_baru, dibuat = Module.objects.get_or_create(
            project=p_tujuan, name=nama, defaults={"workspace": ws})
        if dibuat:
            asal_mod = daftar[0].module
            Module.objects.filter(pk=mod_baru.pk).update(
                description=asal_mod.description or "",
                start_date=asal_mod.start_date, target_date=asal_mod.target_date,
                status=asal_mod.status, lead=asal_mod.lead,
                view_props=asal_mod.view_props or {})
            for mm in ModuleMember.objects.filter(
                    module=asal_mod, deleted_at__isnull=True):
                ModuleMember.objects.get_or_create(
                    module=mod_baru, member=mm.member,
                    project=p_tujuan, workspace=ws)
        for mi in daftar:
            ModuleIssue.objects.filter(pk=mi.pk).update(deleted_at=timezone.now())
            ModuleIssue.objects.get_or_create(
                module=mod_baru, issue=mi.issue,
                project=p_tujuan, workspace=ws)
            n_taut += 1
        n_modul += 1

print("-" * 70)
print("  modul disalin: %d - tautan dipindah: %d" % (n_modul, n_taut))
if not APPLY:
    print("  UJI KERING, tidak ada yang ditulis.")
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
