# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ringkasan Dashboard Divisi untuk pimpinan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Angka di balik Dashboard Divisi (KEP-60).

Direktur dan Super Admin membuka halaman ini untuk satu pertanyaan: bagian mana
yang perlu saya lihat? Karena itu setiap project diberi status kesehatan, project
dikelompokkan ke divisinya (KEP-29), dan ada angka pembanding minggu lalu.

## Kenapa agregat, bukan perulangan per project

Versi lama menjalankan ~6 kueri per project. Dengan 40 project itu 240 kueri tiap
kali halaman dibuka. Di sini jumlahnya tetap (satu kueri per jenis angka) berapa
pun banyaknya project.

## Status kesehatan

`terlambat / aktif * 100`, dengan aktif = belum selesai dan belum dibatalkan.
Ambangnya diatur Super Admin di God Mode > Features (`DASHBOARD_PERHATIAN_PERSEN`,
`DASHBOARD_KRITIS_PERSEN`). Kalau keduanya tertukar (perhatian > kritis), yang
lebih kecil dipakai sebagai "perhatian": tertukar adalah salah ketik, bukan niat.
"""

# Python imports
from datetime import datetime, time, timedelta

# Django imports
from django.db.models import Count, F, Min, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

# Module imports
from plane.db.models import (
    DepartemenProject,
    Issue,
    IssueWorkLog,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    STATUS_PERSETUJUAN_MENUNGGU,
)
from plane.utils.hierarki import pengajuan_boleh_diputuskan
from plane.utils.menunggu_persetujuan import q_bisa_terlambat
from plane.utils.saklar_instance import (
    DASHBOARD_KRITIS_PERSEN,
    DASHBOARD_ON_TIME_WINDOW_DAYS,
    DASHBOARD_PERHATIAN_PERSEN,
    setelan_angka,
)
from plane.utils.setelan_instance import hari_ini_kantor, zona_kantor
from plane.utils.tanggal_otomatis import batas_terlambat
from plane.utils.wiki_access import WIKI_IDENTIFIER

LANCAR = "lancar"
PERHATIAN = "perhatian"
KRITIS = "kritis"
_URUTAN_STATUS = {KRITIS: 0, PERHATIAN: 1, LANCAR: 2}

_SELESAI = "completed"
_BATAL = "cancelled"
# Jendela "Selesai tepat waktu" kini setelan God Mode DASHBOARD_ON_TIME_WINDOW_DAYS
# (bawaan 30). Kunci internal `_bertenggat_30` / `_tepat_waktu_30` tetap bernama
# lama; angkanya mengikuti setelan.


def project_terjangkau(user, slug):
    """Project aktif yang user ini anggotanya. Sama dengan versi lama."""
    return (
        Project.objects.filter(
            workspace__slug=slug,
            project_projectmember__member=user,
            project_projectmember__is_active=True,
            archived_at__isnull=True,
        )
        # Wiki itu pustaka berkas, bukan project kerja: tak masuk angka dashboard.
        .exclude(identifier=WIKI_IDENTIFIER)
        .distinct()
        .order_by("name")
    )


def ambang_kesehatan():
    """(perhatian, kritis) dalam persen, perhatian <= kritis."""
    a = setelan_angka(DASHBOARD_PERHATIAN_PERSEN)
    b = setelan_angka(DASHBOARD_KRITIS_PERSEN)
    return min(a, b), max(a, b)


def status_kesehatan(terlambat, aktif, perhatian, kritis):
    """Lancar / perhatian / kritis dari porsi tugas aktif yang lewat tenggat."""
    if aktif <= 0 or terlambat <= 0:
        return LANCAR
    persen = terlambat * 100 / aktif
    if persen >= kritis:
        return KRITIS
    if persen >= perhatian:
        return PERHATIAN
    return LANCAR


def _persen(bagian, keseluruhan):
    return round(bagian * 100 / keseluruhan) if keseluruhan > 0 else None


def _angka_tugas(project_ids, hari_ini, sekarang, jendela_tepat_waktu):
    """{project_id: angka tugas} dalam satu kueri.

    Terlambat memakai `batas_terlambat` (tenggang `OVERDUE_GRACE_DAYS` dari God
    Mode), jadi angkanya sama dengan Due date yang tampil merah di aplikasi.
    """
    tujuh_hari = sekarang - timedelta(days=7)
    empat_belas_hari = sekarang - timedelta(days=14)
    sepekan_lalu = hari_ini - timedelta(days=7)
    awal_jendela = sekarang - timedelta(days=jendela_tepat_waktu)

    belum_tuntas = ~Q(state__group__in=[_SELESAI, _BATAL])
    # KEP-84: yang menunggu persetujuan selesai tidak terlambat (tetap dihitung
    # aktif di penyebut kesehatan: tugasnya memang belum disetujui selesai).
    bisa_terlambat = q_bisa_terlambat()
    terlambat = Q(target_date__lt=batas_terlambat(hari_ini)) & belum_tuntas & bisa_terlambat
    selesai = Q(state__group=_SELESAI)
    selesai_bertenggat = selesai & Q(completed_at__gte=awal_jendela, target_date__isnull=False)
    # Tepat waktu = tanggal selesai (hari kantor, BUKAN hari UTC) <= tenggat, aturan
    # yang sama dengan laporan selesai (`utils/laporan_selesai.py`).
    tepat_waktu = selesai_bertenggat & Q(tanggal_selesai__lte=F("target_date"))
    awal_sepekan_lalu = datetime.combine(sepekan_lalu, time.min, tzinfo=zona_kantor())

    baris = (
        Issue.issue_objects.filter(project_id__in=project_ids)
        .annotate(tanggal_selesai=TruncDate("completed_at", tzinfo=zona_kantor()))
        .values("project_id")
        .annotate(
            total=Count("id"),
            selesai=Count("id", filter=selesai),
            batal=Count("id", filter=Q(state__group=_BATAL)),
            terlambat=Count("id", filter=terlambat),
            terlambat_tertua=Min("target_date", filter=terlambat),
            selesai_7=Count("id", filter=selesai & Q(completed_at__gte=tujuh_hari)),
            selesai_7_lalu=Count(
                "id", filter=selesai & Q(completed_at__gte=empat_belas_hari, completed_at__lt=tujuh_hari)
            ),
            # Lewat tenggat seminggu lalu: tenggatnya sudah lewat saat itu dan
            # tugasnya belum selesai saat itu (atau sampai sekarang). Yang kini
            # menunggu persetujuan disaring sama dengan angka minggu ini, supaya
            # pembandingnya setara.
            terlambat_lalu=Count(
                "id",
                filter=Q(target_date__lt=batas_terlambat(sepekan_lalu))
                & ~Q(state__group=_BATAL)
                & (Q(completed_at__isnull=True) | Q(completed_at__gte=awal_sepekan_lalu))
                & bisa_terlambat,
            ),
            bertenggat_30=Count("id", filter=selesai_bertenggat),
            tepat_waktu_30=Count("id", filter=tepat_waktu),
        )
    )
    return {r["project_id"]: r for r in baris}


def _menit_kerja(project_ids, awal_bulan):
    baris = (
        IssueWorkLog.objects.filter(project_id__in=project_ids)
        .values("project_id")
        .annotate(total=Sum("duration"), bulan=Sum("duration", filter=Q(logged_at__gte=awal_bulan)))
    )
    return {r["project_id"]: r for r in baris}


def _jumlah_anggota(project_ids):
    baris = (
        ProjectMember.objects.filter(project_id__in=project_ids, is_active=True)
        .values("project_id")
        .annotate(n=Count("id"))
    )
    return {r["project_id"]: r["n"] for r in baris}


def _persetujuan_untuk_saya(user, projects):
    """{project_id: jumlah} pengajuan menunggu yang boleh user ini putuskan.

    Wewenang dinilai per (project, pemohon) lewat `pengajuan_boleh_diputuskan`,
    sama dengan POST setuju/tolak: angka di sini = baris yang memang bisa ia putuskan.
    """
    baris = (
        PersetujuanPenugasan.objects.filter(project_id__in=[p.id for p in projects], status=STATUS_PERSETUJUAN_MENUNGGU)
        .exclude(pemohon=user)
        .values_list("project_id", "pemohon_id")
        .annotate(n=Count("id"))
    )
    jumlah = {(pid, pemohon): n for pid, pemohon, n in baris}
    if not jumlah:
        return {}
    # Hanya project yang memang punya antrean yang diperiksa wewenangnya.
    workspace_dari = {p.id: p.workspace_id for p in projects}
    per_workspace = {}
    for pasangan in jumlah:
        per_workspace.setdefault(workspace_dari[pasangan[0]], set()).add(pasangan)
    hasil = {}
    for workspace_id, pasangan in per_workspace.items():
        for pid, pemohon in pengajuan_boleh_diputuskan(user, workspace_id, pasangan):
            hasil[pid] = hasil.get(pid, 0) + jumlah[(pid, pemohon)]
    return hasil


def _peta_departemen(project_ids):
    """{project_id: DepartemenProject} untuk departemen & divisi yang masih hidup."""
    baris = DepartemenProject.objects.filter(
        project_id__in=project_ids,
        departemen__deleted_at__isnull=True,
        departemen__divisi__deleted_at__isnull=True,
    ).select_related("departemen__divisi")
    return {b.project_id: b for b in baris}


def _baris_project(project, tugas, kerja, anggota, persetujuan, peta, hari_ini, ambang):
    total = tugas.get("total", 0)
    selesai = tugas.get("selesai", 0)
    aktif = total - selesai - tugas.get("batal", 0)
    terlambat = tugas.get("terlambat", 0)
    tertua = tugas.get("terlambat_tertua")
    dp = peta.get(project.id)
    return {
        "id": str(project.id),
        "identifier": project.identifier,
        "name": project.name,
        "members": anggota.get(project.id, 0),
        "issues_total": total,
        "issues_completed": selesai,
        "issues_open": total - selesai,
        "issues_active": aktif,
        "issues_overdue": terlambat,
        "overdue_oldest_days": (hari_ini - tertua).days if tertua else None,
        "completion_rate": _persen(selesai, total - tugas.get("batal", 0)),
        "completed_7d": tugas.get("selesai_7", 0),
        "completed_prev_7d": tugas.get("selesai_7_lalu", 0),
        "overdue_prev_7d": tugas.get("terlambat_lalu", 0),
        "_bertenggat_30": tugas.get("bertenggat_30", 0),
        "_tepat_waktu_30": tugas.get("tepat_waktu_30", 0),
        "pending_approvals": persetujuan.get(project.id, 0),
        "worklog_minutes_total": kerja.get("total") or 0,
        "worklog_minutes_month": kerja.get("bulan") or 0,
        "health": status_kesehatan(terlambat, aktif, *ambang),
        "department": (
            {"id": str(dp.departemen_id), "code": dp.departemen.kode, "name": dp.departemen.nama} if dp else None
        ),
        "division_id": str(dp.departemen.divisi_id) if dp else None,
        "_division": dp.departemen.divisi if dp else None,
    }


_JUMLAHKAN = (
    "issues_total",
    "issues_completed",
    "issues_open",
    "issues_active",
    "issues_overdue",
    "completed_7d",
    "completed_prev_7d",
    "overdue_prev_7d",
    "pending_approvals",
    "worklog_minutes_total",
    "worklog_minutes_month",
    "_bertenggat_30",
    "_tepat_waktu_30",
)


def _jumlahkan(rows):
    return {k: sum(r[k] for r in rows) for k in _JUMLAHKAN}


def _rangkum(jumlah, ambang):
    """Tambahkan angka turunan ke hasil `_jumlahkan`."""
    batal = jumlah["issues_open"] - jumlah["issues_active"]
    return {
        **{k: v for k, v in jumlah.items() if not k.startswith("_")},
        "completion_rate": _persen(jumlah["issues_completed"], jumlah["issues_total"] - batal),
        "on_time_rate": _persen(jumlah["_tepat_waktu_30"], jumlah["_bertenggat_30"]),
        "health": status_kesehatan(jumlah["issues_overdue"], jumlah["issues_active"], *ambang),
    }


def _kunci_urut(baris):
    return (_URUTAN_STATUS[baris["health"]], -baris["issues_overdue"], baris["name"].lower())


def _kelompokkan_divisi(rows, ambang):
    kelompok = {}
    for r in rows:
        divisi = r["_division"]
        kunci = divisi.id if divisi else None
        if kunci not in kelompok:
            kelompok[kunci] = {
                "id": str(divisi.id) if divisi else None,
                "code": divisi.kode if divisi else "",
                "name": divisi.nama if divisi else "",
                "rows": [],
            }
        kelompok[kunci]["rows"].append(r)

    hasil = []
    for k in kelompok.values():
        anggota = k.pop("rows")
        hasil.append(
            {
                **k,
                **_rangkum(_jumlahkan(anggota), ambang),
                "project_ids": [r["id"] for r in sorted(anggota, key=_kunci_urut)],
            }
        )
    # Divisi tanpa nama (project belum dipetakan) selalu paling akhir.
    return sorted(hasil, key=lambda d: (d["id"] is None, *_kunci_urut(d)))


def hitung_ringkasan(user, slug, sekarang=None):
    """Seluruh isi Dashboard Divisi untuk `user`."""
    sekarang = sekarang or timezone.now()
    hari_ini = hari_ini_kantor(sekarang)
    awal_bulan = sekarang.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ambang = ambang_kesehatan()

    projects = list(project_terjangkau(user, slug))
    ids = [p.id for p in projects]
    jendela_tepat_waktu = setelan_angka(DASHBOARD_ON_TIME_WINDOW_DAYS)
    tugas = _angka_tugas(ids, hari_ini, sekarang, jendela_tepat_waktu)
    kerja = _menit_kerja(ids, awal_bulan)
    anggota = _jumlah_anggota(ids)
    persetujuan = _persetujuan_untuk_saya(user, projects)
    peta = _peta_departemen(ids)

    rows = [
        _baris_project(p, tugas.get(p.id, {}), kerja.get(p.id, {}), anggota, persetujuan, peta, hari_ini, ambang)
        for p in projects
    ]
    divisions = _kelompokkan_divisi(rows, ambang)
    totals = {"projects": len(rows), **_rangkum(_jumlahkan(rows), ambang)}

    for r in rows:
        for k in ("_division", "_bertenggat_30", "_tepat_waktu_30"):
            r.pop(k)

    return {
        "generated_at": sekarang,
        "thresholds": {"attention": ambang[0], "critical": ambang[1]},
        # Label "Selesai tepat waktu (N hari terakhir)" di apps/web membaca ini.
        "on_time_window_days": jendela_tepat_waktu,
        "totals": totals,
        "divisions": divisions,
        "projects": sorted(rows, key=_kunci_urut),
    }
