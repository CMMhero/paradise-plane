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
    """True kalau `user` boleh MENGEDIT/mengunggah ke `page` di Wiki ber-ACL.

    Sejak 2026-10-26 hanya Super Admin atau admin workspace. Kepemilikan folder
    per-divisi (`WikiFolderAccess`) kini hanya mengatur NAMA penanggung jawab
    yang tampil, bukan hak tulis.
    """
    return is_wiki_admin(user, workspace_id=page.workspace_id)


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


_WORKSPACE_ADMIN = 20


def is_wiki_admin(user, workspace_id=None, workspace_slug=None):
    """Satu-satunya yang boleh MENGUBAH/mengelola Wiki: Super Admin atau admin workspace.

    Keputusan user 2026-10-26: walaupun Wiki (termasuk folder General) terbuka
    dibaca semua orang, hak ubah/kelola/unggah hanya admin workspace atau Super
    Admin. Pengunggah, kepala divisi, dan admin project Wiki yang bukan admin
    workspace TIDAK lagi punya hak tulis.
    """
    from plane.db.models import WorkspaceMember

    if user is None or getattr(user, "is_anonymous", True):
        return False
    if is_super_admin(user):
        return True
    filters = {"member": user, "role": _WORKSPACE_ADMIN, "is_active": True, "deleted_at__isnull": True}
    if workspace_id is not None:
        filters["workspace_id"] = workspace_id
    elif workspace_slug is not None:
        filters["workspace__slug"] = workspace_slug
    else:
        return False
    return WorkspaceMember.objects.filter(**filters).exists()


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
    return is_wiki_admin(user, workspace_id=page.workspace_id)


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


def is_division_supervisor(user, division_ids, workspace_id):
    """True kalau berpangkat supervisor+ DAN anggota salah satu divisi pemilik.

    SPV dalam aturan hapus materi (keputusan user 2026-10-24): atasan yang
    berpangkat, bukan siapa pun yang kebetulan memegang role admin project.
    Cakupannya divisi pemilik saja: SPV divisi lain tidak ikut.
    """
    from plane.db.models import ProjectMember, TINGKAT_SUPERVISOR  # noqa: PLC0415

    if user is None or getattr(user, "is_anonymous", True):
        return False
    if not division_ids:
        return False

    from plane.utils.hierarki import tingkat_anggota  # noqa: PLC0415

    tingkat = tingkat_anggota(user.id, workspace_id)
    if tingkat is None or tingkat < TINGKAT_SUPERVISOR:
        return False
    return ProjectMember.objects.filter(
        member=user,
        project_id__in=division_ids,
        is_active=True,
        deleted_at__isnull=True,
    ).exists()


def can_manage_wiki_material(user, asset):
    """True kalau `user` boleh mengubah atau menghapus sebuah Materi Wiki.

    Sejak 2026-10-26 hanya Super Admin atau admin workspace; pengunggah asli
    tidak lagi otomatis berhak.
    """
    return is_wiki_admin(user, workspace_id=asset.workspace_id)


def pastikan_folder_divisi(workspace, actor=None):
    """Pastikan tiap Divisi punya foldernya di Wiki (project WIKI).

    Keputusan user 2026-10-24: tiap divisi otomatis punya wikinya sendiri —
    tidak perlu dibuat manual. Idempoten: folder yang sudah ada tidak
    disentuh (kecuali daftar pemiliknya diselaraskan), yang belum ada dibuat
    sebagai halaman top-level + baris `WikiFolderAccess` per project
    departemen divisi itu.

    Dipanggil sesudah tulis organisasi (buat/ubah/hapus divisi & departemen,
    petakan project) dan sekali sebagai backfill. `actor` menjadi `owned_by`
    folder yang baru dibuat (biasanya admin God Mode yang bertindak).
    Mengembalikan {"dibuat": [nama], "folder": n}.
    """
    from plane.db.models import (  # noqa: PLC0415
        Departemen,
        DepartemenProject,
        Divisi,
        Page,
        Project,
        ProjectPage,
        WikiFolderAccess,
    )

    hasil = {"dibuat": [], "folder": 0}
    if workspace is None:
        return hasil
    wiki = Project.objects.filter(
        workspace=workspace, identifier="WIKI", deleted_at__isnull=True
    ).first()
    if wiki is None:
        return hasil

    divisi_semua = Divisi.objects.filter(workspace=workspace, deleted_at__isnull=True).order_by("nama")
    for divisi in divisi_semua:
        folder = (
            Page.objects.filter(
                workspace=workspace,
                parent__isnull=True,
                name=divisi.nama,
                project_pages__project=wiki,
                project_pages__deleted_at__isnull=True,
                deleted_at__isnull=True,
                archived_at__isnull=True,
            )
            .order_by("created_at")
            .first()
        )
        if folder is None:
            if actor is None:
                continue
            folder = Page.objects.create(
                workspace=workspace,
                owned_by=actor,
                name=divisi.nama,
                access=Page.PUBLIC_ACCESS,
            )
            ProjectPage.objects.create(workspace=workspace, project=wiki, page=folder)
            hasil["dibuat"].append(divisi.nama)
        hasil["folder"] += 1

        diinginkan = set(
            DepartemenProject.objects.filter(
                workspace=workspace,
                departemen__divisi=divisi,
                departemen__deleted_at__isnull=True,
                project__deleted_at__isnull=True,
                deleted_at__isnull=True,
            ).values_list("project_id", flat=True)
        )
        sekarang = set(
            WikiFolderAccess.objects.filter(folder=folder, deleted_at__isnull=True).values_list(
                "division_id", flat=True
            )
        )
        for pid in diinginkan - sekarang:
            lama = WikiFolderAccess.all_objects.filter(folder=folder, division_id=pid).first()
            if lama is None:
                WikiFolderAccess.objects.create(
                    workspace=workspace, project=wiki, folder=folder, division_id=pid
                )
            else:
                lama.deleted_at = None
                lama.save(update_fields=["deleted_at", "updated_at"])
        for pid in sekarang - diinginkan:
            obj = WikiFolderAccess.objects.filter(folder=folder, division_id=pid).first()
            if obj is not None:
                obj.delete()
    return hasil


def selaraskan_nama_folder_divisi(workspace, lama, baru):
    """Ikutkan ganti nama Divisi ke folder Wikinya (kalau foldernya ada).

    Dipanggil dari God Mode sesudah `Divisi` diganti namanya, supaya folder
    otomatisnya tidak yatim (sync hanya mencocokkan berdasarkan nama).
    """
    from plane.db.models import Page, Project  # noqa: PLC0415

    if not lama or not baru or lama == baru or workspace is None:
        return False
    wiki = Project.objects.filter(
        workspace=workspace, identifier="WIKI", deleted_at__isnull=True
    ).first()
    if wiki is None:
        return False
    folder = (
        Page.objects.filter(
            workspace=workspace,
            parent__isnull=True,
            name=lama,
            project_pages__project=wiki,
            project_pages__deleted_at__isnull=True,
            deleted_at__isnull=True,
        )
        .order_by("created_at")
        .first()
    )
    if folder is None:
        return False
    folder.name = baru[:255]
    folder.save(update_fields=["name", "updated_at"])
    return True
