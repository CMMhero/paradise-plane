# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan project baru di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Setelan yang diterima project BARU, diatur Super Admin di God Mode.

Pola sama dengan bawaan member (KEP-44): satu baris `InstanceConfiguration`
JSON, dibaca ulang tiap dipakai, diubah lewat endpoint sendiri yang memeriksa
isinya. Berlaku dua lapis:

- web mengisi formulir "Create project" dengan nilai ini (lewat
  `paradise_project_defaults` di konfigurasi instance), jadi pembuatnya melihat
  dan masih bisa mengubah visibilitas;
- server mengisi kolom yang TIDAK dikirim pemanggil (API v1, skrip, klien lama).

Fitur project (modules, views, pages, intake) tidak diatur di sini: semuanya
menyala dan diatur lewat modul God Mode (KEP-53).
"""

import json
import logging

import pytz

logger = logging.getLogger("plane.api")

KUNCI = "PARADISE_BAWAAN_PROJECT"

# Project.network: 0 = Secret (private), 2 = Public.
VISIBILITAS_SAH = frozenset({0, 2})
# Project.archive_in / close_in: 0 = mati, 1..12 bulan (validator model).
BULAN_MAKS = 12

PABRIK = {
    "network": 2,
    "timezone": "UTC",
    "archive_in": 0,
    "close_in": 0,
    "guest_view_all_features": False,
}


# --- Plafon arsip otomatis (KEP-83) ---
#
# AUTO_ARCHIVE_DONE_DAYS (God Mode, hari) adalah PLAFON untuk `archive_in`
# project (bulan): project boleh mengarsipkan lebih cepat, tidak lebih lambat.
# Satu bulan dihitung 30 hari, sama dengan task harian (issue_automation_task)
# dan dengan web (pilihan boleh bila bulan * 30 <= plafon). Plafon 0 = aturan
# instance mati, jadi tidak ada plafon.
HARI_SEBULAN = 30


def bulan_arsip_maks():
    """Bulan `archive_in` terbesar yang masih di bawah plafon, atau None tanpa plafon."""
    from plane.utils.saklar_instance import AUTO_ARCHIVE_DONE_DAYS, setelan_angka  # noqa: PLC0415

    plafon = setelan_angka(AUTO_ARCHIVE_DONE_DAYS)
    if not plafon:
        return None
    return min(plafon // HARI_SEBULAN, BULAN_MAKS)


def galat_archive_in(bulan):
    """Pesan galat kalau `archive_in` melewati plafon instance, atau None kalau boleh.

    0 (arsip project mati) selalu boleh: aturan instance tetap berjalan.
    """
    if not isinstance(bulan, int) or isinstance(bulan, bool) or bulan <= 0:
        return None
    maks = bulan_arsip_maks()
    if maks is None or bulan <= maks:
        return None
    from plane.utils.saklar_instance import AUTO_ARCHIVE_DONE_DAYS, setelan_angka  # noqa: PLC0415

    plafon = setelan_angka(AUTO_ARCHIVE_DONE_DAYS)
    if maks == 0:
        return (
            f"Auto-archive cannot be later than the instance limit of {plafon} days. "
            "Turn it off here; the instance rule already archives done work items."
        )
    return (
        f"Auto-archive cannot be later than the instance limit of {plafon} days. "
        f"Pick {maks} {'month' if maks == 1 else 'months'} or less."
    )


def galat_archive_in_project(bulan, project=None):
    """`galat_archive_in` untuk create/update project.

    Project lama yang SUDAH memegang nilai di atas plafon tidak dirusak: mengirim
    ulang nilai yang sama (formulir yang menyimpan semua kolom) tetap boleh. Task
    harian mengarsipkan pada mana pun yang lebih dulu, jadi plafonnya tetap berlaku.
    """
    if project is not None and bulan == project.archive_in:
        return None
    return galat_archive_in(bulan)


def baca_bawaan() -> dict:
    """Bawaan yang berlaku sekarang. Baris rusak = pabrik, dicatat ke log, tidak meledak.

    `archive_in` yang tersimpan di atas plafon arsip instance (plafonnya diturunkan
    sesudah bawaan disimpan) dijepit ke plafon itu, supaya project baru tidak
    ditolak karena bawaannya sendiri (KEP-83).
    """
    from plane.license.models import InstanceConfiguration

    mentah = InstanceConfiguration.objects.filter(key=KUNCI).values_list("value", flat=True).first()
    tersimpan = {}
    if mentah:
        try:
            tersimpan = json.loads(mentah)
        except (TypeError, ValueError):
            logger.warning("%s bukan JSON sah; memakai bawaan pabrik", KUNCI)
    if not isinstance(tersimpan, dict):
        tersimpan = {}
    hasil = {kunci: tersimpan.get(kunci, nilai) for kunci, nilai in PABRIK.items()}
    if galat_archive_in(hasil["archive_in"]):
        hasil["archive_in"] = bulan_arsip_maks()
    return hasil


def _bulan(nama, nilai):
    if isinstance(nilai, bool) or not isinstance(nilai, int) or not 0 <= nilai <= BULAN_MAKS:
        return f"{nama} must be a whole number of months from 0 to {BULAN_MAKS}."
    return None


def periksa_perubahan(data) -> tuple[dict, str | None]:
    """Cek PATCH parsial. Kembalikan (bawaan_lengkap_sesudahnya, galat)."""
    if not isinstance(data, dict) or not data:
        return {}, "No changes."
    asing = set(data) - set(PABRIK)
    if asing:
        return {}, f"Unknown fields: {', '.join(sorted(asing))}."
    if "network" in data and (isinstance(data["network"], bool) or data["network"] not in VISIBILITAS_SAH):
        return {}, "Visibility must be Public (2) or Private (0)."
    if "timezone" in data and data["timezone"] not in pytz.all_timezones_set:
        return {}, "Invalid timezone."
    for nama in ("archive_in", "close_in"):
        if nama in data:
            galat = _bulan(nama, data[nama])
            if galat:
                return {}, galat
    if "archive_in" in data:
        galat = galat_archive_in(data["archive_in"])
        if galat:
            return {}, galat
    if "guest_view_all_features" in data and not isinstance(data["guest_view_all_features"], bool):
        return {}, "guest_view_all_features must be true or false."
    return {**baca_bawaan(), **data}, None


def simpan_bawaan(bawaan: dict) -> None:
    from plane.license.models import InstanceConfiguration

    InstanceConfiguration.objects.update_or_create(
        key=KUNCI,
        defaults={"value": json.dumps(bawaan), "category": "PARADISE", "is_encrypted": False},
    )


def lengkapi_data_project(data) -> dict:
    """Salinan `data` permintaan pembuatan project, kolom yang tak dikirim diisi bawaan."""
    hasil = dict(data)
    for kunci, nilai in baca_bawaan().items():
        hasil.setdefault(kunci, nilai)
    return hasil
