# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode siapa yang dikabari saat disebut
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""MENTION_NOTIFY_REACH dijaga API (`dalam_jangkauan`, dipakai notifikasi dan pemilih @).

Dunia sama dengan test_kabar_lebur_sebutan_app.py: `cici` anggota project, `luar`
anggota workspace saja, `sekre` sekretaris (35). Sinkron direktur menjadikan
sekretaris anggota project; keanggotaannya dinonaktifkan di sini supaya yang diuji
memang jalur jangkauan seluruh organisasi (project yang belum tersinkron).
"""

import pytest
from rest_framework.test import APIClient

from plane.db.models import ProjectMember
from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_kabar_lebur_sebutan_app import org  # noqa: F401 (fixture)
from plane.utils.aturan.area_visibilitas import MENTION_NOTIFY_REACH
from plane.utils.jangkauan_sebutan import dalam_jangkauan


def _setel(nilai):
    InstanceConfiguration.objects.update_or_create(
        key=MENTION_NOTIFY_REACH, defaults={"value": nilai, "category": "PARADISE"}
    )


def _dikabari(org):
    """{user_id: dikabari} dari pemilih @ (entity-search), seperti yang dilihat web."""
    klien = APIClient()
    klien.force_authenticate(user=org.bob)
    res = klien.get(
        f"/api/workspaces/{org.ws.slug}/entity-search/",
        {"query_type": "user_mention", "project_id": str(org.project.id), "query": "", "count": 50},
    )
    assert res.status_code == 200, res.data
    return {u["member__id"]: u["dikabari"] for u in res.data["user_mention"]}


@pytest.fixture
def org_tanpa_sinkron(org):
    ProjectMember.objects.filter(project=org.project, member=org.sekre).update(is_active=False)
    return org


def _ids(org):
    return [org.cici.id, org.luar.id, org.sekre.id]


@pytest.mark.contract
@pytest.mark.django_db
class TestJangkauanSebutan:
    def test_bawaan_project_dan_jangkauan_seluruh_organisasi(self, org_tanpa_sinkron):
        org = org_tanpa_sinkron
        assert dalam_jangkauan(org.project.id, _ids(org)) == {str(org.cici.id), str(org.sekre.id)}
        peta = _dikabari(org)
        assert (peta[org.cici.id], peta[org.luar.id], peta[org.sekre.id]) == (True, False, True)

    def test_hanya_anggota_project(self, org_tanpa_sinkron):
        org = org_tanpa_sinkron
        _setel("project")
        assert dalam_jangkauan(org.project.id, _ids(org)) == {str(org.cici.id)}
        peta = _dikabari(org)
        assert (peta[org.cici.id], peta[org.luar.id], peta[org.sekre.id]) == (True, False, False)

    def test_seluruh_anggota_workspace(self, org_tanpa_sinkron):
        org = org_tanpa_sinkron
        _setel("workspace")
        assert dalam_jangkauan(org.project.id, _ids(org)) == {str(org.cici.id), str(org.luar.id), str(org.sekre.id)}
        assert all(_dikabari(org)[u] for u in _ids(org))
