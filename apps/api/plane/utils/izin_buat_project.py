# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: siapa yang boleh membuat project baru
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu sumber aturan "boleh membuat project" (4 Nov 2026).

Permintaan user: member biasa / staf TIDAK boleh membuat project baru. Yang boleh:

    Super Admin (God Mode)            selalu
    Admin workspace (role 20)         selalu
    Member workspace (role 15)        hanya kalau jenjangnya PROJECT_CREATE_MIN_LEVEL
                                      ke atas (God Mode, bawaan Supervisor)
    Guest (role 5) / bukan anggota    tidak pernah

Jenjang dibaca lewat `tingkat_efektif`: orang tanpa baris jabatan dihitung STAF,
jadi akun baru tidak pernah lolos hanya karena jenjangnya belum diisi.

Dipakai oleh jalur web (`ProjectViewSet.create`), API v1 (`ProjectListCreateAPIEndpoint.post`),
dan endpoint `boleh-buat-project/` yang dibaca apps/web untuk menyembunyikan tombol.
Kalau aturan ini berubah, ubah di sini saja.
"""

# Module imports
from plane.db.models import WorkspaceMember
from plane.db.superadmin import is_super_admin
from plane.utils import aturan
from plane.utils.aturan.area_tugas import PROJECT_CREATE_MIN_LEVEL
from plane.utils.aturan.jenis import NAMA_TINGKAT
from plane.utils.hierarki import tingkat_efektif

PERAN_ADMIN_WORKSPACE = 20
PERAN_MEMBER_WORKSPACE = 15

PESAN_DEPARTEMEN_DI_GODMODE = "Departments are created in God Mode."


def pesan_tolak_buat_project() -> str:
    """Pesan 403 yang menyebut jenjang terendah yang berlaku sekarang."""
    nama = NAMA_TINGKAT[aturan.get_int(PROJECT_CREATE_MIN_LEVEL)]
    return f"Only workspace admins and members at {nama} level and above can create projects."


def boleh_buat_project(user, workspace_id) -> bool:
    """True kalau `user` boleh membuat project di workspace ini."""
    if user is None or getattr(user, "is_anonymous", True):
        return False
    if is_super_admin(user):
        return True
    peran = (
        WorkspaceMember.objects.filter(workspace_id=workspace_id, member_id=user.id, is_active=True)
        .values_list("role", flat=True)
        .first()
    )
    if peran is None or peran < PERAN_MEMBER_WORKSPACE:
        return False
    if peran >= PERAN_ADMIN_WORKSPACE:
        return True
    return tingkat_efektif(user.id, workspace_id) >= aturan.get_int(PROJECT_CREATE_MIN_LEVEL)
