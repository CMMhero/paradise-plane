# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji penyusun acara Google Calendar
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Uji penyusun badan acara, tanpa menyentuh API Google maupun database.

`_badan_acara` murni: ia hanya mengubah argumen jadi dict. Itu membuatnya bisa
diuji langsung, dan di situlah dua jebakan yang paling mudah salah berada.
"""

from datetime import date

import pytest

from plane.utils.google_calendar import _badan_acara

pytestmark = pytest.mark.unit


def _acara(tenggat=date(2026, 8, 20), judul="IT-42 Perpanjang sertifikat"):
    return _badan_acara(judul, tenggat, "Project IT.", "https://contoh/issue/1")


def test_tanggal_akhir_eksklusif_sehari_setelah_tenggat():
    """Jebakan utama. `end.date` pada acara sepanjang hari bersifat EKSKLUSIF.

    Diisi tanggal yang sama dengan `start`, acaranya tidak muncul sama sekali di
    kalender, dan tidak ada pesan galat apa pun yang menjelaskan kenapa.
    """
    a = _acara(tenggat=date(2026, 8, 20))

    assert a["start"]["date"] == "2026-08-20"
    assert a["end"]["date"] == "2026-08-21"


def test_akhir_bulan_menyeberang_dengan_benar():
    """Penambahan hari lewat timedelta, bukan lewat menaikkan angka tanggal."""
    a = _acara(tenggat=date(2026, 8, 31))

    assert a["end"]["date"] == "2026-09-01"


def test_tahun_kabisat():
    a = _acara(tenggat=date(2028, 2, 29))

    assert a["end"]["date"] == "2028-03-01"


def test_alarm_menyamai_lampiran_ics():
    """Empat alarm yang sama dengan ALARM_HARI di jalur .ics.

    Kalau keduanya berbeda, orang yang memakai dua jalur sekaligus akan
    diingatkan pada waktu yang berlainan untuk tenggat yang sama, dan itu
    membuat keduanya terasa tidak bisa dipercaya.
    """
    a = _acara()
    menit = [o["minutes"] for o in a["reminders"]["overrides"]]

    assert menit == [7 * 1440, 5 * 1440, 3 * 1440, 1 * 1440]
    assert a["reminders"]["useDefault"] is False


def test_acara_tidak_memblokir_waktu():
    """Tenggat bukan rapat. Menandainya sibuk akan membuat orang terlihat penuh
    seharian dan menolak undangan yang sebenarnya bisa mereka terima."""
    assert _acara()["transparency"] == "transparent"


def test_url_ikut_di_deskripsi():
    a = _acara()

    assert "https://contoh/issue/1" in a["description"]
    assert a["source"]["url"] == "https://contoh/issue/1"


def test_tanpa_url_tidak_menyisipkan_baris_kosong():
    """APP_BASE_URL bisa kosong di instance yang belum dikonfigurasi."""
    a = _badan_acara("X", date(2026, 8, 20), "Project IT.", "")

    assert a["description"] == "Project IT."
    assert a["source"] is None
