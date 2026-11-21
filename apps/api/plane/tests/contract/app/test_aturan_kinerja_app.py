# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode cakupan KPI
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""KPI_TEAM_MIN_LEVEL dan KPI_WORKSPACE_ADMINS_SEE_ALL dijaga API (`lingkup_untuk`).

Bawaan = test_kinerja_app.py apa adanya: leader dan supervisor membuka KPI
departemennya, admin workspace membuka seluruh organisasi. Diubah di God Mode:
permintaan yang tadinya 200 dijawab 403, dan pemilih lingkup ikut menyempit.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import TINGKAT_LEADER
from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_kinerja_app import URL_LINGKUP, _ambil, _orang, org  # noqa: F401 (fixture org)
from plane.utils.aturan.area_visibilitas import KPI_TEAM_MIN_LEVEL, KPI_WORKSPACE_ADMINS_SEE_ALL


def _setel(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": str(nilai), "category": "PARADISE"})


def _departemen(user, org, workspace):
    return _ambil(user, workspace.slug, lingkup="departemen", id=str(org["gudang"].id)).status_code


def _pilihan(user, workspace):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien.get(URL_LINGKUP.format(slug=workspace.slug)).data


@pytest.mark.contract
class TestJenjangKpiTim:
    def test_bawaan_leader_dan_supervisor_membuka_departemen(self, org, workspace):
        leader = _orang(workspace, "leader-gudang", TINGKAT_LEADER, org["gudang"])
        assert _departemen(leader, org, workspace) == status.HTTP_200_OK
        assert _departemen(org["spv"], org, workspace) == status.HTTP_200_OK

    def test_supervisor_ke_atas_leader_hanya_dirinya(self, org, workspace):
        leader = _orang(workspace, "leader-gudang", TINGKAT_LEADER, org["gudang"])
        _setel(KPI_TEAM_MIN_LEVEL, 20)
        assert _departemen(leader, org, workspace) == status.HTTP_403_FORBIDDEN
        assert _ambil(leader, workspace.slug, lingkup="orang", id=str(org["staf_a"].id)).status_code == 403
        assert _pilihan(leader, workspace)["departments"] == []
        assert _ambil(leader, workspace.slug, lingkup="saya").status_code == status.HTTP_200_OK
        assert _departemen(org["spv"], org, workspace) == status.HTTP_200_OK

    def test_manager_ke_atas_supervisor_hanya_dirinya_manager_tetap(self, org, workspace):
        _setel(KPI_TEAM_MIN_LEVEL, 30)
        assert _departemen(org["spv"], org, workspace) == status.HTTP_403_FORBIDDEN
        assert _pilihan(org["spv"], workspace)["people"] == []
        manager = org["manager"]
        assert _ambil(manager, workspace.slug, lingkup="divisi", id=str(org["ops"].id)).status_code == 200
        assert _departemen(manager, org, workspace) == status.HTTP_200_OK
        assert _ambil(org["direktur"], workspace.slug, lingkup="organisasi").status_code == 200


@pytest.mark.contract
class TestAdminWorkspaceKpi:
    def test_bawaan_admin_workspace_seluruh_organisasi(self, org, workspace, create_user):
        assert _ambil(create_user, workspace.slug, lingkup="organisasi").status_code == status.HTTP_200_OK
        assert _pilihan(create_user, workspace)["organisation"] is True

    def test_dimatikan_admin_workspace_mengikuti_penempatannya(self, org, workspace, create_user):
        _setel(KPI_WORKSPACE_ADMINS_SEE_ALL, 0)
        assert _ambil(create_user, workspace.slug, lingkup="organisasi").status_code == status.HTTP_403_FORBIDDEN
        assert _departemen(create_user, org, workspace) == status.HTTP_403_FORBIDDEN
        assert _pilihan(create_user, workspace)["organisation"] is False
        assert _ambil(create_user, workspace.slug, lingkup="saya").status_code == status.HTTP_200_OK
        # Direktur tidak terpengaruh: jangkauannya dari jenjang, bukan dari peran admin.
        assert _ambil(org["direktur"], workspace.slug, lingkup="organisasi").status_code == 200
