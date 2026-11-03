# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Super Admin terlihat lewat penempatan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Super Admin yang ditempatkan di departemen/divisi muncul di project-nya.

Laporan user 3 Nov: filter Created by, Assignees, Mentions tidak memuat orang
yang kebetulan Super Admin, padahal ia staf/manager di departemen itu. Penyebab:
`sembunyikan()` hanya mengenal penanda manual `SuperAdminTerlihatDiProject`.

Bentuk uji:

    SALES -> SMT1 (P1) · SMT2 (P2)
    HRGA  -> HR   (P3)
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    SuperAdminTerlihatDiProject,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    User,
    WorkspaceMember,
)
from plane.db.superadmin import sembunyikan, sembunyikan_lintas_project, sinkronkan_super_admin
from plane.license.models import Instance, InstanceAdmin


def _user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_name="Uji"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _super_admin(workspace):
    instance = Instance.objects.first() or Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-sa-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user("super", workspace)
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _terlihat(project, user):
    qs = ProjectMember.objects.filter(project=project, is_active=True)
    return sembunyikan(qs, project_id=project.id).filter(member=user).exists()


def _terlihat_lintas(project, user):
    qs = ProjectMember.objects.filter(project=project, is_active=True)
    return sembunyikan_lintas_project(qs).filter(member=user).exists()


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.p1, o.p2, o.p3 = (
        Project.objects.create(name=n, identifier=i, workspace=workspace, created_by=create_user)
        for n, i in (("SMT1 Board", "P1"), ("SMT2 Board", "P2"), ("HR Board", "P3"))
    )
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.hrga = Divisi.objects.create(workspace=workspace, kode="HRGA", nama="HRGA")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="Sales Team 1")
    o.smt2 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT2", nama="Sales Team 2")
    o.hr = Departemen.objects.create(workspace=workspace, divisi=o.hrga, kode="HR", nama="Human Resources")
    for dep, p in ((o.smt1, o.p1), (o.smt2, o.p2), (o.hr, o.p3)):
        DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=p)
    o.sa = _super_admin(workspace)
    sinkronkan_super_admin(o.sa.id)
    o.semua = (o.p1, o.p2, o.p3)
    return o


@pytest.mark.contract
@pytest.mark.django_db
class TestSuperAdminTerlihatLewatPenempatan:
    def test_tanpa_penempatan_tetap_tersembunyi(self, org):
        for p in org.semua:
            assert ProjectMember.objects.filter(project=p, member=org.sa, is_active=True).exists()
            assert not _terlihat(p, org.sa)
            assert not _terlihat_lintas(p, org.sa)

    def test_penempatan_departemen_hanya_project_departemen_itu(self, org):
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.sa, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
        hasil = {p.identifier: (_terlihat(p, org.sa), _terlihat_lintas(p, org.sa)) for p in org.semua}
        assert hasil == {"P1": (True, True), "P2": (False, False), "P3": (False, False)}

    def test_penempatan_divisi_semua_project_divisi_itu(self, org):
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.sa, tingkat=TINGKAT_MANAGER, divisi=org.sales)
        hasil = {p.identifier: (_terlihat(p, org.sa), _terlihat_lintas(p, org.sa)) for p in org.semua}
        assert hasil == {"P1": (True, True), "P2": (True, True), "P3": (False, False)}

    def test_direktur_tanpa_tempat_tetap_tersembunyi(self, org):
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.sa, tingkat=TINGKAT_DIREKTUR)
        for p in org.semua:
            assert not _terlihat(p, org.sa)
            assert not _terlihat_lintas(p, org.sa)

    def test_penempatan_dicabut_kembali_tersembunyi(self, org):
        baris = JabatanOrganisasi.objects.create(
            workspace=org.ws, member=org.sa, tingkat=TINGKAT_MEMBER, departemen=org.smt1
        )
        assert _terlihat(org.p1, org.sa)
        baris.delete()
        assert not _terlihat(org.p1, org.sa)
        assert not _terlihat_lintas(org.p1, org.sa)

    def test_departemen_terhapus_tidak_membuka(self, org):
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.sa, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
        DepartemenProject.objects.filter(departemen=org.smt1).delete()
        assert not _terlihat(org.p1, org.sa)
        assert not _terlihat_lintas(org.p1, org.sa)

    def test_penanda_manual_tetap_berlaku(self, org):
        SuperAdminTerlihatDiProject.objects.create(workspace=org.ws, project=org.p3, member=org.sa)
        assert _terlihat(org.p3, org.sa)
        assert _terlihat_lintas(org.p3, org.sa)
        assert not _terlihat(org.p2, org.sa)

    def test_endpoint_daftar_anggota_memuatnya(self, org):
        """Sumber filter Created by / Assignees / Mentions di frontend."""
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.sa, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
        rekan = _user("rekan", org.ws)
        for p in (org.p1, org.p2):
            ProjectMember.objects.get_or_create(project=p, member=rekan, workspace=org.ws, defaults={"role": 15})
        client = APIClient()
        client.force_authenticate(user=rekan)

        def ids(p):
            res = client.get(f"/api/workspaces/{org.ws.slug}/projects/{p.id}/members/")
            assert res.status_code == 200, res.data
            return {str(m["member"]) for m in res.data}

        assert str(org.sa.id) in ids(org.p1)
        assert str(org.sa.id) not in ids(org.p2)
