# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji widget "Needs attention" di Home
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kontrak `GET /workspaces/<slug>/paradise/attention/`.

Dikunci:

1. Pengelompokan: lewat tenggat, jatuh tempo 7 hari, ditolak, menunggu, disebut.
2. Bagian atasan (`decide`, `team_overdue`) hanya untuk yang berwenang.
3. Hanya project yang user anggotai; tugas selesai tidak ikut.
4. Jumlah kueri tidak tumbuh mengikuti jumlah tugas.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.utils.setelan_instance import hari_ini_kantor
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueAssignee,
    IssueMention,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    State,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    User,
    WorkspaceMember,
)

URL = "/api/workspaces/{slug}/paradise/attention/"


def _user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _tugas(project, state, nama, tenggat=None, assignee=None):
    issue = Issue(name=nama, workspace=project.workspace, project=project, state=state, target_date=tenggat)
    issue.save()
    if assignee:
        IssueAssignee.objects.create(issue=issue, assignee=assignee, project=project, workspace=project.workspace)
    return issue


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.p1 = Project.objects.create(name="Gudang", identifier="WH", workspace=workspace, created_by=create_user)
    o.asing = Project.objects.create(name="Asing", identifier="AS", workspace=workspace, created_by=create_user)
    o.divisi = Divisi.objects.create(workspace=workspace, kode="SCM", nama="Supply Chain")
    o.dept = Departemen.objects.create(workspace=workspace, divisi=o.divisi, kode="WH", nama="Gudang")
    DepartemenProject.objects.create(workspace=workspace, departemen=o.dept, project=o.p1)
    o.staf = _user("staf", workspace)
    o.rekan = _user("rekan", workspace)
    o.manager = _user("mgr", workspace)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.staf, tingkat=TINGKAT_MEMBER, departemen=o.dept)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.rekan, tingkat=TINGKAT_MEMBER, departemen=o.dept)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.manager, tingkat=TINGKAT_MANAGER, divisi=o.divisi)
    for proj in (o.p1, o.asing):
        o.__dict__.setdefault("states", {})[proj.id] = {
            g: State.objects.create(
                name=g, group=g, color="#000000", project=proj, workspace=workspace, default=g == "unstarted"
            )
            for g in ("unstarted", "started", "completed", "cancelled")
        }
    o.s = o.states[o.p1.id]
    ProjectMember.objects.get_or_create(project=o.asing, member=o.rekan, workspace=workspace, defaults={"role": 20})
    return o


def _kunci(data):
    return {g["key"]: g for g in data["groups"]}


@pytest.mark.contract
class TestPerhatian:
    @pytest.mark.django_db
    def test_pengelompokan_untuk_staf(self, org):
        hari = hari_ini_kantor()
        lewat = _tugas(org.p1, org.s["unstarted"], "Lewat", hari - timedelta(days=3), org.staf)
        _tugas(org.p1, org.s["unstarted"], "Hari ini", hari, org.staf)
        _tugas(org.p1, org.s["unstarted"], "Minggu depan", hari + timedelta(days=7), org.staf)
        _tugas(org.p1, org.s["unstarted"], "Jauh", hari + timedelta(days=30), org.staf)
        _tugas(org.p1, org.s["completed"], "Selesai lewat", hari - timedelta(days=5), org.staf)
        _tugas(org.p1, org.s["unstarted"], "Milik rekan", hari - timedelta(days=5), org.rekan)
        ditolak = _tugas(org.p1, org.s["started"], "Ditolak", None, org.staf)
        PersetujuanPenugasan.objects.create(
            workspace=org.ws,
            project=org.p1,
            issue=ditolak,
            pemohon=org.staf,
            penerima=org.staf,
            status="ditolak",
            alasan="Belum lengkap",
            diputuskan_oleh=org.manager,
            diputuskan_pada=timezone.now(),
        )
        menunggu = _tugas(org.p1, org.s["completed"], "Menunggu", None, org.staf)
        PersetujuanPenugasan.objects.create(
            workspace=org.ws, project=org.p1, issue=menunggu, pemohon=org.staf, penerima=org.staf, status="menunggu"
        )
        disebut = _tugas(org.p1, org.s["unstarted"], "Disebut", None, org.rekan)
        IssueMention.objects.create(issue=disebut, mention=org.staf, project=org.p1, workspace=org.ws)

        respon = _klien(org.staf).get(URL.format(slug=org.ws.slug))
        assert respon.status_code == status.HTTP_200_OK, respon.data
        data = respon.json()
        g = _kunci(data)

        assert [i["name"] for i in g["overdue_mine"]["items"]] == ["Lewat"]
        assert g["overdue_mine"]["items"][0]["identifier"] == f"WH-{lewat.sequence_id}"
        assert [i["name"] for i in g["due_soon"]["items"]] == ["Hari ini", "Minggu depan"]
        assert [i["name"] for i in g["rejected"]["items"]] == ["Ditolak"]
        assert g["rejected"]["items"][0]["reason"] == "Belum lengkap"
        assert [i["name"] for i in g["waiting_mine"]["items"]] == ["Menunggu"]
        assert [i["name"] for i in g["mentioned"]["items"]] == ["Disebut"]
        assert data["is_supervisor"] is False

    @pytest.mark.django_db
    def test_bagian_atasan_tidak_bocor_ke_staf(self, org):
        hari = hari_ini_kantor()
        _tugas(org.p1, org.s["unstarted"], "Rekan lewat", hari - timedelta(days=2), org.rekan)
        diajukan = _tugas(org.p1, org.s["completed"], "Diajukan rekan", None, org.rekan)
        PersetujuanPenugasan.objects.create(
            workspace=org.ws, project=org.p1, issue=diajukan, pemohon=org.rekan, penerima=org.rekan, status="menunggu"
        )
        g = _kunci(_klien(org.staf).get(URL.format(slug=org.ws.slug)).json())
        assert "decide" not in g
        assert "team_overdue" not in g

    @pytest.mark.django_db
    def test_manager_melihat_antrean_dan_tim(self, org):
        hari = hari_ini_kantor()
        _tugas(org.p1, org.s["unstarted"], "Rekan lewat", hari - timedelta(days=2), org.rekan)
        _tugas(org.p1, org.s["unstarted"], "Manager lewat", hari - timedelta(days=2), org.manager)
        diajukan = _tugas(org.p1, org.s["completed"], "Diajukan rekan", None, org.rekan)
        PersetujuanPenugasan.objects.create(
            workspace=org.ws, project=org.p1, issue=diajukan, pemohon=org.rekan, penerima=org.rekan, status="menunggu"
        )
        data = _klien(org.manager).get(URL.format(slug=org.ws.slug)).json()
        g = _kunci(data)
        assert data["is_supervisor"] is True
        assert g["decide"]["count"] == 1
        assert g["decide"]["items"][0]["name"] == "Diajukan rekan"
        assert g["decide"]["top_project_id"] == str(org.p1.id)
        # Tugas manager sendiri ada di overdue_mine, bukan di tim.
        assert [i["name"] for i in g["team_overdue"]["items"]] == ["Rekan lewat"]
        assert [i["name"] for i in g["overdue_mine"]["items"]] == ["Manager lewat"]

    @pytest.mark.django_db
    def test_hanya_project_yang_dianggotai(self, org):
        hari = hari_ini_kantor()
        _tugas(org.asing, org.states[org.asing.id]["unstarted"], "Di project asing", hari - timedelta(days=1), org.staf)
        g = _kunci(_klien(org.staf).get(URL.format(slug=org.ws.slug)).json())
        assert g["overdue_mine"]["count"] == 0

    @pytest.mark.django_db
    def test_jumlah_penuh_item_dipotong_dan_kueri_tetap(self, org):
        hari = hari_ini_kantor()
        url = URL.format(slug=org.ws.slug)
        _tugas(org.p1, org.s["unstarted"], "Awal", hari - timedelta(days=1), org.manager)
        _klien(org.manager).get(url)  # pemanasan cache (setelan, dll.)
        with CaptureQueriesContext(connection) as sedikit:
            _klien(org.manager).get(url)
        for n in range(8):
            _tugas(org.p1, org.s["unstarted"], f"Banyak {n}", hari - timedelta(days=2 + n), org.manager)
        with CaptureQueriesContext(connection) as banyak:
            data = _klien(org.manager).get(url).json()
        g = _kunci(data)
        assert g["overdue_mine"]["count"] == 9
        assert len(g["overdue_mine"]["items"]) == 5
        assert len(banyak) == len(sedikit)

    @pytest.mark.django_db
    def test_kosong_tidak_error(self, org):
        data = _klien(org.staf).get(URL.format(slug=org.ws.slug)).json()
        assert data["total"] == 0
        assert all(g["count"] == 0 and g["items"] == [] for g in data["groups"])
