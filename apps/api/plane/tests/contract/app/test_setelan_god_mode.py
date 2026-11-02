# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: setelan angka & modul di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Setelan angka dan saklar modul yang diatur dari God Mode > Features.

Yang dijaga: angka dijepit ke rentangnya walau database berisi nilai liar
(retensi 0 hari = semua riwayat terhapus), PATCH menolak angka di luar rentang
tanpa menulis apa pun, dan /api/instances/ mengumumkan modul yang menyala
sehingga apps/web bisa menyembunyikan menunya.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import User
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils.saklar_instance import (
    CHAT_EMAIL_QUIET_MINUTES,
    ENABLE_ANALYTICS,
    ENABLE_INITIATIVES,
    LOGIN_HISTORY_RETENTION_DAYS,
    MODUL_APLIKASI,
    SAKLAR_BAWAAN,
    TRASH_RETENTION_DAYS,
    modul_aktif,
    setelan_angka,
)

URL = "/api/instances/configurations/"


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-setelan-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _buat_user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _patch(aktor, badan):
    request = APIRequestFactory().patch(URL, badan, format="json")
    force_authenticate(request, user=aktor)
    return InstanceConfigurationEndpoint.as_view()(request)


def _simpan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": nilai, "category": "PARADISE"})


@pytest.mark.contract
class TestSetelanAngka:
    @pytest.mark.django_db
    def test_tanpa_baris_memakai_bawaan(self, monkeypatch):
        monkeypatch.delenv(CHAT_EMAIL_QUIET_MINUTES, raising=False)
        assert setelan_angka(CHAT_EMAIL_QUIET_MINUTES) == 10

    @pytest.mark.django_db
    def test_database_menang_atas_env(self, monkeypatch):
        monkeypatch.setenv(LOGIN_HISTORY_RETENTION_DAYS, "30")
        _simpan(LOGIN_HISTORY_RETENTION_DAYS, "120")
        assert setelan_angka(LOGIN_HISTORY_RETENTION_DAYS) == 120

    @pytest.mark.django_db
    @pytest.mark.parametrize("liar, harapan", [("0", 1), ("-5", 1), ("999999", 3650), ("abc", None)])
    def test_nilai_liar_dijepit(self, liar, harapan):
        _simpan(TRASH_RETENTION_DAYS, liar)
        hasil = setelan_angka(TRASH_RETENTION_DAYS)
        if harapan is None:
            # Bukan angka: jatuh ke bawaan, tetap di dalam rentang.
            assert 1 <= hasil <= 3650
        else:
            assert hasil == harapan

    @pytest.mark.django_db
    def test_patch_angka_sah_tersimpan(self, super_admin):
        response = _patch(super_admin, {CHAT_EMAIL_QUIET_MINUTES: "15"})
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert setelan_angka(CHAT_EMAIL_QUIET_MINUTES) == 15

    @pytest.mark.django_db
    @pytest.mark.parametrize("nilai", ["0", "3", "1000", "dua", "", None])
    def test_patch_di_luar_rentang_ditolak_tanpa_menulis(self, super_admin, nilai):
        response = _patch(super_admin, {LOGIN_HISTORY_RETENTION_DAYS: nilai, ENABLE_ANALYTICS: "0"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not InstanceConfiguration.objects.filter(key=LOGIN_HISTORY_RETENTION_DAYS).exists()
        assert not InstanceConfiguration.objects.filter(key=ENABLE_ANALYTICS).exists()


@pytest.mark.contract
class TestModulAplikasi:
    @pytest.mark.django_db
    def test_bawaan_sama_dengan_perilaku_lama(self, monkeypatch):
        for kunci in MODUL_APLIKASI.values():
            monkeypatch.delenv(kunci, raising=False)
        assert modul_aktif() == {
            # Sidebar utama, menu workspace, dan tab project: tampil seperti dulu.
            "inbox": True,
            "your_work": True,
            "stickies": True,
            "drafts": True,
            "quick_links": True,
            "dashboards": True,
            "initiatives": False,
            "views": True,
            "analytics": True,
            "chat": True,
            "wiki": True,
            "archives": True,
            "work_items": True,
            "modules": True,
            "pages": True,
            "intake": True,
            "approvals": True,
            # Dulu dimatikan di kode lewat PARADISE_FEATURES; bawaannya tetap mati.
            "time_tracking": False,
            "estimates": False,
        }

    @pytest.mark.django_db
    def test_fitur_yang_dicabut_bukan_modul_lagi(self):
        # KEP-53: cycles, work item types, templates, dan jadwal berulang dicabut.
        # Tak boleh muncul lagi sebagai saklar, termasuk lewat baris lama di DB.
        for nama in ("cycles", "work_item_types", "templates"):
            assert nama not in MODUL_APLIKASI
            assert nama not in modul_aktif()
        for kunci in ("ENABLE_CYCLES", "ENABLE_WORK_ITEM_TYPES", "ENABLE_TEMPLATES", "ENABLE_RECURRING_ISSUES"):
            assert kunci not in SAKLAR_BAWAAN

    def test_kunci_saklar_mengikuti_nama_modul(self):
        # apps/web dan God Mode menyusun kuncinya sendiri dari nama modul.
        for nama, kunci in MODUL_APLIKASI.items():
            assert kunci == f"ENABLE_{nama.upper()}"
            assert kunci in SAKLAR_BAWAAN

    @pytest.mark.django_db
    def test_modul_baru_bisa_dimatikan_dan_dinyalakan(self, super_admin):
        response = _patch(super_admin, {"ENABLE_STICKIES": "0", "ENABLE_ESTIMATES": "1", "ENABLE_WORK_ITEMS": "0"})
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        hasil = modul_aktif()
        assert hasil["stickies"] is False
        assert hasil["estimates"] is True
        assert hasil["work_items"] is False

    @pytest.mark.django_db
    def test_saklar_dari_god_mode_terbaca(self, super_admin):
        assert _patch(super_admin, {ENABLE_ANALYTICS: "0", ENABLE_INITIATIVES: "1"}).status_code == 200
        hasil = modul_aktif()
        assert hasil["analytics"] is False
        assert hasil["initiatives"] is True

    @pytest.mark.django_db
    def test_nilai_modul_selain_0_1_ditolak(self, super_admin):
        response = _patch(super_admin, {ENABLE_ANALYTICS: "off"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
