# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: retensi log dan batas pratinjau Wiki di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Empat setelan yang dulu setelan Django: retensi log API, webhook, dan email,
plus batas ukuran konversi pratinjau Wiki.

Yang dijaga: registri memuatnya dengan bawaan dan rentang yang benar, PATCH
menolak nilai di luar rentang tanpa menulis apa pun, nilai sah terbaca ulang dan
tercatat di audit, env lama hanya benih, dan pembacanya memakai nilai God Mode.
"""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from auditlog.models import LogEntry
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.app.views.wiki_berkas import WikiPratinjauEndpoint
from plane.db.models import User
from plane.license.api.views.setelan import InstanceSettingsEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils import saklar_instance as si

URL = "/api/instances/settings/"
KUNCI_BARU = (
    si.API_ACTIVITY_LOG_RETENTION_DAYS,
    si.WEBHOOK_LOG_RETENTION_DAYS,
    si.EMAIL_LOG_RETENTION_DAYS,
    si.WIKI_PREVIEW_MAX_MB,
)


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-retensi-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"super-{unik}@uji.id", username=f"super_{unik}")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    cache.clear()
    yield user
    cache.clear()


def _get(aktor):
    request = APIRequestFactory().get(URL)
    force_authenticate(request, user=aktor)
    return InstanceSettingsEndpoint.as_view()(request)


def _patch(aktor, badan):
    request = APIRequestFactory().patch(URL, badan, format="json")
    force_authenticate(request, user=aktor)
    return InstanceSettingsEndpoint.as_view()(request)


def _butir(res, kunci):
    return next(d for d in res.data["settings"] if d["key"] == kunci)


def _baris(kunci):
    return InstanceConfiguration.objects.filter(key=kunci).values_list("value", flat=True).first()


@pytest.mark.contract
class TestRetensiLogDanPratinjauWiki:
    @pytest.mark.django_db
    def test_registri_memuat_bawaan_dan_rentang(self, super_admin, monkeypatch):
        for env in (*KUNCI_BARU, "WIKI_PREVIEW_MAX_BYTES"):
            monkeypatch.delenv(env, raising=False)
        res = _get(super_admin)
        assert res.status_code == status.HTTP_200_OK
        harapan = {
            si.API_ACTIVITY_LOG_RETENTION_DAYS: ("14", 1, 365),
            si.WEBHOOK_LOG_RETENTION_DAYS: ("14", 1, 365),
            si.EMAIL_LOG_RETENTION_DAYS: ("7", 1, 365),
            si.WIKI_PREVIEW_MAX_MB: (str(si.SETELAN_ANGKA[si.WIKI_PREVIEW_MAX_MB][0]), 1, 1024),
        }
        for kunci, (bawaan, minimum, maksimum) in harapan.items():
            butir = _butir(res, kunci)
            assert butir["kind"] == "number"
            assert (butir["default"], butir["min"], butir["max"]) == (bawaan, minimum, maksimum)
            assert butir["value"] == bawaan
            assert butir["sensitive"] is False

    @pytest.mark.django_db
    def test_patch_terbaca_ulang_dan_diaudit(self, super_admin):
        res = _patch(
            super_admin,
            {"values": {si.EMAIL_LOG_RETENTION_DAYS: "30", si.WIKI_PREVIEW_MAX_MB: 20}},
        )
        assert res.status_code == status.HTTP_200_OK, res.data
        assert _baris(si.EMAIL_LOG_RETENTION_DAYS) == "30"
        assert _baris(si.WIKI_PREVIEW_MAX_MB) == "20"
        ulang = _get(super_admin)
        assert _butir(ulang, si.EMAIL_LOG_RETENTION_DAYS)["value"] == "30"
        assert _butir(ulang, si.WIKI_PREVIEW_MAX_MB)["value"] == "20"
        assert si.setelan_angka(si.EMAIL_LOG_RETENTION_DAYS) == 30
        entri = LogEntry.objects.get(
            content_type__model="instanceconfiguration",
            object_repr=f"Instance setting: {si.EMAIL_LOG_RETENTION_DAYS}",
        )
        assert entri.changes == {"value": ["7", "30"]}
        assert entri.actor_id == super_admin.id

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ("kunci", "nilai"),
        [
            (si.API_ACTIVITY_LOG_RETENTION_DAYS, 0),
            (si.WEBHOOK_LOG_RETENTION_DAYS, 366),
            (si.EMAIL_LOG_RETENTION_DAYS, "abc"),
            (si.WIKI_PREVIEW_MAX_MB, 0),
            (si.WIKI_PREVIEW_MAX_MB, 1025),
        ],
    )
    def test_di_luar_rentang_ditolak_tanpa_menulis(self, super_admin, kunci, nilai):
        res = _patch(super_admin, {"values": {kunci: nilai, si.STUCK_AFTER_DAYS: 10}})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert set(res.data["errors"]) == {kunci}
        assert _baris(kunci) is None
        assert _baris(si.STUCK_AFTER_DAYS) is None
        assert not LogEntry.objects.filter(content_type__model="instanceconfiguration").exists()

    @pytest.mark.django_db
    def test_env_lama_hanya_benih(self, monkeypatch):
        monkeypatch.setenv(si.WEBHOOK_LOG_RETENTION_DAYS, "21")
        assert si.setelan_angka(si.WEBHOOK_LOG_RETENTION_DAYS) == 21
        InstanceConfiguration.objects.create(key=si.WEBHOOK_LOG_RETENTION_DAYS, value="5", category="PARADISE")
        assert si.setelan_angka(si.WEBHOOK_LOG_RETENTION_DAYS) == 5

    @pytest.mark.django_db
    def test_env_bernama_kunci_pratinjau_tidak_dibaca(self, monkeypatch):
        # Kunci baru: env dengan namanya sendiri bukan benih (KEP-48), hanya WIKI_PREVIEW_MAX_BYTES lama.
        monkeypatch.setenv(si.WIKI_PREVIEW_MAX_MB, "3")
        assert si.setelan_angka(si.WIKI_PREVIEW_MAX_MB) == si.SETELAN_ANGKA[si.WIKI_PREVIEW_MAX_MB][0]

    @pytest.mark.django_db
    def test_konversi_memakai_batas_god_mode(self, settings):
        settings.GOTENBERG_URL = "http://gotenberg.invalid"
        InstanceConfiguration.objects.create(key=si.WIKI_PREVIEW_MAX_MB, value="1", category="PARADISE")
        materi = SimpleNamespace(berkas=SimpleNamespace(size=2 * 1024 * 1024))
        aset, alasan = WikiPratinjauEndpoint()._konversi(None, materi)
        assert aset is None
        assert alasan == "the file is too large to convert"
