# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# Seed Workspace Wiki, Paradise Task Tracker
# Jalankan: docker exec -i pradise_plane-api-1 python manage.py shell < paradise/bin/seed-wiki.py
#
# !!! JANGAN JALANKAN LAGI DI PRODUKSI TANPA MEMBACA INI DULU !!!
#
# Berkas ini hanya membuat Wiki dari NOL. Ia sudah tidak menggambarkan produksi
# dan "idempoten"-nya lebih dangkal daripada kelihatannya:
#
#   1. Kunci get_or_create halamannya (workspace, name, owned_by), BUKAN
#      (project, name). Begitu sebuah folder diganti namanya, menjalankan ulang
#      berkas ini akan MELAHIRKAN LAGI folder lama dengan nama di ROOT_PAGES,
#      di samping yang sudah ada.
#   2. Folder yang lahir dari sini TIDAK punya divisi pemilik, dan folder tanpa
#      pemilik di Wiki ber-governance bukan berarti bebas, melainkan TERKUNCI
#      untuk semua orang kecuali admin project.
#   3. Ia tidak menyentuh WikiGovernedProject maupun WikiFolderAccess sama
#      sekali. Yang mengurus keduanya adalah `seed-wiki-access.py`.
#
# Jadi: untuk instance BARU, jalankan berkas ini lalu `seed-wiki-access.py`.
# Untuk produksi yang sudah hidup, jangan sentuh berkas ini.
#
# Idempotent: aman dijalankan ulang (get_or_create semua), dengan catatan di atas.
#
# Membuat project "Wiki" perusahaan: public, semua user aktif jadi Member (bisa menulis),
# hanya fitur Pages yang aktif, di-seed halaman root per divisi + halaman umum.

from plane.db.models import (
    Page, Project, ProjectMember, ProjectPage, ProjectUserProperty,
    State, User, Workspace, WorkspaceMember,
)
from plane.db.models.state import DEFAULT_STATES

try:
    from plane.db.models import ProjectIdentifier
except ImportError:
    ProjectIdentifier = None

ADMIN, MEMBER = 20, 15
WIKI_ADMINS = {
    "bintang.ramadhan@paradiseperkasa.com",
    "henry@paradiseperkasa.com",
    "suarno.radin@paradiseperkasa.com",
}

ROOT_PAGES = [
    "📖 Panduan Perusahaan",
    "📋 SOP & Kebijakan",
    "🧭 Onboarding Karyawan Baru",
    "📚 Wiki Sales & Marketing",
    "📚 Wiki SCM & Procurement",
    "📚 Wiki Finance & Accounting",
    "📚 Wiki HRGA & Legal",
    "📚 Wiki IT",
    "📚 Wiki Warehouse & Logistik",
]

ws = Workspace.objects.get(slug="pt-paradise-perkasa")
owner = User.objects.get(email="bintang.ramadhan@paradiseperkasa.com")

# 1) Project Wiki (network=2 = public untuk seluruh anggota workspace)
wiki, created = Project.objects.get_or_create(
    workspace=ws,
    identifier="WIKI",
    defaults={
        "name": "Wiki",
        "description": "Basis pengetahuan perusahaan, SOP, panduan, dokumentasi divisi.",
        "network": 2,
        "created_by": owner,
        "page_view": True,
        "cycle_view": False,
        "module_view": False,
        "issue_views_view": False,
        "intake_view": False,
    },
)
print(("CREATED" if created else "exists "), "project Wiki:", wiki.id)

if ProjectIdentifier:
    ProjectIdentifier.objects.get_or_create(name="WIKI", project=wiki, defaults={"workspace": ws})

# States wajib ada walau fokus pages (issue tetap fitur dasar project)
if not State.objects.filter(project=wiki).exists():
    State.objects.bulk_create(
        [State(project=wiki, workspace=ws, created_by=owner, **s) for s in DEFAULT_STATES]
    )
    print("states default dibuat")

# 2) Semua anggota workspace aktif jadi anggota Wiki
added = 0
for wm in WorkspaceMember.objects.filter(workspace=ws, is_active=True).select_related("member"):
    role = ADMIN if wm.member.email in WIKI_ADMINS else MEMBER
    _, was_new = ProjectMember.objects.get_or_create(
        project=wiki, workspace=ws, member=wm.member, defaults={"role": role}
    )
    ProjectUserProperty.objects.get_or_create(project=wiki, workspace=ws, user=wm.member)
    if was_new:
        added += 1
print(f"anggota ditambahkan: {added} (total {ProjectMember.objects.filter(project=wiki).count()})")

# 3) Halaman root per topik/divisi
made = 0
for title in ROOT_PAGES:
    page, was_new = Page.objects.get_or_create(
        workspace=ws,
        name=title,
        owned_by=owner,
        defaults={
            "access": 0,  # public dalam project
            # TANPA <h1> judul: Plane sudah merender nama halaman sendiri di atas
            # badan dokumen, jadi <h1>{title}</h1> membuat judul tampil DUA KALI.
            "description_html": "<p>Tulis dokumentasi di sini…</p>",
            "created_by": owner,
        },
    )
    ProjectPage.objects.get_or_create(
        page=page, project=wiki, defaults={"workspace": ws, "created_by": owner}
    )
    if was_new:
        made += 1
print(f"halaman root dibuat: {made} / {len(ROOT_PAGES)}")
print("SELESAI, Wiki siap di project 'Wiki' (identifier WIKI).")
