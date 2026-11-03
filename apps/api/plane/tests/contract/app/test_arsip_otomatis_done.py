# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: arsip otomatis work item Done
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Arsip otomatis work item Done dari God Mode > Features (AUTO_ARCHIVE_DONE_DAYS).

Yang dijaga: hanya grup completed yang diarsipkan, hitungan dari `completed_at`
(fallback `updated_at`), 0 = mati, dan PATCH hanya menerima nilai di daftar pilihan.
"""

from datetime import timedelta
from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.bgtasks.issue_automation_task import archive_done_issues_instance
from plane.db.models import Issue, Project, State, User, Workspace
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils.saklar_instance import AUTO_ARCHIVE_DONE_DAYS, setelan_angka


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")


def _simpan(nilai):
    InstanceConfiguration.objects.update_or_create(
        key=AUTO_ARCHIVE_DONE_DAYS, defaults={"value": nilai, "category": "PARADISE"}
    )


@pytest.fixture
def project(db):
    pemilik = _buat_user("pemilik")
    workspace = Workspace.objects.create(name="Uji", slug=f"uji-{uuid4().hex[:8]}", owner=pemilik)
    return Project.objects.create(name="Uji", identifier="UJI", workspace=workspace, created_by=pemilik)


@pytest.fixture
def states(project):
    return {
        grup: State.objects.create(name=grup, project=project, group=grup, default=grup == "backlog")
        for grup in ("backlog", "started", "completed", "cancelled")
    }


def _issue(project, state, selesai_hari_lalu=None, diubah_hari_lalu=None):
    issue = Issue.objects.create(name="Tugas", workspace=project.workspace, project=project, state=state)
    sekarang = timezone.now()
    perubahan = {}
    if selesai_hari_lalu is not None:
        perubahan["completed_at"] = sekarang - timedelta(days=selesai_hari_lalu)
    if diubah_hari_lalu is not None:
        perubahan["completed_at"] = None
        perubahan["updated_at"] = sekarang - timedelta(days=diubah_hari_lalu)
    if perubahan:
        Issue.objects.filter(id=issue.id).update(**perubahan)
    return issue


def _diarsipkan(issue):
    return Issue.all_objects.get(id=issue.id).archived_at is not None


@pytest.fixture(autouse=True)
def tanpa_aktivitas():
    with mock.patch("plane.bgtasks.issue_automation_task.issue_activity") as palsu:
        yield palsu


@pytest.mark.contract
class TestArsipOtomatisDone:
    @pytest.mark.django_db
    def test_done_lewat_batas_diarsipkan(self, project, states, tanpa_aktivitas):
        _simpan("30")
        lama = _issue(project, states["completed"], selesai_hari_lalu=31)
        baru = _issue(project, states["completed"], selesai_hari_lalu=10)

        assert archive_done_issues_instance() == 1
        assert _diarsipkan(lama)
        assert not _diarsipkan(baru)
        kwargs = tanpa_aktivitas.delay.call_args.kwargs
        assert kwargs["notification"] is False
        assert kwargs["issue_id"] == str(lama.id)

    @pytest.mark.django_db
    def test_hanya_grup_completed(self, project, states):
        _simpan("7")
        batal = _issue(project, states["cancelled"], diubah_hari_lalu=100)
        jalan = _issue(project, states["started"], diubah_hari_lalu=100)

        archive_done_issues_instance()
        assert not _diarsipkan(batal)
        assert not _diarsipkan(jalan)

    @pytest.mark.django_db
    def test_tanpa_completed_at_pakai_updated_at(self, project, states):
        _simpan("30")
        lama = _issue(project, states["completed"], diubah_hari_lalu=40)
        baru = _issue(project, states["completed"], diubah_hari_lalu=5)

        archive_done_issues_instance()
        assert _diarsipkan(lama)
        assert not _diarsipkan(baru)

    @pytest.mark.django_db
    def test_nol_berarti_mati(self, project, states):
        _simpan("0")
        lama = _issue(project, states["completed"], selesai_hari_lalu=400)

        assert archive_done_issues_instance() == 0
        assert not _diarsipkan(lama)

    @pytest.mark.django_db
    def test_bawaan_90_hari(self, monkeypatch):
        InstanceConfiguration.objects.filter(key=AUTO_ARCHIVE_DONE_DAYS).delete()
        monkeypatch.delenv(AUTO_ARCHIVE_DONE_DAYS, raising=False)
        assert setelan_angka(AUTO_ARCHIVE_DONE_DAYS) == 90


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-arsip-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _buat_user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _patch(aktor, badan):
    request = APIRequestFactory().patch("/api/instances/configurations/", badan, format="json")
    force_authenticate(request, user=aktor)
    return InstanceConfigurationEndpoint.as_view()(request)


@pytest.mark.contract
class TestPilihanArsipOtomatis:
    @pytest.mark.django_db
    @pytest.mark.parametrize("nilai", ["0", "7", "30", "365"])
    def test_pilihan_sah_tersimpan(self, super_admin, nilai):
        response = _patch(super_admin, {AUTO_ARCHIVE_DONE_DAYS: nilai})
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert setelan_angka(AUTO_ARCHIVE_DONE_DAYS) == int(nilai)

    @pytest.mark.django_db
    @pytest.mark.parametrize("nilai", ["5", "45", "366", "-1", "abc"])
    def test_di_luar_pilihan_ditolak(self, super_admin, nilai):
        _simpan("90")
        response = _patch(super_admin, {AUTO_ARCHIVE_DONE_DAYS: nilai})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert setelan_angka(AUTO_ARCHIVE_DONE_DAYS) == 90
