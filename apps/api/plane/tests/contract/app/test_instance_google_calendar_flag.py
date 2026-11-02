# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bendera Google Calendar di /api/instances/
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""apps/web menyembunyikan tab Connections kalau bendera ini False.

Yang dijaga: False tanpa kredensial, False kalau cuma salah satu terisi (tombol
Connect tetap gagal), True kalau keduanya terisi di God Mode.
"""

from uuid import uuid4

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory

from plane.license.api.views.instance import InstanceEndpoint
from plane.license.models import Instance, InstanceConfiguration

KUNCI_ID = "GOOGLE_CALENDAR_CLIENT_ID"
KUNCI_SECRET = "GOOGLE_CALENDAR_CLIENT_SECRET"


@pytest.fixture
def instance(db, monkeypatch):
    monkeypatch.delenv(KUNCI_ID, raising=False)
    monkeypatch.delenv(KUNCI_SECRET, raising=False)
    Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-gcal-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    # GET /api/instances/ di-cache 2 jam; tanpa ini kasus kedua membaca jawaban kasus pertama.
    cache.clear()
    yield
    cache.clear()


def _simpan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": nilai, "category": "GOOGLE_CALENDAR", "is_encrypted": False}
    )


def _bendera():
    response = InstanceEndpoint.as_view()(APIRequestFactory().get("/api/instances/"))
    assert response.status_code == status.HTTP_200_OK
    return response.data["config"]["has_google_calendar_configured"]


@pytest.mark.django_db
def test_false_tanpa_kredensial(instance):
    assert _bendera() is False


@pytest.mark.django_db
def test_false_kalau_secret_kosong(instance):
    _simpan(KUNCI_ID, "id-uji.apps.googleusercontent.com")
    assert _bendera() is False


@pytest.mark.django_db
def test_true_kalau_keduanya_terisi(instance):
    _simpan(KUNCI_ID, "id-uji.apps.googleusercontent.com")
    _simpan(KUNCI_SECRET, "rahasia-uji")
    assert _bendera() is True
