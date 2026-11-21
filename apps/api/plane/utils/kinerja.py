# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: dashboard KPI untuk semua orang
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Angka di balik halaman KPI (`/kinerja`).

Semua orang punya halaman ini. Yang berbeda hanya LINGKUP yang boleh dibuka:

    staf                 -> dirinya sendiri
    leader / supervisor  -> + departemennya dan tiap bawahannya di sana
    manager              -> + divisinya, departemen di dalamnya, orang-orangnya
    direktur cabang      -> + cabangnya, semua divisi dan departemen di dalamnya
    sekretaris, direktur,
    admin workspace      -> seluruh organisasi

Dua bagian bisa diubah di God Mode: jenjang terendah yang melihat KPI tim
(KPI_TEAM_MIN_LEVEL, bawaan Leader) dan apakah admin workspace melihat seluruh
organisasi (KPI_WORKSPACE_ADMINS_SEE_ALL, bawaan ya). Super Admin selalu semua.

## Satu tabel metrik

`METRIK` adalah satu-satunya daftar metrik. Server menghitung tiap baris dari
angka mentah (`hitung`), dan mengirim daftarnya (`metrics`) ke web, jadi halaman
tidak punya daftar kedua yang bisa melenceng.

## Definisi

- **Hari = hari kantor** (`zona_kantor`), sama dengan laporan selesai (KEP-62).
- **Selesai, tepat waktu, terlambat, tanpa tenggat**: aturan `ketepatan` di
  `utils/ketepatan_waktu.py` (tenggat efektif = max(Due date, hari dicatat)).
- **Terlambat sekarang**: aturan `_angka_tugas` di `utils/ringkasan_divisi.py`
  (tenggang `OVERDUE_GRACE_DAYS`, yang menunggu persetujuan tidak dihitung).
- **Waktu siklus** = `completed_at` dikurangi Start date (awal hari kantor), atau
  waktu dibuat kalau Start date kosong.
- **Banyak penanggung jawab**: tiap orang mendapat kredit penuh. Di angka
  kelompok (departemen, divisi, organisasi) satu tugas tetap dihitung sekali.
- **Kelompok = orangnya**, bukan project-nya: angka departemen adalah tugas milik
  orang yang ditempatkan di departemen itu, di project mana pun.
- **Pembanding** = jendela sepanjang periode itu tepat sebelumnya.

Jumlah kueri tetap berapa pun banyaknya orang: satu kueri berkelompok per
keluarga angka, tanpa perulangan per orang.
"""

# Python imports
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Callable

# Django imports
from django.db.models import (
    Aggregate,
    Avg,
    Count,
    DateTimeField,
    DurationField,
    Exists,
    ExpressionWrapper,
    F,
    FloatField,
    Func,
    OuterRef,
    Q,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, Extract, Greatest
from django.utils import timezone

# Module imports
from plane.db.models import (
    Cabang,
    Departemen,
    Divisi,
    Issue,
    IssueAssignee,
    IssueWorkLog,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    STATUS_PERSETUJUAN_DISETUJUI,
    STATUS_PERSETUJUAN_DITOLAK,
    TINGKAT_CABANG,
    TINGKAT_MANAGER,
    User,
    WorkspaceMember,
    menjangkau_seluruh_organisasi,
)
from plane.db.superadmin import is_super_admin
from plane.utils import aturan
from plane.utils.akses_privat import saring_tugas_privat
from plane.utils.aturan.area_visibilitas import KPI_TEAM_MIN_LEVEL, KPI_WORKSPACE_ADMINS_SEE_ALL
from plane.utils.hierarki import _bawahan_ids, adalah_admin_penuh, divisi_diawasi
from plane.utils.ketepatan_waktu import anotasi_ketepatan, dibuat_dihitung, ketepatan, q_tepat_waktu, q_terlambat
from plane.utils.menunggu_persetujuan import q_bisa_terlambat
from plane.utils.setelan_instance import hari_ini_kantor, zona_kantor
from plane.utils.tanggal_otomatis import batas_terlambat

LINGKUP_SAYA = "saya"
LINGKUP_ORANG = "orang"
LINGKUP_DEPARTEMEN = "departemen"
LINGKUP_DIVISI = "divisi"
LINGKUP_CABANG = "cabang"
LINGKUP_ORGANISASI = "organisasi"
LINGKUP_SAH = (
    LINGKUP_SAYA,
    LINGKUP_ORANG,
    LINGKUP_DEPARTEMEN,
    LINGKUP_DIVISI,
    LINGKUP_CABANG,
    LINGKUP_ORGANISASI,
)

PERIODE_PEKAN_INI = "this_week"
PERIODE_BULAN_INI = "this_month"
PERIODE_30_HARI = "30d"
PERIODE_KUARTAL_INI = "this_quarter"
PERIODE_KHUSUS = "custom"
PERIODE_SAH = (PERIODE_PEKAN_INI, PERIODE_BULAN_INI, PERIODE_30_HARI, PERIODE_KUARTAL_INI, PERIODE_KHUSUS)
PERIODE_BAWAAN = PERIODE_BULAN_INI
RENTANG_KHUSUS_MAKS = 366

# Rentang sampai sepanjang ini digambar per hari, lebih panjang per pekan.
TREN_HARIAN_MAKS = 31
BATAS_DAFTAR = 20

_SELESAI = "completed"
_BATAL = "cancelled"
_GRUP_STATUS = ("backlog", "unstarted", "started")
_PRIORITAS = ("urgent", "high", "medium", "low", "none")


class LingkupDitolak(Exception):
    """Lingkup yang diminta di luar jangkauan pemanggil (HTTP 403)."""


class PermintaanSalah(ValueError):
    """Parameter tidak sah (HTTP 400)."""


# --------------------------------------------------------------------------
# Tabel metrik
# --------------------------------------------------------------------------


def _persen(bagian, keseluruhan):
    return round(bagian * 100 / keseluruhan) if keseluruhan > 0 else None


def _satu_desimal(nilai):
    return None if nilai is None else round(nilai, 1)


@dataclass(frozen=True)
class Metrik:
    kunci: str
    # count | percent | days | hours
    satuan: str
    # up = makin besar makin baik, down = makin kecil makin baik, neutral = tanpa penilaian
    arah: str
    hitung: Callable[[dict], float | int | None]
    # True = keadaan saat ini, tidak mengikuti periode.
    sesaat: bool = False

    def bentuk_api(self):
        return {
            "key": self.kunci,
            "label_key": f"kinerja.metric.{self.kunci}",
            "unit": self.satuan,
            "direction": self.arah,
            "snapshot": self.sesaat,
        }


METRIK = (
    Metrik("completed", "count", "up", lambda a: a["completed"]),
    Metrik("on_time_rate", "percent", "up", lambda a: _persen(a["on_time"], a["on_time"] + a["late"])),
    Metrik("completed_late", "count", "down", lambda a: a["late"]),
    Metrik("completed_no_due_date", "count", "neutral", lambda a: a["no_due_date"]),
    Metrik("overdue", "count", "down", lambda a: a["overdue"], sesaat=True),
    Metrik("open", "count", "neutral", lambda a: a["open"], sesaat=True),
    Metrik("cycle_avg_days", "days", "down", lambda a: _satu_desimal(a["cycle_avg"])),
    Metrik("cycle_median_days", "days", "down", lambda a: _satu_desimal(a["cycle_median"])),
    Metrik("approvals_approved", "count", "up", lambda a: a["approved"]),
    Metrik("approvals_rejected", "count", "down", lambda a: a["rejected"]),
    Metrik("worklog_hours", "hours", "neutral", lambda a: round(a["worklog_minutes"] / 60, 1)),
)

# Angka mentah yang kosongnya berarti nol; rata-rata tetap None.
_ANGKA_NOL = (
    "completed",
    "on_time",
    "late",
    "no_due_date",
    "overdue",
    "open",
    "approved",
    "rejected",
    "worklog_minutes",
)
_ANGKA_SEMUA = (*_ANGKA_NOL, "cycle_avg", "cycle_median")


def _nilai(angka):
    return {m.kunci: m.hitung(angka) for m in METRIK}


def _lengkapi(*bagian):
    angka = dict.fromkeys(_ANGKA_SEMUA)
    for b in bagian:
        angka.update({k: v for k, v in b.items() if k in angka and v is not None})
    for k in _ANGKA_NOL:
        angka[k] = angka[k] or 0
    return angka


# --------------------------------------------------------------------------
# Periode
# --------------------------------------------------------------------------


def rentang_periode(periode, hari_ini, mulai=None, sampai=None):
    """((awal, akhir), (awal_lalu, akhir_lalu)) dalam tanggal kantor, akhir eksklusif.

    Periode berjalan berakhir hari ini (inklusif). `custom` memakai `mulai` dan
    `sampai` (keduanya inklusif).
    """
    besok = hari_ini + timedelta(days=1)
    if periode == PERIODE_PEKAN_INI:
        awal, akhir = hari_ini - timedelta(days=hari_ini.weekday()), besok
    elif periode == PERIODE_BULAN_INI:
        awal, akhir = hari_ini.replace(day=1), besok
    elif periode == PERIODE_30_HARI:
        awal, akhir = besok - timedelta(days=30), besok
    elif periode == PERIODE_KUARTAL_INI:
        awal, akhir = date(hari_ini.year, 3 * ((hari_ini.month - 1) // 3) + 1, 1), besok
    elif periode == PERIODE_KHUSUS:
        if mulai is None or sampai is None:
            raise PermintaanSalah("Custom period needs 'mulai' and 'sampai' (YYYY-MM-DD).")
        if sampai < mulai:
            raise PermintaanSalah("'sampai' must not be before 'mulai'.")
        if (sampai - mulai).days >= RENTANG_KHUSUS_MAKS:
            raise PermintaanSalah(f"Custom period must not exceed {RENTANG_KHUSUS_MAKS} days.")
        awal, akhir = mulai, sampai + timedelta(days=1)
    else:
        raise PermintaanSalah(f"periode must be one of: {', '.join(PERIODE_SAH)}")
    panjang = akhir - awal
    return (awal, akhir), (awal - panjang, awal)


def _ke_waktu(hari):
    return datetime.combine(hari, time.min, tzinfo=zona_kantor())


# --------------------------------------------------------------------------
# Lingkup
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Lingkup:
    """Apa saja yang boleh dibuka satu orang. Semua id berupa str."""

    user_id: str
    seluruh: bool
    # Orang yang KPI pribadinya boleh dibuka (termasuk dirinya).
    orang: frozenset
    # departemen_id -> semua orang yang ditempatkan di sana (isi angka departemen).
    departemen: dict
    # divisi_id -> orang di semua departemennya + manager divisi itu.
    divisi: dict
    # cabang_id -> orang di semua divisinya + Direktur Cabang itu.
    cabang: dict
    # Seluruh anggota aktif workspace; hanya terisi kalau `seluruh`.
    semua_orang: frozenset
    info_departemen: dict
    info_divisi: dict
    info_cabang: dict


def lingkup_untuk(user, workspace_id):
    """Jangkauan KPI `user` dari penempatannya (KEP-29, KEP-93)."""
    saya = str(user.id)

    def _s(nilai):
        return str(nilai) if nilai else None

    baris = [
        (str(m), t, _s(dep), _s(div), _s(cab))
        for m, t, dep, div, cab in JabatanOrganisasi.objects.filter(workspace_id=workspace_id).values_list(
            "member_id", "tingkat", "departemen_id", "divisi_id", "cabang_id"
        )
    ]
    info_departemen = {
        str(d["id"]): {"id": str(d["id"]), "code": d["kode"], "name": d["nama"], "division_id": str(d["divisi_id"])}
        for d in Departemen.objects.filter(workspace_id=workspace_id, divisi__deleted_at__isnull=True).values(
            "id", "kode", "nama", "divisi_id"
        )
    }
    info_divisi = {
        str(d["id"]): {"id": str(d["id"]), "code": d["kode"], "name": d["nama"], "branch_id": _s(d["cabang_id"])}
        for d in Divisi.objects.filter(workspace_id=workspace_id).values("id", "kode", "nama", "cabang_id")
    }
    info_cabang = {
        str(c["id"]): {"id": str(c["id"]), "code": c["kode"], "name": c["nama"]}
        for c in Cabang.objects.filter(workspace_id=workspace_id).values("id", "kode", "nama")
    }

    jenjang = {}
    anggota_dep = {dep: set() for dep in info_departemen}
    anggota_div = {div: set() for div in info_divisi}
    anggota_cab = {cab: set() for cab in info_cabang}
    peran_dep = {}
    for m, t, dep, div, _ in baris:
        jenjang[m] = max(t, jenjang.get(m, t))
        if dep in anggota_dep:
            anggota_dep[dep].add(m)
            peran_dep[(m, dep)] = t
            anggota_div[info_departemen[dep]["division_id"]].add(m)
    # Baris divisi hanya berlaku untuk manager ke atas (`project_penempatan`).
    for m, t, _, div, cab in baris:
        if div in anggota_div and t >= TINGKAT_MANAGER:
            anggota_div[div].add(m)
        if cab in anggota_cab:
            anggota_cab[cab].add(m)
    for div, info in info_divisi.items():
        if info["branch_id"] in anggota_cab:
            anggota_cab[info["branch_id"]] |= anggota_div[div]

    seluruh = menjangkau_seluruh_organisasi(jenjang.get(saya)) or (
        adalah_admin_penuh(user, workspace_id)
        and (aturan.get_bool(KPI_WORKSPACE_ADMINS_SEE_ALL) or is_super_admin(user))
    )
    if seluruh:
        semua = frozenset(
            str(m)
            for m in WorkspaceMember.objects.filter(
                workspace_id=workspace_id, is_active=True, member__is_bot=False
            ).values_list("member_id", flat=True)
        )
        return Lingkup(
            saya,
            True,
            semua | {saya},
            anggota_dep,
            anggota_div,
            anggota_cab,
            semua,
            info_departemen,
            info_divisi,
            info_cabang,
        )

    orang = {saya}
    departemen = {}
    divisi = {}
    cabang = {}
    jenjang_saya = jenjang.get(saya)
    # Bawaan Leader (12) = dulu `> TINGKAT_MEMBER`: setiap jenjang di atas Staf.
    min_tim = aturan.get_int(KPI_TEAM_MIN_LEVEL)

    def buka_divisi(div):
        divisi[div] = anggota_div[div]
        for dep_id, info in info_departemen.items():
            if info["division_id"] == div:
                departemen[dep_id] = anggota_dep[dep_id]

    for m, _, dep, div, cab in baris:
        if m != saya:
            continue
        if cab in anggota_cab and jenjang_saya >= TINGKAT_CABANG:
            cabang[cab] = anggota_cab[cab]
            for div_id, info in info_divisi.items():
                if info["branch_id"] == cab:
                    buka_divisi(div_id)
            orang |= {m2 for m2 in anggota_cab[cab] if jenjang[m2] < jenjang_saya}
        if div in anggota_div and jenjang_saya >= TINGKAT_MANAGER:
            buka_divisi(div)
            orang |= {m2 for m2 in anggota_div[div] if jenjang[m2] < jenjang_saya}
        # Peran di departemen ini setinggi KPI_TEAM_MIN_LEVEL (bawaan: leader,
        # supervisor): bawahannya adalah yang perannya di departemen itu lebih rendah.
        if dep in anggota_dep and peran_dep[(saya, dep)] >= min_tim:
            departemen[dep] = anggota_dep[dep]
            orang |= {m2 for m2 in anggota_dep[dep] if peran_dep[(m2, dep)] < peran_dep[(saya, dep)]}

    if not info_divisi and (jenjang_saya or 0) >= min_tim:
        # Struktur belum diisi: bawahan datang dari keanggotaan project, seperti
        # resolver hierarki yang lain.
        for project_id in divisi_diawasi(user.id, workspace_id):
            orang |= {str(m) for m in _bawahan_ids(user.id, workspace_id, project_id)}

    return Lingkup(
        saya,
        False,
        frozenset(orang),
        departemen,
        divisi,
        cabang,
        frozenset(),
        info_departemen,
        info_divisi,
        info_cabang,
    )


def _orang_ringkas(ids):
    baris = User.objects.filter(id__in=list(ids)).order_by("display_name", "email")
    return [{"id": str(u.id), "display_name": u.display_name or u.email, "avatar_url": u.avatar_url} for u in baris]


def pilihan_lingkup(user, workspace_id):
    """Isi pemilih lingkup di halaman KPI."""
    lingkup = lingkup_untuk(user, workspace_id)
    return {
        "self": {"id": lingkup.user_id, "display_name": user.display_name or user.email},
        "organisation": lingkup.seluruh,
        "branches": sorted((lingkup.info_cabang[c] for c in lingkup.cabang), key=lambda c: c["name"].lower()),
        "divisions": sorted((lingkup.info_divisi[d] for d in lingkup.divisi), key=lambda d: d["name"].lower()),
        "departments": sorted(
            (lingkup.info_departemen[d] for d in lingkup.departemen), key=lambda d: d["name"].lower()
        ),
        "people": _orang_ringkas(lingkup.orang - {lingkup.user_id}),
    }


@dataclass(frozen=True)
class Sasaran:
    """Lingkup yang sudah lolos pemeriksaan wewenang."""

    jenis: str
    id: str | None
    nama: str
    # Orang yang tugasnya dihitung.
    orang: frozenset
    # Orang yang tampil di tabel (KPI pribadinya boleh dibuka pemanggil).
    tabel: frozenset
    # (jenis, {unit_id: orang}) untuk rincian per departemen/divisi.
    rincian: tuple | None = None


def sasaran_dari(lingkup, user, jenis, id_):
    """Terjemahkan (`lingkup`, `id`) permintaan jadi `Sasaran`, atau tolak."""
    if jenis not in LINGKUP_SAH:
        raise PermintaanSalah(f"lingkup must be one of: {', '.join(LINGKUP_SAH)}")
    if jenis == LINGKUP_SAYA or (jenis == LINGKUP_ORANG and id_ == lingkup.user_id):
        nama = user.display_name or user.email
        return Sasaran(LINGKUP_ORANG, lingkup.user_id, nama, frozenset({lingkup.user_id}), frozenset())
    if jenis == LINGKUP_ORGANISASI:
        if not lingkup.seluruh:
            raise LingkupDitolak
        return Sasaran(jenis, None, "", lingkup.semua_orang, lingkup.semua_orang, (LINGKUP_DIVISI, lingkup.divisi))
    if not id_:
        raise PermintaanSalah("id is required for this lingkup.")
    if jenis == LINGKUP_ORANG:
        if id_ not in lingkup.orang:
            raise LingkupDitolak
        orang = User.objects.filter(id=id_).first()
        if orang is None:
            raise LingkupDitolak
        return Sasaran(jenis, id_, orang.display_name or orang.email, frozenset({id_}), frozenset())
    if jenis == LINGKUP_DEPARTEMEN:
        if id_ not in lingkup.departemen:
            raise LingkupDitolak
        anggota = frozenset(lingkup.departemen[id_])
        return Sasaran(jenis, id_, lingkup.info_departemen[id_]["name"], anggota, anggota & lingkup.orang)
    if jenis == LINGKUP_CABANG:
        if id_ not in lingkup.cabang:
            raise LingkupDitolak
        anggota = frozenset(lingkup.cabang[id_])
        divisi = {div: lingkup.divisi[div] for div, info in lingkup.info_divisi.items() if info["branch_id"] == id_}
        return Sasaran(
            jenis, id_, lingkup.info_cabang[id_]["name"], anggota, anggota & lingkup.orang, (LINGKUP_DIVISI, divisi)
        )
    if id_ not in lingkup.divisi:
        raise LingkupDitolak
    anggota = frozenset(lingkup.divisi[id_])
    departemen = {
        dep: lingkup.departemen[dep] for dep, info in lingkup.info_departemen.items() if info["division_id"] == id_
    }
    return Sasaran(
        jenis, id_, lingkup.info_divisi[id_]["name"], anggota, anggota & lingkup.orang, (LINGKUP_DEPARTEMEN, departemen)
    )


# --------------------------------------------------------------------------
# Kueri
# --------------------------------------------------------------------------


class _Median(Aggregate):
    function = "PERCENTILE_CONT"
    template = "%(function)s(0.5) WITHIN GROUP (ORDER BY %(expressions)s)"
    output_field = FloatField()


class _AwalHariKantor(Func):
    """`date` -> `timestamptz` tengah malam di zona kantor."""

    function = "timezone"
    template = "%(function)s(%(expressions)s::timestamp)"
    output_field = DateTimeField()


def _tugas(workspace_id):
    zona = zona_kantor()
    mulai = Coalesce(_AwalHariKantor(Value(zona.key), F("start_date")), F("created_at"))
    lama = ExpressionWrapper(F("completed_at") - mulai, output_field=DurationField())
    return Issue.issue_objects.filter(workspace_id=workspace_id).annotate(
        **anotasi_ketepatan(),
        hari_siklus=Greatest(
            ExpressionWrapper(Extract(lama, "epoch") / Value(86400.0), output_field=FloatField()), Value(0.0)
        ),
    )


def _milik(qs, orang):
    """Tugas yang penanggung jawabnya salah satu `orang`, tiap tugas sekali."""
    return qs.filter(
        Exists(IssueAssignee.objects.filter(issue_id=OuterRef("pk"), assignee_id__in=orang, deleted_at__isnull=True))
    )


def _q_selesai(awal, akhir):
    return Q(state__group=_SELESAI, completed_at__gte=_ke_waktu(awal), completed_at__lt=_ke_waktu(akhir))


_BELUM_TUNTAS = ~Q(state__group__in=[_SELESAI, _BATAL])


def _agregat_tugas(jendela, jendela_lalu, hari_ini, dengan_siklus):
    """Agregat bersyarat untuk periode ini dan pembandingnya, dalam satu kueri.

    `distinct=True` karena pengelompokan per unit menggandakan tugas yang
    penanggung jawabnya lebih dari satu di unit yang sama.
    """

    def hitung(syarat):
        return Count("id", filter=syarat, distinct=True)

    bisa_terlambat = q_bisa_terlambat()
    agregat = {
        "overdue": hitung(Q(target_date__lt=batas_terlambat(hari_ini)) & _BELUM_TUNTAS & bisa_terlambat),
        # Sudah lewat tenggat di awal periode dan saat itu belum selesai.
        "overdue_lalu": hitung(
            Q(target_date__lt=batas_terlambat(jendela[0]))
            & ~Q(state__group=_BATAL)
            & (Q(completed_at__isnull=True) | Q(completed_at__gte=_ke_waktu(jendela[0])))
            & bisa_terlambat
        ),
        "open": hitung(_BELUM_TUNTAS),
    }
    for akhiran, (awal, akhir) in (("", jendela), ("_lalu", jendela_lalu)):
        selesai = _q_selesai(awal, akhir)
        bertenggat = selesai & Q(target_date__isnull=False)
        agregat[f"completed{akhiran}"] = hitung(selesai)
        agregat[f"on_time{akhiran}"] = hitung(bertenggat & q_tepat_waktu())
        agregat[f"late{akhiran}"] = hitung(bertenggat & q_terlambat())
        agregat[f"no_due_date{akhiran}"] = hitung(selesai & Q(target_date__isnull=True))
        if dengan_siklus:
            agregat[f"cycle_avg{akhiran}"] = Avg("hari_siklus", filter=selesai)
            agregat[f"cycle_median{akhiran}"] = _Median("hari_siklus", filter=selesai)
    return agregat


def _pisah(baris):
    """Satu baris agregat -> (angka periode ini, angka pembanding)."""
    kini = {k: v for k, v in baris.items() if not k.endswith("_lalu")}
    lalu = {k[: -len("_lalu")]: v for k, v in baris.items() if k.endswith("_lalu")}
    # Tidak ada "terbuka di awal periode": tidak dicatat, jadi tidak dibandingkan.
    lalu["open"] = None
    return kini, lalu


def _per_orang(model, kolom_orang, kolom_waktu, orang, workspace_id, jendela, jendela_lalu, agregat):
    """{orang_id: baris} untuk model yang tiap barisnya milik satu orang."""

    def dalam(rentang):
        return Q(**{f"{kolom_waktu}__gte": _ke_waktu(rentang[0]), f"{kolom_waktu}__lt": _ke_waktu(rentang[1])})

    baris = (
        model.objects.filter(workspace_id=workspace_id, **{f"{kolom_orang}__in": orang})
        .filter(dalam(jendela) | dalam(jendela_lalu))
        .values(kolom_orang)
        .annotate(**agregat(dalam(jendela), dalam(jendela_lalu)))
    )
    return {str(b[kolom_orang]): b for b in baris}


def _agregat_persetujuan(kini, lalu):
    return {
        "approved": Count("id", filter=kini & Q(status=STATUS_PERSETUJUAN_DISETUJUI)),
        "rejected": Count("id", filter=kini & Q(status=STATUS_PERSETUJUAN_DITOLAK)),
        "approved_lalu": Count("id", filter=lalu & Q(status=STATUS_PERSETUJUAN_DISETUJUI)),
        "rejected_lalu": Count("id", filter=lalu & Q(status=STATUS_PERSETUJUAN_DITOLAK)),
    }


def _agregat_kerja(kini, lalu):
    return {
        "worklog_minutes": Sum("duration", filter=kini),
        "worklog_minutes_lalu": Sum("duration", filter=lalu),
    }


def _jumlah(peta, orang):
    """Jumlahkan baris per orang untuk sekelompok orang (tiap baris milik satu orang)."""
    hasil = {}
    for o in orang:
        for k, v in peta.get(o, {}).items():
            if isinstance(v, int):
                hasil[k] = hasil.get(k, 0) + v
    return hasil


def _beban(qs):
    """Tugas terbuka menurut grup status dan prioritas, satu kueri."""
    per_status = dict.fromkeys(_GRUP_STATUS, 0)
    per_prioritas = dict.fromkeys(_PRIORITAS, 0)
    for b in qs.filter(_BELUM_TUNTAS).values("state__group", "priority").annotate(n=Count("id")):
        per_status[b["state__group"]] = per_status.get(b["state__group"], 0) + b["n"]
        prioritas = b["priority"] or "none"
        per_prioritas[prioritas] = per_prioritas.get(prioritas, 0) + b["n"]
    return {"by_state_group": per_status, "by_priority": per_prioritas}


def _tren(qs, jendela, hari_ini):
    """Selesai, tepat waktu, dan yang baru lewat tenggat per hari atau per pekan."""
    awal, akhir = jendela
    harian = (akhir - awal).days <= TREN_HARIAN_MAKS

    def ember(hari):
        if harian:
            return hari
        return max(awal, hari - timedelta(days=hari.weekday()))

    titik = {}
    hari = awal
    while hari < akhir:
        titik.setdefault(ember(hari), {"completed": 0, "on_time": 0, "became_overdue": 0})
        hari += timedelta(days=1)

    for b in (
        qs.filter(_q_selesai(awal, akhir))
        .values("tanggal_selesai")
        .annotate(
            completed=Count("id"),
            on_time=Count("id", filter=q_tepat_waktu()),
        )
    ):
        t = titik[ember(b["tanggal_selesai"])]
        t["completed"] += b["completed"]
        t["on_time"] += b["on_time"]

    # Tugas bertenggat T mulai terlambat pada hari T + tenggang + 1, yaitu hari
    # pertama `T < batas_terlambat(hari)`. T = tenggat efektif: tugas yang dicatat
    # sesudah Due date-nya tidak mungkin sudah terlambat sebelum ia ada.
    geser = hari_ini - batas_terlambat(hari_ini) + timedelta(days=1)
    terakhir = min(akhir, hari_ini + timedelta(days=1))
    for b in (
        qs.filter(tenggat_efektif__gte=awal - geser, tenggat_efektif__lt=terakhir - geser)
        .filter(~Q(state__group=_BATAL) & q_bisa_terlambat())
        .filter(Q(completed_at__isnull=True) | Q(tanggal_selesai__gte=F("tenggat_efektif") + geser))
        .values("tenggat_efektif")
        .annotate(n=Count("id"))
    ):
        titik[ember(b["tenggat_efektif"] + geser)]["became_overdue"] += b["n"]

    return {
        "bucket": "day" if harian else "week",
        "points": [{"start": k, **v} for k, v in sorted(titik.items())],
    }


# --------------------------------------------------------------------------
# Daftar tugas (lingkup satu orang)
# --------------------------------------------------------------------------


def _tugas_terlihat(penonton, qs):
    """Hanya tugas yang boleh dilihat `penonton`: project yang ia anggotai, tanpa privat orang lain.

    Satu-satunya tempat judul tugas keluar dari modul ini, jadi angka tidak ikut
    berubah: tugas privat tetap dihitung (keputusan P29 #8).
    """
    return saring_tugas_privat(
        qs.filter(
            project__project_projectmember__member=penonton,
            project__project_projectmember__is_active=True,
            project__project_projectmember__deleted_at__isnull=True,
        ),
        penonton,
    )


def _baris_tugas(issue):
    return {
        "id": str(issue.id),
        "project_id": str(issue.project_id),
        "project_identifier": issue.project.identifier,
        "sequence_id": issue.sequence_id,
        "name": issue.name,
        "priority": issue.priority,
        "target_date": issue.target_date,
        "completed_date": issue.tanggal_selesai,
        "timing": (
            ketepatan(issue.tanggal_selesai, issue.target_date, dibuat_dihitung(issue.created_at))
            if issue.tanggal_selesai
            else None
        ),
    }


def _daftar(penonton, qs, jendela, hari_ini):
    terlihat = _tugas_terlihat(penonton, qs).select_related("project")
    terlambat = terlihat.filter(
        Q(target_date__lt=batas_terlambat(hari_ini)) & _BELUM_TUNTAS & q_bisa_terlambat()
    ).order_by("target_date", "sequence_id")
    selesai = terlihat.filter(_q_selesai(*jendela)).order_by("-completed_at", "-sequence_id")
    return {
        "overdue": [_baris_tugas(t) for t in terlambat[:BATAS_DAFTAR]],
        "completed": [_baris_tugas(t) for t in selesai[:BATAS_DAFTAR]],
    }


# --------------------------------------------------------------------------
# Susunan akhir
# --------------------------------------------------------------------------


def _rincian_unit(sasaran, lingkup, semua_tugas, workspace_id, persetujuan, kerja, agregat):
    """Baris per departemen (lingkup divisi) atau per divisi (lingkup organisasi).

    Dikelompokkan lewat penempatan penanggung jawabnya. Satu tugas dihitung sekali
    per unit walau beberapa penanggung jawabnya di unit itu (`distinct`), dan
    orang di dua unit menyumbang ke keduanya. Waktu siklus tidak ikut: rata-rata
    atas baris yang tergandakan tidak jujur.
    """
    jenis, peta_unit = sasaran.rincian
    jabatan = "issue_assignee__assignee__jabatan_organisasi"
    if jenis == LINGKUP_DEPARTEMEN:
        info = lingkup.info_departemen
        unit = F(f"{jabatan}__departemen_id")
        di_unit = Q(**{f"{jabatan}__departemen_id__in": list(peta_unit)})
    else:
        info = lingkup.info_divisi
        unit = Coalesce(F(f"{jabatan}__departemen__divisi_id"), F(f"{jabatan}__divisi_id"))
        di_unit = Q(**{f"{jabatan}__departemen__divisi_id__in": list(peta_unit)}) | Q(
            **{f"{jabatan}__divisi_id__in": list(peta_unit), f"{jabatan}__tingkat__gte": TINGKAT_MANAGER}
        )
    per_unit = {
        str(b["unit"]): b
        for b in semua_tugas.filter(
            di_unit,
            issue_assignee__deleted_at__isnull=True,
            **{f"{jabatan}__workspace_id": workspace_id, f"{jabatan}__deleted_at__isnull": True},
        )
        .annotate(unit=unit)
        .values("unit")
        .annotate(**agregat)
    }
    baris = []
    for unit_id, orang in peta_unit.items():
        angka = _lengkapi(
            _pisah(per_unit.get(unit_id, {}))[0],
            _pisah(_jumlah(persetujuan, orang))[0],
            _pisah(_jumlah(kerja, orang))[0],
        )
        baris.append({**info[unit_id], "people": len(orang), "values": _nilai(angka)})
    return {"kind": jenis, "rows": sorted(baris, key=lambda b: b["name"].lower())}


def hitung_kinerja(user, workspace_id, jenis, id_=None, periode=PERIODE_BAWAAN, mulai=None, sampai=None, sekarang=None):
    """Seluruh isi halaman KPI untuk satu lingkup. Melempar `LingkupDitolak` / `PermintaanSalah`."""
    sekarang = sekarang or timezone.now()
    hari_ini = hari_ini_kantor(sekarang)
    jendela, jendela_lalu = rentang_periode(periode, hari_ini, mulai, sampai)
    lingkup = lingkup_untuk(user, workspace_id)
    sasaran = sasaran_dari(lingkup, user, jenis, id_)

    orang = list(sasaran.orang)
    semua_tugas = _tugas(workspace_id)
    milik = _milik(semua_tugas, orang)

    kini, lalu = _pisah(milik.aggregate(**_agregat_tugas(jendela, jendela_lalu, hari_ini, dengan_siklus=True)))
    persetujuan = _per_orang(
        PersetujuanPenugasan,
        "pemohon_id",
        "diputuskan_pada",
        orang,
        workspace_id,
        jendela,
        jendela_lalu,
        _agregat_persetujuan,
    )
    kerja = _per_orang(
        IssueWorkLog, "logged_by_id", "logged_at", orang, workspace_id, jendela, jendela_lalu, _agregat_kerja
    )
    lain_kini, lain_lalu = _pisah({**_jumlah(persetujuan, orang), **_jumlah(kerja, orang)})

    hasil = {
        "generated_at": sekarang,
        "scope": {"kind": sasaran.jenis, "id": sasaran.id, "name": sasaran.nama, "people": len(orang)},
        "period": {
            "key": periode,
            "start": jendela[0],
            # Inklusif untuk tampilan.
            "end": jendela[1] - timedelta(days=1),
            "previous_start": jendela_lalu[0],
            "previous_end": jendela_lalu[1] - timedelta(days=1),
        },
        "metrics": [m.bentuk_api() for m in METRIK],
        "values": _nilai(_lengkapi(kini, lain_kini)),
        "previous": _nilai(_lengkapi(lalu, lain_lalu) | {"open": None}),
        "workload": _beban(milik),
        "trend": _tren(milik, jendela, hari_ini),
        "people": None,
        "breakdown": None,
        "items": None,
    }

    if sasaran.jenis == LINGKUP_ORANG:
        hasil["items"] = _daftar(user, milik, jendela, hari_ini)
        return hasil

    # Satu kueri berkelompok per orang: tiap pasangan (tugas, penanggung jawab)
    # muncul sekali, jadi tiap orang mendapat kredit penuh.
    kolom = "issue_assignee__assignee_id"
    per_orang = {
        str(b[kolom]): b
        for b in semua_tugas.filter(issue_assignee__assignee_id__in=orang, issue_assignee__deleted_at__isnull=True)
        .values(kolom)
        .annotate(**_agregat_tugas(jendela, jendela_lalu, hari_ini, dengan_siklus=True))
    }
    hasil["people"] = [
        {
            **o,
            "values": _nilai(
                _lengkapi(
                    _pisah(per_orang.get(o["id"], {}))[0],
                    _pisah(persetujuan.get(o["id"], {}))[0],
                    _pisah(kerja.get(o["id"], {}))[0],
                )
            ),
        }
        for o in _orang_ringkas(sasaran.tabel)
    ]
    if sasaran.rincian:
        hasil["breakdown"] = _rincian_unit(
            sasaran,
            lingkup,
            semua_tugas,
            workspace_id,
            persetujuan,
            kerja,
            _agregat_tugas(jendela, jendela_lalu, hari_ini, dengan_siklus=False),
        )
    return hasil
