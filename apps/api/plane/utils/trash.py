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
"""

# Django imports
from django.conf import settings
from django.utils import timezone

# Auditlog (MIT, jazzband), lihat NOTICE.md
from auditlog.models import LogEntry

# Module imports
from plane.bgtasks.deletion_task import restore_related_objects
from plane.db.models import Cycle, Issue, Module, Page


def _filter_page_project(qs, project_id):
    # Page tidak punya project_id sendiri, tautannya lewat tabel project_pages.
    return qs.filter(project_pages__project_id=project_id)


def _filter_langsung(qs, project_id):
    return qs.filter(project_id=project_id)


# Hanya barang yang berarti bagi orang. Anak-anaknya (komentar, tautan, reaksi,
# aktivitas) sengaja TIDAK didaftarkan: mereka ikut terhapus bersama induknya
# dan ikut kembali saat induknya dipulihkan, jadi menampilkannya sendiri-sendiri
# hanya membuat tong sampah penuh barang yang tidak bisa ditindaklanjuti.
TRASH_MODELS = {
    "issue": {
        "model": Issue,
        "label": "Work item",
        "filter_project": _filter_langsung,
        "nama": lambda o: o.name,
        "project_id": lambda o: o.project_id,
    },
    "page": {
        "model": Page,
        "label": "Halaman",
        "filter_project": _filter_page_project,
        "nama": lambda o: o.name or "(tanpa judul)",
        "project_id": lambda o: (o.project_pages.first().project_id if o.project_pages.exists() else None),
    },
    "cycle": {
        "model": Cycle,
        "label": "Cycle",
        "filter_project": _filter_langsung,
        "nama": lambda o: o.name,
        "project_id": lambda o: o.project_id,
    },
    "module": {
        "model": Module,
        "label": "Module",
        "filter_project": _filter_langsung,
        "nama": lambda o: o.name,
        "project_id": lambda o: o.project_id,
    },
}


def _peta_penghapus(tipe, pks):
    """Siapa yang membuang barang ini, dibaca dari jejak audit.

    `deleted_at` hanya menyimpan KAPAN, bukan SIAPA, tidak ada kolomnya di
    model. Pelakunya ada di jejak audit, jadi diambil dari sana dengan SATU
    query untuk seluruh halaman, bukan satu query per baris.

    Hanya tersedia untuk model yang memang dipantau auditlog (issue & page).
    Selain itu hasilnya kosong, dan itu ditampilkan apa adanya, bukan ditebak.
    """
    if not pks:
        return {}
    entri = (
        LogEntry.objects.filter(
            content_type__model=tipe,
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
        peta[e.object_pk] = (
            {"email": e.actor.email, "display_name": e.actor.display_name} if e.actor else None
        )
    return peta


def _sisa_hari(deleted_at):
    batas = deleted_at + timezone.timedelta(days=settings.HARD_DELETE_AFTER_DAYS)
    sisa = (batas - timezone.now()).days
    return max(sisa, 0)


def kumpulkan(project_id=None, tipe=None, limit=200):
    """Daftar barang di tong sampah. `project_id=None` berarti seluruh instance."""
    hasil = []
    kunci = [tipe] if tipe in TRASH_MODELS else list(TRASH_MODELS)

    for k in kunci:
        spec = TRASH_MODELS[k]
        qs = spec["model"].all_objects.filter(deleted_at__isnull=False)
        if project_id:
            qs = spec["filter_project"](qs, project_id)
        qs = qs.order_by("-deleted_at")[:limit]

        objek = list(qs)
        penghapus = _peta_penghapus(k, [o.pk for o in objek])

        for o in objek:
            hasil.append(
                {
                    "id": str(o.pk),
                    "type": k,
                    "type_label": spec["label"],
                    "name": spec["nama"](o),
                    "project_id": str(spec["project_id"](o)) if spec["project_id"](o) else None,
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
    id-nya.
    """
    spec = TRASH_MODELS.get(tipe)
    if not spec:
        return None, None
    qs = spec["model"].all_objects.filter(pk=pk, deleted_at__isnull=False)
    if project_id:
        qs = spec["filter_project"](qs, project_id)
    return qs.first(), spec


def pulihkan(obj):
    """Kembalikan barang beserta anak-anak yang ikut terhapus bersamanya."""
    cutoff = obj.deleted_at
    return restore_related_objects(obj._meta.app_label, obj._meta.model_name, obj.pk, cutoff)


def buang_permanen(obj):
    """Hapus sungguhan. Tidak bisa dibatalkan."""
    obj.delete(soft=False)
