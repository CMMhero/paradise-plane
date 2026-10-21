# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Bagian A2, akun: serah-terima email, ganti alamat, buat akun baru, buang akun uji
#
# Jalankan:
#   docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/org-migrate-a2-accounts.py
#
# Uji kering (default):  tanpa ORG_APPLY
# Terapkan:              ORG_APPLY=1
#
# Idempotent: tiap langkah memeriksa keadaan dulu, aman dijalankan ulang.
# TIDAK menyentuh keanggotaan project maupun peran, itu A3.

import os

from django.db import transaction

from plane.db.models import User, Workspace, WorkspaceMember

APPLY = os.environ.get("ORG_APPLY") == "1"
DEFAULT_PASSWORD = "P@ssw0rd"  # sama dengan seed 77 karyawan; wajib ganti saat login pertama

ws = Workspace.objects.get(slug="pt-paradise-perkasa")


def uname(email):
    """Pola username di repo ini: email dengan '.' dan '@' jadi '_'."""
    return email.replace(".", "_").replace("@", "_")


def split_nama(nama):
    bagian = nama.split()
    return bagian[0], " ".join(bagian[1:]) if len(bagian) > 1 else ""


# --- 1. Email berpindah tangan (konflik identitas, dikonfirmasi user) --------
# Akun ini dulu dipegang orang lain, sekarang pemiliknya berbeda.
# Aman: sudah diperiksa, KEDUANYA nol riwayat (0 issue, 0 worklog, 0 komentar,
# 0 halaman, belum pernah login), jadi tidak ada jejak milik pemilik lama yang
# ikut berpindah nama.
SERAH_TERIMA = [
    ("acc.stf1@paradiseperkasa.com", "Oky Lianto", "Raymond Mainaki"),
    ("it.support2@itechmandiri.com", "Andri Andreas", "Dimas"),
]

# --- 2. Ganti alamat email (K3) ---------------------------------------------
# Orang yang sama, alamat berbeda antara sistem dan file. File yang dipakai.
# Akun TIDAK dibuat ulang supaya riwayat & keanggotaan lama tetap menempel.
GANTI_EMAIL = [
    ("sls.coo7@paradiseperkasa.com", "alex@paradiseperkasa.com", "Alexander Feri Wijaya Ali"),
    ("andywijaya@paradiseperkasa.com", "andy.wijaya@paradiseperkasa.com", "Andy Wijaya Saragih"),
    ("scm.stf3@paradiseperkasa.com", "michel@paradiseperkasa.com", "Michel Famena Surya Putri"),
    ("alkindy@paradiseperkasa.com", "scm.stf1@paradiseperkasa.com", "Muhammad Yos Alkindy"),
    ("kurniawan@ctadvance.co.id", "kurniawan@paradiseperkasa.com", "Kurniawan Basari"),
]

# --- 3. Akun baru (10) ------------------------------------------------------
AKUN_BARU = [
    ("tan.andy@paradiseperkasa.com", "Andy Oentoro"),
    ("sls.coo12@paradiseperkasa.com", "Johanris Rapael Gultom"),
    ("sls.adm2@paradiseperkasa.com", "Maria Setri Margining Widhi"),
    ("sls.adm1@paradiseperkasa.com", "Patricia Evionita"),
    ("mkt.stf1@paradiseperkasa.com", "Ade Tri Hartati Sidabutar"),
    ("inv.stf1@paradiseperkasa.com", "Aranti Sisca"),
    ("lgl.stf2@paradiseperkasa.com", "Muhammad Nabil Ilfas"),
    ("lgl.stf1@paradiseperkasa.com", "Muhammad Adhitya Yusra"),
    ("it.dev1@itechmandiri.com", "Andri Andreas"),
    ("it.sap2@itechmandiri.com", "Oky Lianto"),
]

# --- 4. Akun uji dibuang (K8) -----------------------------------------------
AKUN_UJI = "tester@paradiseperkasa.com"

print("=" * 70)
print("A2, akun   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("=" * 70)

with transaction.atomic():
    print("\n1) Serah-terima email (pemilik berganti)")
    for email, lama, baru in SERAH_TERIMA:
        u = User.objects.filter(email=email).first()
        if not u:
            print(f"   ! {email} tidak ada, dilewati")
            continue
        if u.display_name == baru:
            print(f"   ada  {email:<34} sudah {baru}")
            continue
        f, l = split_nama(baru)
        print(f"   UBAH {email:<34} {u.display_name} -> {baru}")
        if APPLY:
            u.display_name, u.first_name, u.last_name = baru, f, l
            u.save(update_fields=["display_name", "first_name", "last_name"])

    print("\n2) Ganti alamat email (orang sama, alamat beda)")
    for lama, baru, nama in GANTI_EMAIL:
        u = User.objects.filter(email=lama).first()
        if not u:
            if User.objects.filter(email=baru).exists():
                print(f"   ada  {baru:<34} sudah dipakai {nama}")
            else:
                print(f"   ! {lama} tidak ada dan {baru} juga tidak, dilewati")
            continue
        if User.objects.filter(email=baru).exclude(pk=u.pk).exists():
            print(f"   !! BENTROK {baru} sudah dipakai akun lain, DILEWATI, perlu ditinjau")
            continue
        print(f"   UBAH {lama:<34} -> {baru}  ({nama})")
        if APPLY:
            u.email, u.username = baru, uname(baru)
            u.save(update_fields=["email", "username"])

    print("\n3) Akun baru")
    dibuat = 0
    for email, nama in AKUN_BARU:
        if User.objects.filter(email=email).exists():
            print(f"   ada  {email:<34} {nama}")
            continue
        print(f"   BUAT {email:<34} {nama}")
        dibuat += 1
        if APPLY:
            f, l = split_nama(nama)
            u = User.objects.create(
                email=email,
                username=uname(email),
                display_name=nama,
                first_name=f,
                last_name=l,
                is_password_autoset=False,
            )
            u.set_password(DEFAULT_PASSWORD)
            u.save()
            # Tanpa WorkspaceMember, user tidak bisa masuk workspace sama sekali.
            WorkspaceMember.objects.get_or_create(
                workspace=ws, member=u, defaults={"role": 15}
            )

    print("\n4) Akun uji dibuang")
    t = User.objects.filter(email=AKUN_UJI).first()
    if not t:
        print(f"   ada  {AKUN_UJI} sudah tidak ada")
    elif not t.is_active:
        print(f"   ada  {AKUN_UJI} sudah nonaktif")
    else:
        # Dinonaktifkan, bukan dihapus permanen: menghapus baris User akan
        # memutus rujukan di audit log dan riwayat mana pun yang menyentuhnya.
        # Nonaktif sudah cukup, tidak bisa login, tidak muncul sebagai anggota.
        print(f"   NONAKTIFKAN {AKUN_UJI}  ({t.display_name})")
        if APPLY:
            t.is_active = False
            t.save(update_fields=["is_active"])
            WorkspaceMember.objects.filter(workspace=ws, member=t).delete()

    if not APPLY:
        print("\n  UJI KERING, membatalkan transaksi, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 70)
print(f"  total akun aktif: {User.objects.filter(is_active=True, is_bot=False).count()}")
if not APPLY:
    print("  Jalankan dengan ORG_APPLY=1 untuk menerapkan.")
