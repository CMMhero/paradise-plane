# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tanggal mulai & selesai otomatis (KEP-41)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Aturan murni untuk tanggal mulai/selesai yang diisi sistem.

Keputusan user 2026-10-30 (KEP-41):

* Tugas masuk grup `started` -> `start_date` diisi hari ini.
* Tugas masuk grup `completed` (dan disetujui atasan bila perlu) -> `target_date`
  diisi tanggal selesainya.

Keduanya HANYA mengisi yang kosong; tanggal yang direncanakan orang tidak pernah
ditimpa, dan tidak dikosongkan lagi saat tugas mundur. Pengecualian yang dipilih
Super Admin: `DUE_DATE_ON_EARLY_DONE` memajukan Due date ke hari selesai untuk
tugas yang selesai lebih awal. Ketiga aturan diatur di God Mode > Features
(`aturan_tanggal`), bawaannya sama dengan perilaku sebelum setelan ada. Pasangan yang akan
melanggar "Start date cannot exceed target date" (validasi semua serializer)
dilewati, bukan dipotong, supaya tanggal yang tersimpan selalu benar.

"Hari ini" dihitung di zona waktu project, bukan UTC: tugas yang dimulai pukul
06.00 WIB jangan tercatat kemarin.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import pytz
from django.utils import timezone

from plane.utils.saklar_instance import (
    AUTO_DUE_DATE_ON_DONE,
    AUTO_START_DATE_ON_START,
    DUE_DATE_MAJU_KE_SELESAI,
    DUE_DATE_ON_EARLY_DONE,
    OVERDUE_GRACE_DAYS,
    saklar_aktif,
    setelan_angka,
)


def tanggal_lokal(saat: datetime | None, nama_zona: str | None) -> date:
    """Tanggal kalender `saat` (default: sekarang) di zona `nama_zona`.

    pytz, bukan zoneinfo: image API berbasis Alpine dan pytz membawa data zonanya
    sendiri, jadi "Asia/Jakarta" tidak diam-diam jatuh ke UTC. Pilihan zona
    project juga berasal dari `pytz.common_timezones`.
    """
    saat = saat or timezone.now()
    try:
        zona = pytz.timezone(nama_zona or "UTC")
    except pytz.UnknownTimeZoneError:
        zona = pytz.UTC
    return saat.astimezone(zona).date()


def mulai_otomatis(start_date: date | None, target_date: date | None, hari_ini: date) -> date | None:
    """Tanggal mulai yang harus diisi, atau None kalau tidak ada yang diisi.

    Tugas yang tenggatnya sudah lewat dilewati: mengisi hari ini membuat mulai
    jatuh SESUDAH tenggat, pasangan yang ditolak serializer pada suntingan berikutnya.
    """
    if start_date is not None:
        return None
    if target_date is not None and hari_ini > target_date:
        return None
    return hari_ini


def selesai_otomatis(
    start_date: date | None,
    target_date: date | None,
    hari_selesai: date,
    *,
    isi_kosong: bool = True,
    majukan_rencana: bool = False,
) -> date | None:
    """Tanggal selesai (target_date) yang harus diisi, atau None.

    * Due date kosong -> diisi hari selesai, kalau `isi_kosong` (God Mode
      `AUTO_DUE_DATE_ON_DONE`).
    * Due date ada dan tugas selesai LEBIH AWAL -> dimajukan ke hari selesai,
      hanya kalau `majukan_rencana` (God Mode `DUE_DATE_ON_EARLY_DONE`).
    * Selesai pas atau TERLAMBAT -> Due date tidak pernah disentuh: menggesernya
      ke hari selesai mengubah tugas terlambat jadi "tepat waktu" di laporan.

    Dilewati kalau tugas selesai SEBELUM tanggal mulai yang direncanakan, dengan
    alasan yang sama: pasangan mulai > selesai tidak boleh lahir.
    """
    if start_date is not None and hari_selesai < start_date:
        return None
    if target_date is None:
        return hari_selesai if isi_kosong else None
    if majukan_rencana and hari_selesai < target_date:
        return hari_selesai
    return None


def batas_terlambat(hari_ini: date) -> date:
    """Tugas belum tuntas dengan `target_date` < batas ini dihitung terlambat.

    Tanpa tenggang (bawaan 0) batasnya hari ini: sehari sesudah Due date sudah
    terlambat. `OVERDUE_GRACE_DAYS` menggeser batas itu mundur sekian hari.
    """
    return hari_ini - timedelta(days=setelan_angka(OVERDUE_GRACE_DAYS))


@dataclass(frozen=True)
class AturanTanggal:
    """Setelan tanggal otomatis yang berlaku, dari God Mode > Features."""

    isi_mulai: bool
    isi_selesai: bool
    majukan_rencana: bool


def aturan_tanggal() -> AturanTanggal:
    """Dibaca ulang tiap dipanggil, jadi perubahan di God Mode berlaku seketika."""
    return AturanTanggal(
        isi_mulai=saklar_aktif(AUTO_START_DATE_ON_START),
        isi_selesai=saklar_aktif(AUTO_DUE_DATE_ON_DONE),
        majukan_rencana=setelan_angka(DUE_DATE_ON_EARLY_DONE) == DUE_DATE_MAJU_KE_SELESAI,
    )
