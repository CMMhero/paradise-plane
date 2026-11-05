# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi Trashbin & TPA
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Sumber tunggal untuk Trashbin (per project) dan TPA (God Mode).

Keduanya membaca data yang SAMA, barang ber-`deleted_at`, hanya cakupannya
yang berbeda: Trashbin dibatasi satu project dan dioperasikan admin project,
TPA melihat seluruh instance dan dioperasikan Super Admin. Karena itu logikanya
tinggal di sini, bukan disalin dua kali; kalau disalin, cepat atau lambat
keduanya akan berbeda pendapat soal apa yang sebenarnya ada di tong sampah.

Akun adalah satu-satunya jenis yang bukan soft-delete: barisnya digosok, dan
identitas aslinya disimpan di `AkunTerhapus`. Ia punya jalur sendiri di bawah
(`_AKUN`), hanya terlihat di TPA.
"""

# Django imports
from django.db import IntegrityError, transaction
from django.utils import timezone

# Auditlog (MIT, jazzband), lihat NOTICE.md
from auditlog.models import LogEntry

# Module imports
from plane.utils.saklar_instance import TRASH_RETENTION_DAYS, setelan_angka
from plane.bgtasks.deletion_task import restore_related_objects
from plane.db.models import (
    AkunTerhapus,
    Cycle,
    Initiative,
    JabatanOrganisasi,
    Issue,
    IssueTemplate,
    IssueView,
    Label,
    Module,
    Page,
    Project,
    User,
    WorkspaceMember,
)


class TrashConflict(Exception):
    """Barang tidak bisa dipulihkan karena tempatnya sudah dipakai yang lain."""


def _filter_page_project(qs, project_id):
    # Page tidak punya project_id sendiri, tautannya lewat tabel project_pages.
    return qs.filter(project_pages__project_id=project_id)


def _filter_langsung(qs, project_id):
    return qs.filter(project_id=project_id)


def _induk_hidup(qs):
    # Barang yang ikut terhapus karena PROJECT-nya dihapus tidak ditampilkan
    # satu per satu: mereka kembali bersama project-nya. Tanpa saringan ini satu
    # project terhapus membanjiri TPA dengan ratusan work item.
    return qs.filter(project__deleted_at__isnull=True)


def _pid(o):
    return o.project_id


# Pemeriksaan bentrok SEBELUM memulihkan. Pemulihan berjenjang mengembalikan
# anak lebih dulu baru induknya; kalau induknya baru gagal di akhir, anaknya
# sudah terlanjur hidup di bawah induk yang masih terhapus.
def _cek_project(o):
    hidup = Project.objects.filter(workspace_id=o.workspace_id)
    if hidup.filter(identifier=o.identifier).exists():
        raise TrashConflict(f"Another project already uses the identifier {o.identifier}.")
    if hidup.filter(name=o.name).exists():
        raise TrashConflict(f"Another project is already named {o.name}.")


def _cek_label(o):
    if Label.objects.filter(workspace_id=o.workspace_id, project_id=o.project_id, name=o.name).exists():
        raise TrashConflict(f"Another label is already named {o.name}.")


# Hanya barang yang berarti bagi orang. Anak-anaknya (komentar, tautan, reaksi,
# aktivitas) sengaja TIDAK didaftarkan: mereka ikut terhapus bersama induknya
# dan ikut kembali saat induknya dipulihkan, jadi menampilkannya sendiri-sendiri
# hanya membuat tong sampah penuh barang yang tidak bisa ditindaklanjuti.
#
# `filter_project=None` = jenis tingkat instance/workspace, hanya tampil di TPA.
TRASH_MODELS = {
    "project": {
        "model": Project,
        "label": "Project",
        "filter_project": None,
        "nama": lambda o: f"{o.name} ({o.identifier})",
        "cek": _cek_project,
        "project_id": lambda o: o.pk,
    },
    "issue": {
        "model": Issue,
        "label": "Work item",
        "filter_project": _filter_langsung,
        "saring": _induk_hidup,
        "nama": lambda o: o.name,
        "project_id": _pid,
    },
    "page": {
        "model": Page,
        "label": "Page",
        "filter_project": _filter_page_project,
        "nama": lambda o: o.name or "(untitled)",
        "project_id": lambda o: o.project_pages.first().project_id if o.project_pages.exists() else None,
    },
    "cycle": {
        "model": Cycle,
        "label": "Cycle",
        "filter_project": _filter_langsung,
        "saring": _induk_hidup,
        "nama": lambda o: o.name,
        "project_id": _pid,
    },
    "module": {
        "model": Module,
        "label": "Module",
        "filter_project": _filter_langsung,
        "saring": _induk_hidup,
        "nama": lambda o: o.name,
        "project_id": _pid,
    },
    "view": {
        "model": IssueView,
        "label": "View",
        "filter_project": _filter_langsung,
        "nama": lambda o: o.name,
        "project_id": _pid,
    },
    "label": {
        "model": Label,
        "label": "Label",
        "cek": _cek_label,
        "filter_project": _filter_langsung,
        "nama": lambda o: o.name,
        "project_id": _pid,
    },
    "template": {
        "model": IssueTemplate,
        "label": "Template",
        "filter_project": _filter_langsung,
        "saring": _induk_hidup,
        "nama": lambda o: o.name,
        "project_id": _pid,
    },
    "initiative": {
        "model": Initiative,
        "label": "Initiative",
        "filter_project": None,
        "nama": lambda o: o.name,
        "project_id": lambda o: None,
    },
}

TIPE_AKUN = "account"
SEMUA_TIPE = (*TRASH_MODELS, TIPE_AKUN)


def _peta_penghapus(model_name, pks):
    """Siapa yang membuang barang ini, dibaca dari jejak audit.

    `deleted_at` hanya menyimpan KAPAN, bukan SIAPA, tidak ada kolomnya di
    model. Pelakunya ada di jejak audit, jadi diambil dari sana dengan SATU
    query untuk seluruh halaman, bukan satu query per baris.

    Hanya tersedia untuk model yang memang dipantau auditlog. Selain itu
    hasilnya kosong, dan itu ditampilkan apa adanya, bukan ditebak.
    """
    if not pks:
        return {}
    entri = (
        LogEntry.objects.filter(
            content_type__model=model_name,
            action=LogEntry.Action.DELETE,
            object_pk__in=[str(p) for p in pks],
        )
        .select_related("actor")
        .order_by("object_pk", "-timestamp")
    )
    peta = {}
    for e in entri:
        # Urutannya menurun per object_pk, jadi yang pertama = paling akhir.
        if e.object_pk in peta:
            continue
        peta[e.object_pk] = _orang(e.actor)
    return peta


def _orang(u):
    return {"id": str(u.id), "email": u.email, "display_name": u.display_name} if u else None


def _sisa_hari(deleted_at):
    batas = deleted_at + timezone.timedelta(days=setelan_angka(TRASH_RETENTION_DAYS))
    sisa = (batas - timezone.now()).days
    return max(sisa, 0)


def _queryset(spec, project_id):
    qs = spec["model"].all_objects.filter(deleted_at__isnull=False)
    if spec.get("saring"):
        qs = spec["saring"](qs)
    if project_id:
        qs = spec["filter_project"](qs, project_id)
    return qs


def _kumpulkan_akun(limit):
    snapshot = AkunTerhapus.objects.select_related("dihapus_oleh").order_by("-dihapus_pada")[:limit]
    return [
        {
            "id": str(a.user_id),
            "type": TIPE_AKUN,
            "type_label": "Account",
            "name": f"{a.display_name} <{a.email}>" if a.display_name else a.email,
            "project_id": None,
            "deleted_at": a.dihapus_pada,
            "days_left": _sisa_hari(a.dihapus_pada),
            "deleted_by": _orang(a.dihapus_oleh),
        }
        for a in snapshot
    ]


def kumpulkan(project_id=None, tipe=None, limit=200):
    """Daftar barang di tong sampah. `project_id=None` berarti seluruh instance."""
    hasil = []
    kunci = [tipe] if tipe in SEMUA_TIPE else list(SEMUA_TIPE)

    for k in kunci:
        if k == TIPE_AKUN:
            if not project_id:
                hasil.extend(_kumpulkan_akun(limit))
            continue
        spec = TRASH_MODELS[k]
        if project_id and spec["filter_project"] is None:
            continue

        objek = list(_queryset(spec, project_id).order_by("-deleted_at")[:limit])
        penghapus = _peta_penghapus(spec["model"]._meta.model_name, [o.pk for o in objek])

        for o in objek:
            pid = spec["project_id"](o)
            hasil.append(
                {
                    "id": str(o.pk),
                    "type": k,
                    "type_label": spec["label"],
                    "name": spec["nama"](o),
                    "project_id": str(pid) if pid else None,
                    "deleted_at": o.deleted_at,
                    "days_left": _sisa_hari(o.deleted_at),
                    "deleted_by": penghapus.get(str(o.pk)),
                }
            )

    hasil.sort(key=lambda x: x["deleted_at"], reverse=True)
    return hasil[:limit]


def ambil(tipe, pk, project_id=None):
    """Ambil satu barang dari tong sampah, atau None kalau bukan haknya.

    `project_id` mempersempit ke satu project, dipakai Trashbin supaya admin
    project A tidak bisa memulihkan barang milik project B hanya dengan menebak
    id-nya. Jenis tingkat instance (project, initiative, akun) tidak pernah
    terjangkau dari Trashbin project.
    """
    if tipe == TIPE_AKUN:
        if project_id:
            return None, None
        return AkunTerhapus.objects.filter(user_id=pk).select_related("user").first(), None
    spec = TRASH_MODELS.get(tipe)
    if not spec or (project_id and spec["filter_project"] is None):
        return None, None
    return _queryset(spec, project_id).filter(pk=pk).first(), spec


def _pulihkan_akun(snap):
    u = snap.user
    if User.objects.filter(email__iexact=snap.email).exclude(pk=u.pk).exists():
        raise TrashConflict(f"Another account already uses {snap.email}.")
    u.email = snap.email
    u.username = snap.username
    u.display_name = snap.display_name
    u.first_name = snap.first_name
    u.last_name = snap.last_name
    u.is_active = True
    u.save(update_fields=["email", "username", "display_name", "first_name", "last_name", "is_active"])
    # Hanya keanggotaan yang aktif saat dihapus, dan hanya di workspace yang
    # masih ada. Super Admin sengaja tidak dikembalikan (lihat model).
    jumlah = WorkspaceMember.objects.filter(
        id__in=snap.workspace_member_ids, workspace__deleted_at__isnull=True
    ).update(is_active=True)
    # Penempatan organisasi yang dicabut SAAT akun dihapus (lihat
    # InstanceMemberDetailEndpoint.delete) kembali juga; yang dicabut sebelumnya tidak.
    jabatan = JabatanOrganisasi.all_objects.filter(member=u, deleted_at__gte=snap.dihapus_pada)
    workspace_ids = set(jabatan.values_list("workspace_id", flat=True))
    jumlah += jabatan.update(deleted_at=None)
    snap.delete()
    if workspace_ids:
        from plane.db.jangkauan import sinkronkan_satu  # noqa: PLC0415

        for ws_id in workspace_ids:
            transaction.on_commit(lambda ws_id=ws_id: sinkronkan_satu(ws_id, u.id))
    return 1 + jumlah


def pulihkan(obj, spec=None):
    """Kembalikan barang beserta anak-anak yang ikut terhapus bersamanya.

    Melempar `TrashConflict` kalau tempatnya sudah diambil barang lain
    (email akun, identifier project, nama label).

    Akun dipulihkan dalam satu transaksi: identitas dan keanggotaannya kembali
    bersama atau tidak sama sekali. Barang lain sengaja TIDAK: pemulihan
    berjenjang melewati anak yang bentrok satu per satu (lihat
    `restore_related_objects`), dan satu transaksi akan membuat satu anak
    bentrok menggagalkan seluruh project.
    """
    try:
        if isinstance(obj, AkunTerhapus):
            with transaction.atomic():
                return _pulihkan_akun(obj)
        if spec and spec.get("cek"):
            spec["cek"](obj)
        if spec and spec.get("pulihkan"):
            return spec["pulihkan"](obj)
        return restore_related_objects(obj._meta.app_label, obj._meta.model_name, obj.pk, obj.deleted_at)
    except IntegrityError as e:
        raise TrashConflict("Something with the same name or identifier already exists.") from e


def buang_permanen(obj):
    """Hapus sungguhan. Tidak bisa dibatalkan.

    Untuk akun: identitas aslinya dimusnahkan; baris User tetap ada sebagai
    "Deleted account" supaya rujukan lama tidak putus.
    """
    if isinstance(obj, AkunTerhapus):
        obj.delete()
        return
    obj.delete(soft=False)
