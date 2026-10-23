# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian E4, emoji + zona waktu project.
#
# Jalankan:
#   docker exec -i api python manage.py shell < paradise/bin/org-migrate-e4-emoji-zona.py
#
# Uji kering (default): tanpa ORG_APPLY  |  Terapkan: ORG_APPLY=1
# Idempotent: hanya menulis yang beda, aman dijalankan ulang.
#
# KENAPA SKRIP INI
# Permintaan user 2026-10-24: tiap project punya emoji yang cocok, dan semua
# project berzona Asia/Jakarta. Perilaku bawaan SUDAH benar (Project.save memakai
# workspace.timezone = Asia/Jakarta kalau tidak diisi eksplisit); yang diperbaiki
# di sini warisan lama: project yang lahir saat workspace masih UTC/Bangkok.
#
# Project arsip/terhapus tidak disentuh (tak terlihat); project E3 (BE/RND/
# TENDER/WHBPN/WHMDN) tidak diberi emoji karena akan dipensiunkan.

import os

from django.db import transaction

from plane.db.models import Project, Workspace

APPLY = os.environ.get("ORG_APPLY") == "1"
ZONA = "Asia/Jakarta"

ws = Workspace.objects.get(slug="pt-paradise-perkasa")

EMOJI = {
    "ACC": "\U0001F9FE",  # Accounting
    "ANNEALINGF": "\U0001F525",  # Annealing Furnace
    "FIN": "\U0001F4B0",  # Finance
    "GA": "\U0001F3E2",  # General Affairs
    "HR": "\U0001F9D1\u200D\u0001F4BC",  # Human Resources
    "INV": "\U0001F4E6",  # Stock Control
    "ITAI": "\U0001F916",  # IT AI dan Infrastruktur
    "ITSAP": "\U0001F5A5\uFE0F",  # IT SAP Support Project
    "LEGAL": "\u2696\uFE0F",  # Legal
    "MGMT": "\U0001F3DB\uFE0F",  # Management
    "MKT": "\U0001F4E3",  # Marketing
    "OFL": "\U0001F69A",  # Order Fulfillment
    "PRICING": "\U0001F3F7\uFE0F",  # Pricing
    "PROC": "\U0001F6D2",  # Procurement
    "SHIP": "\U0001F6A2",  # Shipping
    "SMT1": "\U0001F4BC",  # Sales Tim 1
    "SMT2": "\U0001F91D",  # Sales Tim 2
    "WH178": "\U0001F3ED",  # Warehouse 178
    "WIKI": "\U0001F4DA",  # Wiki
}

print("=" * 70)
print("E4, emoji + zona waktu project   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)
print("zona workspace: %s (bawaan project baru mengikuti ini)" % ws.timezone)

n_emoji = n_zona = n_logo = 0

with transaction.atomic():
    hidup = list(Project.objects.filter(
        workspace=ws, deleted_at__isnull=True, archived_at__isnull=True))
    print("\n1) Emoji project (%d aktif)" % len(hidup))
    for p in sorted(hidup, key=lambda x: x.identifier):
        mau = EMOJI.get(p.identifier)
        if mau is None:
            print("   -    %s: tanpa emoji (tak dikenal, dilewati)" % p.identifier)
            continue
        if p.emoji == mau:
            continue
        print("   %s   %s %s" % ("+" if APPLY else "rencana", p.identifier, mau))
        n_emoji += 1
        if APPLY:
            Project.objects.filter(pk=p.pk).update(emoji=mau)

    print("\n2b) Logo project <- emoji (yang tampil di sidebar/dropdown)")
    print("   (Logo menyimpan desimal codepoint dash-pisah ala emoji picker,")
    print("   mis. 💰 -> '128176'. Karakter mentah tidak dirender komponen Logo.)")
    for p in sorted(hidup, key=lambda x: x.identifier):
        if not p.emoji:
            continue
        desimal = "-".join(str(ord(c)) for c in p.emoji)
        logo = p.logo_props or {}
        if logo.get("in_use") == "emoji" and (logo.get("emoji") or {}).get("value") == desimal:
            continue
        print("   %s   %s logo <- %s (%s)" % ("+" if APPLY else "rencana", p.identifier, p.emoji, desimal))
        n_logo += 1
        if APPLY:
            Project.objects.filter(pk=p.pk).update(
                logo_props={"in_use": "emoji", "emoji": {"value": desimal}})

    print("\n2) Zona waktu -> %s" % ZONA)
    for p in sorted(hidup, key=lambda x: x.identifier):
        if p.timezone == ZONA:
            continue
        print("   %s   %s %s -> %s" % ("+" if APPLY else "rencana", p.identifier, p.timezone, ZONA))
        n_zona += 1
        if APPLY:
            Project.objects.filter(pk=p.pk).update(timezone=ZONA)

    if not APPLY:
        transaction.set_rollback(True)

print("-" * 70)
print("  emoji: %d - logo: %d - zona waktu: %d" % (n_emoji, n_logo, n_zona))
if not APPLY:
    print("  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
