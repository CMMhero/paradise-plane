# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Resolver ACL Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Satu sumber kebenaran "boleh edit halaman ini?", dipakai oleh izin API Django
# (ProjectPagePermission) DAN endpoint can-edit untuk server Live. Jangan
# duplikat logika ini di tempat lain: dua penegak, satu aturan.

_MAX_DEPTH = 50  # jaga-jaga dari rantai parent melingkar / rusak


def is_wiki_governed(project_id):
    """True kalau project ini Wiki ber-ACL folder (punya baris WikiGovernedProject)."""
    from plane.db.models import WikiGovernedProject

    return WikiGovernedProject.objects.filter(
        project_id=project_id, deleted_at__isnull=True
    ).exists()


def top_level_folder(page):
    """Telusuri naik rantai parent ke halaman folder paling atas.

    Sub-halaman mewarisi kepemilikan folder top-level-nya, jadi izin selalu
    dievaluasi terhadap folder teratas.
    """
    seen = set()
    depth = 0
    while page.parent_id and page.parent_id not in seen and depth < _MAX_DEPTH:
        seen.add(page.id)
        page = page.parent
        depth += 1
    return page


def owning_division_ids(folder):
    """ID divisi (project) yang anggotanya boleh mengedit folder ini."""
    from plane.db.models import WikiFolderAccess

    return list(
        WikiFolderAccess.objects.filter(folder=folder, deleted_at__isnull=True).values_list(
            "division_id", flat=True
        )
    )


def can_edit_wiki_page(user, page):
    """True kalau `user` boleh MENGEDIT `page` di Wiki ber-ACL.

    Aturan: user harus anggota aktif salah satu divisi pemilik folder top-level.
    Folder tanpa pemilik → False (hanya admin, ditangani di lapisan izin).
    Tidak memakai kepemilikan halaman individual: hak edit murni per-divisi.
    """
    from plane.db.models import ProjectMember

    if user is None or getattr(user, "is_anonymous", True):
        return False

    folder = top_level_folder(page)
    division_ids = owning_division_ids(folder)
    if not division_ids:
        return False

    return ProjectMember.objects.filter(
        member=user,
        project_id__in=division_ids,
        is_active=True,
        deleted_at__isnull=True,
    ).exists()


# --- Hak KELOLA (sunting, arsip, hapus, kunci) atas materi yang SUDAH ada -----
#
# Hak UNGGAH dan hak KELOLA sengaja berbeda, dan bedanya itu inti aturan yang
# diminta pemilik instance:
#
#   unggah materi baru  -> siapa pun anggota aktif divisi pemilik folder
#   kelola materi lama  -> pengunggahnya sendiri, kepala divisi pemilik, atau
#                          Super Admin instance
#
# Jadi satu divisi tetap bisa mengisi Wiki-nya bersama-sama, tapi tidak ada yang
# bisa membuang atau menimpa kerja rekannya. "Menimpa" ikut dikunci karena
# mengosongkan isi sebuah materi hasilnya sama saja dengan menghapusnya.
#
# Kepala divisi ikut dimasukkan bukan demi kelonggaran, melainkan demi jalan
# keluar: tidak ada alih kepemilikan halaman di Plane, jadi tanpa kepala divisi
# setiap materi milik karyawan yang resign hanya bisa disentuh Super Admin,
# selamanya.

_ROLE_ADMIN = 20


def is_super_admin(user):
    """Diteruskan dari `plane.db.superadmin`, di situlah definisinya hidup.

    Tetap diekspor dari sini karena sudah dipakai lapisan izin Wiki, dan satu
    nama yang menunjuk satu fungsi lebih baik daripada dua fungsi yang kebetulan
    sering sependapat.
    """
    from plane.db.superadmin import is_super_admin as _asli

    return _asli(user)


def is_division_lead(user, page):
    """True kalau `user` Admin (role 20) di salah satu divisi pemilik folder teratas."""
    from plane.db.models import ProjectMember

    if user is None or getattr(user, "is_anonymous", True):
        return False

    division_ids = owning_division_ids(top_level_folder(page))
    if not division_ids:
        return False

    return ProjectMember.objects.filter(
        member=user,
        project_id__in=division_ids,
        role=_ROLE_ADMIN,
        is_active=True,
        deleted_at__isnull=True,
    ).exists()


def can_manage_wiki_page(user, page):
    """True kalau `user` boleh menyunting, mengarsip, atau menghapus `page`."""
    if user is None or getattr(user, "is_anonymous", True):
        return False
    if page.owned_by_id == user.id:
        return True
    if is_super_admin(user):
        return True
    return is_division_lead(user, page)


def has_foreign_descendants(page, user, max_depth=_MAX_DEPTH):
    """True kalau ada keturunan `page` yang diunggah orang LAIN.

    Dipakai sebelum mengarsipkan folder. Mengarsipkan folder di Plane menyeret
    SELURUH keturunannya lewat satu SQL rekursif tanpa cek kepemilikan, jadi
    tanpa pemeriksaan ini pemilik sebuah Topik bisa menyembunyikan materi satu
    divisi hanya dengan mengarsipkan foldernya sendiri.

    Ditelusuri per tingkat, bukan rekursif per baris: kedalaman Wiki cuma tiga,
    jadi ini paling banyak tiga query, dan batas kedalaman menjaga dari rantai
    parent yang melingkar.
    """
    from plane.db.models import Page

    frontier = [page.id]
    depth = 0
    seen = {page.id}
    while frontier and depth < max_depth:
        children = list(
            Page.objects.filter(parent_id__in=frontier, deleted_at__isnull=True).values_list(
                "id", "owned_by_id"
            )
        )
        if not children:
            return False
        if any(owner_id != user.id for _, owner_id in children):
            return True
        frontier = [child_id for child_id, _ in children if child_id not in seen]
        seen.update(frontier)
        depth += 1
    return False


def can_manage_wiki_material(user, asset):
    """True kalau `user` boleh mengubah atau menghapus sebuah Materi Wiki.

    Aturannya SAMA PERSIS dengan aturan halaman, cuma sumbernya beda: pemilik
    sebuah materi adalah `created_by` pada berkasnya, bukan `owned_by` pada
    halaman. Sengaja diturunkan dari fungsi yang sama supaya tidak ada dua
    aturan hapus yang suatu saat berbeda pendapat.

    Materi yang tidak menempel ke halaman mana pun tidak bisa dinilai terhadap
    folder mana pun, jadi ia hanya boleh disentuh pengunggahnya atau Super
    Admin. Itu keadaan yang seharusnya tidak pernah terjadi, tapi kalau terjadi
    jawabannya harus menutup, bukan membuka.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    if asset.created_by_id == user.id:
        return True
    if is_super_admin(user):
        return True
    if asset.page_id is None:
        return False

    from plane.db.models import Page

    page = Page.objects.filter(id=asset.page_id).first()
    if page is None:
        return False
    return is_division_lead(user, page)
