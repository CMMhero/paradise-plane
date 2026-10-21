# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji berkas .ics pengingat tenggat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Uji penyusun .ics pengingat tenggat, tanpa menyentuh database.

`bangun_ics` murni: ia hanya membaca atribut work item, jadi objek tiruan cukup
dan tidak perlu marka `django_db`.
"""

from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from plane.bgtasks.deadline_reminder_email import EPOCH_SEQUENCE, bangun_ics

pytestmark = pytest.mark.unit


def _issue(diubah: datetime, tenggat: date = date(2026, 8, 20)) -> SimpleNamespace:
    return SimpleNamespace(id=uuid4(), target_date=tenggat, updated_at=diubah)


def _ambil(ics: str, kunci: str) -> str:
    for baris in ics.split("\r\n"):
        if baris.startswith(f"{kunci}:"):
            return baris.split(":", 1)[1]
    raise AssertionError(f"{kunci} tidak ada di berkas .ics")


def test_sequence_naik_saat_work_item_disunting():
    lama = _issue(datetime(2026, 8, 11, 10, 0, tzinfo=dt_timezone.utc))
    baru = _issue(datetime(2026, 8, 12, 10, 0, tzinfo=dt_timezone.utc))

    urutan_lama = int(_ambil(bangun_ics(lama, "X", "d", ""), "SEQUENCE"))
    urutan_baru = int(_ambil(bangun_ics(baru, "X", "d", ""), "SEQUENCE"))

    assert urutan_baru > urutan_lama


def test_sequence_tetap_kalau_tidak_ada_perubahan():
    """Delapan pengingat untuk tenggat yang sama tidak boleh saling menimpa."""
    issue = _issue(datetime(2026, 8, 11, 10, 0, tzinfo=dt_timezone.utc))

    assert _ambil(bangun_ics(issue, "X", "d", ""), "SEQUENCE") == _ambil(
        bangun_ics(issue, "X", "d", ""), "SEQUENCE"
    )


def test_sequence_muat_di_integer_32_bit():
    """Alasan EPOCH_SEQUENCE ada. Detik Unix menembus batas ini pada 2038."""
    jauh = _issue(EPOCH_SEQUENCE + timedelta(days=365 * 20))

    assert int(_ambil(bangun_ics(jauh, "X", "d", ""), "SEQUENCE")) < 2**31 - 1


def test_sequence_tidak_pernah_negatif():
    """Work item yang belum tersimpan tidak punya updated_at."""
    belum_tersimpan = SimpleNamespace(
        id=uuid4(), target_date=date(2026, 8, 20), updated_at=None
    )

    assert int(_ambil(bangun_ics(belum_tersimpan, "X", "d", ""), "SEQUENCE")) == 0


def test_sequence_ada_di_dalam_vevent():
    """Di luar VEVENT, SEQUENCE tidak sah dan berkasnya bisa ditolak."""
    ics = bangun_ics(_issue(datetime(2026, 8, 11, tzinfo=dt_timezone.utc)), "X", "d", "")
    isi = ics.split("\r\n")

    assert isi.index("BEGIN:VEVENT") < next(
        i for i, b in enumerate(isi) if b.startswith("SEQUENCE:")
    ) < isi.index("END:VEVENT")
