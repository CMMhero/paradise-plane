# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Wiki default hanya admin/superadmin yang boleh ubah
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Kontrak aturan Wiki jalur DEFAULT (project tanpa governance folder).

Keputusan user 2026-10-24: yang boleh MENGUBAH/mengelola Wiki hanya admin
project atau Super Admin. Member boleh membaca dan MENAMBAH halaman ke
projectnya, tidak lebih.

Matriks yang dikunci di sini (project non-governance):

    baca (GET)              semua peran aktif -> 200
    tambah (POST tanpa id)   admin + member   -> 201
    ubah (PATCH)            admin saja        -> member 403
    arsip (POST /archive/)  admin saja        -> member 403
    kunci (POST /lock/)     admin saja        -> member 403
    Super Admin             lolos tanpa baris ProjectMember
"""

import uuid

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import Page, Project, ProjectMember, ProjectPage, User
from plane.license.models import Instance, InstanceAdmin


def _buat_project(workspace, identifier):
    return Project.objects.create(
        name=f"Project {identifier}",
        identifier=identifier,
        workspace=workspace,
    )


def _buat_halaman(workspace, project, pemilik, akses=Page.PUBLIC_ACCESS):
    halaman = Page.objects.create(
        workspace=workspace,
        owned_by=pemilik,
        access=akses,
        name="Halaman uji",
    )
    ProjectPage.objects.create(workspace=workspace, project=project, page=halaman)
    return halaman


def _url(workspace, project_id, akhir=""):
    return f"/api/workspaces/{workspace.slug}/projects/{project_id}/pages/{akhir}"


@pytest.mark.contract
class TestWikiDefaultHanyaAdminBolehUbah:
    @pytest.fixture
    def siap(self, db, workspace):
        admin = User.objects.create(email=f"admin_{uuid.uuid4().hex[:8]}@uji.id", username="admin-wiki")
        member = User.objects.create(email=f"member_{uuid.uuid4().hex[:8]}@uji.id", username="member-wiki")
        project = _buat_project(workspace, "WIK")
        ProjectMember.objects.create(workspace=workspace, project=project, member=admin, role=20)
        ProjectMember.objects.create(workspace=workspace, project=project, member=member, role=15)
        halaman = _buat_halaman(workspace, project, admin)
        return admin, member, project, halaman

    @pytest.mark.django_db
    def test_member_tidak_boleh_ubah_isi(self, api_client, workspace, siap):
        _, member, project, halaman = siap
        api_client.force_authenticate(user=member)
        res = api_client.patch(_url(workspace, project.id, f"{halaman.id}/"), {"name": "Diubah member"}, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_member_boleh_tambah_halaman(self, api_client, workspace, siap):
        _, member, project, _ = siap
        api_client.force_authenticate(user=member)
        res = api_client.post(
            _url(workspace, project.id), {"name": "Halaman baru member", "access": 0}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_member_tetap_boleh_baca(self, api_client, workspace, siap):
        _, member, project, halaman = siap
        api_client.force_authenticate(user=member)
        res = api_client.get(_url(workspace, project.id, f"{halaman.id}/"))
        assert res.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_member_tidak_boleh_arsip_atau_kunci(self, api_client, workspace, siap):
        _, member, project, halaman = siap
        api_client.force_authenticate(user=member)
        arsip = api_client.post(_url(workspace, project.id, f"{halaman.id}/archive/"))
        assert arsip.status_code == status.HTTP_403_FORBIDDEN
        kunci = api_client.post(_url(workspace, project.id, f"{halaman.id}/lock/"))
        assert kunci.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_boleh_ubah_dan_arsip(self, api_client, workspace, siap):
        admin, _, project, halaman = siap
        api_client.force_authenticate(user=admin)
        ubah = api_client.patch(_url(workspace, project.id, f"{halaman.id}/"), {"name": "Diubah admin"}, format="json")
        assert ubah.status_code == status.HTTP_200_OK
        arsip = api_client.post(_url(workspace, project.id, f"{halaman.id}/archive/"))
        assert arsip.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_super_admin_tanpa_keanggotaan_tetap_boleh_ubah(self, api_client, workspace, siap):
        _, _, project, halaman = siap
        instance = Instance.objects.create(
            instance_name="uji",
            instance_id=f"uji-wiki-{uuid.uuid4().hex[:8]}",
            current_version="uji",
            last_checked_at=timezone.now(),
        )
        super_admin = User.objects.create(email=f"sa_{uuid.uuid4().hex[:8]}@uji.id", username="sa-wiki")
        InstanceAdmin.objects.create(instance=instance, user=super_admin, role=20)
        api_client.force_authenticate(user=super_admin)
        res = api_client.patch(_url(workspace, project.id, f"{halaman.id}/"), {"name": "Diubah SA"}, format="json")
        assert res.status_code == status.HTTP_200_OK
