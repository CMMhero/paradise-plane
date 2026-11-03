# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kartu profil anggota + Super Admin bisa di-mention
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kartu profil anggota dan endpoint daftar anggota untuk Super Admin yang ditempatkan.

Dua laporan user 3 Nov:

1. Super Admin yang ditempatkan di departemen tidak bisa di-mention, ditugaskan,
   atau dipilih di filter. Semua endpoint daftar anggota project harus lewat
   `sembunyikan()` yang sadar penempatan (KEP-61), diuji di sini lewat HTTP.
2. Kartu profil anggota (`member-profile`): hanya anggota aktif workspace yang
   sama, akun terhapus 404, kontak tidak untuk Guest; ekstensi telepon bisa
   diubah sendiri dan oleh Super Admin.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from plane.db.models import (
    DOMAIN_AKUN_TERHAPUS,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    JabatanOrganisasi,
    Profile,
    Project,
    ProjectMember,
    TINGKAT_MEMBER,
    TINGKAT_MANAGER,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.db.superadmin import sinkronkan_super_admin
from plane.license.api.views.member import InstanceMemberEndpoint
from plane.license.models import Instance, InstanceAdmin


def _user(prefix, workspace=None, role=15, email=None):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=email or f"{prefix}-{unik}@plane.so",
        username=f"{prefix}_{unik}",
        first_name=prefix.capitalize(),
        last_name="Uji",
        display_name=f"{prefix}{unik}",
    )
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _jadikan_super_admin(user):
    instance = Instance.objects.first() or Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-profil-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    sinkronkan_super_admin(user.id)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.p1 = Project.objects.create(name="SMT1 Board", identifier="P1", workspace=workspace, created_by=create_user)
    o.p2 = Project.objects.create(name="HR Board", identifier="P2", workspace=workspace, created_by=create_user)
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.hrga = Divisi.objects.create(workspace=workspace, kode="HRGA", nama="HRGA")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="Sales Team 1")
    o.hr = Departemen.objects.create(workspace=workspace, divisi=o.hrga, kode="HR", nama="Human Resources")
    DepartemenProject.objects.create(workspace=workspace, departemen=o.smt1, project=o.p1)
    DepartemenProject.objects.create(workspace=workspace, departemen=o.hr, project=o.p2)

    o.sa = _jadikan_super_admin(_user("superadm", workspace))
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.sa, tingkat=TINGKAT_MEMBER, departemen=o.smt1)

    o.rekan = _user("rekan", workspace)
    for p in (o.p1, o.p2):
        ProjectMember.objects.create(project=p, member=o.rekan, workspace=workspace, role=15)
    return o


# --------------------------------------------------------------------------
# 1. Super Admin yang ditempatkan muncul di setiap pemilih anggota project
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestSuperAdminDitempatkanBisaDipilih:
    def _mention(self, org, project, query):
        res = _klien(org.rekan).get(
            f"/api/workspaces/{org.ws.slug}/entity-search/",
            {"query_type": "user_mention", "project_id": str(project.id), "query": query, "count": 20},
        )
        assert res.status_code == 200, res.data
        return {str(u["member__id"]) for u in res.data["user_mention"]}

    def test_mention_project_departemennya_memuat_super_admin(self, org):
        assert str(org.sa.id) in self._mention(org, org.p1, "superadm")

    def test_mention_project_lain_tetap_tersembunyi(self, org):
        assert str(org.sa.id) not in self._mention(org, org.p2, "superadm")

    def test_mention_cari_nama_lengkap(self, org):
        """Mengetik "Nama Belakang" (nama depan + belakang) juga menemukan orangnya."""
        assert str(org.sa.id) in self._mention(org, org.p1, "Superadm Uji")

    def test_mention_tidak_menawarkan_akun_terhapus(self, org):
        hapus = _user("hapusan", org.ws, email=f"y-{uuid4().hex[:8]}@{DOMAIN_AKUN_TERHAPUS}")
        ProjectMember.objects.create(project=org.p1, member=hapus, workspace=org.ws, role=15)
        assert str(hapus.id) not in self._mention(org, org.p1, "hapusan")
        res = _klien(org.rekan).get(
            f"/api/workspaces/{org.ws.slug}/entity-search/", {"query_type": "user_mention", "query": "hapusan"}
        )
        assert str(hapus.id) not in {str(u["member__id"]) for u in res.data["user_mention"]}

    def test_daftar_pengikut_work_item(self, org):
        issue = Issue.objects.create(name="Tugas", project=org.p1, workspace=org.ws)
        res = _klien(org.rekan).get(
            f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/issues/{issue.id}/issue-subscribers/"
        )
        assert res.status_code == 200, res.data
        ids = {str(m["member"]["id"]) if isinstance(m["member"], dict) else str(m["member"]) for m in res.data}
        assert str(org.sa.id) in ids

    def test_peta_anggota_lintas_project(self, org):
        res = _klien(org.rekan).get(f"/api/workspaces/{org.ws.slug}/project-members/")
        assert res.status_code == 200, res.data
        p1 = {str(m["member"]) for m in res.data.get(str(org.p1.id), [])}
        p2 = {str(m["member"]) for m in res.data.get(str(org.p2.id), [])}
        assert str(org.sa.id) in p1
        assert str(org.sa.id) not in p2

    def test_super_admin_sebagai_peminta_melihat_dirinya(self, org):
        """Sisi sebaliknya: Super Admin yang ditempatkan melihat dirinya di daftar anggota project."""
        res = _klien(org.sa).get(f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/members/")
        assert res.status_code == 200, res.data
        assert str(org.sa.id) in {str(m["member"]) for m in res.data}


# --------------------------------------------------------------------------
# 2. Kartu profil anggota
# --------------------------------------------------------------------------


def _profil(client, ws, user_id):
    return client.get(f"/api/workspaces/{ws.slug}/member-profile/{user_id}/")


@pytest.mark.contract
@pytest.mark.django_db
class TestProfilAnggota:
    def test_isi_lengkap_untuk_sesama_anggota(self, org):
        Profile.objects.update_or_create(
            user=org.sa, defaults={"job_title": "IT Support", "phone_extension": "1234"}
        )
        res = _profil(_klien(org.rekan), org.ws, org.sa.id)
        assert res.status_code == 200, res.data
        assert res.data["email"] == org.sa.email
        assert res.data["job_title"] == "IT Support"
        assert res.data["phone_extension"] == "1234"
        assert res.data["penempatan"] == [
            {
                "tingkat": TINGKAT_MEMBER,
                "departemen": {"id": str(org.smt1.id), "kode": "SMT1", "nama": "Sales Team 1"},
                "divisi": {"id": str(org.sales.id), "kode": "SALES", "nama": "Sales"},
            }
        ]

    def test_penempatan_manager_divisi(self, org):
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.rekan, tingkat=TINGKAT_MANAGER, divisi=org.hrga)
        res = _profil(_klien(org.sa), org.ws, org.rekan.id)
        assert res.status_code == 200, res.data
        assert res.data["penempatan"][0]["departemen"] is None
        assert res.data["penempatan"][0]["divisi"]["kode"] == "HRGA"

    def test_departemen_terhapus_tidak_ditampilkan(self, org):
        org.smt1.delete()
        res = _profil(_klien(org.rekan), org.ws, org.sa.id)
        assert res.status_code == 200, res.data
        assert res.data["penempatan"] == []

    def test_guest_tidak_melihat_kontak(self, org):
        tamu = _user("tamu", org.ws, role=5)
        res = _profil(_klien(tamu), org.ws, org.sa.id)
        assert res.status_code == 200, res.data
        assert res.data["email"] is None
        assert res.data["phone_extension"] is None
        assert res.data["display_name"] == org.sa.display_name

    def test_bukan_anggota_workspace_404(self, org):
        luar = _user("luar")
        assert _profil(_klien(org.rekan), org.ws, luar.id).status_code == 404

    def test_anggota_workspace_lain_404(self, org, create_user):
        lain = Workspace.objects.create(name="Lain", owner=create_user, slug=f"lain-{uuid4().hex[:6]}")
        orang_lain = _user("lain", lain)
        assert _profil(_klien(org.rekan), org.ws, orang_lain.id).status_code == 404

    def test_akun_terhapus_404(self, org):
        hapus = _user("hapus", org.ws, email=f"x-{uuid4().hex[:8]}@{DOMAIN_AKUN_TERHAPUS}")
        assert _profil(_klien(org.rekan), org.ws, hapus.id).status_code == 404

    def test_peminta_bukan_anggota_ditolak(self, org):
        luar = _user("luar")
        assert _profil(_klien(luar), org.ws, org.rekan.id).status_code == 403


@pytest.mark.contract
@pytest.mark.django_db
class TestUbahKontak:
    def test_ubah_sendiri_lewat_profil_saya(self, org):
        Profile.objects.get_or_create(user=org.rekan)
        client = _klien(org.rekan)
        res = client.patch("/api/users/me/profile/", {"phone_extension": "21 #5", "job_title": "Sales"}, format="json")
        assert res.status_code == 200, res.data
        profil = Profile.objects.get(user=org.rekan)
        assert (profil.phone_extension, profil.job_title) == ("21 #5", "Sales")

    def test_ekstensi_tidak_sah_ditolak(self, org):
        Profile.objects.get_or_create(user=org.rekan)
        res = _klien(org.rekan).patch("/api/users/me/profile/", {"phone_extension": "abc"}, format="json")
        assert res.status_code == 400

    def _god_mode(self, aktor, pk, badan):
        request = APIRequestFactory().patch(f"/api/instances/members/{pk}/", badan, format="json")
        force_authenticate(request, user=aktor)
        return InstanceMemberEndpoint.as_view()(request, pk=pk)

    def test_super_admin_mengubah_dari_god_mode(self, org):
        res = self._god_mode(org.sa, org.rekan.id, {"phone_extension": " 4321 ", "job_title": "Account Exec"})
        assert res.status_code == 200, res.data
        assert res.data["phone_extension"] == "4321"
        assert res.data["job_title"] == "Account Exec"

    def test_god_mode_menolak_tanpa_menulis_apa_pun(self, org):
        nama_lama = org.rekan.display_name
        res = self._god_mode(org.sa, org.rekan.id, {"display_name": "Nama Baru", "phone_extension": "x1"})
        assert res.status_code == 400
        org.rekan.refresh_from_db()
        assert org.rekan.display_name == nama_lama
