# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: setelan tanggal & terlambat di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Setelan tanggal otomatis dan terlambat yang diatur dari God Mode > Features.

* `AUTO_START_DATE_ON_START` / `AUTO_DUE_DATE_ON_DONE` mematikan isian KEP-41.
* `DUE_DATE_ON_EARLY_DONE` = 1 memajukan Due date tugas yang selesai lebih awal,
  dengan rencana lamanya tersimpan di aktivitas; tugas terlambat tidak pernah
  digeser (laporan tepat waktu harus tetap jujur). Berlaku juga lewat persetujuan.
* `OVERDUE_GRACE_DAYS` menggeser batas terlambat di Dashboard Divisi dan
  diumumkan ke apps/web lewat /api/instances/.
* PATCH konfigurasi menolak nilai di luar pilihan/rentang.
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from plane.db.models import (
    DEFAULT_STATES,
    Issue,
    IssueActivity,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    State,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.api.views.instance import InstanceEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils.hierarki import FLAG_GERBANG
from plane.utils.saklar_instance import (
    AUTO_DUE_DATE_ON_DONE,
    AUTO_START_DATE_ON_START,
    DASHBOARD_ON_TIME_WINDOW_DAYS,
    DUE_DATE_ON_EARLY_DONE,
    OVERDUE_GRACE_DAYS,
    setelan_angka,
)
from plane.utils.tanggal_otomatis import batas_terlambat, selesai_otomatis, tanggal_lokal

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_PUTUSKAN = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/{pk}/"
URL_DASHBOARD = "/api/workspaces/{slug}/divisi-dashboard/"
ZONA = "Asia/Jakarta"


def _simpan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": nilai, "category": "PARADISE"})


def _buat_user(prefix, workspace, role=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _hari_ini():
    return tanggal_lokal(None, ZONA)


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email="owner-tglset@plane.so", username="owner_tglset")
    return Workspace.objects.create(name="WS", slug="ws-tglset", owner=pemilik)


@pytest.fixture
def staf(db, workspace):
    return _buat_user("staftglset", workspace)


@pytest.fixture
def bos(db, workspace):
    return _buat_user("bostglset", workspace, role=20)


@pytest.fixture
def divisi(db, workspace, bos, staf):
    project = Project.objects.create(
        name="Divisi S", identifier="DIVS", workspace=workspace, created_by=bos, timezone=ZONA
    )
    ProjectMember.objects.create(project=project, member=bos, workspace=workspace, role=20)
    ProjectMember.objects.create(project=project, member=staf, workspace=workspace, role=15)
    JabatanOrganisasi.objects.create(workspace=workspace, member=bos, tingkat=TINGKAT_SUPERVISOR)
    JabatanOrganisasi.objects.create(workspace=workspace, member=staf, tingkat=TINGKAT_MEMBER)
    for d in DEFAULT_STATES:
        State.objects.get_or_create(
            project=project,
            workspace=workspace,
            name=d["name"],
            defaults={
                "color": d["color"],
                "sequence": d["sequence"],
                "group": d["group"],
                "default": d.get("default", False),
            },
        )
    return project


def _state(divisi, group):
    return State.objects.filter(project=divisi, group=group).order_by("sequence").first()


def _buat(user, workspace, divisi, **extra):
    res = _klien(user).post(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id),
        {"name": "Tugas setelan", "assignee_ids": [str(user.id)], **extra},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED, getattr(res, "data", None)
    return res.json()["id"]


def _geser(user, workspace, divisi, issue_id, group):
    res = _klien(user).patch(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id) + f"{issue_id}/",
        {"state": str(_state(divisi, group).id)},
        format="json",
    )
    assert res.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(res, "data", None)
    return Issue.objects.get(pk=issue_id)


@pytest.mark.unit
class TestAturanMurni:
    HARI = date(2026, 11, 3)

    @pytest.mark.parametrize(
        "mulai, tenggat, isi_kosong, majukan, harapan",
        [
            # Tenggat kosong: diisi hanya kalau saklarnya menyala.
            (None, None, True, False, HARI),
            (None, None, False, False, None),
            # Selesai lebih awal (rencana 5 Nov, selesai 3 Nov).
            (None, date(2026, 11, 5), True, False, None),
            (None, date(2026, 11, 5), True, True, HARI),
            # Selesai pas tenggat / terlambat: tidak pernah digeser.
            (None, HARI, True, True, None),
            (None, date(2026, 11, 1), True, True, None),
            # Mulai sesudah hari selesai: pasangan mulai > selesai tidak boleh lahir.
            (date(2026, 11, 4), date(2026, 11, 5), True, True, None),
            (date(2026, 11, 4), None, True, False, None),
        ],
    )
    def test_selesai_otomatis(self, mulai, tenggat, isi_kosong, majukan, harapan):
        hasil = selesai_otomatis(mulai, tenggat, self.HARI, isi_kosong=isi_kosong, majukan_rencana=majukan)
        assert hasil == harapan

    @pytest.mark.django_db
    @pytest.mark.parametrize("tenggang, harapan", [("0", date(2026, 11, 3)), ("2", date(2026, 11, 1))])
    def test_batas_terlambat(self, tenggang, harapan):
        _simpan(OVERDUE_GRACE_DAYS, tenggang)
        assert batas_terlambat(date(2026, 11, 3)) == harapan


@pytest.mark.contract
class TestSaklarTanggalOtomatis:
    @pytest.mark.django_db
    def test_isi_mulai_dimatikan(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        _simpan(AUTO_START_DATE_ON_START, "0")
        issue_id = _buat(bos, workspace, divisi)

        issue = _geser(bos, workspace, divisi, issue_id, "started")

        assert issue.start_date is None
        assert not IssueActivity.objects.filter(issue_id=issue_id, comment__contains="automatically").exists()

    @pytest.mark.django_db
    def test_isi_tenggat_dimatikan(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        _simpan(AUTO_DUE_DATE_ON_DONE, "0")
        issue_id = _buat(bos, workspace, divisi)

        issue = _geser(bos, workspace, divisi, issue_id, "completed")

        assert issue.target_date is None

    @pytest.mark.django_db
    def test_bawaan_tetap_mengisi(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        for kunci in (AUTO_START_DATE_ON_START, AUTO_DUE_DATE_ON_DONE):
            monkeypatch.delenv(kunci, raising=False)
        issue_id = _buat(bos, workspace, divisi)

        assert _geser(bos, workspace, divisi, issue_id, "started").start_date == _hari_ini()
        assert _geser(bos, workspace, divisi, issue_id, "completed").target_date == _hari_ini()


@pytest.mark.contract
class TestSelesaiLebihAwal:
    @pytest.mark.django_db
    def test_bawaan_rencana_dibiarkan(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        monkeypatch.delenv(DUE_DATE_ON_EARLY_DONE, raising=False)
        rencana = _hari_ini() + timedelta(days=2)
        issue_id = _buat(bos, workspace, divisi, target_date=str(rencana))

        assert _geser(bos, workspace, divisi, issue_id, "completed").target_date == rencana

    @pytest.mark.django_db
    def test_dimajukan_dan_rencana_tercatat(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        _simpan(DUE_DATE_ON_EARLY_DONE, "1")
        rencana = _hari_ini() + timedelta(days=2)
        issue_id = _buat(bos, workspace, divisi, target_date=str(rencana))

        issue = _geser(bos, workspace, divisi, issue_id, "completed")

        assert issue.target_date == _hari_ini()
        jejak = IssueActivity.objects.get(issue_id=issue_id, field="target_date", comment__contains="automatically")
        assert jejak.old_value == str(rencana)
        assert jejak.new_value == str(_hari_ini())
        assert jejak.actor_id == bos.id

    @pytest.mark.django_db
    def test_terlambat_TIDAK_digeser(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        _simpan(DUE_DATE_ON_EARLY_DONE, "1")
        rencana = _hari_ini() - timedelta(days=2)
        issue_id = _buat(bos, workspace, divisi, target_date=str(rencana))

        assert _geser(bos, workspace, divisi, issue_id, "completed").target_date == rencana

    @pytest.mark.django_db
    def test_lewat_persetujuan_memakai_hari_selesai(self, workspace, staf, bos, divisi, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _simpan(DUE_DATE_ON_EARLY_DONE, "1")
        rencana = _hari_ini() + timedelta(days=3)
        issue_id = _buat(staf, workspace, divisi, target_date=str(rencana))

        issue = _geser(staf, workspace, divisi, issue_id, "completed")
        assert issue.target_date == rencana, "masih menunggu atasan, belum boleh bergeser"

        baris = PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")
        res = _klien(bos).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "setujui"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)

        issue.refresh_from_db()
        assert issue.target_date == tanggal_lokal(issue.completed_at, ZONA)
        jejak = IssueActivity.objects.get(issue_id=issue_id, field="target_date", comment__contains="automatically")
        assert jejak.old_value == str(rencana)
        assert jejak.actor_id == bos.id


@pytest.mark.contract
class TestTenggangTerlambat:
    @pytest.mark.django_db
    def test_dashboard_divisi_menghormati_tenggang(self, workspace, bos, divisi):
        state = _state(divisi, "unstarted")
        Issue(
            name="Lewat dua hari",
            workspace=workspace,
            project=divisi,
            state=state,
            target_date=timezone.localdate() - timedelta(days=2),
        ).save()
        url = URL_DASHBOARD.format(slug=workspace.slug)

        _simpan(OVERDUE_GRACE_DAYS, "0")
        assert _klien(bos).get(url).data["totals"]["issues_overdue"] == 1

        _simpan(OVERDUE_GRACE_DAYS, "2")
        assert _klien(bos).get(url).data["totals"]["issues_overdue"] == 0

        _simpan(OVERDUE_GRACE_DAYS, "1")
        assert _klien(bos).get(url).data["totals"]["issues_overdue"] == 1

    @pytest.mark.django_db
    def test_jendela_tepat_waktu_diumumkan(self, workspace, bos, divisi):
        _simpan(DASHBOARD_ON_TIME_WINDOW_DAYS, "60")
        data = _klien(bos).get(URL_DASHBOARD.format(slug=workspace.slug)).data
        assert data["on_time_window_days"] == 60

    @pytest.mark.django_db
    def test_diumumkan_ke_web(self):
        Instance.objects.create(
            instance_name="uji",
            instance_id=f"uji-tenggang-{uuid4().hex[:8]}",
            current_version="uji",
            last_checked_at=timezone.now(),
        )
        _simpan(OVERDUE_GRACE_DAYS, "3")
        cache.clear()
        try:
            response = InstanceEndpoint.as_view()(APIRequestFactory().get("/api/instances/"))
            assert response.status_code == status.HTTP_200_OK
            assert response.data["config"]["paradise_overdue_grace_days"] == 3
        finally:
            cache.clear()


@pytest.mark.contract
class TestPatchSetelanTanggal:
    @pytest.fixture
    def super_admin(self, db):
        instance = Instance.objects.create(
            instance_name="uji",
            instance_id=f"uji-tglset-{uuid4().hex[:8]}",
            current_version="uji",
            last_checked_at=timezone.now(),
        )
        unik = uuid4().hex[:8]
        user = User.objects.create(email=f"super-{unik}@plane.so", username=f"super_{unik}")
        InstanceAdmin.objects.create(instance=instance, user=user, role=20)
        return user

    def _patch(self, aktor, badan):
        request = APIRequestFactory().patch("/api/instances/configurations/", badan, format="json")
        force_authenticate(request, user=aktor)
        return InstanceConfigurationEndpoint.as_view()(request)

    @pytest.mark.django_db
    def test_nilai_sah_tersimpan(self, super_admin):
        response = self._patch(
            super_admin,
            {
                DUE_DATE_ON_EARLY_DONE: "1",
                OVERDUE_GRACE_DAYS: "3",
                DASHBOARD_ON_TIME_WINDOW_DAYS: "90",
                AUTO_START_DATE_ON_START: "0",
            },
        )
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert setelan_angka(DUE_DATE_ON_EARLY_DONE) == 1
        assert setelan_angka(OVERDUE_GRACE_DAYS) == 3
        assert setelan_angka(DASHBOARD_ON_TIME_WINDOW_DAYS) == 90

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "kunci, nilai",
        [
            (DUE_DATE_ON_EARLY_DONE, "2"),
            (OVERDUE_GRACE_DAYS, "31"),
            (OVERDUE_GRACE_DAYS, "-1"),
            (DASHBOARD_ON_TIME_WINDOW_DAYS, "3"),
            (AUTO_DUE_DATE_ON_DONE, "ya"),
        ],
    )
    def test_nilai_liar_ditolak_tanpa_menulis(self, super_admin, kunci, nilai):
        response = self._patch(super_admin, {kunci: nilai})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not InstanceConfiguration.objects.filter(key=kunci).exists()
