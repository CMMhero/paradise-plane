# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Needs attention direktur hanya tugas buatan manager
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kelompok `team_overdue` di Needs attention untuk direktur.

Direktur (jangkauan seluruh organisasi) hanya melihat tugas terlambat yang DIBUAT
manager ke atas, jadi tugas buatan supervisor dan staf dilewati. Jenjang minimum
pembuatnya diatur di God Mode (ATTENTION_ORG_MIN_CREATOR_LEVEL, bawaan 30).
Supervisor dan manager tidak terpengaruh: mereka melihat seluruh timnya.
"""

from datetime import timedelta

import pytest

from plane.db.models import TINGKAT_DIREKTUR, TINGKAT_MANAGER, TINGKAT_SUPERVISOR
from plane.db.penempatan import setel_penempatan
from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_perhatian_app import (  # noqa: F401 (fixture org)
    URL,
    Issue,
    IssueAssignee,
    _klien,
    _kunci,
    _user,
    org,
)
from plane.utils import aturan
from plane.utils.aturan.area_visibilitas import ATTENTION_ORG_MIN_CREATOR_LEVEL
from plane.utils.setelan_instance import hari_ini_kantor

pytestmark = pytest.mark.contract


def _atur(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": aturan.ke_teks(aturan.REGISTRI[kunci], nilai), "category": "PARADISE"}
    )


def _tugas_buatan(org, nama, pembuat):
    """Tugas terlambat milik `org.staf`, dibuat oleh `pembuat`."""
    issue = Issue(
        name=nama,
        workspace=org.ws,
        project=org.p1,
        state=org.s["unstarted"],
        target_date=hari_ini_kantor() - timedelta(days=3),
    )
    issue.save(created_by_id=pembuat.id)
    IssueAssignee.objects.create(issue=issue, assignee=org.staf, project=org.p1, workspace=org.ws)
    return issue


@pytest.fixture
def dunia(org):
    org.spv = _user("spv", org.ws)
    setel_penempatan(org.ws, org.spv, TINGKAT_SUPERVISOR, [org.dept.id], [])
    org.dir = _user("dir", org.ws)
    setel_penempatan(org.ws, org.dir, TINGKAT_DIREKTUR, [], [])
    _tugas_buatan(org, "Buatan manager", org.manager)
    _tugas_buatan(org, "Buatan supervisor", org.spv)
    _tugas_buatan(org, "Buatan staf", org.rekan)
    return org


def _nama_tim(user, org):
    data = _klien(user).get(URL.format(slug=org.ws.slug)).json()
    grup = _kunci(data).get("team_overdue")
    return sorted(i["name"] for i in grup["items"]) if grup else []


@pytest.mark.django_db
class TestPerhatianDirektur:
    def test_bawaan_direktur_hanya_buatan_manager(self, dunia):
        assert aturan.get_int(ATTENTION_ORG_MIN_CREATOR_LEVEL) == TINGKAT_MANAGER
        assert _nama_tim(dunia.dir, dunia) == ["Buatan manager"]

    def test_jenjang_supervisor_ikut_masuk(self, dunia):
        _atur(ATTENTION_ORG_MIN_CREATOR_LEVEL, TINGKAT_SUPERVISOR)
        assert _nama_tim(dunia.dir, dunia) == ["Buatan manager", "Buatan supervisor"]

    def test_jenjang_member_menampilkan_semuanya(self, dunia):
        _atur(ATTENTION_ORG_MIN_CREATOR_LEVEL, 10)
        assert _nama_tim(dunia.dir, dunia) == ["Buatan manager", "Buatan staf", "Buatan supervisor"]

    def test_jumlah_kelompok_ikut_tersaring(self, dunia):
        data = _klien(dunia.dir).get(URL.format(slug=dunia.ws.slug)).json()
        assert _kunci(data)["team_overdue"]["count"] == 1

    def test_manager_tetap_melihat_seluruh_timnya(self, dunia):
        # Manager bukan jangkauan seluruh organisasi: aturan direktur tidak menyentuhnya.
        assert _nama_tim(dunia.manager, dunia) == ["Buatan manager", "Buatan staf", "Buatan supervisor"]
