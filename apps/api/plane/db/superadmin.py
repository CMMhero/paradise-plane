# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Super Admin tersembunyi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Super Admin: akses ke semua project tanpa perlu di-assign, dan tidak terlihat.

Yang diminta: Super Admin (instance admin / God Mode) bisa memantau dan
mengerjakan apa pun di seluruh project, termasuk project yang baru dibuat,
tanpa ditambahkan manual, dan **keberadaannya tidak terlihat** oleh user maupun
admin project.

## Kenapa lewat keanggotaan otomatis, bukan menembus lapisan izin

Plane menentukan akses lewat keanggotaan: **33 berkas** menyaring queryset
dengan `project__project_projectmember__member=request.user`. Menambahkan jalan
pintas di lapisan izin berarti menyentuh ketiga puluh tiga tempat itu, dan satu
kondisi yang salah tulis di antaranya membuka akses ke orang yang salah, pada
instance berisi 79 orang.

Jadi Super Admin tetap PUNYA baris `ProjectMember`, dibuatkan otomatis, lalu
**disaring keluar dari setiap daftar anggota**. Hasil yang dilihat orang persis
sama dengan yang diminta, tanpa membongkar lapisan izin.

> **Batas yang harus disadari:** ini menyembunyikan di lapisan tampilan, bukan
> di penyimpanan. Barisnya tetap ada di tabel `project_members`. Siapa pun yang
> bisa membaca database langsung akan melihatnya, dan itu wajar, karena orang
> yang punya akses database sudah punya akses ke segalanya.

## Kapan keanggotaan dibuat

1. **Project baru dibuat** → seluruh Super Admin ikut ditambahkan.
2. **Super Admin baru diangkat** → ia ditambahkan ke seluruh project yang ada.

Keduanya lewat signal, bukan dipanggil dari view, supaya jalur pembuatan project
mana pun (API, skrip, shell) ikut tercakup.
"""

# Django imports
from django.db.models.signals import post_save
from django.dispatch import receiver


def super_admin_user_ids():
    """Id user yang berstatus instance admin (Super Admin).

    Diimpor di dalam fungsi: `plane.license` memuat model dari `plane.db`, jadi
    impor di tingkat modul akan melingkar saat app dimuat.
    """
    from plane.license.models import InstanceAdmin

    return set(InstanceAdmin.objects.values_list("user_id", flat=True))


def angkat_super_admin(instance, user, role=20):
    """Jadikan `user` instance admin, menghidupkan baris lama kalau ada.

    Mencabut Super Admin itu SOFT delete (`deleted_at` diisi, baris tetap ada),
    sedangkan `InstanceAdmin.unique_together = (instance, user)` tidak memuat
    `deleted_at`. `get_or_create` lewat manager bawaan tidak melihat baris
    yang sudah dicabut, lalu INSERT-nya menabrak unik: IntegrityError, yang
    oleh view dibalas "The payload is not valid". Jadi carinya lewat
    `all_objects`, dan baris yang dicabut dihidupkan kembali.
    """
    from plane.license.models import InstanceAdmin

    admin = InstanceAdmin.all_objects.filter(instance=instance, user=user).first()
    if admin is None:
        return InstanceAdmin.objects.create(instance=instance, user=user, role=role, is_verified=True)
    if admin.deleted_at is not None or admin.role != role or not admin.is_verified:
        admin.deleted_at = None
        admin.role = role
        admin.is_verified = True
        admin.save(update_fields=["deleted_at", "role", "is_verified"])
    return admin


def is_super_admin(user):
    """True kalau `user` berstatus Super Admin instance (God Mode).

    Satu definisi untuk seluruh aplikasi. Definisi Super Admin yang bercabang
    dua adalah cara paling rapi untuk membocorkan akses tanpa sadar, dan sudah
    ada tujuh pemakai `super_admin_user_ids()` di repo ini.
    """
    if user is None or getattr(user, "is_anonymous", True):
        return False
    return user.id in super_admin_user_ids()


def _q_penempatan_di_project(project_ref):
    """Q atas `JabatanOrganisasi`: penempatan orang ini mencakup project `project_ref`.

    `project_ref` boleh id biasa atau `OuterRef`. Cakupan dibaca dari struktur
    organisasi (KEP-29), bukan dari keanggotaan project:

        penempatan departemen -> project milik departemen itu
        penempatan divisi     -> project di semua departemen divisi itu

    Direktur (baris tanpa departemen & divisi) sengaja TIDAK dihitung. Ia
    mengawasi semua project, tapi tidak "berada di" departemen mana pun, jadi
    perlakuannya sama dengan Super Admin pengawas: tidak muncul.

    Tabel yang di-join tidak disaring manager soft-delete, jadi `deleted_at`
    tiap sambungan ditulis eksplisit.
    """
    from django.db.models import Q

    lewat_departemen = Q(
        departemen__deleted_at__isnull=True,
        departemen__divisi__deleted_at__isnull=True,
        departemen__project_departemen__deleted_at__isnull=True,
        departemen__project_departemen__project_id=project_ref,
    )
    lewat_divisi = Q(
        divisi__deleted_at__isnull=True,
        divisi__departemen__deleted_at__isnull=True,
        divisi__departemen__project_departemen__deleted_at__isnull=True,
        divisi__departemen__project_departemen__project_id=project_ref,
    )
    return lewat_departemen | lewat_divisi


def terlihat_di_project(project_id, ids=None):
    """Id Super Admin yang TIDAK disembunyikan di satu project.

    Dua jalan, salah satu cukup:

    1. Baris `SuperAdminTerlihatDiProject` (penanda manual "anggota asli").
    2. Penempatan God Mode-nya (departemen/divisi) mencakup project ini.
       Super Admin yang juga staf/supervisor/manager di sebuah departemen
       adalah rekan kerja di sana: ia harus bisa ditugaskan dan muncul di
       filter Created by, Assignees, Mentions, dan seterusnya.
    """
    from plane.db.models import JabatanOrganisasi, SuperAdminTerlihatDiProject  # noqa: PLC0415

    ids = super_admin_user_ids() if ids is None else ids
    if not ids or not project_id:
        return set()
    manual = SuperAdminTerlihatDiProject.objects.filter(project_id=project_id, member_id__in=ids).values_list(
        "member_id", flat=True
    )
    ditempatkan = (
        JabatanOrganisasi.objects.filter(_q_penempatan_di_project(project_id), member_id__in=ids)
        .values_list("member_id", flat=True)
        .distinct()
    )
    return set(manual) | set(ditempatkan)


def sembunyikan(queryset, field="member_id", project_id=None):
    """Buang Super Admin dari queryset keanggotaan SEBUAH PROJECT.

    Dipakai semua endpoint yang mengembalikan daftar anggota project. Satu
    fungsi supaya kalau kelak ada daftar baru, cukup dipanggil, bukan disalin
    logikanya.

    `project_id` WAJIB diisi untuk daftar per-project. Tanpa itu penyaringan
    berlaku menyeluruh, dan itulah yang dulu merusak: seseorang yang disaring
    dari SEMUA project ikut hilang dari project tempat ia benar-benar bekerja,
    sehingga tim IT tak bisa diberi tugas di project IT sendiri.

    Super Admin yang anggota asli project itu TIDAK disembunyikan: lewat baris
    `SuperAdminTerlihatDiProject` atau lewat penempatan departemen/divisinya
    (lihat `terlihat_di_project`).

    CATATAN PENTING: jangan pernah memakai fungsi ini pada daftar anggota
    WORKSPACE. Nama setiap orang di seluruh aplikasi diresolusi dari daftar itu;
    menyembunyikan seseorang di sana membuat namanya mustahil dirender di mana
    pun, dan hasilnya avatar "?" tanpa nama di dropdown assignee, mention, dan
    kartu work item.
    """
    ids = super_admin_user_ids()
    if not ids:
        return queryset

    if project_id:
        ids = ids - terlihat_di_project(project_id, ids)

    return queryset.exclude(**{f"{field}__in": ids}) if ids else queryset


def sembunyikan_lintas_project(queryset, field="member_id"):
    """Varian `sembunyikan()` untuk queryset yang MENCAKUP BANYAK PROJECT.

    Dipakai endpoint yang mengembalikan keanggotaan beberapa project sekaligus,
    sehingga tidak ada satu `project_id` yang bisa diberikan. Pengecualian
    diperiksa per-baris: sebuah baris ikut tampil bila si Super Admin punya
    penanda "anggota asli" untuk project pada baris itu sendiri.

    Memakai `Exists` alih-alih mengambil daftar id lebih dulu, supaya tetap satu
    query dan tidak melebar mengikuti jumlah project.
    """
    from django.db.models import Exists, OuterRef

    from plane.db.models import JabatanOrganisasi, SuperAdminTerlihatDiProject  # noqa: PLC0415

    ids = super_admin_user_ids()
    if not ids:
        return queryset

    manual = SuperAdminTerlihatDiProject.objects.filter(project_id=OuterRef("project_id"), member_id=OuterRef(field))
    ditempatkan = JabatanOrganisasi.objects.filter(
        _q_penempatan_di_project(OuterRef("project_id")), member_id=OuterRef(field)
    )
    return queryset.annotate(_terlihat_manual=Exists(manual), _terlihat_penempatan=Exists(ditempatkan)).exclude(
        **{f"{field}__in": ids, "_terlihat_manual": False, "_terlihat_penempatan": False}
    )


def _tambahkan_ke_project(user_ids, projects):
    """Jadikan anggota project, tanpa menggandakan baris yang sudah ada.

    Isinya satu panggilan ke `plane.db.membership.jadikan_anggota_project()`
    per pasangan: "periksa dulu, hidupkan kalau pernah dicabut" adalah satu
    invarian, dan invarian yang disalin ke dua tempat adalah invarian yang
    lambat-laun berbeda. Fungsi itu yang menjelaskan kenapa manager bawaan
    (`objects`) tidak boleh dipakai di sini.
    """
    from plane.db.membership import jadikan_anggota_project

    jumlah = 0
    for p in projects:
        for uid in user_ids:
            _, berubah = jadikan_anggota_project(p.id, uid, 20, workspace_id=p.workspace_id)
            jumlah += 1 if berubah else 0
    return jumlah


@receiver(post_save, sender="db.Project")
def project_baru_untuk_super_admin(sender, instance, created, **kwargs):
    """Project baru → semua Super Admin langsung punya akses."""
    if not created:
        return
    ids = super_admin_user_ids()
    if ids:
        _tambahkan_ke_project(ids, [instance])


def sinkronkan_super_admin(user_id=None):
    """Pastikan Super Admin jadi anggota SELURUH project yang ada.

    Dipanggil setelah mengangkat Super Admin baru. Aman dijalankan ulang,
    `get_or_create`, jadi tidak menggandakan.
    """
    from plane.db.models import Project

    ids = {user_id} if user_id else super_admin_user_ids()
    if not ids:
        return 0
    return _tambahkan_ke_project(ids, Project.objects.filter(deleted_at__isnull=True))
