# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: saklar fitur di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Saklar fitur Paradise diatur dari God Mode, bukan dari `.env`.

Yang dijaga: nilai di database menang atas env, env hanya cadangan saat barisnya
belum ada, PATCH membuat baris yang belum ada alih-alih membalas 200 kosong, dan
nilai selain 0/1 ditolak sebelum apa pun ditulis.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import User
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils.hierarki import gerbang_aktif
from plane.utils.saklar_instance import (
    ENABLE_CHAT_EMAIL,
    ENABLE_TUGAS_KE_DM,
    HIERARKI_GERBANG_TUGAS,
    saklar_aktif,
)

URL = "/api/instances/configurations/"


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-saklar-{uuid4().hex[:8]}",
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
class TestSaklarGodMode:
    @pytest.mark.django_db
    def test_database_menang_atas_env(self, monkeypatch):
        monkeypatch.setenv(ENABLE_CHAT_EMAIL, "1")
        _simpan(ENABLE_CHAT_EMAIL, "0")
        assert saklar_aktif(ENABLE_CHAT_EMAIL) is False

        monkeypatch.setenv(HIERARKI_GERBANG_TUGAS, "0")
        _simpan(HIERARKI_GERBANG_TUGAS, "1")
        assert gerbang_aktif() is True

    @pytest.mark.django_db
    def test_tanpa_baris_jatuh_ke_env_lalu_bawaan(self, monkeypatch):
        monkeypatch.setenv(ENABLE_CHAT_EMAIL, "1")
        assert saklar_aktif(ENABLE_CHAT_EMAIL) is True
        monkeypatch.delenv(ENABLE_CHAT_EMAIL)
        assert saklar_aktif(ENABLE_CHAT_EMAIL) is False
        monkeypatch.delenv(ENABLE_TUGAS_KE_DM, raising=False)
        assert saklar_aktif(ENABLE_TUGAS_KE_DM) is True

    @pytest.mark.django_db
    def test_kunci_tak_dikenal_adalah_bug(self):
        with pytest.raises(KeyError):
            saklar_aktif("ENABLE_SEMBARANG")

    @pytest.mark.django_db
    def test_patch_membuat_baris_yang_belum_ada(self, super_admin, monkeypatch):
        monkeypatch.setenv(ENABLE_CHAT_EMAIL, "0")
        assert not InstanceConfiguration.objects.filter(key=ENABLE_CHAT_EMAIL).exists()

        response = _patch(super_admin, {ENABLE_CHAT_EMAIL: "1"})

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert InstanceConfiguration.objects.get(key=ENABLE_CHAT_EMAIL).value == "1"
        assert saklar_aktif(ENABLE_CHAT_EMAIL) is True

    @pytest.mark.django_db
    def test_rahasia_kalender_tersimpan_terenkripsi(self, super_admin):
        response = _patch(super_admin, {"GOOGLE_CALENDAR_CLIENT_SECRET": "rahasia"})

        assert response.status_code == status.HTTP_200_OK
        baris = InstanceConfiguration.objects.get(key="GOOGLE_CALENDAR_CLIENT_SECRET")
        assert baris.is_encrypted is True
        assert baris.value != "rahasia"

    @pytest.mark.django_db
    @pytest.mark.parametrize("nilai", ["ya", "2", "", None])
    def test_nilai_selain_0_1_ditolak_tanpa_menulis(self, super_admin, nilai):
        _simpan(ENABLE_CHAT_EMAIL, "1")

        response = _patch(super_admin, {ENABLE_CHAT_EMAIL: nilai, ENABLE_TUGAS_KE_DM: "0"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert InstanceConfiguration.objects.get(key=ENABLE_CHAT_EMAIL).value == "1"
        assert not InstanceConfiguration.objects.filter(key=ENABLE_TUGAS_KE_DM).exists()

    @pytest.mark.django_db
    def test_bukan_super_admin_ditolak(self, db):
        response = _patch(_buat_user("staf"), {ENABLE_CHAT_EMAIL: "1"})
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        assert not InstanceConfiguration.objects.filter(key=ENABLE_CHAT_EMAIL).exists()
