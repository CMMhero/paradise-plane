# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan kepemilikan tugas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapa boleh membuang dan siapa boleh menggeser tenggat sebuah tugas.

Aturan ini berlaku di SELURUH project, yang sekarang maupun yang dibuat nanti,
dan datang dari pemilik instance:

    hapus tugas        pembuatnya, Super Admin, atau admin project
                       (gerbang hierarki aktif: sama dengan hak UBAH, yaitu
                       pembuat/assignee atau atasannya, plus Super Admin)
    arsipkan tugas     sama dengan hapus
    ganti Due Date     HANYA pembuatnya atau Super Admin
    sisanya            bebas seperti biasa untuk semua anggota

Dua baris pertama dan baris ketiga sengaja BERBEDA, dan itu bukan
ketidakkonsistenan. Menghapus tugas adalah urusan beres-beres papan, jadi kepala
divisi ikut dipercaya. Menggeser tenggat adalah mengubah janji kepada orang
lain, dan itu hanya boleh dilakukan yang membuat janjinya.

Kenapa satu berkas sendiri: aturan ini harus dijawab sama persis di lapisan API
aplikasi, di API token, dan nanti di tampilan. Satu aturan yang disalin ke tiga
tempat cepat atau lambat jadi tiga aturan.
"""

from plane.db.superadmin import is_super_admin

_ROLE_ADMIN = 20


def _admin_project(user, slug, project_id):
    from plane.db.models import ProjectMember

    return ProjectMember.objects.filter(
        member=user,
        workspace__slug=slug,
        project_id=project_id,
        role=_ROLE_ADMIN,
        is_active=True,
    ).exists()


def bisa_hapus_tugas(user, issue, slug, project_id):
    """Boleh menghapus atau mengarsipkan tugas ini.

    Arsip disamakan dengan hapus dengan sengaja: mengarsipkan tugas
    menyembunyikannya dari SEMUA papan, jadi kalau hapus dikunci sementara arsip
    dibiarkan bebas, orang yang di-assign tetap bisa membuat tugas orang lain
    lenyap dari pandangan, hanya lewat pintu yang namanya berbeda.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    if is_super_admin(user):
        return True

    # Gerbang hierarki aktif: hapus/arsip ikut aturan UBAH (`galat_ubah_tugas`),
    # yaitu pembuat/assignee tugas itu sendiri, atau atasannya. Admin project
    # TIDAK lagi cukup: di kantor ini hampir semua staf berperan admin project,
    # jadi jalur itu membuat staf bisa menghapus tugas orang lain.
    from plane.utils.hierarki import galat_ubah_tugas, gerbang_aktif  # noqa: PLC0415

    if gerbang_aktif():
        return galat_ubah_tugas(project_id, issue, actor=user) is None

    if issue.created_by_id == user.id:
        return True
    return _admin_project(user, slug, project_id)


def bisa_ganti_tenggat(user, issue):
    """Boleh menggeser Due Date tugas ini.

    Sengaja LEBIH KETAT daripada hak hapus: admin project tidak termasuk.
    Tenggat adalah janji yang dibuat seseorang, dan menggesernya diam-diam dari
    atas adalah persis hal yang ingin dicegah pemilik instance.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    return issue.created_by_id == user.id or is_super_admin(user)


def _tanggal(nilai):
    """Normalkan tanggal ke bentuk `YYYY-MM-DD` supaya bisa dibandingkan.

    Klien mengirim tanggal sebagai teks, kadang berikut jamnya, sementara di
    database ia `DateField`. Tanpa penormalan, "2026-08-25" dan
    "2026-08-25T00:00:00Z" akan terlihat berbeda dan setiap penyimpanan biasa
    dituduh mengubah tenggat.
    """
    if nilai in (None, ""):
        return None
    teks = str(nilai)
    return teks[:10]


def tenggat_diubah(issue, data):
    """True hanya kalau permintaan ini benar-benar MENGUBAH Due Date.

    Ini bukan kerapian, ini penentu benar atau salahnya seluruh aturan. Beberapa
    layar mengirim ulang seluruh isi formulir saat menyimpan, termasuk tenggat
    yang tidak disentuh. Menolak berdasarkan "ada target_date di payload" akan
    membuat orang yang di-assign tidak bisa menyimpan apa pun, padahal yang ia
    ubah cuma prioritas.
    """
    if "target_date" not in data:
        return False
    return _tanggal(data.get("target_date")) != _tanggal(issue.target_date)
