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
ditimpa, dan tidak dikosongkan lagi saat tugas mundur. Pasangan yang akan
melanggar "Start date cannot exceed target date" (validasi semua serializer)
dilewati, bukan dipotong, supaya tanggal yang tersimpan selalu benar.

"Hari ini" dihitung di zona waktu project, bukan UTC: tugas yang dimulai pukul
06.00 WIB jangan tercatat kemarin.
"""

from datetime import date, datetime

import pytz
from django.utils import timezone


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


def selesai_otomatis(start_date: date | None, target_date: date | None, hari_selesai: date) -> date | None:
    """Tanggal selesai (target_date) yang harus diisi, atau None.

    Dilewati kalau tugas selesai SEBELUM tanggal mulai yang direncanakan, dengan
    alasan yang sama: pasangan mulai > selesai tidak boleh lahir.
    """
    if target_date is not None:
        return None
    if start_date is not None and hari_selesai < start_date:
        return None
    return hari_selesai
