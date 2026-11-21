# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode angka direktur dan pilih departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""ORG_VIEW_LEADER_CREATED_ONLY dan ASK_UNPLACED_TO_CHOOSE_DEPARTMENT dijaga API.

1. Angka direktur (Dashboard Divisi, laporan direktur) bawaannya hanya dari tugas
   buatan Supervisor ke atas (statistik_pimpinan.py). Dimatikan: tugas buatan staf
   ikut dihitung. Supervisor tidak pernah terpengaruh.
2. Staf tanpa penempatan bawaannya diminta memilih departemen. Dimatikan: GET
   menjawab tidak perlu dan POST ditolak, jadi tidak ada penempatan mandiri.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks.direktur_digest_task import DataWorkspace
from plane.db.models import (
    Departemen,
    Divisi,
    Issue,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    State,
    TINGKAT_DIREKTUR,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)
from plane.license.models import InstanceConfiguration
from plane.utils.aturan.area_visibilitas import ASK_UNPLACED_TO_CHOOSE_DEPARTMENT, ORG_VIEW_LEADER_CREATED_ONLY
from plane.utils.setelan_instance import hari_ini_kantor

URL_DASBOR = "/api/workspaces/{slug}/divisi-dashboard/"
URL_PENEMPATAN = "/api/workspaces/{slug}/penempatan-saya/"


def _matikan(kunci):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": "0", "category": "PARADISE"})


def _orang(workspace, nama, tingkat=None):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{nama}-{unik}@plane.so", username=f"{nama}_{unik}", display_name=nama)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    if tingkat is not None:
        JabatanOrganisasi.objects.create(workspace=workspace, member=user, tingkat=tingkat)
    return user


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


@pytest.fixture
def dunia(db, workspace):
    """Satu project, dua tugas lewat tenggat 10 hari: satu buatan staf, satu buatan supervisor."""
    d = type("D", (), {})()
    d.ws = workspace
    d.direktur = _orang(workspace, "dir", TINGKAT_DIREKTUR)
    d.sup = _orang(workspace, "sup", TINGKAT_SUPERVISOR)
    d.staf = _orang(workspace, "staf")
    d.project = Project.objects.create(name="Gudang", identifier="GDA", workspace=workspace)
    for user in (d.direktur, d.sup):
        ProjectMember.objects.update_or_create(
            project=d.project, member=user, workspace=workspace, defaults={"role": 20, "is_active": True}
        )
    belum = State.objects.create(
        name="Todo", group="unstarted", color="#000000", project=d.project, workspace=workspace, default=True
    )
    lewat = hari_ini_kantor() - timedelta(days=10)
    for pembuat in (d.staf, d.sup):
        issue = Issue(name=f"Lewat {pembuat.display_name}", workspace=workspace, project=d.project, state=belum)
        issue.save()
        Issue.objects.filter(pk=issue.pk).update(created_by=pembuat, target_date=lewat)
    return d


def _terlambat_di_dasbor(user, d):
    res = _klien(user).get(URL_DASBOR.format(slug=d.ws.slug))
    assert res.status_code == status.HTTP_200_OK, res.data
    return res.data["totals"]["issues_overdue"]


def _terlambat_di_laporan(d):
    sejak = timezone.now() - timedelta(days=1)
    return DataWorkspace(d.ws.id, hari_ini_kantor(), sejak, hari_macet=7, hari_ke_depan=7).angka[d.project.id].lewat


@pytest.mark.contract
class TestAngkaDirektur:
    def test_bawaan_hanya_buatan_supervisor_ke_atas(self, dunia):
        assert _terlambat_di_dasbor(dunia.direktur, dunia) == 1
        assert _terlambat_di_laporan(dunia) == 1
        assert _terlambat_di_dasbor(dunia.sup, dunia) == 2

    def test_dimatikan_buatan_staf_ikut_dihitung(self, dunia):
        _matikan(ORG_VIEW_LEADER_CREATED_ONLY)
        assert _terlambat_di_dasbor(dunia.direktur, dunia) == 2
        assert _terlambat_di_laporan(dunia) == 2
        assert _terlambat_di_dasbor(dunia.sup, dunia) == 2


@pytest.mark.contract
class TestPilihDepartemen:
    @pytest.fixture
    def tanpa_tempat(self, db, workspace):
        divisi = Divisi.objects.create(workspace=workspace, kode="D8", nama="Divisi 8")
        departemen = Departemen.objects.create(workspace=workspace, divisi=divisi, kode="DP8", nama="Dept 8")
        return _orang(workspace, "baru"), departemen

    def test_bawaan_diminta_memilih(self, workspace, tanpa_tempat):
        user, departemen = tanpa_tempat
        assert _klien(user).get(URL_PENEMPATAN.format(slug=workspace.slug)).data["perlu_pilih"] is True
        res = _klien(user).post(
            URL_PENEMPATAN.format(slug=workspace.slug), {"departemen_id": str(departemen.id)}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED, res.data

    def test_dimatikan_tidak_diminta_dan_post_ditolak(self, workspace, tanpa_tempat):
        user, departemen = tanpa_tempat
        _matikan(ASK_UNPLACED_TO_CHOOSE_DEPARTMENT)
        assert _klien(user).get(URL_PENEMPATAN.format(slug=workspace.slug)).data == {
            "perlu_pilih": False,
            "departemen": [],
        }
        res = _klien(user).post(
            URL_PENEMPATAN.format(slug=workspace.slug), {"departemen_id": str(departemen.id)}, format="json"
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert not JabatanOrganisasi.objects.filter(workspace=workspace, member=user).exists()
