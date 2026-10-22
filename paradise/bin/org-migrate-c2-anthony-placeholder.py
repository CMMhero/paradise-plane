# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian C2, akun placeholder Anthony (manager Sales & Marketing)
#
# Jalankan:
#   docker exec -i -e ORG_APPLY=1 pradise_plane-api-1 python manage.py shell < paradise/bin/org-migrate-c2-anthony-placeholder.py
#
# Uji kering (default): tanpa ORG_APPLY   |   Terapkan: ORG_APPLY=1
#
# "Anthony" belum punya email dari IT, tapi kursi Manager SM harus terisi supaya
# Sales & Marketing punya penanggung jawab di struktur. Akun ini PLACEHOLDER:
# begitu email asli dari IT ada, ganti email akun ini (bukan buat akun baru)
# supaya penempatan Manager SM-nya ikut pindah. Pola akun mengikuti A2
# (password default sama, wajib ganti saat login pertama).
#
# Penempatannya sendiri dikerjakan C1 (idempotent): jalankan ulang C1 sesudah
# akun ini ada, Anthony otomatis jadi Manager SM. Skrip ini HANYA membuat akun.

import os

from django.db import transaction

from plane.db.models import User, Workspace, WorkspaceMember

APPLY = os.environ.get("ORG_APPLY") == "1"
DEFAULT_PASSWORD = "P@ssw0rd"  # sama dengan seed/A2; wajib ganti saat login pertama

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

EMAIL = "anthony@paradiseperkasa.com"
NAMA = "Anthony"


def uname(email):
    return email.replace(".", "_").replace("@", "_")


print("=" * 70)
print("C2, akun placeholder Anthony   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

with transaction.atomic():
    u = User.objects.filter(email=EMAIL).first()
    if u:
        print(f"   ada  {EMAIL} sudah ada ({u.display_name}), akun tidak dibuat ulang")
    else:
        print(f"   BUAT {EMAIL}  ({NAMA} — PLACEHOLDER, ganti email saat email asli dari IT ada)")
        if APPLY:
            u = User.objects.create(
                email=EMAIL,
                username=uname(EMAIL),
                display_name=NAMA,
                first_name=NAMA,
                last_name="",
                is_password_autoset=False,
            )
            u.set_password(DEFAULT_PASSWORD)
            u.save()

    if u and APPLY:
        # Tanpa WorkspaceMember, user tidak bisa masuk workspace sama sekali.
        WorkspaceMember.objects.get_or_create(workspace=ws, member=u, defaults={"role": 15})

    if u:
        print(f"   akun aktif: {u.is_active} | di workspace: ", end="")
        if APPLY:
            print(WorkspaceMember.objects.filter(workspace=ws, member=u).exists())
        else:
            print("(uji kering, tidak diubah)")
    else:
        print("   (uji kering, akun belum dibuat)")

    if not APPLY:
        print("\n  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 70)
print("  Langkah berikut: jalankan ulang C1 (idempotent) untuk menempatkan")
print("  Anthony sebagai Manager SM.")
if not APPLY:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
