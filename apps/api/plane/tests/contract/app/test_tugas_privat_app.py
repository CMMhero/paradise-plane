# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tugas privat (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tugas privat hanya terlihat oleh assignee, pembuat, atasan langsung assignee, dan Super Admin.

Bentuk uji:

    SALES -> SMT1 (P1)        OPS -> OPS1 (P3)

    assignee, pembuat, rekan   staf SMT1
    sup                        supervisor SMT1
    manager                    manager divisi SALES
    direktur                   direktur (tanpa tempat, `divisi_diawasi` = semua project)
    admin_ws                   admin workspace, anggota eksplisit P1, tanpa penempatan
    sa                         Super Admin
    luar                       staf OPS1, anggota eksplisit P1

Direktur melihat karena `divisi_diawasi` memberinya semua project dan semua
anggota P1 yang jenjangnya lebih rendah adalah bawahannya (`_bawahan_ids`).
"""

import json
from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.app.serializers import IssueActivitySerializer
from plane.bgtasks.notification_task import notifications
from plane.db.models import (
    APIToken,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueActivity,
    IssueAssignee,
    IssueSubscriber,
    JabatanOrganisasi,
    Notification,
    Project,
    ProjectMember,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    WorkspaceMember,
)
from plane.db.superadmin import sinkronkan_super_admin
from plane.license.models import Instance, InstanceAdmin
from plane.tests.contract.app.test_persetujuan_manager_app import _klien, _states, _user
from plane.utils.preferensi_email import SAKLAR_NOTIFIKASI

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_DETAIL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
URL_SUB = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/sub-issues/"
URL_KOMENTAR = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/comments/"
URL_CARI = "/api/workspaces/{slug}/search/"
URL_CARI_ENTITAS = "/api/workspaces/{slug}/entity-search/"
URL_CARI_PROJECT = "/api/workspaces/{slug}/projects/{project_id}/search-issues/"
URL_KABAR = "/api/workspaces/{slug}/users/notifications/"
URL_KABAR_BELUM = "/api/workspaces/{slug}/users/notifications/unread/"
URL_DASHBOARD = "/api/workspaces/{slug}/divisi-dashboard/"
URL_LAPORAN = "/api/workspaces/{slug}/divisi-dashboard/laporan/"
URL_V1_ISSUES = "/api/v1/workspaces/{slug}/projects/{project_id}/issues/"
URL_V1_DETAIL = "/api/v1/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"

MELIHAT = ["assignee", "pembuat", "sup", "manager", "direktur", "sa"]
TIDAK_MELIHAT = ["rekan", "admin_ws", "luar"]
SEMUA = MELIHAT + TIDAK_MELIHAT


def _tempatkan(o, user, tingkat, departemen=None, divisi=None):
    JabatanOrganisasi.objects.create(workspace=o.ws, member=user, tingkat=tingkat, departemen=departemen, divisi=divisi)


def _anggota(o, user, project, role):
    ProjectMember.objects.update_or_create(
        project=project, member=user, workspace=o.ws, defaults={"role": role, "is_active": True}
    )


def _tugas(o, nama, pembuat, assignee=(), privat=False, **kolom):
    issue = Issue(name=nama, workspace=o.ws, project=o.p1, state=o.states["started"], is_private=privat, **kolom)
    issue.save()
    Issue.objects.filter(pk=issue.pk).update(created_by=pembuat)
    for user in assignee:
        IssueAssignee.objects.create(issue=issue, assignee=user, project=o.p1, workspace=o.ws)
    issue.refresh_from_db()
    return issue


@pytest.fixture
def o(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.p1 = Project.objects.create(name="SMT1 Board", identifier="P1", workspace=workspace, created_by=create_user)
    o.p3 = Project.objects.create(name="OPS1 Board", identifier="P3", workspace=workspace, created_by=create_user)
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.ops = Divisi.objects.create(workspace=workspace, kode="OPS", nama="Operations")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="Sales Team 1")
    o.ops1 = Departemen.objects.create(workspace=workspace, divisi=o.ops, kode="OPS1", nama="Ops Team 1")
    DepartemenProject.objects.create(workspace=workspace, departemen=o.smt1, project=o.p1)
    DepartemenProject.objects.create(workspace=workspace, departemen=o.ops1, project=o.p3)

    o.user = {nama: _user(nama, workspace) for nama in SEMUA}
    for nama in ("assignee", "pembuat", "rekan"):
        _tempatkan(o, o.user[nama], TINGKAT_MEMBER, departemen=o.smt1)
    _tempatkan(o, o.user["sup"], TINGKAT_SUPERVISOR, departemen=o.smt1)
    _tempatkan(o, o.user["manager"], TINGKAT_MANAGER, divisi=o.sales)
    _tempatkan(o, o.user["direktur"], TINGKAT_DIREKTUR)
    _tempatkan(o, o.user["luar"], TINGKAT_MEMBER, departemen=o.ops1)
    _anggota(o, o.user["luar"], o.p1, 15)
    WorkspaceMember.objects.filter(workspace=workspace, member=o.user["admin_ws"]).update(role=20)
    _anggota(o, o.user["admin_ws"], o.p1, 20)

    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-privat-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    InstanceAdmin.objects.create(instance=instance, user=o.user["sa"], role=20)
    sinkronkan_super_admin(o.user["sa"].id)

    o.states = _states(workspace, o.p1)
    o.induk = _tugas(o, "Induk umum", o.user["pembuat"], [o.user["assignee"]])
    o.nama = f"Rahasia {uuid4().hex[:6]}"
    o.tugas = _tugas(o, o.nama, o.user["pembuat"], [o.user["assignee"]], privat=True, parent=o.induk)
    return o


def _ada(respon, issue):
    assert respon.status_code == status.HTTP_200_OK, respon.content[:300]
    return str(issue.id) in respon.content.decode()


@pytest.mark.contract
class TestLihatPerPeran:
    @pytest.mark.parametrize("peran", SEMUA)
    def test_daftar_project(self, o, peran):
        respon = _klien(o.user[peran]).get(URL_ISSUES.format(slug=o.ws.slug, project_id=o.p1.id))
        assert _ada(respon, o.tugas) is (peran in MELIHAT)
        assert _ada(respon, o.induk)

    @pytest.mark.parametrize("peran", SEMUA)
    def test_detail_404_bagi_yang_tidak_berhak(self, o, peran):
        respon = _klien(o.user[peran]).get(URL_DETAIL.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=o.tugas.id))
        harapan = status.HTTP_200_OK if peran in MELIHAT else status.HTTP_404_NOT_FOUND
        assert respon.status_code == harapan

    @pytest.mark.parametrize("peran", SEMUA)
    def test_pencarian(self, o, peran):
        klien = _klien(o.user[peran])
        terlihat = peran in MELIHAT
        cari = klien.get(URL_CARI.format(slug=o.ws.slug), {"search": o.nama, "entities": "issue"})
        assert _ada(cari, o.tugas) is terlihat
        pemilih = klien.get(
            URL_CARI_ENTITAS.format(slug=o.ws.slug),
            {"query": o.nama, "query_type": "issue", "project_id": str(o.p1.id)},
        )
        assert _ada(pemilih, o.tugas) is terlihat
        project = klien.get(URL_CARI_PROJECT.format(slug=o.ws.slug, project_id=o.p1.id), {"search": o.nama})
        assert _ada(project, o.tugas) is terlihat

    @pytest.mark.parametrize("peran", SEMUA)
    def test_daftar_sub_item(self, o, peran):
        respon = _klien(o.user[peran]).get(URL_SUB.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=o.induk.id))
        assert _ada(respon, o.tugas) is (peran in MELIHAT)

    @pytest.mark.parametrize("peran", SEMUA)
    def test_api_v1(self, o, peran):
        token = APIToken.objects.create(user=o.user[peran], label=f"uji-{uuid4().hex[:6]}", user_type=0)
        klien = APIClient()
        klien.credentials(HTTP_X_API_KEY=token.token)
        daftar = klien.get(URL_V1_ISSUES.format(slug=o.ws.slug, project_id=o.p1.id))
        assert _ada(daftar, o.tugas) is (peran in MELIHAT)
        detail = klien.get(URL_V1_DETAIL.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=o.tugas.id))
        assert detail.status_code == (status.HTTP_200_OK if peran in MELIHAT else status.HTTP_404_NOT_FOUND)

    @pytest.mark.parametrize("peran", TIDAK_MELIHAT)
    def test_sub_sumber_ikut_404(self, o, peran):
        respon = _klien(o.user[peran]).get(URL_KOMENTAR.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=o.tugas.id))
        assert respon.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.contract
class TestTanpaAssignee:
    def test_hanya_pembuat_dan_super_admin(self, o):
        tugas = _tugas(o, "Catatan pribadi", o.user["pembuat"], privat=True)
        url = URL_DETAIL.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=tugas.id)
        for peran in SEMUA:
            harapan = status.HTTP_200_OK if peran in ("pembuat", "sa") else status.HTTP_404_NOT_FOUND
            assert _klien(o.user[peran]).get(url).status_code == harapan, peran


@pytest.fixture
def _saklar_hidup():
    semua = dict.fromkeys(SAKLAR_NOTIFIKASI, True)
    with (
        mock.patch("plane.bgtasks.notification_task.saklar_untuk", lambda _u: dict(semua)),
        mock.patch("plane.utils.sinyal_data.siarkan_notifikasi_baris"),
        mock.patch("plane.utils.kanal_sistem.siarkan"),
        mock.patch("plane.utils.kartu_obrolan.siarkan"),
    ):
        yield


@pytest.mark.contract
class TestNotifikasi:
    def test_hanya_yang_boleh_melihat_dikabari(self, o, _saklar_hidup):
        for user in o.user.values():
            IssueSubscriber.objects.create(issue=o.tugas, subscriber=user, project=o.p1, workspace=o.ws)
        pelaku = o.user["assignee"]
        aktivitas = IssueActivity.objects.create(
            issue=o.tugas,
            project=o.p1,
            workspace=o.ws,
            actor=pelaku,
            field="priority",
            verb="updated",
            old_value="none",
            new_value="high",
            comment="updated the priority to",
            epoch=1,
        )
        notifications(
            type="issue.activity.updated",
            issue_id=str(o.tugas.id),
            project_id=str(o.p1.id),
            actor_id=str(pelaku.id),
            subscriber=False,
            issue_activities_created=json.dumps(
                list(IssueActivitySerializer([aktivitas], many=True).data), default=str
            ),
            requested_data=json.dumps({"priority": "high"}),
            current_instance=json.dumps({"priority": "none"}),
        )
        penerima = set(Notification.objects.filter(entity_identifier=o.tugas.id).values_list("receiver_id", flat=True))
        harapan = {o.user[p].id for p in MELIHAT if p != "assignee"}
        assert penerima == harapan

    def test_kabar_lama_disembunyikan(self, o):
        rekan = o.user["rekan"]
        Notification.objects.create(
            workspace=o.ws,
            project=o.p1,
            receiver=rekan,
            entity_identifier=o.tugas.id,
            entity_name="issue",
            sender="in_app:issue_activities:subscribed",
            data={"issue": {"id": str(o.tugas.id), "name": o.nama}},
        )
        klien = _klien(rekan)
        assert o.nama not in klien.get(URL_KABAR.format(slug=o.ws.slug)).content.decode()
        belum = klien.get(URL_KABAR_BELUM.format(slug=o.ws.slug)).json()
        assert belum["total_unread_notifications_count"] == 0


@pytest.mark.contract
class TestUbahPrivat:
    def _patch(self, o, peran, issue, nilai):
        return _klien(o.user[peran]).patch(
            URL_DETAIL.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=issue.id),
            {"is_private": nilai},
            format="json",
        )

    def test_buat_privat_dari_modal(self, o):
        respon = _klien(o.user["assignee"]).post(
            URL_ISSUES.format(slug=o.ws.slug, project_id=o.p1.id),
            {"name": "Baru privat", "is_private": True},
            format="json",
        )
        assert respon.status_code == status.HTTP_201_CREATED, respon.content[:300]
        assert respon.json()["is_private"] is True
        url = URL_DETAIL.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=respon.json()["id"])
        assert _klien(o.user["rekan"]).get(url).status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize("peran", ["pembuat", "assignee", "sup", "sa"])
    def test_yang_boleh_mengubah_boleh_mengganti(self, o, peran):
        assert self._patch(o, peran, o.induk, True).status_code == status.HTTP_200_OK
        o.induk.refresh_from_db()
        assert o.induk.is_private is True

    @pytest.mark.parametrize("peran", ["rekan", "luar"])
    def test_yang_tidak_terlibat_ditolak_walau_gerbang_mati(self, o, peran):
        assert self._patch(o, peran, o.induk, True).status_code == status.HTTP_403_FORBIDDEN
        o.induk.refresh_from_db()
        assert o.induk.is_private is False

    @pytest.mark.parametrize("url", [URL_DETAIL, URL_V1_DETAIL])
    @pytest.mark.parametrize("peran", ["pembuat", "sa"])
    def test_tugas_selesai_terkunci_untuk_privat_juga(self, o, peran, url):
        Issue.objects.filter(pk=o.induk.pk).update(state=o.states["completed"])
        respon = _klien(o.user[peran]).patch(
            url.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=o.induk.id), {"is_private": True}, format="json"
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN, respon.content[:300]
        o.induk.refresh_from_db()
        assert o.induk.is_private is False

    def test_tugas_privat_tak_terlihat_tidak_bisa_dibuka(self, o):
        assert self._patch(o, "rekan", o.tugas, False).status_code == status.HTTP_404_NOT_FOUND
        o.tugas.refresh_from_db()
        assert o.tugas.is_private is True


@pytest.mark.contract
class TestAgregatTetapMenghitung:
    def test_dashboard_divisi_menghitung_tugas_privat(self, o):
        tersembunyi = _tugas(o, "Privat pembuat", o.user["pembuat"], privat=True)
        klien = _klien(o.user["manager"])
        url_detail = URL_DETAIL.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=tersembunyi.id)
        assert klien.get(url_detail).status_code == status.HTTP_404_NOT_FOUND
        data = klien.get(URL_DASHBOARD.format(slug=o.ws.slug)).data
        sales = next(d for d in data["divisions"] if d["name"] == "Sales")
        assert sales["issues_active"] == 3

    def test_laporan_selesai_menghitung_tapi_tidak_mendaftar(self, o):
        selesai = _tugas(o, "Privat selesai", o.user["pembuat"], privat=True)
        Issue.objects.filter(pk=selesai.pk).update(state=o.states["completed"], completed_at=timezone.now())
        data = _klien(o.user["manager"]).get(URL_LAPORAN.format(slug=o.ws.slug)).data
        assert data["totals"]["completed"] == 1
        assert str(selesai.id) not in {i["id"] for i in data["items"]}
