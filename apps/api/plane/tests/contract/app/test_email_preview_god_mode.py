# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pratinjau email di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""God Mode > Email > Preview.

Yang dijaga: hanya Super Admin; setiap email di daftar bisa dirender di kedua
bahasa; gambar CID sudah jadi data: URI (peramban tidak bisa membaca cid:);
dan halaman ini TIDAK PERNAH mengirim apa pun.
"""

from uuid import uuid4

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import User
from plane.license.api.views.email_preview import InstanceEmailPreviewEndpoint
from plane.license.models import Instance, InstanceAdmin

URL = "/api/instances/email-preview/"


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-pratinjau-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _buat_user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _get(aktor, key=None, lang="id"):
    url = f"{URL}{key}/" if key else URL
    request = APIRequestFactory().get(url, {"lang": lang})
    force_authenticate(request, user=aktor)
    return InstanceEmailPreviewEndpoint.as_view()(request, **({"key": key} if key else {}))


@pytest.mark.django_db
def test_bukan_super_admin_ditolak():
    assert _get(_buat_user("biasa")).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["id", "en"])
def test_semua_email_terender_tanpa_terkirim(super_admin, lang):
    daftar = _get(super_admin, lang=lang)
    assert daftar.status_code == status.HTTP_200_OK
    hasil = daftar.data["results"]
    assert len(hasil) >= 20
    assert not [h["key"] for h in hasil if h["error"]]

    for item in hasil:
        r = _get(super_admin, item["key"], lang)
        assert r.status_code == status.HTTP_200_OK, item["key"]
        assert r.data["subject"] == item["subject"]
        assert "cid:" not in r.data["html"], item["key"]
        assert "data:image/png;base64," in r.data["html"], item["key"]  # logo selalu ikut
        assert r.data["text"].strip(), item["key"]

    assert mail.outbox == []


@pytest.mark.django_db
def test_kunci_tak_dikenal_dan_tak_sah(super_admin):
    assert _get(super_admin, "tidak-ada").status_code == status.HTTP_404_NOT_FOUND
    assert _get(super_admin, "../etc").status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_bahasa_tak_dikenal_jatuh_ke_indonesia(super_admin):
    assert _get(super_admin, lang="fr").data["lang"] == "id"
