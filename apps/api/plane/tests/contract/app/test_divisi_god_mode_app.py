# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes kontrak divisi-anggota God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak: `GET|POST /api/instances/divisi-anggota/`.

Kenapa endpoint ini ada: endpoint project biasa memeriksa keanggotaan PEMANGGIL
per divisi (`allow_permission([ROLE.ADMIN])`), jadi dari God Mode ia 403 di tengah
simpan bertahap — terbukti di log produksi 2026-10-16 (GET `.../members/` 403
beruntun untuk divisi tempat pemanggil bukan anggota). Endpoint ini memakai
`InstanceAdminPermission` dan mengganti seluruh daftar dalam satu transaksi.

Kontrol negatif yang dikunci di sini:

* Orang biasa (bukan Super Admin) TIDAK bisa membaca maupun menulis.
* Tanpa login DITOLAK.
* Project asing (di luar workspace) DITOLAK, bukan diabaikan diam-diam.
* role selain 15/20 DITOLAK (Guest diatur admin divisi, bukan God Mode).
* POST atomik: yang tidak disebut dikeluarkan — dan dikeluarkan berarti
  `is_active=False`, bukan hapus baris (riwayat tetap ada).
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import JabatanOrganisasi, Project, ProjectMember, User, Workspace, WorkspaceMember
from plane.license.api.views.divisi import InstanceDivisiAnggotaEndpoint
from plane.license.models import Instance, InstanceAdmin
from plane.utils.hierarki import TINGKAT_MEMBER, TINGKAT_SUPERVISOR

URL_DIVISI = "/api/instances/divisi-anggota/"


def _buat_user(prefix, workspace=None, peran_workspace=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=peran_workspace)
    return user


def _buat_project(nama, identifier, workspace, pembuat, anggota=()):
    project = Project.objects.create(name=nama, identifier=identifier, workspace=workspace, created_by=pembuat)
    for user, role in anggota:
        ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role)
    return project


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email="owner@paradise.test", username="owner_paradise_test")
    return Workspace.objects.create(name="Paradise", slug="paradise", owner=pemilik)


@pytest.fixture
def instance_god_mode(db):
    return Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-divisi-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )


@pytest.fixture
def super_admin(db, instance_god_mode, workspace):
    user = _buat_user("super", workspace, peran_workspace=20)
    InstanceAdmin.objects.create(instance=instance_god_mode, user=user, role=20)
    return user


@pytest.fixture
def staf_a(db, workspace):
    return _buat_user("stafa", workspace, peran_workspace=15)


@pytest.fixture
def staf_b(db, workspace):
    return _buat_user("stafb", workspace, peran_workspace=15)


@pytest.fixture
def bos_b(db, workspace):
    return _buat_user("bosb", workspace, peran_workspace=15)


@pytest.fixture
def divisi_a(db, workspace, staf_a):
    return _buat_project("Divisi A", "DIVA", workspace, staf_a, anggota=[(staf_a, 15)])


@pytest.fixture
def divisi_b(db, workspace, bos_b, staf_b):
    return _buat_project("Divisi B", "DIVB", workspace, bos_b, anggota=[(bos_b, 20), (staf_b, 15)])


@pytest.fixture
def jenjang(db, workspace, bos_b, staf_a):
    JabatanOrganisasi.objects.create(workspace=workspace, member=bos_b, tingkat=TINGKAT_SUPERVISOR)
    JabatanOrganisasi.objects.create(workspace=workspace, member=staf_a, tingkat=TINGKAT_MEMBER)
    return True


def _get(aktor, params=""):
    from django.test import RequestFactory

    request = RequestFactory().get(URL_DIVISI + params)
    if aktor is not None:
        force_authenticate(request, user=aktor)
    return InstanceDivisiAnggotaEndpoint.as_view()(request)


def _post(aktor, badan):
    request = APIRequestFactory().post(URL_DIVISI, badan, format="json")
    if aktor is not None:
        force_authenticate(request, user=aktor)
    return InstanceDivisiAnggotaEndpoint.as_view()(request)


@pytest.mark.contract
class TestDivisiAnggotaGodMode:
    @pytest.mark.django_db
    def test_super_admin_bisa_membaca(self, workspace, instance_god_mode, super_admin, divisi_a, staf_a):
        response = _get(super_admin, f"?member_id={staf_a.id}")
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert response.data["member_id"] == str(staf_a.id)
        assert {b["identifier"] for b in response.data["divisi"]} == {"DIVA"}

    @pytest.mark.django_db
    def test_anggota_biasa_TIDAK_bisa_membaca(self, workspace, instance_god_mode, staf_a, staf_b):
        response = _get(staf_a, f"?member_id={staf_b.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_tanpa_login_TIDAK_bisa_membaca(self, workspace, instance_god_mode, staf_a):
        response = _get(None, f"?member_id={staf_a.id}")
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    @pytest.mark.django_db
    def test_tanpa_member_id_ditolak(self, workspace, instance_god_mode, super_admin):
        response = _get(super_admin)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_ganti_atomik_masuk_keluar_ubah_peran(
        self, workspace, instance_god_mode, super_admin, divisi_a, divisi_b, staf_a
    ):
        """staf_a: DIVA(15) → DIVB(20). DIVA hilang (soft), DIVB lahir sebagai 20."""
        response = _post(
            super_admin, {"member_id": str(staf_a.id), "divisi": [{"project_id": str(divisi_b.id), "role": 20}]}
        )
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert response.data["divisi"] == [{"project_id": str(divisi_b.id), "identifier": "DIVB", "role": 20}]
        assert ProjectMember.objects.filter(member=staf_a, project=divisi_a, is_active=True).count() == 0
        mati = ProjectMember.objects.filter(member=staf_a, project=divisi_a).first()
        assert mati is not None and not mati.is_active, "keluar harus soft delete, bukan hapus baris"
        assert ProjectMember.objects.filter(member=staf_a, project=divisi_b, is_active=True).first().role == 20

    @pytest.mark.django_db
    def test_project_asing_ditolak(self, workspace, instance_god_mode, super_admin, staf_a):
        response = _post(super_admin, {"member_id": str(staf_a.id), "divisi": [{"project_id": str(uuid4()), "role": 15}]})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_role_guest_ditolak(self, workspace, instance_god_mode, super_admin, divisi_a, staf_a):
        response = _post(
            super_admin, {"member_id": str(staf_a.id), "divisi": [{"project_id": str(divisi_a.id), "role": 5}]}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_anggota_biasa_TIDAK_bisa_menulis(self, workspace, instance_god_mode, divisi_a, staf_a, staf_b):
        response = _post(
            staf_a, {"member_id": str(staf_b.id), "divisi": [{"project_id": str(divisi_a.id), "role": 15}]}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_peran_tak_wajar_jadi_peringatan_bukan_penolakan(
        self, workspace, instance_god_mode, super_admin, divisi_b, jenjang, bos_b
    ):
        """bos_b supervisor diberi 15: tersimpan, tapi ada peringatan."""
        response = _post(
            super_admin, {"member_id": str(bos_b.id), "divisi": [{"project_id": str(divisi_b.id), "role": 15}]}
        )
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert len(response.data["peringatan"]) == 1
