# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area C (bawaan tampilan) dari God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Aturan bawaan tampilan di plane/utils/aturan/area_tampilan.py.

Pola per aturan: tanpa baris database perilakunya sama dengan sebelum aturannya
ada; nilai lain mengubah payload API atau baris milik akun BARU; akun lama hanya
berubah lewat tombol "Apply to existing members".
"""

from datetime import date
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from plane.db.models import (
    Project,
    ProjectUserProperty,
    User,
    Workspace,
    WorkspaceHomePreference,
    WorkspaceMember,
)
from plane.license.api.views.aturan import InstanceRulesEndpoint
from plane.license.api.views.bawaan_member import InstanceMemberDefaultsApplyEndpoint, InstanceMemberDefaultsEndpoint
from plane.license.api.views.instance import InstanceEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.tests.contract.app.test_kinerja_app import _ambil, org  # noqa: F401 (fixture)
from plane.utils import aturan
from plane.utils.aturan import jenis
from plane.utils.aturan.area_tampilan import (
    ACTIVITY_DEFAULT_FILTERS,
    ATTENTION_ITEMS_PER_GROUP,
    DIVISION_REPORT_DEFAULT_PERIOD,
    HOME_WIDGETS,
    KPI_DEFAULT_PERIOD,
    KPI_LIST_SIZE,
    PEEK_MODE_DEFAULT,
    WORK_ITEMS_FIELDS,
    WORK_ITEMS_GROUP_BY,
    WORK_ITEMS_ORDER_BY,
    WORK_ITEMS_SHOW_EMPTY_GROUPS,
    WORK_ITEMS_SHOW_SUB_ISSUES,
)
from plane.utils.aturan.jenis import Rule, ke_teks, normalkan
from plane.utils.perhatian import _kelompok

URL_RULES = "/api/instances/rules/"

# Nilai kolom ProjectUserProperty sebelum aturan area C ada (db/models/issue.py di main).
FILTER_LAMA = {
    "layout": "kanban",
    "group_by": "state",
    "order_by": "-created_at",
    "type": None,
    "sub_issue": True,
    "show_empty_groups": True,
    "calendar_date_range": "",
}
PROPERTI_LAMA = dict.fromkeys(
    (
        "assignee",
        "attachment_count",
        "created_on",
        "due_date",
        "estimate",
        "key",
        "labels",
        "link",
        "priority",
        "start_date",
        "state",
        "sub_issue_count",
        "updated_on",
    ),
    True,
)


def _user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-tampilan-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


@pytest.fixture
def ruang(db, super_admin):
    ws = Workspace.objects.create(name="Uji", owner=super_admin, slug=f"uji-{uuid4().hex[:6]}")
    staf = _user("staf")
    WorkspaceMember.objects.create(workspace=ws, member=staf, role=15)
    project = Project.objects.create(name="Proyek", identifier=f"P{uuid4().hex[:4].upper()}", workspace=ws)
    return ws, staf, project


def _panggil(view, metode, aktor, badan=None, url=URL_RULES, **kw):
    pabrik = APIRequestFactory()
    request = getattr(pabrik, metode)(url, badan, format="json") if badan is not None else getattr(pabrik, metode)(url)
    force_authenticate(request, user=aktor)
    return view.as_view()(request, **kw)


def _atur(super_admin, nilai: dict):
    res = _panggil(InstanceRulesEndpoint, "patch", super_admin, {"values": nilai})
    assert res.status_code == status.HTTP_200_OK, res.data
    return res


def _terapkan(super_admin, bagian):
    res = _panggil(
        InstanceMemberDefaultsApplyEndpoint,
        "post",
        super_admin,
        {"sections": [bagian]},
        url="/api/instances/members/defaults/apply/",
    )
    assert res.status_code == status.HTTP_200_OK, res.data
    return res.data["updated"][bagian]


def _baris(kunci, nilai):
    rule = aturan.REGISTRI[kunci]
    InstanceConfiguration.objects.create(key=kunci, value=ke_teks(rule, nilai), category="PARADISE")


@pytest.mark.unit
class TestDaftarBerurutan:
    def _rule(self, **lain):
        dasar = {
            "key": "UJI",
            "kind": jenis.KEY_LIST,
            "default": ("a", "b"),
            "choices": (("a", "A"), ("b", "B"), ("c", "C")),
            "group": "display",
            "label": "x",
            "help": "y",
            "risk": "low",
        }
        return Rule(**{**dasar, **lain})

    def test_urutan_isian_dipertahankan(self):
        assert normalkan(self._rule(ordered=True), ["c", "a"]) == ("c", "a")
        assert normalkan(self._rule(ordered=True), "b,a") == ("b", "a")

    def test_tanpa_ordered_tetap_urutan_choices(self):
        assert normalkan(self._rule(), ["c", "a"]) == ("a", "c")

    def test_ordered_hanya_untuk_daftar(self):
        with pytest.raises(ValueError):
            Rule(
                key="UJI", kind=jenis.BOOL, default=True, group="display", label="x", help="y", risk="low", ordered=True
            )

    def test_aturan_work_items_menyebut_bagiannya(self, super_admin):
        butir = next(
            d for d in _panggil(InstanceRulesEndpoint, "get", super_admin).data["rules"] if d["key"] == HOME_WIDGETS
        )
        assert (butir["ordered"], butir["apply_section"]) == (True, "tampilan")


@pytest.mark.contract
class TestTampilanWorkItem:
    @pytest.mark.django_db
    def test_bawaan_tidak_berubah(self, ruang):
        ws, staf, project = ruang
        prop = ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        assert prop.display_filters == FILTER_LAMA
        assert prop.display_properties == PROPERTI_LAMA

    @pytest.mark.django_db
    def test_nilai_lain_berlaku_untuk_baris_baru_saja(self, super_admin, ruang):
        ws, staf, project = ruang
        lama = ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        res = _atur(
            super_admin,
            {
                WORK_ITEMS_GROUP_BY: "priority",
                WORK_ITEMS_ORDER_BY: "-priority",
                WORK_ITEMS_SHOW_SUB_ISSUES: False,
                WORK_ITEMS_SHOW_EMPTY_GROUPS: False,
                WORK_ITEMS_FIELDS: ["key", "state", "assignee"],
            },
        )
        butir = next(d for d in res.data["rules"] if d["key"] == WORK_ITEMS_GROUP_BY)
        assert (butir["store"], butir["apply_section"]) == ("member_default", "work_items")
        assert not InstanceConfiguration.objects.filter(key=WORK_ITEMS_GROUP_BY).exists()

        bawaan = _panggil(InstanceMemberDefaultsEndpoint, "get", super_admin, url="/api/instances/members/defaults/")
        assert bawaan.data["work_items"]["group_by"] == "priority"
        assert bawaan.data["work_items"]["layout"] == "kanban"

        lain = Project.objects.create(name="Lain", identifier=f"L{uuid4().hex[:4].upper()}", workspace=ws)
        baru = ProjectUserProperty.objects.create(user=staf, project=lain, workspace=ws)
        assert baru.display_filters == {
            **FILTER_LAMA,
            "group_by": "priority",
            "order_by": "-priority",
            "sub_issue": False,
            "show_empty_groups": False,
        }
        tampil = {k for k, v in baru.display_properties.items() if v}
        assert tampil == {"key", "state", "assignee"}
        assert baru.display_properties["approval_status"] is False

        lama.refresh_from_db()
        assert lama.display_filters == FILTER_LAMA
        assert lama.display_properties == PROPERTI_LAMA

    @pytest.mark.django_db
    def test_tanpa_kelompok_di_list(self, super_admin, ruang):
        ws, staf, project = ruang
        _panggil(
            InstanceMemberDefaultsEndpoint,
            "patch",
            super_admin,
            {"work_items": {"layout": "list"}},
            url="/api/instances/members/defaults/",
        )
        prop = ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        assert prop.display_filters == {**FILTER_LAMA, "layout": "list", "group_by": None}

    @pytest.mark.django_db
    def test_terapkan_ke_member_lama(self, super_admin, ruang):
        ws, staf, project = ruang
        prop = ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        prop.display_filters = {**prop.display_filters, "group_by": "labels", "order_by": "sort_order"}
        prop.display_properties = {**prop.display_properties, "labels": False}
        prop.save()
        _atur(super_admin, {WORK_ITEMS_GROUP_BY: "assignees", WORK_ITEMS_FIELDS: ["key", "labels"]})

        assert _terapkan(super_admin, "work_items") >= 1
        prop.refresh_from_db()
        assert prop.display_filters["group_by"] == "assignees"
        assert prop.display_filters["order_by"] == "-created_at"
        assert {k for k, v in prop.display_properties.items() if v} == {"key", "labels"}

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "badan",
        [
            {"work_items": {"group_by": "cycle"}},
            {"work_items": {"display_properties": ["key", "tidak_ada"]}},
            {"work_items": {"layout": "kanban", "lain": 1}},
        ],
    )
    def test_members_defaults_memvalidasi(self, super_admin, badan):
        res = _panggil(
            InstanceMemberDefaultsEndpoint, "patch", super_admin, badan, url="/api/instances/members/defaults/"
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST


def _widget_home(user, ws):
    from plane.app.views.workspace.home import WorkspaceHomePreferenceViewSet

    url = f"/api/workspaces/{ws.slug}/home-preferences/"
    res = _panggil(WorkspaceHomePreferenceViewSet, "get", user, url=url, slug=ws.slug)
    assert res.status_code == status.HTTP_200_OK
    return {b["key"]: (b["is_enabled"], b["sort_order"]) for b in res.data}


@pytest.mark.contract
class TestWidgetHome:
    @pytest.mark.django_db
    def test_bawaan_tidak_berubah(self, ruang):
        ws, staf, _ = ruang
        assert _widget_home(staf, ws) == {
            "needs_attention": (True, 2000),
            "quick_links": (True, 998),
            "recents": (True, 997),
            "my_stickies": (True, 996),
            "announcements": (True, 995),
            "changelog": (True, 994),
        }

    @pytest.mark.django_db
    def test_baris_yang_hilang_diberi_nomor_seperti_dulu(self, ruang):
        ws, staf, _ = ruang
        WorkspaceHomePreference.objects.create(user=staf, workspace=ws, key="needs_attention", sort_order=2000)
        assert _widget_home(staf, ws)["quick_links"] == (True, 999)

    @pytest.mark.django_db
    def test_widget_baru_masuk_di_bawah_widget_lama_changelog_terakhir(self, ruang):
        ws, staf, _ = ruang
        # Akun lama: hanya empat widget sebelum 2.13, nomor seperti dulu.
        for key, nomor in (("needs_attention", 2000), ("quick_links", 998), ("recents", 997), ("my_stickies", 996)):
            WorkspaceHomePreference.objects.create(user=staf, workspace=ws, key=key, sort_order=nomor)
        hasil = _widget_home(staf, ws)
        assert hasil["announcements"] == (True, 995)
        assert hasil["changelog"] == (True, 994)
        assert min(nomor for _, nomor in hasil.values()) == hasil["changelog"][1]

    @pytest.mark.django_db
    def test_nilai_lain_untuk_akun_baru_saja(self, super_admin, ruang):
        ws, staf, _ = ruang
        sebelum = _widget_home(staf, ws)
        _atur(super_admin, {HOME_WIDGETS: ["recents", "needs_attention"]})

        baru = _user("baru")
        WorkspaceMember.objects.create(workspace=ws, member=baru, role=15)
        assert _widget_home(baru, ws) == {
            "recents": (True, 2000),
            "needs_attention": (True, 998),
            "quick_links": (False, 997),
            "my_stickies": (False, 996),
            "announcements": (False, 995),
            "changelog": (False, 994),
        }
        assert _widget_home(staf, ws) == sebelum

    @pytest.mark.django_db
    def test_terapkan_ke_member_lama(self, super_admin, ruang):
        ws, staf, _ = ruang
        _widget_home(staf, ws)
        _atur(super_admin, {HOME_WIDGETS: ["my_stickies"]})

        assert _terapkan(super_admin, "tampilan") >= 4
        assert _widget_home(staf, ws) == {
            "my_stickies": (True, 2000),
            "needs_attention": (False, 998),
            "quick_links": (False, 997),
            "recents": (False, 996),
            "announcements": (False, 995),
            "changelog": (False, 994),
        }


@pytest.mark.contract
class TestAturanLangsung:
    @pytest.mark.django_db
    def test_baris_per_kelompok_perhatian(self):
        for i in range(7):
            _user(f"hitung{i}")
        qs = User.objects.filter(email__startswith="hitung").values("id")

        jumlah, baris = _kelompok(qs, ("email",), bangun=lambda b: b)
        assert (jumlah, len(baris)) == (7, 5)

        _baris(ATTENTION_ITEMS_PER_GROUP, 2)
        jumlah, baris = _kelompok(qs, ("email",), bangun=lambda b: b)
        assert (jumlah, len(baris)) == (7, 2)

    @pytest.mark.django_db
    def test_periode_dan_daftar_kpi(self, org, workspace):  # noqa: F811
        staf = org["staf_a"]
        data = _ambil(staf, workspace.slug).data
        assert data["period"]["key"] == "this_month"
        assert len(data["items"]["completed"]) == 4

        _baris(KPI_DEFAULT_PERIOD, "this_quarter")
        data = _ambil(staf, workspace.slug).data
        assert (data["period"]["key"], data["period"]["start"]) == ("this_quarter", date(2026, 10, 1))
        assert len(data["items"]["completed"]) == 5

        _baris(KPI_LIST_SIZE, 3)
        assert len(_ambil(staf, workspace.slug).data["items"]["completed"]) == 3
        # Periode yang dikirim web tetap menang.
        assert _ambil(staf, workspace.slug, periode="this_week").data["period"]["key"] == "this_week"

    @pytest.mark.django_db
    def test_periode_laporan_divisi(self, workspace, create_user):
        klien = APIClient()
        klien.force_authenticate(user=create_user)
        url = f"/api/workspaces/{workspace.slug}/divisi-dashboard/laporan/"
        assert klien.get(url).data["period"]["key"] == "7d"
        _baris(DIVISION_REPORT_DEFAULT_PERIOD, "last_month")
        assert klien.get(url).data["period"]["key"] == "last_month"

    @pytest.mark.django_db
    def test_aturan_web_area_c_ikut_paradise_rules(self, super_admin):
        res = _panggil(InstanceEndpoint, "get", _user("tamu"), url="/api/instances/")
        rules = res.data["config"]["paradise_rules"]
        assert rules[ACTIVITY_DEFAULT_FILTERS] == ["ACTIVITY", "COMMENT", "STATE", "ASSIGNEE"]
        assert rules[PEEK_MODE_DEFAULT] == "side-peek"
        assert HOME_WIDGETS not in rules and KPI_LIST_SIZE not in rules

        # Lewat endpoint: ia membuang cache /api/instances/, baris tulis tangan tidak.
        _atur(super_admin, {PEEK_MODE_DEFAULT: "modal"})
        res = _panggil(InstanceEndpoint, "get", _user("tamu"), url="/api/instances/")
        assert res.data["config"]["paradise_rules"][PEEK_MODE_DEFAULT] == "modal"
