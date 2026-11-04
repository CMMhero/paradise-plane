# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tanggal mulai & selesai otomatis
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Tes kontrak KEP-41: status menggerakkan tanggal mulai & selesai.

* Masuk `started` mengisi start_date yang kosong; masuk `completed` mengisi
  target_date yang kosong. Tanggal yang sudah ada tidak pernah ditimpa, dan
  tidak dikosongkan saat tugas mundur.
* Staf yang menggeser ke selesai masih menunggu atasan: target_date baru
  diisi saat DISETUJUI, dengan tanggal PENGAJUAN (KEP-84, bawaan
  APPROVAL_FINISH_TIME). Ditolak = tetap kosong.
* Tiap isian otomatis meninggalkan jejak aktivitas.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

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
from plane.utils.hierarki import FLAG_GERBANG
from plane.utils.tanggal_otomatis import tanggal_lokal

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_PUTUSKAN = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/{pk}/"
ZONA = "Asia/Jakarta"


def _buat_user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email="owner-tgl@plane.so", username="owner_tgl")
    return Workspace.objects.create(name="WS", slug="ws-tgl", owner=pemilik)


@pytest.fixture
def staf(db, workspace):
    return _buat_user("staftgl", workspace)


@pytest.fixture
def bos(db, workspace):
    return _buat_user("bostgl", workspace)


@pytest.fixture
def divisi(db, workspace, bos, staf):
    project = Project.objects.create(
        name="Divisi T", identifier="DIVT", workspace=workspace, created_by=bos, timezone=ZONA
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
        {"name": "Tugas tanggal", "assignee_ids": [str(user.id)], **extra},
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


def _hari_ini():
    return tanggal_lokal(None, ZONA)


@pytest.mark.contract
class TestTanggalMulai:
    @pytest.mark.django_db
    def test_masuk_started_mengisi_mulai_dan_mencatat_aktivitas(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        issue_id = _buat(bos, workspace, divisi)

        issue = _geser(bos, workspace, divisi, issue_id, "started")

        assert issue.start_date == _hari_ini()
        jejak = IssueActivity.objects.filter(issue_id=issue_id, field="start_date", comment__contains="automatically")
        assert jejak.count() == 1
        assert jejak.first().actor_id == bos.id

    @pytest.mark.django_db
    def test_mulai_rencana_TIDAK_ditimpa(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        rencana = _hari_ini() + timedelta(days=3)
        issue_id = _buat(bos, workspace, divisi, start_date=str(rencana))

        issue = _geser(bos, workspace, divisi, issue_id, "started")

        assert issue.start_date == rencana
        assert not IssueActivity.objects.filter(issue_id=issue_id, comment__contains="automatically").exists()

    @pytest.mark.django_db
    def test_tenggat_sudah_lewat_mulai_TETAP_kosong(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        issue_id = _buat(bos, workspace, divisi, target_date=str(_hari_ini() - timedelta(days=1)))

        issue = _geser(bos, workspace, divisi, issue_id, "started")

        assert issue.start_date is None

    @pytest.mark.django_db
    def test_mundur_ke_todo_mulai_TIDAK_dikosongkan(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        issue_id = _buat(bos, workspace, divisi)
        _geser(bos, workspace, divisi, issue_id, "started")

        issue = _geser(bos, workspace, divisi, issue_id, "unstarted")

        assert issue.start_date == _hari_ini()


@pytest.mark.contract
class TestTanggalSelesai:
    @pytest.mark.django_db
    def test_supervisor_selesai_langsung_mengisi_tenggat(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id = _buat(bos, workspace, divisi)

        issue = _geser(bos, workspace, divisi, issue_id, "completed")

        assert issue.target_date == _hari_ini()
        assert IssueActivity.objects.filter(
            issue_id=issue_id, field="target_date", comment__contains="automatically"
        ).exists()

    @pytest.mark.django_db
    def test_tenggat_yang_ada_TIDAK_ditimpa(self, workspace, bos, divisi, monkeypatch):
        monkeypatch.delenv(FLAG_GERBANG, raising=False)
        tenggat = _hari_ini() + timedelta(days=5)
        issue_id = _buat(bos, workspace, divisi, target_date=str(tenggat))

        issue = _geser(bos, workspace, divisi, issue_id, "completed")

        assert issue.target_date == tenggat

    @pytest.mark.django_db
    def test_staf_menunggu_tenggat_kosong_lalu_terisi_saat_disetujui(
        self, workspace, staf, bos, divisi, monkeypatch
    ):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id = _buat(staf, workspace, divisi)

        issue = _geser(staf, workspace, divisi, issue_id, "completed")
        assert issue.target_date is None, "masih menunggu atasan, belum boleh terisi"

        baris = PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")
        # KEP-84: bawaan APPROVAL_FINISH_TIME = saat diajukan. Pengajuan dibuat dua
        # hari lalu, disetujui hari ini: tanggalnya hari PENGAJUAN.
        diajukan = timezone.now() - timedelta(days=2)
        PersetujuanPenugasan.objects.filter(pk=baris.pk).update(created_at=diajukan)
        res = _klien(bos).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "setujui"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)

        issue.refresh_from_db()
        assert issue.completed_at == diajukan
        assert issue.target_date == tanggal_lokal(diajukan, ZONA)
        jejak = IssueActivity.objects.get(issue_id=issue_id, field="target_date", comment__contains="automatically")
        assert jejak.actor_id == bos.id

    @pytest.mark.django_db
    def test_staf_ditolak_tenggat_TETAP_kosong(self, workspace, staf, bos, divisi, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id = _buat(staf, workspace, divisi)
        _geser(staf, workspace, divisi, issue_id, "completed")

        baris = PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")
        res = _klien(bos).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "tolak", "alasan": "Belum lengkap"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)

        assert Issue.objects.get(pk=issue_id).target_date is None
