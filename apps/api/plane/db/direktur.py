# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: direktur otomatis anggota semua divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Direktur (tingkat 40) selalu jadi anggota setiap project di workspace-nya.

Keputusan user: "by default, direktur can view all division in projects".
Tanpa ini, KEP-02 (divisi = project private) mengunci direktur keluar dari
divisi yang ia bukan anggotanya — dan gerbang hierarki menolaknya sebagai
"bukan anggota divisi", padahal kalimat user memberi direktur kewenangan
lintas divisi "karena tingkat teratas".

## Kenapa lewat signal, bukan lewat God Mode manual

Sama alasannya dengan Super Admin tersembunyi (B1, `plane/db/superadmin.py`):
kalau lewat klik manual di God Mode, project yang dibuat BELAKANGAN tidak
ikut terjangkau — dan "direktur bisa lihat semua divisi" jadi janji yang
bocor setiap kali divisi baru lahir. Lewat signal, jalur pembuatan mana pun
(API, skrip, shell) ikut tercakup.

## Bedanya dengan Super Admin: TIDAK disembunyikan

Super Admin disaring keluar dari daftar anggota (B1). Direktur TIDAK —
direktur memang pimpinan yang wajar terlihat di daftar divisinya. Barisnya
adalah `ProjectMember` biasa (role 20), jadi tidak ada divergensi izin baru:
seluruh 33 tempat yang membaca keanggotaan langsung mengenalinya.

## Kapan keanggotaan lahir

1. **Project baru dibuat** → seluruh direktur di workspace itu ikut ditambahkan.
2. **Seseorang diangkat jadi direktur** (baris `JabatanOrganisasi` tingkat 40
   dibuat) → ia disusulkan ke seluruh project yang ada di workspace itu.
3. **Jenjang direktur dicabut** → TIDAK mengeluarkan dari project. Mengeluarkan
   orang dari 31 divisi karena satu baris jenjang berubah adalah tindakan
   merusak yang tidak bisa dibatalkan diam-diam; kalau memang harus keluar,
   admin project yang mengeluarkan lewat jalur biasa.
"""

# Django imports
from django.db.models.signals import post_save
from django.dispatch import receiver


def direktur_user_ids(workspace_id=None):
    """Id user berjenjang direktur (tingkat >= 40)."""
    from plane.db.models import JabatanOrganisasi, TINGKAT_DIREKTUR

    qs = JabatanOrganisasi.objects.filter(tingkat__gte=TINGKAT_DIREKTUR)
    if workspace_id is not None:
        qs = qs.filter(workspace_id=workspace_id)
    return set(qs.values_list("member_id", flat=True))


def sinkronkan_direktur(workspace_id=None, user_id=None):
    """Pastikan direktur jadi anggota seluruh project di workspace-nya.

    Dipanggil sesudah pengangkatan direktur baru, dan aman dijalankan ulang
    (baris yang pernah dicabut dihidupkan kembali, bukan digandakan — jebakan
    A21). Mengembalikan jumlah keanggotaan yang benar-benar berubah.
    """
    from plane.db.models import Project

    if user_id is not None:
        ids = {user_id}
        qs = Project.objects.filter(deleted_at__isnull=True)
        if workspace_id is not None:
            qs = qs.filter(workspace_id=workspace_id)
    else:
        ids = direktur_user_ids(workspace_id)
        if not ids:
            return 0
        qs = Project.objects.filter(deleted_at__isnull=True)
        if workspace_id is not None:
            qs = qs.filter(workspace_id=workspace_id)
    return _tambahkan_ke_project(ids, qs)


def _tambahkan_ke_project(user_ids, projects):
    """Jadikan anggota project, tanpa menggandakan baris yang sudah ada.

    Satu panggilan ke `plane.db.membership.jadikan_anggota_project()` per
    pasangan — invarian yang sama dengan Super Admin, jadi tidak disalin.
    Role 20: direktur di divisinya bertindak sebagai admin divisi.
    """
    from plane.db.membership import jadikan_anggota_project

    jumlah = 0
    for p in projects:
        for uid in user_ids:
            _, berubah = jadikan_anggota_project(p.id, uid, 20, workspace_id=p.workspace_id)
            jumlah += 1 if berubah else 0
    return jumlah


@receiver(post_save, sender="db.Project")
def project_baru_untuk_direktur(sender, instance, created, **kwargs):
    """Project baru → semua direktur di workspace itu langsung punya akses."""
    if not created:
        return
    ids = direktur_user_ids(instance.workspace_id)
    if ids:
        _tambahkan_ke_project(ids, [instance])


@receiver(post_save, sender="db.JabatanOrganisasi")
def jabatan_direktur_baru_disusulkan(sender, instance, created, **kwargs):
    """Seseorang menjadi direktur → susulkan ke seluruh project yang ada.

    Dipicu saat barisnya BARU dan tingkatnya direktur, ATAU saat baris lama
    NAIK menjadi direktur (God Mode memakai POST yang sama untuk keduanya:
    `upsert` lewat create-or-revive). Pencabutan tidak mengeluarkan dari
    project (lihat docstring modul).
    """
    from plane.db.models import TINGKAT_DIREKTUR

    if (instance.tingkat or 0) < TINGKAT_DIREKTUR:
        return
    if instance.deleted_at is not None:
        return
    sinkronkan_direktur(workspace_id=instance.workspace_id, user_id=instance.member_id)
