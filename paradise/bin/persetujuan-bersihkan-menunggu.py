# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bersihkan pengajuan persetujuan lama yang masih MENUNGGU.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/persetujuan-bersihkan-menunggu.py
#
# Uji kering (default): tanpa PERSETUJUAN_APPLY  |  Terapkan: PERSETUJUAN_APPLY=1
#
# Keputusan user 2026-10-26: persetujuan HANYA ditagih saat staf menggeser tugas
# ke selesai. Pengajuan lama lahir saat tugas DIBUAT, jadi tugasnya masih
# terbuka -- pengajuannya dicabut dan baru muncul lagi kalau staf mencoba
# menyelesaikan tugasnya. Tugas yang SUDAH selesai tidak diajukan ulang
# ("abaikan yang sudah tersimpan"), jadi pengajuan menunggunya ikut dicabut.
#
# Pencabutan = soft delete (riwayat tetap ada, bisa dipulihkan). Pengajuan yang
# sudah disetujui/ditolak TIDAK disentuh. Idempotent.

import os
from collections import Counter

from plane.db.models import PersetujuanPenugasan, STATUS_PERSETUJUAN_MENUNGGU

APPLY = os.environ.get("PERSETUJUAN_APPLY") == "1"

print("=" * 70)
print("Bersihkan pengajuan menunggu   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

baris = list(
    PersetujuanPenugasan.objects.filter(status=STATUS_PERSETUJUAN_MENUNGGU).select_related("issue__state")
)
hitung = Counter()
for b in baris:
    issue = b.issue
    if issue is None or issue.deleted_at is not None:
        hitung["tugas dihapus/hilang"] += 1
    elif issue.state_id and issue.state.group == "completed":
        hitung["tugas sudah selesai"] += 1
    else:
        hitung["tugas masih terbuka"] += 1

print("  pengajuan menunggu: %d" % len(baris))
for kunci, n in hitung.most_common():
    print("    - %s: %d" % (kunci, n))

if APPLY:
    for b in baris:
        b.delete()  # soft delete: riwayat tetap ada
    print("  dicabut: %d" % len(baris))
else:
    print("  (uji kering: tidak ada yang diubah; set PERSETUJUAN_APPLY=1 untuk menerapkan)")
