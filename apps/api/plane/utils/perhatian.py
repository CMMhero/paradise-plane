# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ringkasan "perlu perhatian" di Home
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi widget "Needs attention" di Home.

Satu panggilan, kueri berjumlah tetap. Tiap kelompok memakai SATU kueri yang
membawa totalnya lewat fungsi jendela (`Count` atas seluruh hasil sebelum
`LIMIT`), jadi menampilkan lima baris teratas tetap tahu ada berapa semuanya.

## Cakupan

Hanya project yang user anggotai (sama dengan Dashboard Divisi) dan tugas aktif
(bukan selesai/batal; arsip, draf, dan Triage sudah disaring `issue_objects`).

## Kelompok

Semua orang: `overdue_mine`, `due_soon`, `rejected`, `waiting_mine`, `mentioned`.
Atasan saja: `decide` (menunggu keputusan saya) dan `team_overdue`. Atasan
ditentukan oleh aturan antrean persetujuan per baris (`pengajuan_boleh_diputuskan`,
sama dengan POST setuju/tolak) dan `divisi_diawasi`; tidak ada aturan wewenang
baru di sini.

Satu tugas bisa muncul di dua kelompok (mis. ditolak DAN lewat tenggat). Itu
sengaja: tiap kelompok menjawab pertanyaan yang berbeda.
"""

from datetime import timedelta

from functools import reduce
from operator import or_

from django.db.models import Count, Exists, OuterRef, Q, Window
from django.utils import timezone

from plane.db.models import (
    IssueAssignee,
    Issue,
    IssueMention,
    PersetujuanPenugasan,
    STATUS_PERSETUJUAN_DITOLAK,
    STATUS_PERSETUJUAN_MENUNGGU,
    Workspace,
)
from plane.utils.hierarki import divisi_diawasi, pengajuan_boleh_diputuskan
from plane.utils.menunggu_persetujuan import q_bisa_terlambat
from plane.utils.ringkasan_divisi import project_terjangkau
from plane.utils.tanggal_otomatis import batas_terlambat
from plane.utils.saklar_instance import DIGEST_LOOKAHEAD_DAYS, setelan_angka
from plane.utils.setelan_instance import hari_ini_kantor
# Jendela "rejected" dan "mentioned" dari God Mode (KEP-83); bawaan 14 dan 7 hari.
from plane.utils.saklar_instance import ATTENTION_MENTION_DAYS, ATTENTION_REJECTED_DAYS

# Baris yang dikirim per kelompok; sisanya cukup berupa angka `count`.
BATAS_ITEM = 5

_TUNTAS = ("completed", "cancelled")
# Pengajuan menunggu yang tugasnya sudah Done (data lama, KEP-55) tetap harus
# terlihat dan bisa diputuskan; hanya yang dibatalkan yang gugur.
_BATAL = ("cancelled",)

# Urutan di layar: yang menunggu keputusan saya paling atas.
URUTAN = ("decide", "overdue_mine", "rejected", "team_overdue", "due_soon", "waiting_mine", "mentioned")

_KOLOM_TUGAS = ("id", "sequence_id", "name", "project_id", "project__identifier", "project__name", "target_date")
# Kolom yang sama bila barisnya adalah persetujuan/sebutan (tugas lewat `issue`).
_KOLOM_VIA_ISSUE = (
    "issue_id",
    "issue__sequence_id",
    "issue__name",
    "project_id",
    "project__identifier",
    "project__name",
    "issue__target_date",
)


def _item(baris, **tambahan):
    """Daftar-putih bentuk baris: nomor, judul, tenggat, project. Tidak ada isi lain."""
    return {
        "id": str(baris["id"]),
        "sequence_id": baris["sequence_id"],
        "identifier": f"{baris['project__identifier']}-{baris['sequence_id']}",
        "name": baris["name"],
        "project_id": str(baris["project_id"]),
        "project_name": baris["project__name"],
        "target_date": baris["target_date"],
        **tambahan,
    }


def _item_via_issue(baris, **tambahan):
    return _item(
        {
            "id": baris["issue_id"],
            "sequence_id": baris["issue__sequence_id"],
            "project__identifier": baris["project__identifier"],
            "name": baris["issue__name"],
            "project_id": baris["project_id"],
            "project__name": baris["project__name"],
            "target_date": baris["issue__target_date"],
        },
        **tambahan,
    )


def _kelompok(queryset, urutan, bangun=_item):
    """(jumlah, [item]) dari satu kueri `.values(...)`."""
    baris = list(queryset.annotate(_total=Window(Count("id"))).order_by(*urutan)[:BATAS_ITEM])
    return (baris[0]["_total"] if baris else 0), [bangun(b) for b in baris]


def _tugas_aktif(project_ids):
    return Issue.issue_objects.filter(project_id__in=project_ids).exclude(state__group__in=_TUNTAS)


def _ditugaskan_ke(user):
    return Exists(IssueAssignee.objects.filter(issue_id=OuterRef("pk"), assignee=user))


def _persetujuan(project_ids, kecuali_grup, **saring):
    """Baris persetujuan yang tugasnya hidup dan tidak berstatus `kecuali_grup`."""
    return (
        PersetujuanPenugasan.objects.filter(project_id__in=project_ids, issue__deleted_at__isnull=True, **saring)
        .exclude(issue__state__group__in=kecuali_grup)
        .exclude(issue__archived_at__isnull=False)
        .exclude(issue__is_draft=True)
    )


def susun_perhatian(user, slug):
    """Balasan endpoint `paradise/attention/`. Lihat docstring modul."""
    sekarang = timezone.now()
    hari_ini = hari_ini_kantor(sekarang)
    batas = batas_terlambat(hari_ini)
    workspace_id = Workspace.objects.values_list("id", flat=True).get(slug=slug)
    project_ids = list(project_terjangkau(user, slug).values_list("id", flat=True))

    kelompok = {}

    def simpan(kunci, hasil, **tambahan):
        kelompok[kunci] = {"count": hasil[0], "items": hasil[1], **tambahan}

    punya_saya = _tugas_aktif(project_ids).filter(_ditugaskan_ke(user))
    # KEP-84: yang menunggu persetujuan selesai tidak terlambat dan tidak
    # "segera jatuh tempo"; ia tetap terlihat di `waiting_mine` (dan `decide`).
    bisa_terlambat = q_bisa_terlambat()
    punya_saya_jalan = punya_saya.filter(bisa_terlambat)

    simpan(
        "overdue_mine",
        _kelompok(punya_saya_jalan.filter(target_date__lt=batas).values(*_KOLOM_TUGAS), ("target_date", "sequence_id")),
    )
    # Hari ini sampai DIGEST_LOOKAHEAD_DAYS (God Mode, bawaan 7, sama dengan
    # ringkasan harian) ke depan. Mulai dari batas terlambat supaya tidak ada
    # celah ketika ada tenggang (OVERDUE_GRACE_DAYS).
    hari_depan = setelan_angka(DIGEST_LOOKAHEAD_DAYS)
    depan = hari_ini + timedelta(days=hari_depan)
    simpan(
        "due_soon",
        _kelompok(
            punya_saya_jalan.filter(target_date__gte=batas, target_date__lte=depan).values(*_KOLOM_TUGAS),
            ("target_date", "sequence_id"),
        ),
    )

    # Ditolak dan belum diajukan ulang: hanya baris TERBARU tugas itu yang dihitung.
    lebih_baru = PersetujuanPenugasan.objects.filter(issue_id=OuterRef("issue_id"), created_at__gt=OuterRef("created_at"))
    ditolak = (
        _persetujuan(
            project_ids,
            _TUNTAS,
            pemohon=user,
            status=STATUS_PERSETUJUAN_DITOLAK,
            diputuskan_pada__gte=sekarang - timedelta(days=setelan_angka(ATTENTION_REJECTED_DAYS)),
        )
        .filter(~Exists(lebih_baru))
        .values(*_KOLOM_VIA_ISSUE, "alasan", "diputuskan_pada")
    )
    simpan(
        "rejected",
        _kelompok(
            ditolak,
            ("-diputuskan_pada",),
            lambda b: _item_via_issue(b, reason=b["alasan"], decided_at=b["diputuskan_pada"]),
        ),
    )

    # Yang saya ajukan dan masih ditunggu atasan.
    menunggu = _persetujuan(project_ids, _BATAL, pemohon=user, status=STATUS_PERSETUJUAN_MENUNGGU).values(
        *_KOLOM_VIA_ISSUE, "created_at"
    )
    simpan(
        "waiting_mine",
        _kelompok(menunggu, ("created_at",), lambda b: _item_via_issue(b, requested_at=b["created_at"])),
    )

    # Disebut dalam tugas yang masih aktif, seminggu terakhir.
    sebutan = (
        IssueMention.objects.filter(
            mention=user,
            project_id__in=project_ids,
            created_at__gte=sekarang - timedelta(days=setelan_angka(ATTENTION_MENTION_DAYS)),
            issue__deleted_at__isnull=True,
            issue__is_draft=False,
            issue__archived_at__isnull=True,
        )
        .exclude(issue__state__group__in=_TUNTAS)
        .values(*_KOLOM_VIA_ISSUE, "created_at")
    )
    simpan(
        "mentioned",
        _kelompok(sebutan, ("-created_at",), lambda b: _item_via_issue(b, mentioned_at=b["created_at"])),
    )

    # Bagian atasan. Aturannya dipinjam utuh dari hierarki, tidak dihitung ulang:
    # wewenang dinilai per (project, pemohon), sama dengan POST setuju/tolak, jadi
    # pengajuan supervisor (APPROVAL_REQUIRED_BELOW_LEVEL dinaikkan) hanya muncul
    # untuk yang jenjangnya lebih tinggi dari pemohon.
    # Pembuat TUGAS ikut dalam kunci: direktur hanya memutuskan tugas buatan manager.
    antrean = {
        (pid, pemohon, pembuat): n
        for pid, pemohon, pembuat, n in PersetujuanPenugasan.objects.filter(
            project_id__in=project_ids, status=STATUS_PERSETUJUAN_MENUNGGU
        )
        .exclude(pemohon=user)
        .values_list("project_id", "pemohon_id", "issue__created_by_id")
        .annotate(n=Count("id"))
    }
    sah = pengajuan_boleh_diputuskan(user, workspace_id, antrean) if antrean else set()
    jumlah_sah = {}
    for pid, pemohon, pembuat in sah:
        jumlah_sah[pid] = jumlah_sah.get(pid, 0) + antrean[(pid, pemohon, pembuat)]
    boleh = set(jumlah_sah)
    diawasi = divisi_diawasi(user.id, workspace_id) & set(project_ids)
    is_supervisor = bool(boleh or diawasi)

    if is_supervisor:
        # Kosong = Q yang tak pernah cocok (pk__in=[]), bukan "semua baris".
        # Per (project, pemohon, pembuat tugas): pemohon yang sama bisa punya tugas
        # buatan manager (boleh saya putuskan) dan buatan staf (tidak, bagi direktur).
        hanya_sah = reduce(
            or_,
            (
                Q(project_id=pid, pemohon_id=pemohon, issue__created_by_id=pembuat)
                if pembuat is not None
                else Q(project_id=pid, pemohon_id=pemohon, issue__created_by__isnull=True)
                for pid, pemohon, pembuat in sah
            ),
            Q(pk__in=[]),
        )
        keputusan = (
            _persetujuan(list(boleh), _BATAL, status=STATUS_PERSETUJUAN_MENUNGGU)
            .filter(hanya_sah)
            .exclude(pemohon=user)
            .values(*_KOLOM_VIA_ISSUE, "created_at", "pemohon__display_name")
        )
        terbanyak = max(boleh, key=lambda p: jumlah_sah[p], default=None)
        simpan(
            "decide",
            _kelompok(
                keputusan,
                ("created_at",),
                lambda b: _item_via_issue(b, requested_at=b["created_at"], requester=b["pemohon__display_name"]),
            ),
            top_project_id=str(terbanyak) if terbanyak else None,
        )
        # Tim = project yang saya awasi. Tugas saya sendiri sudah ada di `overdue_mine`.
        tim = (
            _tugas_aktif(list(diawasi))
            .filter(target_date__lt=batas)
            .filter(bisa_terlambat)
            .exclude(_ditugaskan_ke(user))
        )
        simpan("team_overdue", _kelompok(tim.values(*_KOLOM_TUGAS), ("target_date", "sequence_id")))

    urut = [{"key": k, **kelompok[k]} for k in URUTAN if k in kelompok]
    return {
        "generated_at": sekarang,
        "is_supervisor": is_supervisor,
        # Jendela `due_soon` yang berlaku, supaya label web ("7 hari ke depan")
        # tidak berbohong saat DIGEST_LOOKAHEAD_DAYS diubah di God Mode.
        "lookahead_days": hari_depan,
        "total": sum(g["count"] for g in urut),
        "groups": urut,
    }
