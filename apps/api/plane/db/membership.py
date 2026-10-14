# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Satu tempat untuk menjadikan seseorang anggota sebuah project.

KENAPA BERKAS INI ADA

`ProjectMember.objects.create()` telanjang TIDAK aman dipakai untuk menambah
anggota, dan itu tidak kelihatan dari namanya. `ProjectMember.save()` membuat
baris `ProjectUserProperty` untuk pasangan (user, project) setiap kali
`_state.adding`, dan `ProjectUserProperty` punya constraint unik
`project_user_property_unique_user_project_when_deleted_at_null`. Jadi
`create()` kedua untuk pasangan yang sama tidak gagal dengan pesan "sudah jadi
anggota" — ia gagal dengan `IntegrityError` dari tabel LAIN, dan pemanggilnya
menerima 500 atau 400 yang tidak menyebut sebabnya sama sekali.

Bukti terukurnya (di stack lokal, 14 Okt 2026):

    IntegrityError: duplicate key value violates unique constraint
    "project_user_property_unique_user_project_when_deleted_at_null"
    DETAIL: Key (user_id, project_id)=(a8676efa-…, 0a9a29a3-…) already exists.

Dua pemanggil nyata yang tertabrak: pembuatan project oleh Super Admin (signal
`plane.db.superadmin` sudah menambahkan mereka lebih dulu) dan penerimaan
undangan project. Karena itu keanggotaan tidak boleh dibuat "buta" di mana pun;
semuanya lewat fungsi di bawah.

Manager yang dipakai `all_objects`, BUKAN manager bawaan, karena manager bawaan
menyaring habis baris ber-`deleted_at` — dengan manager bawaan, keanggotaan
yang pernah dicabut tidak terlihat, `create()` dibuat ulang, dan pembuatnya
menabrak constraint unik yang sama seperti di atas. Keanggotaan yang pernah
dicabut **dihidupkan kembali**, bukan digandakan.
"""


def jadikan_anggota_project(project_id, user_id, role, workspace_id=None):
    """Pastikan ada tepat satu `ProjectMember` aktif untuk (project, user).

    Mengembalikan `(member, berubah)`. `berubah` True kalau barisnya baru dibuat
    atau baru dihidupkan/diubah — dipakai pemanggil yang melaporkan berapa
    anggota yang benar-benar ditambahkan.

    Impor `ProjectMember` di dalam fungsi: `plane.db.models` memuat modul ini
    lewat app registry, jadi impor di tingkat modul akan melingkar.
    """
    from plane.db.models import ProjectMember

    member = ProjectMember.all_objects.filter(project_id=project_id, member_id=user_id).first()

    if member is None:
        kwargs = {"project_id": project_id, "member_id": user_id, "role": role}
        if workspace_id is not None:
            kwargs["workspace_id"] = workspace_id
        return ProjectMember.objects.create(**kwargs), True

    if member.deleted_at is not None or not member.is_active or member.role != role:
        member.deleted_at = None
        member.is_active = True
        member.role = role
        member.save(update_fields=["deleted_at", "is_active", "role"])
        return member, True

    return member, False
