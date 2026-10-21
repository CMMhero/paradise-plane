# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian D2, zona waktu bawaan Asia/Jakarta untuk akun yang masih bawaan pabrik.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-d2-zona-waktu.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
#
# Yang diubah HANYA akun yang masih bernilai "UTC" persis (nilai bawaan kolom
# sejak awal, bukan pilihan sadar -- kantor ini di WIB dan tidak ada alasan
# operasional memakai UTC). Akun yang sudah memilih zona lain (mis. yang sudah
# Asia/Jakarta) TIDAK disentuh. Idempotent: dijalankan ulang tidak mengubah
# apa pun karena penyaringnya hanya yang masih UTC.
#
# Pasangan skema-nya migrasi 0144 (default kolom user_timezone jadi
# Asia/Jakarta) -- migrasi mengurus akun BARU, skrip ini membereskan
# 116 akun lama. Keduanya harus ada; salah satu saja meninggalkan lubang.

import os

from django.db import transaction

from plane.db.models import User

APPLY = os.environ.get("ORG_APPLY") == "1"
BARU = "Asia/Jakarta"
LAMA = "UTC"

print("=" * 70)
print("D2, zona waktu UTC -> Asia/Jakarta   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

qs = User.objects.filter(is_active=True, user_timezone=LAMA).order_by("email")
total = qs.count()
print("  akun masih UTC: %d" % total)
contoh = list(qs.values_list("email", flat=True)[:15])
for email in contoh:
    print("    - %s" % email)
if total > len(contoh):
    print("    ... dan %d lagi" % (total - len(contoh)))

non_utc = (
    User.objects.filter(is_active=True)
    .exclude(user_timezone=LAMA)
    .values_list("user_timezone", flat=True)
    .distinct()
)
print("  nilai lain yang ada (TIDAK disentuh): %s" % (", ".join(sorted(non_utc)) or "-"))

with transaction.atomic():
    if APPLY:
        n = qs.update(user_timezone=BARU)
        print("  diubah: %d akun -> %s" % (n, BARU))
    else:
        print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 70)
if not APPLY:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
