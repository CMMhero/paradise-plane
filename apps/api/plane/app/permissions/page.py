# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import ProjectMember, Page
from plane.app.permissions import ROLE
from plane.utils.wiki_access import (
    can_edit_wiki_page,
    can_manage_wiki_page,
    has_foreign_descendants,
    is_division_lead,
    is_super_admin,
    is_wiki_governed,
)


from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS


# Permission Mappings for workspace members
ADMIN = ROLE.ADMIN.value
MEMBER = ROLE.MEMBER.value
GUEST = ROLE.GUEST.value


class ProjectPagePermission(BasePermission):
    """
    Custom permission to control access to pages within a workspace
    based on user roles, page visibility (public/private), and feature flags.
    """

    def has_permission(self, request, view):
        """
        Check basic project-level permissions before checking object-level permissions.
        """
        if request.user.is_anonymous:
            return False

        user_id = request.user.id
        slug = view.kwargs.get("slug")
        page_id = view.kwargs.get("page_id")
        project_id = view.kwargs.get("project_id")

        # Hook for extended validation
        extended_access, role = self._check_access_and_get_role(request, slug, project_id)
        if extended_access is False:
            return False

        # ACL Wiki: di project ber-governance, hak edit ditentukan
        # kepemilikan folder per-divisi, bukan peran atau kepemilikan halaman.
        if is_wiki_governed(project_id):
            return self._has_wiki_governed_access(request, view, slug, project_id, page_id, role)

        if page_id:
            # Scope the page to the project in the URL. Resolving the page by
            # workspace + page_id alone allowed a member of one project to read
            # pages belonging to another project in the same workspace
            # (GHSA-g49r / GHSA-ghcr). Require an *active* ProjectPage link (both
            # conditions on the same relation so they match one row) so a page
            # removed from the project (soft-deleted link) is also denied.
            page = Page.objects.filter(
                id=page_id,
                workspace__slug=slug,
                project_pages__project_id=project_id,
                project_pages__deleted_at__isnull=True,
            ).first()
            if page is None:
                return False

            # Allow access if the user is the owner of the page
            if page.owned_by_id == user_id:
                return True

            # Handle private page access
            if page.access == Page.PRIVATE_ACCESS:
                return self._has_private_page_action_access(request, slug, page, project_id)

        # Handle public page access
        return self._has_public_page_action_access(request, role)

    def _has_wiki_governed_access(self, request, view, slug, project_id, page_id, role):
        """Izin halaman di Wiki ber-ACL folder.

        Tiga hak yang sengaja dipisah, karena inilah aturan yang diminta pemilik
        instance dan menyatukannya membuat salah satunya pasti salah:

            baca            semua anggota project Wiki
            unggah baru     anggota aktif divisi pemilik folder teratas
            kelola yang ada pengunggahnya, kepala divisi pemilik, atau Super Admin

        Perhatikan admin project Wiki TIDAK lagi otomatis lolos untuk hak ketiga.
        Yang dimaksud "super admin" oleh pemilik instance adalah Super Admin
        instance (God Mode), dan mereka semua sudah punya baris ProjectMember
        role 20 di setiap project, jadi mereka tetap lolos lewat is_super_admin.
        Yang tercabut justru admin project Wiki yang bukan Super Admin, dan itu
        memang tujuannya.

        Membuat folder Divisi (POST tanpa parent) tetap admin project saja,
        supaya tingkat teratas tidak tercemar folder liar.
        """
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        action = getattr(view, "action", None)

        # --- Membuat halaman baru -------------------------------------------
        if not page_id:
            parent_id = request.data.get("parent")
            if not parent_id:
                # Folder Divisi = tingkat teratas, dan folder teratas tanpa baris
                # WikiFolderAccess terkunci untuk semua orang. Jadi membuatnya
                # harus disertai pemberian pemilik, dan itu pekerjaan admin.
                return role == ADMIN
            parent = Page.objects.filter(id=parent_id, workspace__slug=slug).first()
            if parent is None:
                return False
            return can_edit_wiki_page(user, parent)

        # --- Mengubah halaman yang sudah ada --------------------------------
        page = Page.objects.filter(id=page_id, workspace__slug=slug).first()
        if page is None:
            return False

        if not can_manage_wiki_page(user, page):
            raise PermissionDenied(
                "Hanya pengunggahnya, kepala divisi pemilik folder, atau Super Admin "
                "yang boleh mengubah materi ini."
            )

        # Tiga penjaga struktur di bawah ini menutup lubang yang tidak tertutup
        # oleh aturan kepemilikan, karena ketiganya merusak materi ORANG LAIN
        # lewat operasi atas halaman milik SENDIRI.
        if action == "archive" and has_foreign_descendants(page, user):
            if not (is_super_admin(user) or is_division_lead(user, page)):
                raise PermissionDenied(
                    "Folder ini berisi materi milik orang lain, dan mengarsipkannya "
                    "ikut menyembunyikan semuanya. Hanya kepala divisi pemilik folder "
                    "atau Super Admin yang boleh melakukannya."
                )

        if action == "unarchive" and page.parent_id:
            if Page.objects.filter(id=page.parent_id, archived_at__isnull=False).exists():
                raise PermissionDenied(
                    "Buka arsip folder induknya dulu. Kalau tidak, materi ini akan "
                    "lepas ke tingkat teratas dan kehilangan divisi pemiliknya."
                )

        if action == "destroy":
            if Page.objects.filter(parent_id=page.id, deleted_at__isnull=True).exists():
                raise PermissionDenied(
                    "Folder ini masih berisi materi. Pindahkan atau hapus isinya dulu. "
                    "Menghapus folder tidak ikut menghapus isinya, melainkan melempar "
                    "isinya ke tingkat teratas tanpa divisi pemilik."
                )

        return True

    def _check_project_member_access(self, request, slug, project_id):
        """
        Check if the user is a project member.
        """
        return (
            ProjectMember.objects.filter(
                member=request.user,
                workspace__slug=slug,
                is_active=True,
                project_id=project_id,
            )
            .values_list("role", flat=True)
            .first()
        )

    def _check_access_and_get_role(self, request, slug, project_id):
        """
        Hook for extended access checking
        Returns: True (allow), False (deny), None (continue with normal flow)
        """
        role = self._check_project_member_access(request, slug, project_id)
        if not role:
            return False, None
        return True, role

    def _has_private_page_action_access(self, request, slug, page, project_id):
        """
        Check access to private pages. Override for feature flag logic.
        """
        # Base implementation: only owner can access private pages
        return False

    def _check_project_action_access(self, request, role):
        method = request.method

        # Only admins can create (POST) pages
        if method == "POST":
            if role in [ADMIN, MEMBER]:
                return True
            return False

        # Safe methods (GET, HEAD, OPTIONS) allowed for all active roles
        if method in SAFE_METHODS:
            if role in [ADMIN, MEMBER, GUEST]:
                return True
            return False

        # PUT/PATCH: Admins and members can update
        if method in ["PUT", "PATCH"]:
            if role in [ADMIN, MEMBER]:
                return True
            return False

        # DELETE: Only admins can delete
        if method == "DELETE":
            if role in [ADMIN]:
                return True
            return False

        # Deny by default
        return False

    def _has_public_page_action_access(self, request, role):
        """
        Check if the user has permission to access a public page
        and can perform operations on the page.
        """
        project_member_exists = self._check_project_action_access(request, role)
        if not project_member_exists:
            return False
        return True
