# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: halaman Views workspace
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Halaman Views workspace: view departemen, visibilitas, urutan Approval.

Yang dijaga:

1. `GET /workspaces/<slug>/project-views/` hanya mengirim view departemen yang
   juga terlihat di halaman Views departemen itu sendiri: anggota aktif, project
   hidup dengan Views menyala, view publik atau milik sendiri, tamu terbatas cuma
   miliknya. Tidak ada kebocoran view privat orang lain atau departemen lain.
2. `access` (privat/publik) bisa diisi saat membuat dan diubah pemiliknya,
   untuk view workspace maupun departemen; orang lain tetap ditolak mengubahnya.
3. `order_by=approval_status` mengurutkan menurut status persetujuan TERBARU,
   tanpa persetujuan selalu di akhir; baris work item workspace membawa
   `approval_status`.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueView,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.order_queryset import order_issue_queryset

# ---------------------------------------------------------------------------
# Pembantu
# ---------------------------------------------------------------------------


def _user(prefix, workspace, role=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _anggota(project, user, role=15, aktif=True):
    ProjectMember.objects.update_or_create(
        project=project, member=user, workspace=project.workspace, defaults={"role": role, "is_active": aktif}
    )


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _view(workspace, pemilik, project=None, akses=1, nama="View"):
    return IssueView.objects.create(name=nama, workspace=workspace, project=project, owned_by=pemilik, access=akses)


class _Org:
    pass


@pytest.fixture
def org(db):
    o = _Org()
    unik = uuid4().hex[:6]
    o.pemilik_ws = User.objects.create(email=f"own-{unik}@plane.so", username=f"own_{unik}")
    o.ws = Workspace.objects.create(name="WS", slug=f"ws-{unik}", owner=o.pemilik_ws)
    WorkspaceMember.objects.create(workspace=o.ws, member=o.pemilik_ws, role=20)
    o.saya = _user("saya", o.ws)
    o.rekan = _user("rekan", o.ws)
    o.p_saya = Project.objects.create(name="Dep A", identifier=f"A{unik[:3]}", workspace=o.ws)
    o.p_lain = Project.objects.create(name="Dep B", identifier=f"B{unik[:3]}", workspace=o.ws)
    _anggota(o.p_saya, o.saya)
    _anggota(o.p_saya, o.rekan)
    _anggota(o.p_lain, o.rekan)
    return o


def _ids(res):
    return {row["id"] for row in res.json()}


# ---------------------------------------------------------------------------
# 1. View departemen di halaman Views workspace
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestViewDepartemenDiWorkspace:
    url = "/api/workspaces/{slug}/project-views/"

    @pytest.mark.django_db
    def test_hanya_view_yang_boleh_dibuka(self, org):
        publik_rekan = _view(org.ws, org.rekan, org.p_saya, akses=1)
        privat_saya = _view(org.ws, org.saya, org.p_saya, akses=0)
        privat_rekan = _view(org.ws, org.rekan, org.p_saya, akses=0)
        dep_lain = _view(org.ws, org.rekan, org.p_lain, akses=1)
        view_workspace = _view(org.ws, org.rekan, None, akses=1)

        res = _klien(org.saya).get(self.url.format(slug=org.ws.slug))

        assert res.status_code == status.HTTP_200_OK
        ids = _ids(res)
        assert str(publik_rekan.id) in ids
        assert str(privat_saya.id) in ids
        assert str(privat_rekan.id) not in ids
        assert str(dep_lain.id) not in ids
        # View workspace punya endpoint sendiri (`/views/`), tidak ikut di sini.
        assert str(view_workspace.id) not in ids

    @pytest.mark.django_db
    def test_keanggotaan_nonaktif_project_arsip_dan_views_mati_disaring(self, org):
        _anggota(org.p_lain, org.saya, aktif=False)
        nonaktif = _view(org.ws, org.rekan, org.p_lain)
        arsip = Project.objects.create(name="Arsip", identifier="ARS", workspace=org.ws, archived_at=timezone.now())
        _anggota(arsip, org.saya)
        di_arsip = _view(org.ws, org.saya, arsip)
        mati = Project.objects.create(name="Mati", identifier="MAT", workspace=org.ws, issue_views_view=False)
        _anggota(mati, org.saya)
        views_mati = _view(org.ws, org.saya, mati)

        ids = _ids(_klien(org.saya).get(self.url.format(slug=org.ws.slug)))

        assert ids.isdisjoint({str(nonaktif.id), str(di_arsip.id), str(views_mati.id)})

    @pytest.mark.django_db
    def test_tamu_terbatas_hanya_view_miliknya(self, org):
        tamu = _user("tamu", org.ws, role=5)
        _anggota(org.p_saya, tamu, role=5)
        publik = _view(org.ws, org.rekan, org.p_saya, akses=1)
        milik_tamu = _view(org.ws, tamu, org.p_saya, akses=1)

        ids = _ids(_klien(tamu).get(self.url.format(slug=org.ws.slug)))

        assert str(milik_tamu.id) in ids
        assert str(publik.id) not in ids

    @pytest.mark.django_db
    def test_bukan_anggota_workspace_ditolak(self, org):
        orang_luar = User.objects.create(email=f"luar-{uuid4().hex[:6]}@plane.so", username=f"luar_{uuid4().hex[:6]}")
        res = _klien(orang_luar).get(self.url.format(slug=org.ws.slug))
        assert res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# 2. Visibilitas bisa diatur
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestAksesView:
    @pytest.mark.django_db
    def test_buat_view_workspace_privat(self, org):
        res = _klien(org.saya).post(
            f"/api/workspaces/{org.ws.slug}/views/", {"name": "Privat", "access": 0}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert IssueView.objects.get(pk=res.json()["id"]).access == 0

    @pytest.mark.django_db
    def test_buat_view_departemen_privat(self, org):
        res = _klien(org.saya).post(
            f"/api/workspaces/{org.ws.slug}/projects/{org.p_saya.id}/views/",
            {"name": "Privat", "access": 0},
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert IssueView.objects.get(pk=res.json()["id"]).access == 0

    @pytest.mark.django_db
    def test_pemilik_bisa_ganti_akses(self, org):
        view = _view(org.ws, org.saya, org.p_saya, akses=1)
        res = _klien(org.saya).patch(
            f"/api/workspaces/{org.ws.slug}/projects/{org.p_saya.id}/views/{view.id}/", {"access": 0}, format="json"
        )
        assert res.status_code == status.HTTP_200_OK
        view.refresh_from_db()
        assert view.access == 0

    @pytest.mark.django_db
    def test_bukan_pemilik_tidak_bisa_ganti_akses(self, org):
        view = _view(org.ws, org.saya, None, akses=1)
        res = _klien(org.rekan).patch(f"/api/workspaces/{org.ws.slug}/views/{view.id}/", {"access": 0}, format="json")
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN)
        view.refresh_from_db()
        assert view.access == 1

    @pytest.mark.django_db
    def test_akses_tidak_valid_ditolak(self, org):
        res = _klien(org.saya).post(
            f"/api/workspaces/{org.ws.slug}/views/", {"name": "Aneh", "access": 7}, format="json"
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST


# ---------------------------------------------------------------------------
# 3. Urutan Approval
# ---------------------------------------------------------------------------


def _tugas_dengan_status(project, user, nama, status_list):
    issue = Issue.objects.create(name=nama, project=project, workspace=project.workspace)
    for umur, status_baris in enumerate(reversed(status_list)):
        baris = PersetujuanPenugasan.objects.create(
            workspace=project.workspace,
            project=project,
            issue=issue,
            pemohon=user,
            penerima=user,
            status=status_baris,
        )
        PersetujuanPenugasan.objects.filter(pk=baris.pk).update(created_at=timezone.now() - timedelta(minutes=umur + 1))
    return issue


@pytest.mark.unit
class TestUrutanApproval:
    @pytest.mark.django_db
    def test_naik_dan_turun(self, org):
        tanpa = _tugas_dengan_status(org.p_saya, org.saya, "tanpa", [])
        disetujui = _tugas_dengan_status(org.p_saya, org.saya, "disetujui", ["disetujui"])
        # Ditolak lalu diajukan ulang: yang terbaru (menunggu) yang dihitung.
        menunggu = _tugas_dengan_status(org.p_saya, org.saya, "menunggu", ["ditolak", "menunggu"])
        ditolak = _tugas_dengan_status(org.p_saya, org.saya, "ditolak", ["ditolak"])
        semua = Issue.issue_objects.filter(project=org.p_saya)

        naik, kunci = order_issue_queryset(semua, "approval_status")
        assert kunci == "approval_order"
        assert [i.id for i in naik] == [menunggu.id, ditolak.id, disetujui.id, tanpa.id]

        turun, _ = order_issue_queryset(semua, "-approval_status")
        assert [i.id for i in turun] == [disetujui.id, ditolak.id, menunggu.id, tanpa.id]

    @pytest.mark.django_db
    def test_baris_work_item_workspace_membawa_status(self, org):
        menunggu = _tugas_dengan_status(org.p_saya, org.saya, "menunggu", ["menunggu"])
        _tugas_dengan_status(org.p_saya, org.saya, "tanpa", [])

        res = _klien(org.saya).get(
            f"/api/workspaces/{org.ws.slug}/issues/",
            {"order_by": "approval_status", "per_page": 50, "cursor": "50:0:0"},
        )

        assert res.status_code == status.HTTP_200_OK
        hasil = res.json()["results"]
        assert hasil[0]["id"] == str(menunggu.id)
        assert hasil[0]["approval_status"] == "menunggu"
        assert hasil[1]["approval_status"] is None
