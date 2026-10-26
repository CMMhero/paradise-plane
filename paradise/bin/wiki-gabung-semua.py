# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Masukkan SEMUA anggota workspace ke project Wiki (identifier WIKI).
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/wiki-gabung-semua.py
#
# Uji kering (default): tanpa WIKI_APPLY  |  Terapkan: WIKI_APPLY=1
# Workspace: WIKI_WORKSPACE (default pt-paradise-perkasa)
#
# Idempotent: yang sudah anggota aktif tidak disentuh (role-nya tidak diubah).
# Pasangannya signal `plane/db/wiki_default.py`, yang mengurus anggota BARU;
# skrip ini membereskan anggota LAMA.

import os

from django.db import transaction

from plane.db.models import Project, ProjectMember, Workspace, WorkspaceMember
from plane.db.wiki_default import IDENTIFIER_WIKI, gabungkan_ke_wiki

APPLY = os.environ.get("WIKI_APPLY") == "1"
SLUG = os.environ.get("WIKI_WORKSPACE", "pt-paradise-perkasa")

workspace = Workspace.objects.get(slug=SLUG)
wiki = Project.objects.filter(workspace=workspace, identifier=IDENTIFIER_WIKI, deleted_at__isnull=True).first()
print("=" * 70)
print("Gabung semua ke Wiki   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)
if wiki is None:
    print("  Project WIKI tidak ada di workspace %s. Tidak ada yang dikerjakan." % SLUG)
else:
    anggota = list(WorkspaceMember.objects.filter(workspace=workspace, is_active=True).values_list("member_id", "role"))
    sudah = set(
        ProjectMember.objects.filter(project=wiki, is_active=True).values_list("member_id", flat=True)
    )
    belum = [(uid, role) for uid, role in anggota if uid not in sudah]
    print("  anggota workspace: %d  |  sudah di Wiki: %d  |  belum: %d" % (len(anggota), len(sudah), len(belum)))
    if APPLY:
        with transaction.atomic():
            ditambah = sum(1 for uid, role in belum if gabungkan_ke_wiki(workspace.id, uid, role))
        print("  ditambahkan: %d" % ditambah)
    else:
        print("  (uji kering: tidak ada yang diubah; set WIKI_APPLY=1 untuk menerapkan)")
