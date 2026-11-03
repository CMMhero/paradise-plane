# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: laporan tugas selesai untuk pimpinan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Laporan "apa saja yang selesai" di Dashboard Divisi (KEP-62).

Mode Ringkas (KEP-60) menjawab "bagian mana yang bermasalah". Laporan ini
menjawab pertanyaan sesudahnya: "apa yang sudah dikerjakan dalam periode ini?",
lengkap dengan judul tugasnya. Cakupannya sama dengan dashboard
(`project_terjangkau`), jadi tidak ada yang bisa melihat project yang tidak ia
anggotai.

## Definisi

- **Selesai** = grup status `completed` dengan `completed_at` di dalam periode.
  Dibatalkan bukan selesai.
- **Hari = hari kantor (WIB)**, sama dengan ringkasan harian (KEP-58). Server
  berjalan di UTC; tugas yang selesai 06.30 WIB tercatat 23.30 UTC kemarin.
- **Tepat waktu** = punya tenggat dan tanggal selesai (WIB) <= tenggat.
  **Terlambat** = punya tenggat dan selesai sesudahnya. Tanpa tenggat dihitung
  terpisah, tidak masuk penyebut persentase.
- **Periode pembanding** = jendela sepanjang periode itu tepat sebelumnya
  (bulan lalu untuk "bulan ini" dan dua bulan lalu untuk "bulan lalu").

Daftar judul dibatasi `BATAS_DAFTAR` supaya halaman tetap ringan; angka selalu
dihitung dari semua tugas, dan CSV memuat semuanya.
"""

# Python imports
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

# Django imports
from django.db.models import Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

# Module imports
from plane.db.models import Issue, IssueAssignee
from plane.utils.ringkasan_divisi import _peta_departemen, project_terjangkau

ZONA_KANTOR = ZoneInfo("Asia/Jakarta")

PERIODE_7_HARI = "7d"
PERIODE_30_HARI = "30d"
PERIODE_BULAN_INI = "this_month"
PERIODE_BULAN_LALU = "last_month"
PERIODE_SAH = (PERIODE_7_HARI, PERIODE_30_HARI, PERIODE_BULAN_INI, PERIODE_BULAN_LALU)
PERIODE_BAWAAN = PERIODE_7_HARI

TEPAT_WAKTU = "on_time"
TERLAMBAT = "late"
TANPA_TENGGAT = "no_due_date"

BATAS_DAFTAR = 500

_SELESAI = "completed"


def _awal_bulan(hari):
    return hari.replace(day=1)


def _bulan_sebelumnya(awal):
    return _awal_bulan(awal - timedelta(days=1))


def rentang_periode(periode, hari_ini):
    """(awal, akhir) tanggal kantor untuk periode dan pembandingnya; akhir eksklusif.

    Hasil: ((awal, akhir), (awal_lalu, akhir_lalu)).
    """
    besok = hari_ini + timedelta(days=1)
    if periode in (PERIODE_7_HARI, PERIODE_30_HARI):
        panjang = 7 if periode == PERIODE_7_HARI else 30
        awal = besok - timedelta(days=panjang)
        return (awal, besok), (awal - timedelta(days=panjang), awal)
    if periode == PERIODE_BULAN_INI:
        awal = _awal_bulan(hari_ini)
        return (awal, besok), (_bulan_sebelumnya(awal), awal)
    if periode == PERIODE_BULAN_LALU:
        akhir = _awal_bulan(hari_ini)
        awal = _bulan_sebelumnya(akhir)
        return (awal, akhir), (_bulan_sebelumnya(awal), awal)
    raise ValueError(f"periode tidak dikenal: {periode}")


def _ke_waktu(hari):
    return datetime.combine(hari, time.min, tzinfo=ZONA_KANTOR)


def ketepatan(tanggal_selesai, tenggat):
    if tenggat is None:
        return TANPA_TENGGAT
    return TEPAT_WAKTU if tanggal_selesai <= tenggat else TERLAMBAT


def _selesai_di(project_ids, awal, akhir):
    return Issue.issue_objects.filter(
        project_id__in=project_ids,
        state__group=_SELESAI,
        completed_at__gte=_ke_waktu(awal),
        completed_at__lt=_ke_waktu(akhir),
    ).annotate(tanggal_selesai=TruncDate("completed_at", tzinfo=ZONA_KANTOR))


_ANGKA = {
    "completed": Count("id"),
    "on_time": Count("id", filter=Q(target_date__isnull=False, tanggal_selesai__lte=F("target_date"))),
    "late": Count("id", filter=Q(target_date__isnull=False, tanggal_selesai__gt=F("target_date"))),
    "no_due_date": Count("id", filter=Q(target_date__isnull=True)),
}


def _persen(bagian, keseluruhan):
    return round(bagian * 100 / keseluruhan) if keseluruhan > 0 else None


def _lengkapi(angka):
    angka = {k: angka.get(k) or 0 for k in _ANGKA}
    return {**angka, "on_time_rate": _persen(angka["on_time"], angka["on_time"] + angka["late"])}


def _penanggung_jawab(issue_ids):
    """{issue_id: [nama]} lewat IssueAssignee (manajer soft-delete membuang penugasan yang dicabut)."""
    hasil = {}
    baris = (
        IssueAssignee.objects.filter(issue_id__in=issue_ids)
        .select_related("assignee")
        .order_by("assignee__display_name")
    )
    for b in baris:
        hasil.setdefault(b.issue_id, []).append(b.assignee.display_name or b.assignee.email)
    return hasil


def _kelompok(projects, angka_project, peta):
    """Divisi > project, masing-masing dengan angkanya. Divisi terbanyak selesai dulu."""
    divisi = {}
    for p in projects:
        angka = _lengkapi(angka_project.get(p.id, {}))
        if angka["completed"] == 0:
            continue
        dp = peta.get(p.id)
        d = dp.departemen.divisi if dp else None
        kunci = d.id if d else None
        if kunci not in divisi:
            divisi[kunci] = {
                "id": str(d.id) if d else None,
                "code": d.kode if d else "",
                "name": d.nama if d else "",
                "projects": [],
            }
        divisi[kunci]["projects"].append(
            {
                "id": str(p.id),
                "identifier": p.identifier,
                "name": p.name,
                "department": (
                    {"id": str(dp.departemen_id), "code": dp.departemen.kode, "name": dp.departemen.nama}
                    if dp
                    else None
                ),
                **angka,
            }
        )

    hasil = []
    for d in divisi.values():
        d["projects"].sort(key=lambda p: (-p["completed"], p["name"].lower()))
        jumlah = {k: sum(p[k] for p in d["projects"]) for k in _ANGKA}
        hasil.append({**d, **_lengkapi(jumlah)})
    # Project tanpa departemen selalu paling akhir.
    return sorted(hasil, key=lambda d: (d["id"] is None, -d["completed"], d["name"].lower()))


def _baris_tugas(issue, nama):
    return {
        "id": str(issue.id),
        "project_id": str(issue.project_id),
        "project_identifier": issue.project.identifier,
        "project_name": issue.project.name,
        "sequence_id": issue.sequence_id,
        "name": issue.name,
        "priority": issue.priority,
        "completed_at": issue.completed_at,
        "completed_date": issue.tanggal_selesai,
        "target_date": issue.target_date,
        "timing": ketepatan(issue.tanggal_selesai, issue.target_date),
        "assignees": nama.get(issue.id, []),
    }


def daftar_selesai(project_ids, awal, akhir, batas=None):
    """Tugas selesai dalam periode, terbaru dulu, lengkap dengan penanggung jawab."""
    qs = _selesai_di(project_ids, awal, akhir).select_related("project").order_by("-completed_at", "-sequence_id")
    tugas = list(qs[:batas] if batas else qs)
    nama = _penanggung_jawab([t.id for t in tugas])
    return [_baris_tugas(t, nama) for t in tugas]


def susun_laporan(user, slug, periode=PERIODE_BAWAAN, sekarang=None):
    """Seluruh isi tampilan Laporan untuk `user`."""
    if periode not in PERIODE_SAH:
        raise ValueError(f"periode tidak dikenal: {periode}")
    sekarang = sekarang or timezone.now()
    hari_ini = sekarang.astimezone(ZONA_KANTOR).date()
    (awal, akhir), (awal_lalu, akhir_lalu) = rentang_periode(periode, hari_ini)

    projects = list(project_terjangkau(user, slug))
    ids = [p.id for p in projects]

    angka_project = {
        r["project_id"]: r for r in _selesai_di(ids, awal, akhir).values("project_id").annotate(**_ANGKA)
    }
    totals = _lengkapi({k: sum(r[k] for r in angka_project.values()) for k in _ANGKA})
    sebelumnya = _lengkapi(_selesai_di(ids, awal_lalu, akhir_lalu).aggregate(**_ANGKA))
    totals["created"] = Issue.issue_objects.filter(
        project_id__in=ids, created_at__gte=_ke_waktu(awal), created_at__lt=_ke_waktu(akhir)
    ).count()

    items = daftar_selesai(ids, awal, akhir, batas=BATAS_DAFTAR)
    return {
        "generated_at": sekarang,
        "period": {
            "key": periode,
            "start": awal,
            # Inklusif untuk tampilan: "1 - 7 Nov", bukan "1 - 8 Nov".
            "end": akhir - timedelta(days=1),
        },
        "totals": totals,
        "previous": sebelumnya,
        "divisions": _kelompok(projects, angka_project, _peta_departemen(ids)),
        "items": items,
        "items_truncated": totals["completed"] > len(items),
    }


def baris_csv(user, slug, periode=PERIODE_BAWAAN, sekarang=None):
    """Header + semua tugas selesai dalam periode, untuk unduhan CSV (tanpa batas)."""
    sekarang = sekarang or timezone.now()
    hari_ini = sekarang.astimezone(ZONA_KANTOR).date()
    (awal, akhir), _ = rentang_periode(periode, hari_ini)

    ids = list(project_terjangkau(user, slug).values_list("id", flat=True))
    peta = {str(pid): dp for pid, dp in _peta_departemen(ids).items()}
    yield ["Divisi", "Departemen", "Project", "Nomor", "Judul", "Penanggung jawab", "Selesai", "Tenggat", "Ketepatan"]
    for t in daftar_selesai(ids, awal, akhir):
        dp = peta.get(t["project_id"])
        yield [
            dp.departemen.divisi.nama if dp else "",
            dp.departemen.nama if dp else "",
            t["project_name"],
            f"{t['project_identifier']}-{t['sequence_id']}",
            t["name"],
            ", ".join(t["assignees"]),
            _tanggal(t["completed_date"]),
            _tanggal(t["target_date"]),
            LABEL_KETEPATAN[t["timing"]],
        ]


LABEL_KETEPATAN = {TEPAT_WAKTU: "Tepat waktu", TERLAMBAT: "Terlambat", TANPA_TENGGAT: "Tanpa tenggat"}


def _tanggal(nilai):
    return nilai.isoformat() if isinstance(nilai, date) else ""
