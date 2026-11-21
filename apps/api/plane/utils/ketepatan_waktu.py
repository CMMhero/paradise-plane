# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: satu aturan "selesai tepat waktu atau terlambat"
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu-satunya aturan tepat waktu / terlambat untuk tugas yang sudah selesai.

Dipakai laporan selesai (KEP-62), Dashboard Divisi, dan halaman KPI. Sebelumnya
tiap modul menulis `tanggal_selesai <= target_date` sendiri.

## Aturan

    tenggat efektif = max(Due date, hari kantor tugas dibuat)
    terlambat      = hari kantor selesai > tenggat efektif

Tugas tidak bisa terlambat untuk hari-hari sebelum ia dicatat. Kasusnya: staf
lupa membuat work item, mengerjakannya tepat waktu, lalu baru mencatatnya
sepekan kemudian dengan Due date yang asli (sudah lewat) dan langsung mengajukan
selesai. Dengan aturan lama tugas itu terlambat 7 hari, padahal yang terlambat
cuma pencatatannya. Dengan aturan ini, selesai di hari yang sama dengan dicatat =
tepat waktu. Selesai sesudah hari pencatatan tetap dibandingkan dengan tenggat
efektif, jadi pengajuan yang ditunda tetap terhitung terlambat.

"Selesai" = `completed_at`, yang untuk tugas lewat persetujuan = saat diajukan
(APPROVAL_FINISH_TIME bawaan, KEP-84), bukan saat disetujui. Persetujuan yang
lambat tidak membuat tugas terlambat.

Tugas biasa (dibuat sebelum Due date) tidak berubah: tenggat efektifnya tetap
Due date. Semua dihitung saat dibaca dari kolom yang tersimpan; tidak ada nilai
"terlambat" yang disimpan, jadi menghitung ulang selalu memberi hasil yang sama.

Tugas TERBUKA yang lewat tenggat ("terlambat sekarang") tidak memakai modul ini:
lihat `batas_terlambat` dan `q_bisa_terlambat`.

God Mode LATE_FROM_RECORDED_DAY mati = tenggat efektif kembali ke Due date saja.
Karena dihitung saat dibaca, laporan lama ikut berubah. Fungsi murni di bawah
tidak membaca aturan itu (tanpa database); pemanggil yang mengirim `dibuat_pada`
memakai `dibuat_dihitung` dulu, dan `anotasi_ketepatan` membacanya sendiri.
"""

# Python imports
from datetime import date, datetime

# Django imports
from django.db.models import Case, DateField, F, Q, Value, When
from django.db.models.functions import Greatest, TruncDate

# Module imports
from plane.utils import aturan
from plane.utils.aturan.area_tugas import LATE_FROM_RECORDED_DAY
from plane.utils.setelan_instance import zona_kantor

TEPAT_WAKTU = "on_time"
TERLAMBAT = "late"
TANPA_TENGGAT = "no_due_date"


def _hari_kantor(nilai: datetime | date | None) -> date | None:
    if nilai is None or not isinstance(nilai, datetime):
        return nilai
    return nilai.astimezone(zona_kantor()).date()


def dibuat_dihitung(dibuat_pada):
    """`dibuat_pada` kalau hari dicatat ikut menentukan tenggat (God Mode), selain itu None."""
    return dibuat_pada if aturan.get_bool(LATE_FROM_RECORDED_DAY) else None


def tenggat_efektif(target_date: date | None, dibuat_pada: datetime | date | None = None) -> date | None:
    """max(Due date, hari kantor dibuat). None kalau tanpa Due date."""
    if target_date is None:
        return None
    dibuat = _hari_kantor(dibuat_pada)
    return max(target_date, dibuat) if dibuat else target_date


def ketepatan(tanggal_selesai: date, target_date: date | None, dibuat_pada: datetime | date | None = None) -> str:
    """TEPAT_WAKTU / TERLAMBAT / TANPA_TENGGAT untuk satu tugas selesai.

    `tanggal_selesai` = hari kantor `completed_at`. `dibuat_pada` = `created_at`
    tugas (datetime) atau hari kantornya; tanpa itu aturannya Due date saja.
    """
    tenggat = tenggat_efektif(target_date, dibuat_pada)
    if tenggat is None:
        return TANPA_TENGGAT
    return TEPAT_WAKTU if tanggal_selesai <= tenggat else TERLAMBAT


def anotasi_ketepatan() -> dict:
    """Anotasi Issue yang dibutuhkan `q_tepat_waktu` / `q_terlambat`.

    `tanggal_selesai` = hari kantor `completed_at`; `tenggat_efektif` = aturan di
    atas dalam SQL, NULL kalau Due date kosong (GREATEST Postgres mengabaikan NULL,
    jadi dijaga dengan CASE).
    """
    zona = zona_kantor()
    if not aturan.get_bool(LATE_FROM_RECORDED_DAY):
        return {
            "tanggal_selesai": TruncDate("completed_at", tzinfo=zona),
            "tenggat_efektif": F("target_date"),
        }
    return {
        "tanggal_selesai": TruncDate("completed_at", tzinfo=zona),
        "tenggat_efektif": Case(
            When(target_date__isnull=True, then=Value(None)),
            default=Greatest(F("target_date"), TruncDate("created_at", tzinfo=zona)),
            output_field=DateField(),
        ),
    }


def q_tepat_waktu() -> Q:
    """Selesai pada atau sebelum tenggat efektif. Butuh `anotasi_ketepatan()`."""
    return Q(target_date__isnull=False, tanggal_selesai__lte=F("tenggat_efektif"))


def q_terlambat() -> Q:
    """Selesai sesudah tenggat efektif. Butuh `anotasi_ketepatan()`."""
    return Q(target_date__isnull=False, tanggal_selesai__gt=F("tenggat_efektif"))
