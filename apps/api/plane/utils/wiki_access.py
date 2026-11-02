# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Resolver ACL Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Satu sumber kebenaran "boleh edit halaman ini?", dipakai oleh izin API Django
# (ProjectPagePermission) DAN endpoint can-edit untuk server Live. Jangan
# duplikat logika ini di tempat lain: dua penegak, satu aturan.

_MAX_DEPTH = 50  # jaga-jaga dari rantai parent melingkar / rusak

WIKI_IDENTIFIER = "WIKI"


def is_wiki_governed(project_id):
    """True kalau project ini Wiki ber-ACL folder.

    Sejak 2026-11-02 (KEP-51) project ber-identifier WIKI SELALU ber-governance:
    saklar di Setelan project dibuang, jadi tidak ada lagi keadaan "lokal lebih
    longgar dari produksi" karena satu baris tabel lupa dibuat. Baris
    `WikiGovernedProject` tetap dihormati untuk project lain yang sudah ditandai.
    """
    from plane.db.models import Project, WikiGovernedProject

    if Project.objects.filter(id=project_id, identifier=WIKI_IDENTIFIER).exists():
        return True
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


def is_division_folder(folder):
    """True kalau folder teratas ini milik sebuah Divisi (namanya sama).

    Folder divisi dibuat dan dipelihara `pastikan_folder_divisi`, yang
    mencocokkan lewat nama. Folder teratas lain (General, folder khusus buatan
    admin) bukan folder divisi.
    """
    from plane.db.models import Divisi

    return Divisi.objects.filter(
        workspace_id=folder.workspace_id, nama=folder.name, deleted_at__isnull=True
    ).exists()


def uploader_project_ids(folder):
    """Project yang anggotanya boleh MENGUNGGAH ke folder teratas ini.

    Aturan bawaan (KEP-51), tanpa setelan apa pun:

    - punya baris `WikiFolderAccess` -> project-project itu (untuk folder
      divisi: project departemen di bawah divisinya, diselaraskan otomatis);
    - folder divisi tanpa departemen -> kosong, hanya admin;
    - folder lain tanpa baris -> General: project Wiki-nya sendiri, jadi
      semua anggota Wiki boleh mengunggah.
    """
    from plane.db.models import ProjectPage

    ids = owning_division_ids(folder)
    if ids or is_division_folder(folder):
        return ids
    return list(
        ProjectPage.objects.filter(page=folder, deleted_at__isnull=True).values_list(
            "project_id", flat=True
        )
    )


def is_department_member(user, project_ids):
    """Anggota aktif (member/admin, bukan guest) salah satu project ini."""
    from plane.db.models import ProjectMember

    if not project_ids or user is None or getattr(user, "is_anonymous", True):
        return False
    return ProjectMember.objects.filter(
        member=user,
        project_id__in=project_ids,
        role__gte=_ROLE_MEMBER,
        is_active=True,
        deleted_at__isnull=True,
    ).exists()


def can_edit_wiki_page(user, page):
    """True kalau `user` boleh MENGUNGGAH materi ke `page` di Wiki ber-ACL.

    KEP-51 (2026-11-02): admin workspace / Super Admin, atau anggota
    departemen yang memiliki folder teratasnya (lihat `uploader_project_ids`).
    Mengubah struktur (folder, sub-topik) tetap `can_manage_wiki_page`.
    """
    if is_wiki_admin(user, workspace_id=page.workspace_id):
        return True
    return is_department_member(user, uploader_project_ids(top_level_folder(page)))


# --- Matriks hak Wiki (KEP-51, 2026-11-02) -----------------------------------
#
#   baca                  semua anggota project Wiki
#   unggah materi baru    admin, atau anggota departemen pemilik folder divisi
#                         (folder non-divisi tanpa pemilik = General, semua)
#   ubah/hapus materi     admin, atau pengunggahnya sendiri
#   folder & sub-topik    admin saja (buat, ganti nama/ikon, arsip, hapus)
#
# "admin" = admin workspace atau Super Admin instance (`is_wiki_admin`).
# Tidak ada setelan: pemilik folder divisi diturunkan dari struktur organisasi
# God Mode lewat `pastikan_folder_divisi`.

_ROLE_ADMIN = 20
_ROLE_MEMBER = 15


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

    Admin project Wiki yang bukan admin workspace TIDAK termasuk. Anggota
    departemen boleh mengunggah (`can_edit_wiki_page`) dan pengunggah boleh
    mengubah materinya sendiri (`can_manage_wiki_material`), tapi struktur Wiki
    (folder, sub-topik) hanya untuk yang lolos fungsi ini.
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


def can_manage_wiki_material(user, asset):
    """True kalau `user` boleh mengubah atau menghapus sebuah Materi Wiki.

    KEP-51: admin workspace / Super Admin, atau pengunggahnya sendiri.
    """
    if user is None or getattr(user, "is_anonymous", True) or not getattr(user, "id", None):
        return False
    if asset.created_by_id and asset.created_by_id == user.id:
        return True
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
