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


def baca_bawaan() -> dict:
    """Bawaan yang berlaku sekarang. Baris rusak = pabrik, dicatat ke log, tidak meledak."""
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
    return {kunci: tersimpan.get(kunci, nilai) for kunci, nilai in PABRIK.items()}


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
