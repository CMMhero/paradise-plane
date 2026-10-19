#!/usr/bin/env python3
# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Susun gambar pratinjau tautan (Open Graph) dari aset merek yang ada.

Gambar bawaan Plane adalah materi pemasaran mereka ("Modern project management,
powerful, flexible, and built to scale"), lengkap dengan logonya. Ia muncul tiap
kali seseorang membagikan tautan aplikasi di WhatsApp, Slack, atau Teams, dan di
situlah merek vendor paling terlihat oleh orang yang belum pernah membuka
aplikasinya.

Skrip ini disimpan, bukan sekadar gambarnya, supaya kalau logo atau nama berubah
tidak perlu ada yang membuka penyunting gambar dan menebak-nebak ukurannya.

Pakai:  python paradise/bin/buat-og-image.py
Hasil:  apps/web/app/assets/og-image.png (1200x630)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AKAR = Path(__file__).resolve().parents[2]
ASET = AKAR / "apps/web/app/assets"

# Diambil langsung dari piksel logonya, bukan dikira-kira.
MERAH = (0xED, 0x1F, 0x24)
NAVY = (0x27, 0x27, 0x5A)
ABU = (0x6B, 0x72, 0x80)
GARIS = (0xE5, 0xE7, 0xEB)

# 1200x630 adalah ukuran yang diminta Open Graph dan dipakai WhatsApp, Slack,
# Teams, dan Twitter. Rasio yang meleset akan dipotong sembarangan oleh mereka.
LEBAR, TINGGI = 1200, 630
TEPI = 92


def font(nama, ukuran):
    """Segoe UI kalau ada, Arial sebagai cadangan.

    Keduanya ada di Windows; di mesin lain skrip ini akan melempar, dan itu
    disengaja. Diam-diam jatuh ke font bawaan Pillow menghasilkan gambar yang
    terlihat rusak, dan itu lebih buruk daripada gagal terang-terangan.
    """
    for f in nama:
        p = Path("C:/Windows/Fonts") / f
        if p.exists():
            return ImageFont.truetype(str(p), ukuran)
    raise SystemExit(f"font tidak ditemukan: {nama}")


def main() -> None:
    kanvas = Image.new("RGB", (LEBAR, TINGGI), "white")
    d = ImageDraw.Draw(kanvas)

    # Pita merah setinggi kanvas. Satu elemen, satu warna merek, dan cukup untuk
    # membuat gambarnya terbaca sebagai milik seseorang alih-alih kartu kosong.
    d.rectangle([0, 0, 14, TINGGI], fill=MERAH)

    logo = Image.open(ASET / "images/paradise-logo.png").convert("RGBA")
    logo = logo.resize((104, 104), Image.LANCZOS)
    kanvas.paste(logo, (TEPI, 84), logo)

    d.text((TEPI, 224), "Paradise Task Tracker", font=font(["segoeuib.ttf", "arialbd.ttf"], 74), fill=NAVY)
    d.text(
        (TEPI, 322),
        "Manajemen proyek & issue internal",
        font=font(["segoeui.ttf", "arial.ttf"], 34),
        fill=ABU,
    )
    d.text(
        (TEPI, 366),
        "PT Paradise Perkasa",
        font=font(["seguisb.ttf", "arial.ttf"], 34),
        fill=ABU,
    )

    d.line([TEPI, 476, LEBAR - TEPI, 476], fill=GARIS, width=2)

    alamat = "space.paradiseperkasa.com"
    f_alamat = font(["segoeui.ttf", "arial.ttf"], 26)
    lebar_alamat = d.textlength(alamat, font=f_alamat)
    d.text((LEBAR - TEPI - lebar_alamat, 528), alamat, font=f_alamat, fill=ABU)

    keluar = ASET / "og-image.png"
    kanvas.save(keluar, "PNG", optimize=True)
    print(f"ditulis: {keluar.relative_to(AKAR)} ({keluar.stat().st_size} byte, {LEBAR}x{TINGGI})")


if __name__ == "__main__":
    main()
