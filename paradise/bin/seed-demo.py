# Seed organisasi CONTOH untuk pengembangan lokal
# SPDX-License-Identifier: AGPL-3.0-only
#
# Jalankan:
#   docker compose -f docker-compose-local.yml exec -T api \
#       python manage.py shell < paradise/bin/seed-demo.py
#
# Uji kering (default): tanpa SEED_DEMO_APPLY  |  Terapkan: SEED_DEMO_APPLY=1
#
# KENAPA BERKAS INI ADA
#
# `git clone` menghasilkan instance yang KOSONG, dan di instance kosong Wiki
# tidak bisa dipakai sama sekali. Bukan satu bug, melainkan lima gerbang:
#
#   1. Rute /wiki meresolusi project dari identifier "WIKI" saat runtime.
#      Nol project = layar "Wiki belum tersedia", tanpa tombol apa pun.
#   2. Tombol "Divisi baru" hanya muncul untuk admin project Wiki.
#   3. Divisi baru lahir tanpa baris WikiFolderAccess, dan folder teratas tanpa
#      pemilik BUKAN berarti bebas melainkan TERKUNCI.
#   4. "Divisi pemilik" itu project LAIN. Di instance yang cuma punya project
#      Wiki, daftar pilihannya kosong.
#   5. Tanpa baris WikiGovernedProject, seluruh lapisan ACL Wiki DILEWATI, jadi
#      lokal diam-diam berperilaku lebih longgar daripada produksi.
#
# Dua seed lama TIDAK bisa dipakai untuk ini: `seed-wiki.py` dan
# `seed-wiki-access.py` dipatok ke workspace `pt-paradise-perkasa` dan ke email
# karyawan sungguhan, jadi baris pertamanya langsung melempar DoesNotExist di
# mesin orang lain. Keduanya alat pemulihan produksi, bukan installer.
#
# Berkas ini membuat organisasi FIKTIF. Struktur divisi pelanggan sungguhan
# tidak dibawa-bawa ke repo produk.
#
# UNTUK PENGEMBANGAN LOKAL SAJA. Ia membuat akun dengan sandi seragam yang
# tertulis di sini. Jangan pernah menjalankannya ke instance yang dipakai orang.
#
# JEBAKAN YANG SUDAH DITANGANI DI SINI
#
# `BaseModel.save()` menimpa `created_by` dengan pengguna dari request, dan di
# dalam `manage.py shell` tidak ada request. Jadi `Model.objects.create(
# created_by=X)` diam-diam menghasilkan `created_by = None`. Semua penulisan di
# bawah lewat `simpan()` yang mengirim `save(created_by_id=...)`.

# KENAPA JUMLAH ANGGOTA WIKI LEBIH BANYAK DARI YANG DISEBUT DI SINI
#
# `post_save` di `db/superadmin.py:165` memasukkan SETIAP Super Admin instance
# ke setiap project yang baru lahir, dengan role 20. Jadi di instance yang sudah
# punya beberapa Super Admin, jumlah anggota project Wiki akan lebih besar dari
# lima. Itu perilaku yang benar, bukan kebocoran seed ini.

import os

from django.db import transaction

from plane.db.models import (
    Page,
    Profile,
    Project,
    ProjectMember,
    ProjectPage,
    ProjectUserProperty,
    State,
    User,
    WikiFolderAccess,
    WikiGovernedProject,
    Workspace,
    WorkspaceMember,
)
from plane.db.models.state import DEFAULT_STATES
from plane.utils.wiki_access import can_edit_wiki_page, is_division_lead

try:
    from plane.db.models import ProjectIdentifier
except ImportError:
    ProjectIdentifier = None

APPLY = os.environ.get("SEED_DEMO_APPLY") == "1"
SLUG = os.environ.get("SEED_DEMO_WORKSPACE", "nomaden-demo")
NAMA_WS = os.environ.get("SEED_DEMO_NAME", "Nomaden Demo")
DOMAIN = os.environ.get("SEED_DEMO_DOMAIN", "demo.local")
SANDI = os.environ.get("SEED_DEMO_PASSWORD", "Demo1234!")

ADMIN, MEMBER = 20, 15
WIKI_IDENTIFIER = "WIKI"

# Divisi fiktif. Tiga sudah cukup: satu pemilik folder, satu bukan pemilik
# (supaya penolakan izin bisa dibuktikan), satu lagi untuk mengisi daftar
# "divisi pemilik" di panel Kelola.
DIVISI = [
    ("OPS", "Operasional", "Proses harian, jadwal, dan koordinasi lapangan."),
    ("SALES", "Penjualan", "Prospek, penawaran, dan hubungan pelanggan."),
    ("TECH", "Teknologi", "Aplikasi internal, infrastruktur, dan dukungan."),
]

# (surel lokal, nama, {identifier divisi: peran})
ORANG = [
    ("owner", "Dita Pemilik", {"OPS": ADMIN, "SALES": ADMIN, "TECH": ADMIN}),
    ("bagas", "Bagas Nugraha", {"OPS": ADMIN}),
    ("nadia", "Nadia Prameswari", {"OPS": MEMBER}),
    ("rian", "Rian Saputra", {"SALES": ADMIN}),
    ("yuni", "Yuni Larasati", {"TECH": MEMBER}),
]

SURAT_OWNER = "owner@" + DOMAIN

# Tiga folder Wiki, sengaja mewakili TIGA keadaan izin yang berbeda, supaya
# orang yang baru masuk bisa melihat sendiri aturannya bekerja:
#
#   nama folder            pemilik        artinya
#   Panduan Operasional    OPS            hanya anggota OPS boleh mengunggah
#   Pengumuman Umum        GENERAL        seluruh anggota Wiki boleh mengunggah
#   Arsip Terkunci         (tanpa baris)  TERKUNCI untuk semua kecuali admin
#
# "GENERAL" bukan identifier project, melainkan penanda bahwa pemiliknya adalah
# project Wiki itu sendiri. Karena seluruh anggota Wiki adalah ProjectMember
# Wiki, resolver yang sama membacanya sebagai "siapa pun boleh", tanpa cabang
# kode baru. Folder ketiga sengaja dibiarkan tanpa pemilik karena keadaan itu
# kebalikan dari dugaan orang dan lebih baik dilihat daripada dibaca.
FOLDER = [
    ("Panduan Operasional", ["OPS"], "SOP dan checklist harian tim Operasional."),
    ("Pengumuman Umum", ["GENERAL"], "Terbuka untuk semua. Siapa pun boleh menaruh materi."),
    ("Arsip Terkunci", [], "Tanpa divisi pemilik, jadi terkunci untuk semua kecuali admin project."),
]

PENANDA_GENERAL = "GENERAL"


def uname(email):
    """Pola username di repo ini: '.' dan '@' jadi '_'."""
    return email.replace(".", "_").replace("@", "_")


def pisah_nama(nama):
    bagian = nama.split()
    return bagian[0], " ".join(bagian[1:]) if len(bagian) > 1 else ""


def simpan(obj, pemilik_id):
    """Satu-satunya jalan menulis di berkas ini.

    `BaseModel.save()` mengambil pengguna dari request lewat crum, dan di shell
    tidak ada request, jadi tanpa `created_by_id` seluruh baris lahir tanpa
    pembuat. Di Wiki itu bukan kosmetik: materi tanpa pembuat tidak bisa
    dikelola siapa pun kecuali admin project.
    """
    obj.save(created_by_id=pemilik_id)
    return obj


print("=" * 72)
print("Seed organisasi contoh   " + ("[TERAPKAN]" if APPLY else "[UJI KERING]"))
print("workspace '" + SLUG + "' - domain surel '" + DOMAIN + "'")
print("=" * 72)

ws_ada = Workspace.objects.filter(slug=SLUG).first()
if ws_ada and getattr(ws_ada.owner, "email", None) != SURAT_OWNER:
    # Penjaga tunggal, dan sengaja hanya satu: berkas ini membuat akun dengan
    # sandi seragam, jadi satu-satunya kesalahan yang benar-benar mahal adalah
    # menjalankannya ke workspace yang dipakai orang sungguhan.
    raise SystemExit(
        "\nBERHENTI. Workspace '" + SLUG + "' sudah ada dan pemiliknya '"
        + str(getattr(ws_ada.owner, "email", None)) + "', bukan '" + SURAT_OWNER + "'.\n"
        "Berkas ini hanya boleh menyentuh workspace contoh yang dibuatnya sendiri.\n"
        "Pakai SEED_DEMO_WORKSPACE=<slug lain> kalau memang ingin yang baru."
    )

with transaction.atomic():
    # 1) Orang -------------------------------------------------------------
    print("\n1) Akun")
    pengguna = {}
    for lokal, nama, _peran in ORANG:
        email = lokal + "@" + DOMAIN
        u = User.objects.filter(email=email).first()
        if u:
            print("   ada   " + email.ljust(28) + nama)
        else:
            print("   BUAT  " + email.ljust(28) + nama)
            depan, belakang = pisah_nama(nama)
            u = User(
                email=email,
                username=uname(email),
                display_name=nama,
                first_name=depan,
                last_name=belakang,
                is_password_autoset=False,
            )
            u.set_password(SANDI)
            u.save()
        # Tanpa Profile yang ditandai selesai, tiap akun contoh mendarat di
        # wisaya onboarding lebih dulu, dan itu bukan yang mau dilihat orang
        # yang baru meng-clone.
        Profile.objects.update_or_create(
            user=u,
            defaults={
                "is_onboarded": True,
                "is_tour_completed": True,
                "onboarding_step": {
                    "profile_complete": True,
                    "workspace_create": True,
                    "workspace_invite": True,
                    "workspace_join": True,
                },
            },
        )
        pengguna[lokal] = u

    owner = pengguna["owner"]

    # 2) Workspace ---------------------------------------------------------
    ws = ws_ada
    if ws is None:
        ws = simpan(
            Workspace(name=NAMA_WS, slug=SLUG, owner=owner, organization_size="10-50"),
            owner.id,
        )
        print("\n2) Workspace DIBUAT: " + NAMA_WS + " (" + SLUG + ")")
    else:
        print("\n2) Workspace sudah ada: " + ws.name + " (" + SLUG + ")")

    for lokal, _nama, _peran in ORANG:
        WorkspaceMember.objects.get_or_create(
            workspace=ws,
            member=pengguna[lokal],
            defaults={"role": ADMIN if lokal == "owner" else MEMBER},
        )
    print("   anggota workspace: " + str(WorkspaceMember.objects.filter(workspace=ws).count()))

    # Profile.last_workspace_id menentukan ke mana orang mendarat sesudah masuk.
    # Tanpa itu akun contoh berhenti di layar pemilihan workspace.
    Profile.objects.filter(user__in=list(pengguna.values())).update(last_workspace_id=ws.id)

    # 3) Project divisi ----------------------------------------------------
    print("\n3) Project divisi")
    proyek = {}
    for identifier, nama, keterangan in DIVISI:
        p = Project.objects.filter(
            workspace=ws, identifier=identifier, deleted_at__isnull=True
        ).first()
        if p is None:
            p = simpan(
                Project(
                    workspace=ws,
                    identifier=identifier,
                    name=nama,
                    description=keterangan,
                    network=2,
                ),
                owner.id,
            )
            if ProjectIdentifier:
                ProjectIdentifier.objects.get_or_create(
                    name=identifier, project=p, defaults={"workspace": ws}
                )
            print("   BUAT  " + identifier.ljust(8) + nama)
        else:
            print("   ada   " + identifier.ljust(8) + nama)
        proyek[identifier] = p

    # 4) Project Wiki ------------------------------------------------------
    wiki = Project.objects.filter(
        workspace=ws, identifier=WIKI_IDENTIFIER, deleted_at__isnull=True
    ).first()
    if wiki is None:
        wiki = simpan(
            Project(
                workspace=ws,
                identifier=WIKI_IDENTIFIER,
                name="Wiki",
                description="Pustaka berkas perusahaan: panduan, SOP, dan materi tiap divisi.",
                network=2,
                page_view=True,
                cycle_view=False,
                module_view=False,
                issue_views_view=False,
                intake_view=False,
            ),
            owner.id,
        )
        if ProjectIdentifier:
            ProjectIdentifier.objects.get_or_create(
                name=WIKI_IDENTIFIER, project=wiki, defaults={"workspace": ws}
            )
        print("\n4) Project Wiki DIBUAT (identifier " + WIKI_IDENTIFIER + ")")
    else:
        print("\n4) Project Wiki sudah ada (identifier " + WIKI_IDENTIFIER + ")")

    # State wajib ada walau project ini fokus halaman: issue tetap fitur dasar.
    for p in list(proyek.values()) + [wiki]:
        if not State.objects.filter(project=p).exists():
            State.objects.bulk_create(
                [State(project=p, workspace=ws, created_by=owner, **s) for s in DEFAULT_STATES]
            )

    # 5) Keanggotaan project ----------------------------------------------
    print("\n5) Keanggotaan project")
    for lokal, nama, peran in ORANG:
        u = pengguna[lokal]
        for identifier, role in peran.items():
            ProjectMember.objects.get_or_create(
                project=proyek[identifier], workspace=ws, member=u, defaults={"role": role}
            )
            ProjectUserProperty.objects.get_or_create(
                project=proyek[identifier], workspace=ws, user=u
            )
        # SEMUA orang jadi anggota Wiki. Itu bukan kelonggaran, melainkan syarat
        # aturannya: hak BACA di Wiki adalah "anggota project Wiki", dan folder
        # General bekerja justru karena keanggotaan ini.
        ProjectMember.objects.get_or_create(
            project=wiki,
            workspace=ws,
            member=u,
            defaults={"role": ADMIN if lokal == "owner" else MEMBER},
        )
        ProjectUserProperty.objects.get_or_create(project=wiki, workspace=ws, user=u)
        label = " ".join(k + ":" + str(v) for k, v in peran.items())
        print("   " + u.email.ljust(28) + label + "  + WIKI")

    # 6) Governance Wiki ---------------------------------------------------
    governed = WikiGovernedProject.objects.filter(project=wiki, deleted_at__isnull=True).exists()
    if not governed:
        simpan(WikiGovernedProject(project=wiki, workspace=ws), owner.id)
        print("\n6) Governance ACL folder DINYALAKAN untuk project Wiki")
    else:
        print("\n6) Governance ACL folder sudah aktif")

    # 7) Folder Wiki + ACL -------------------------------------------------
    print("\n7) Folder Wiki")
    pilihan_divisi = dict(proyek)
    pilihan_divisi[PENANDA_GENERAL] = wiki
    halaman = {}

    for nama, pemilik, keterangan in FOLDER:
        f = Page.objects.filter(
            projects=wiki, parent__isnull=True, name=nama, deleted_at__isnull=True
        ).first()
        if f is None:
            # TANPA <h1> judul: Plane sudah merender nama halaman di atas badan
            # dokumen, jadi judul di dalam html membuatnya tampil dua kali.
            f = simpan(
                Page(
                    workspace=ws,
                    name=nama,
                    owned_by=owner,
                    access=0,
                    description_html="<p>" + keterangan + "</p>",
                ),
                owner.id,
            )
            ProjectPage.objects.get_or_create(
                page=f, project=wiki, defaults={"workspace": ws, "created_by": owner}
            )
        halaman[nama] = f

        diminta = {}
        for i in pemilik:
            if i in pilihan_divisi:
                diminta[pilihan_divisi[i].id] = i
        sekarang = set(
            WikiFolderAccess.objects.filter(
                folder=f, project=wiki, deleted_at__isnull=True
            ).values_list("division_id", flat=True)
        )
        for division_id in set(diminta) - sekarang:
            simpan(
                WikiFolderAccess(folder=f, division_id=division_id, project=wiki, workspace=ws),
                owner.id,
            )
        label = " ".join(sorted(diminta.values())) or "(tanpa pemilik, TERKUNCI)"
        print("   " + nama.ljust(24) + label)

        # Satu Topik di dalam tiap folder, supaya susunan Divisi -> Topik
        # kelihatan dan pewarisan izin ke bawah bisa diuji.
        topik_nama = "Topik contoh - " + nama
        t = Page.objects.filter(
            projects=wiki, parent=f, name=topik_nama, deleted_at__isnull=True
        ).first()
        if t is None:
            t = simpan(
                Page(
                    workspace=ws,
                    name=topik_nama,
                    owned_by=owner,
                    access=0,
                    parent=f,
                    description_html="<p>Taruh materi di sini.</p>",
                ),
                owner.id,
            )
            ProjectPage.objects.get_or_create(
                page=t, project=wiki, defaults={"workspace": ws, "created_by": owner}
            )
        halaman[topik_nama] = t

    # 8) Pemeriksaan ------------------------------------------------------
    # Ini yang membuat berkas ini lebih dari sekadar pengisi data. Kalau
    # resolver izin Wiki suatu saat berubah arti, seed ini yang berteriak
    # duluan, bukan pemakai di peramban.
    print("\n8) Pemeriksaan matriks izin")
    t_ops = halaman["Topik contoh - Panduan Operasional"]
    t_umum = halaman["Topik contoh - Pengumuman Umum"]
    t_kunci = halaman["Topik contoh - Arsip Terkunci"]

    periksa = [
        ("anggota OPS boleh mengisi folder OPS", can_edit_wiki_page(pengguna["nadia"], t_ops), True),
        ("orang SALES DITOLAK di folder OPS", can_edit_wiki_page(pengguna["rian"], t_ops), False),
        ("siapa pun boleh mengisi folder General", can_edit_wiki_page(pengguna["yuni"], t_umum), True),
        ("folder tanpa pemilik tertutup untuk semua", can_edit_wiki_page(pengguna["bagas"], t_kunci), False),
        ("kepala divisi OPS dikenali", is_division_lead(pengguna["bagas"], t_ops), True),
        ("anggota biasa BUKAN kepala divisi", is_division_lead(pengguna["nadia"], t_ops), False),
    ]
    gagal = 0
    for keterangan, hasil, harapan in periksa:
        cocok = bool(hasil) is harapan
        if not cocok:
            gagal += 1
        print(
            "   " + ("OK   " if cocok else "GAGAL") + " " + keterangan
            + "  (dapat " + str(bool(hasil)) + ", harusnya " + str(harapan) + ")"
        )
    if gagal:
        raise SystemExit("\n" + str(gagal) + " pemeriksaan GAGAL. Tidak ada yang ditulis.")

    if not APPLY:
        print("\n  UJI KERING, transaksi dibatalkan, tidak ada yang ditulis.")
        transaction.set_rollback(True)

print("-" * 72)
if APPLY:
    print("  SELESAI. Masuk ke http://localhost:4000/" + SLUG + "/ lalu buka menu Wiki.")
    print("  Akun: " + SURAT_OWNER + " dan empat lainnya di @" + DOMAIN + ", sandi '" + SANDI + "'.")
    print("  Ganti sandi lewat God Mode kalau instance ini dipakai lebih dari sehari.")
else:
    print("  Jalankan dengan SEED_DEMO_APPLY=1 untuk menerapkan.")
