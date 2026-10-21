# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji aturan kepemilikan tugas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapa boleh membuang tugas, dan siapa boleh menggeser tenggatnya.

Aturan dari pemilik instance, berlaku di seluruh project:

    hapus tugas     pembuatnya, Super Admin, atau admin project
    arsipkan tugas  sama dengan hapus
    ganti Due Date  HANYA pembuatnya atau Super Admin
    sisanya         bebas untuk semua anggota

Dua hal yang dijaga berkas ini, dan yang kedua yang paling gampang merusak
aplikasi tanpa terlihat.

SATU, hak ganti tenggat memang LEBIH KETAT daripada hak hapus. Admin project
boleh membuang tugas, tapi tidak boleh menggeser tenggat orang. Kalau suatu
saat keduanya disamakan "biar konsisten", aturan yang diminta hilang diam-diam.

DUA, penolakan hanya boleh terjadi kalau tenggatnya BENAR-BENAR berubah.
Beberapa layar mengirim ulang seluruh formulir saat menyimpan, termasuk tenggat
yang tidak disentuh. Menolak berdasarkan "ada target_date di payload" akan
membuat orang yang di-assign tidak bisa menyimpan apa pun, padahal yang ia ubah
cuma prioritas. Uji normalisasi tanggal di bawah menjaga persis itu.

Murni, tanpa database.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from plane.utils import task_access

pytestmark = pytest.mark.unit

PEMBUAT = "user-pembuat"
ORANG_LAIN = "user-lain"


def _tugas(created_by=PEMBUAT, target_date=None):
    return SimpleNamespace(created_by_id=created_by, target_date=target_date)


def _orang(uid=ORANG_LAIN):
    return SimpleNamespace(id=uid, is_anonymous=False)


def _pasang(monkeypatch, *, super_admin=False, admin_project=False):
    monkeypatch.setattr(task_access, "is_super_admin", lambda u: super_admin)
    monkeypatch.setattr(task_access, "_admin_project", lambda u, s, p: admin_project)


# --- hapus dan arsip ---------------------------------------------------------


def test_pembuat_boleh_menghapus_tugasnya(monkeypatch):
    _pasang(monkeypatch)
    assert task_access.bisa_hapus_tugas(_orang(PEMBUAT), _tugas(), "ws", "proj") is True


def test_orang_yang_diassign_tidak_boleh_menghapus(monkeypatch):
    _pasang(monkeypatch, super_admin=False, admin_project=False)
    assert task_access.bisa_hapus_tugas(_orang(), _tugas(), "ws", "proj") is False


def test_admin_project_boleh_menghapus(monkeypatch):
    _pasang(monkeypatch, admin_project=True)
    assert task_access.bisa_hapus_tugas(_orang(), _tugas(), "ws", "proj") is True


def test_super_admin_boleh_menghapus(monkeypatch):
    _pasang(monkeypatch, super_admin=True)
    assert task_access.bisa_hapus_tugas(_orang(), _tugas(), "ws", "proj") is True


def test_anonim_ditolak_menghapus(monkeypatch):
    _pasang(monkeypatch, super_admin=True, admin_project=True)
    assert task_access.bisa_hapus_tugas(None, _tugas(), "ws", "proj") is False


# --- ganti tenggat -----------------------------------------------------------


def test_pembuat_boleh_menggeser_tenggat(monkeypatch):
    _pasang(monkeypatch)
    assert task_access.bisa_ganti_tenggat(_orang(PEMBUAT), _tugas()) is True


def test_super_admin_boleh_menggeser_tenggat(monkeypatch):
    _pasang(monkeypatch, super_admin=True)
    assert task_access.bisa_ganti_tenggat(_orang(), _tugas()) is True


def test_admin_project_TIDAK_boleh_menggeser_tenggat(monkeypatch):
    # Sengaja lebih ketat daripada hak hapus. Kalau suatu saat uji ini
    # "diperbaiki" supaya lulus, aturan yang diminta pemilik instance hilang.
    _pasang(monkeypatch, super_admin=False, admin_project=True)
    assert task_access.bisa_ganti_tenggat(_orang(), _tugas()) is False


def test_orang_yang_diassign_tidak_boleh_menggeser_tenggat(monkeypatch):
    _pasang(monkeypatch)
    assert task_access.bisa_ganti_tenggat(_orang(), _tugas()) is False


# --- kapan sebuah permintaan dianggap MENGUBAH tenggat -----------------------


def test_payload_tanpa_target_date_bukan_perubahan():
    assert task_access.tenggat_diubah(_tugas(target_date=date(2026, 8, 25)), {"priority": "high"}) is False


def test_tanggal_sama_walau_beda_bentuk_bukan_perubahan():
    # Ini yang menjaga orang tetap bisa menyimpan perubahan lain. Klien
    # mengirim teks, database menyimpan DateField, dan keduanya harus dianggap
    # sama.
    tugas = _tugas(target_date=date(2026, 8, 25))
    assert task_access.tenggat_diubah(tugas, {"target_date": "2026-08-25"}) is False
    assert task_access.tenggat_diubah(tugas, {"target_date": "2026-08-25T00:00:00Z"}) is False


def test_tanggal_berbeda_dianggap_perubahan():
    tugas = _tugas(target_date=date(2026, 8, 25))
    assert task_access.tenggat_diubah(tugas, {"target_date": "2026-09-01"}) is True


def test_mengisi_tenggat_yang_tadinya_kosong_dianggap_perubahan():
    assert task_access.tenggat_diubah(_tugas(target_date=None), {"target_date": "2026-09-01"}) is True


def test_mengosongkan_tenggat_dianggap_perubahan():
    tugas = _tugas(target_date=date(2026, 8, 25))
    assert task_access.tenggat_diubah(tugas, {"target_date": None}) is True
    assert task_access.tenggat_diubah(tugas, {"target_date": ""}) is True


def test_tenggat_kosong_tetap_kosong_bukan_perubahan():
    assert task_access.tenggat_diubah(_tugas(target_date=None), {"target_date": None}) is False
    assert task_access.tenggat_diubah(_tugas(target_date=None), {"target_date": ""}) is False
