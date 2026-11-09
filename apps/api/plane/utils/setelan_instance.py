# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: registri setelan instance (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Registri SEMUA setelan instance Paradise: jenis, bawaan, rentang, dan pembacanya.

Saklar ("0"/"1") dan angka tetap tinggal di `saklar_instance.py` (SAKLAR_BAWAAN,
SETELAN_ANGKA, SETELAN_PILIHAN). Berkas ini menambah jenis berbentuk teks (jam,
daftar hari, hari kerja, zona waktu), lalu menyatukan ketiganya menjadi satu
registri yang dibaca endpoint God Mode `/api/instances/settings/`.

Jenis (`kind` di API):

    toggle       "0" / "1"
    number       bilangan bulat, min..max
    choice       bilangan bulat, salah satu dari `choices`
    time         "HH:MM" 24 jam, dibaca dalam zona OFFICE_TIMEZONE
    day_list     "a,b,c" bilangan bulat -30..30, unik, terurut, 1..12 butir
    weekday_set  "1,2,3" hari ISO 1 (Senin) .. 7 (Minggu), unik, terurut, minimal 1
    timezone     nama di `pytz.all_timezones_set` (jebakan L2: bukan common_timezones)

Urutan baca sama dengan saklar lama: baris database -> benih env -> bawaan kode.
Kunci teks di sini semuanya baru (KEP-83), jadi TIDAK membaca env sama sekali
(KEP-48: env baru = MAJOR). Nilai rusak yang terlanjur tersimpan jatuh ke bawaan,
tidak pernah melempar galat ke pemanggil (task Celery tidak boleh mati karenanya).

Pesan galat validasi berbahasa Inggris: God Mode English only (KEP-46).
"""

import re
from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytz
from django.conf import settings

from plane.utils.saklar_instance import (
    APPROVAL_FINISH_TIME,
    APPROVAL_PENDING_NOT_LATE,
    APPROVAL_REJECT_REASON_REQUIRED,
    APPROVAL_REQUIRED_BELOW_LEVEL,
    ASSIGN_DOWN_ONLY,
    DUE_DATE_CHANGE_RULE,
    HIERARKI_GERBANG_TUGAS,
    IZIN_ISI,
    IZIN_STRUKTUR,
    SAKLAR_BAWAAN,
    SESSION_DAYS,
    SETELAN_ANGKA,
    SETELAN_PILIHAN,
    TASK_DELETE_RULE,
    env_benih,
)

JENIS_TOGGLE = "toggle"
JENIS_ANGKA = "number"
JENIS_PILIHAN = "choice"
JENIS_JAM = "time"
JENIS_DAFTAR_HARI = "day_list"
JENIS_HARI_KERJA = "weekday_set"
JENIS_ZONA = "timezone"

# --- Kunci teks baru (KEP-83). Bawaan = jadwal yang dulu tertulis di celery.py. ---
# Zona waktu kantor. Semua jam di bawah dimasukkan dalam zona ini.
OFFICE_TIMEZONE = "OFFICE_TIMEZONE"
# Titik pengingat tenggat, dalam hari relatif terhadap Due date (negatif = sebelum).
# Email: dulu `deadline_reminder.py`; inbox: dulu `TITIK_INBOX` di deadline_reminder_task.py.
DEADLINE_REMINDER_EMAIL_DAYS = "DEADLINE_REMINDER_EMAIL_DAYS"
DEADLINE_REMINDER_INBOX_DAYS = "DEADLINE_REMINDER_INBOX_DAYS"
# Jam kirim pengingat tenggat. Dulu cron 01:00 UTC = 08:00 WIB.
DEADLINE_REMINDER_TIME = "DEADLINE_REMINDER_TIME"
# Ringkasan harian pagi/sore dan ringkasan direktur, plus hari kirimnya.
DIGEST_MORNING_TIME = "DIGEST_MORNING_TIME"
DIGEST_EVENING_TIME = "DIGEST_EVENING_TIME"
DIRECTOR_DIGEST_TIME = "DIRECTOR_DIGEST_TIME"
DIGEST_WEEKDAYS = "DIGEST_WEEKDAYS"

ZONA_KANTOR_BAWAAN = "Asia/Jakarta"

SETELAN_TEKS = {
    OFFICE_TIMEZONE: (JENIS_ZONA, ZONA_KANTOR_BAWAAN),
    DEADLINE_REMINDER_EMAIL_DAYS: (JENIS_DAFTAR_HARI, "-7,-5,-3,-1,0,3,5,7"),
    DEADLINE_REMINDER_INBOX_DAYS: (JENIS_DAFTAR_HARI, "-1,0,1,3,7"),
    DEADLINE_REMINDER_TIME: (JENIS_JAM, "08:00"),
    DIGEST_MORNING_TIME: (JENIS_JAM, "08:30"),
    DIGEST_EVENING_TIME: (JENIS_JAM, "17:30"),
    DIRECTOR_DIGEST_TIME: (JENIS_JAM, "08:30"),
    DIGEST_WEEKDAYS: (JENIS_HARI_KERJA, "1,2,3,4,5"),
}

# Mengubah salah satunya mengubah siapa boleh apa (atau berapa lama orang tetap
# masuk). Lewat /api/instances/settings/ wajib membawa FRASA_KONFIRMASI dan
# tercatat di jejak audit; PATCH /api/instances/configurations/ menolaknya.
SENSITIF = frozenset(
    {
        SESSION_DAYS,
        APPROVAL_REQUIRED_BELOW_LEVEL,
        APPROVAL_REJECT_REASON_REQUIRED,
        TASK_DELETE_RULE,
        DUE_DATE_CHANGE_RULE,
        ASSIGN_DOWN_ONLY,
        HIERARKI_GERBANG_TUGAS,
        APPROVAL_FINISH_TIME,
        APPROVAL_PENDING_NOT_LATE,
        *IZIN_ISI,
        *IZIN_STRUKTUR,
    }
)
FRASA_KONFIRMASI = "CHANGE RULES"

HARI_RELATIF_MIN, HARI_RELATIF_MAKS = -30, 30
DAFTAR_HARI_MAKS = 12
_POLA_JAM = re.compile(r"^(\d{1,2}):(\d{2})$")


class NilaiTidakSah(ValueError):
    """Nilai setelan ditolak. `str(e)` = pesan untuk God Mode (bahasa Inggris)."""


def semua_kunci() -> list:
    """Semua kunci registri, urutan tetap: saklar, angka/pilihan, teks."""
    return [*SAKLAR_BAWAAN, *SETELAN_ANGKA, *SETELAN_TEKS]


def dikenal(kunci: str) -> bool:
    return kunci in SAKLAR_BAWAAN or kunci in SETELAN_ANGKA or kunci in SETELAN_TEKS


def jenis(kunci: str) -> str:
    """Jenis setelan `kunci`. Kunci asing: KeyError."""
    if kunci in SAKLAR_BAWAAN:
        return JENIS_TOGGLE
    if kunci in SETELAN_ANGKA:
        return JENIS_PILIHAN if kunci in SETELAN_PILIHAN else JENIS_ANGKA
    return SETELAN_TEKS[kunci][0]


def bawaan(kunci: str) -> str:
    """Bawaan kode `kunci` dalam bentuk kanonik (string, seperti yang disimpan)."""
    if kunci in SAKLAR_BAWAAN:
        return SAKLAR_BAWAAN[kunci]
    if kunci in SETELAN_ANGKA:
        return str(SETELAN_ANGKA[kunci][0])
    return SETELAN_TEKS[kunci][1]


# --------------------------------------------------------------------------
# Validator: nilai masuk -> bentuk kanonik, atau NilaiTidakSah
# --------------------------------------------------------------------------


def _bulat(nilai) -> int:
    if isinstance(nilai, bool):
        raise ValueError
    if isinstance(nilai, int):
        return nilai
    teks = str(nilai).strip()
    if not re.fullmatch(r"-?\d+", teks):
        raise ValueError
    return int(teks)


def _daftar_bulat(nilai) -> list:
    """`"1, 2,3"` atau `[1, 2, 3]` -> [1, 2, 3]. Butir yang bukan bilangan bulat: ValueError."""
    if isinstance(nilai, (list, tuple)):
        butir = list(nilai)
    else:
        teks = str(nilai).strip()
        butir = teks.split(",") if teks else []
    return [_bulat(b) for b in butir]


def _toggle(nilai) -> str:
    if nilai is True or nilai == 1:
        return "1"
    if nilai is False or nilai == 0:
        return "0"
    teks = str(nilai).strip()
    if teks in ("0", "1"):
        return teks
    raise NilaiTidakSah("Must be 0 or 1.")


def _angka(kunci, nilai) -> str:
    _, minimum, maksimum = SETELAN_ANGKA[kunci]
    try:
        angka = _bulat(nilai)
    except (TypeError, ValueError):
        raise NilaiTidakSah("Must be a whole number.") from None
    if kunci in SETELAN_PILIHAN:
        if angka not in SETELAN_PILIHAN[kunci]:
            pilihan = ", ".join(map(str, SETELAN_PILIHAN[kunci]))
            raise NilaiTidakSah(f"Must be one of: {pilihan}.")
    elif not minimum <= angka <= maksimum:
        raise NilaiTidakSah(f"Must be between {minimum} and {maksimum}.")
    return str(angka)


# Beat mendetakkan penjadwal kantor tiap 5 menit (plane/celery.py, `jadwal-kantor`),
# jadi jam slot harus kelipatan 5 menit. Batas akhir 23:50, bukan 23:55: detak
# 23:55 bisa terlambat beberapa detik melewati tengah malam, dan slot yang belum
# jatuh tempo saat tanggal kantor berganti tidak pernah dikirim hari itu.
LANGKAH_MENIT_JAM = 5
JAM_TERAKHIR = (23, 50)
_PESAN_JAM = "Must be a 24-hour time like 08:30, in 5-minute steps, no later than 23:50."


def _jam(nilai) -> str:
    cocok = _POLA_JAM.match(str(nilai).strip()) if isinstance(nilai, str) else None
    if not cocok:
        raise NilaiTidakSah(_PESAN_JAM)
    jam, menit = int(cocok.group(1)), int(cocok.group(2))
    if jam > 23 or menit > 59 or menit % LANGKAH_MENIT_JAM or (jam, menit) > JAM_TERAKHIR:
        raise NilaiTidakSah(_PESAN_JAM)
    return f"{jam:02d}:{menit:02d}"


def _daftar_hari(nilai) -> str:
    try:
        hari = _daftar_bulat(nilai)
    except (TypeError, ValueError):
        raise NilaiTidakSah("Must be a comma-separated list of whole numbers.") from None
    if not 1 <= len(hari) <= DAFTAR_HARI_MAKS:
        raise NilaiTidakSah(f"Pick between 1 and {DAFTAR_HARI_MAKS} days.")
    if len(set(hari)) != len(hari):
        raise NilaiTidakSah("Each day may appear only once.")
    if any(not HARI_RELATIF_MIN <= h <= HARI_RELATIF_MAKS for h in hari):
        raise NilaiTidakSah(f"Each day must be between {HARI_RELATIF_MIN} and {HARI_RELATIF_MAKS}.")
    return ",".join(map(str, sorted(hari)))


def _hari_kerja(nilai) -> str:
    try:
        hari = _daftar_bulat(nilai)
    except (TypeError, ValueError):
        raise NilaiTidakSah("Must be a comma-separated list of weekdays 1-7.") from None
    if not hari:
        raise NilaiTidakSah("Pick at least one weekday.")
    if len(set(hari)) != len(hari):
        raise NilaiTidakSah("Each weekday may appear only once.")
    if any(not 1 <= h <= 7 for h in hari):
        raise NilaiTidakSah("Weekdays are 1 (Monday) to 7 (Sunday).")
    return ",".join(map(str, sorted(hari)))


def _zona(nilai) -> str:
    teks = str(nilai).strip() if isinstance(nilai, str) else ""
    if teks not in pytz.all_timezones_set:
        raise NilaiTidakSah("Unknown time zone.")
    return teks


def normalkan(kunci: str, nilai) -> str:
    """Validasi `nilai` untuk `kunci`, kembalikan bentuk kanonik yang disimpan.

    Kunci asing atau nilai yang tak sah: NilaiTidakSah.
    """
    if not dikenal(kunci):
        raise NilaiTidakSah("Unknown setting.")
    if nilai is None:
        raise NilaiTidakSah("A value is required.")
    j = jenis(kunci)
    if j == JENIS_TOGGLE:
        return _toggle(nilai)
    if j in (JENIS_ANGKA, JENIS_PILIHAN):
        return _angka(kunci, nilai)
    return {
        JENIS_JAM: _jam,
        JENIS_DAFTAR_HARI: _daftar_hari,
        JENIS_HARI_KERJA: _hari_kerja,
        JENIS_ZONA: _zona,
    }[j](nilai)


def nilai_sah(kunci: str, nilai) -> bool:
    try:
        normalkan(kunci, nilai)
    except NilaiTidakSah:
        return False
    return True


# --------------------------------------------------------------------------
# Pembaca
# --------------------------------------------------------------------------


def nilai_tersimpan(kunci_list) -> dict:
    """{kunci: nilai mentah} dari database, satu kueri. Kosong kalau SKIP_ENV_VAR mati."""
    if not settings.SKIP_ENV_VAR:
        return {}
    from plane.license.models import InstanceConfiguration

    return dict(InstanceConfiguration.objects.filter(key__in=list(kunci_list)).values_list("key", "value"))


def efektif(kunci: str, tersimpan: dict | None = None) -> str:
    """Nilai yang BERLAKU untuk `kunci` dalam bentuk kanonik, persis seperti dibaca aplikasi.

    `tersimpan` = hasil `nilai_tersimpan` yang sudah diambil pemanggil (registri penuh
    dalam satu kueri). None = ambil sendiri.
    """
    if tersimpan is None:
        tersimpan = nilai_tersimpan([kunci])
    mentah = tersimpan.get(kunci)
    j = jenis(kunci)
    if j == JENIS_TOGGLE:
        if mentah is None:
            mentah = env_benih(kunci, SAKLAR_BAWAAN[kunci])
        return "1" if str(mentah).strip() == "1" else "0"
    if j in (JENIS_ANGKA, JENIS_PILIHAN):
        nilai_bawaan, minimum, maksimum = SETELAN_ANGKA[kunci]
        if mentah is None:
            mentah = env_benih(kunci)
        try:
            angka = _bulat(mentah) if mentah not in (None, "") else nilai_bawaan
        except (TypeError, ValueError):
            angka = nilai_bawaan
        return str(max(minimum, min(angka, maksimum)))
    # Kunci teks: tanpa env. Nilai rusak jatuh ke bawaan.
    if mentah is None:
        return SETELAN_TEKS[kunci][1]
    try:
        return normalkan(kunci, mentah)
    except NilaiTidakSah:
        return SETELAN_TEKS[kunci][1]


def setelan_teks(kunci: str) -> str:
    """Nilai kanonik kunci teks (`SETELAN_TEKS`). Kunci asing: KeyError."""
    if kunci not in SETELAN_TEKS:
        raise KeyError(kunci)
    return efektif(kunci)


def setelan_jam(kunci: str) -> time:
    """Jam (`time`, tanpa zona) untuk kunci berjenis time. Tafsirkan dalam `zona_kantor()`."""
    if jenis(kunci) != JENIS_JAM:
        raise KeyError(kunci)
    jam, menit = efektif(kunci).split(":")
    return time(int(jam), int(menit))


def setelan_hari(kunci: str) -> tuple:
    """Daftar hari relatif terurut untuk kunci berjenis day_list, mis. (-7, -5, ..., 7)."""
    if jenis(kunci) != JENIS_DAFTAR_HARI:
        raise KeyError(kunci)
    return tuple(int(h) for h in efektif(kunci).split(","))


def setelan_hari_kerja(kunci: str) -> frozenset:
    """Hari ISO (1 = Senin .. 7 = Minggu) untuk kunci berjenis weekday_set."""
    if jenis(kunci) != JENIS_HARI_KERJA:
        raise KeyError(kunci)
    return frozenset(int(h) for h in efektif(kunci).split(","))


def zona_kantor() -> ZoneInfo:
    """ZoneInfo dari OFFICE_TIMEZONE. Nama yang dikenal pytz tapi tidak oleh tzdata
    sistem jatuh ke Asia/Jakarta, bukan melempar galat."""
    try:
        return ZoneInfo(efektif(OFFICE_TIMEZONE))
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(ZONA_KANTOR_BAWAAN)


def hari_ini_kantor(saat=None):
    """Tanggal kalender `saat` (default: sekarang) di zona kantor.

    Server berjalan di UTC, jadi `timezone.localdate()` ketinggalan satu hari
    antara 00.00 dan 07.00 WIB. Semua hitungan terlambat/tepat waktu memakai
    ini, bukan tanggal UTC.
    """
    saat = saat or datetime.now(tz=ZoneInfo("UTC"))
    return saat.astimezone(zona_kantor()).date()


# --------------------------------------------------------------------------
# Bentuk API
# --------------------------------------------------------------------------


def deskripsi(kunci: str, tersimpan: dict) -> dict:
    """Satu butir `settings` di GET /api/instances/settings/."""
    j = jenis(kunci)
    angka = j in (JENIS_ANGKA, JENIS_PILIHAN)
    return {
        "key": kunci,
        "kind": j,
        "default": bawaan(kunci),
        "value": efektif(kunci, tersimpan),
        "min": SETELAN_ANGKA[kunci][1] if angka else None,
        "max": SETELAN_ANGKA[kunci][2] if angka else None,
        "choices": list(SETELAN_PILIHAN[kunci]) if j == JENIS_PILIHAN else None,
        "sensitive": kunci in SENSITIF,
    }


def daftar_setelan() -> list:
    """Seluruh registri dalam satu kueri, urutan `semua_kunci()`."""
    kunci_list = semua_kunci()
    tersimpan = nilai_tersimpan(kunci_list)
    return [deskripsi(k, tersimpan) for k in kunci_list]
