# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: setiap departemen punya Intake
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak: Intake menyala dan punya wadah di setiap departemen.

Bug yang dikunci: `Project.intake_view` bawaannya True, jadi web membuka halaman
Intake, tapi baris `Intake` default hanya dibuat di jalur UPDATE project. Departemen
dari God Mode tidak pernah lewat jalur itu, sehingga daftar Intake menjawab 404
"Intake not found" dan web menampilkan "Error fetching the intake work items".
"""

import importlib
from uuid import uuid4

import pytest
from django.apps import apps as django_apps
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from plane.db.models import Intake, Project, ProjectMember, User, WorkspaceMember
from plane.license.api.views.organisasi import InstanceDepartemenEndpoint, InstanceDivisiEndpoint
from plane.license.models import Instance, InstanceAdmin
from plane.utils.intake_bawaan import ensure_default_intake

URL_INTAKE_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/inbox-issues/"
URL_INTAKES = "/api/workspaces/{slug}/projects/{project_id}/intakes/"

migrasi = importlib.import_module("plane.db.migrations.0185_intake_bawaan")


def _user(prefix, workspace, role=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_name="Uji"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _god(view, aktor, data):
    request = APIRequestFactory().post("/api/instances/organisasi/", data, format="json")
    force_authenticate(request, user=aktor)
    return view.as_view()(request)


@pytest.fixture
def super_admin(db, workspace):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-intake-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user("super", workspace)
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


@pytest.fixture
def anggota(db, workspace):
    return _user("anggota", workspace)


def _project(workspace, anggota, **kolom):
    """Project lahir lewat ORM, tanpa Intake: bentuk data lama di produksi."""
    project = Project.objects.create(
        name=f"Dep {uuid4().hex[:6]}", identifier=uuid4().hex[:5].upper(), workspace=workspace, **kolom
    )
    ProjectMember.objects.create(project=project, member=anggota, workspace=workspace, role=20)
    return project


@pytest.mark.contract
class TestIntakeBawaan:
    @pytest.mark.django_db
    def test_departemen_baru_dari_god_mode_punya_intake_default(self, workspace, super_admin):
        r = _god(InstanceDivisiEndpoint, super_admin, {"kode": "ops", "nama": "Operasional"})
        assert r.status_code == status.HTTP_201_CREATED, r.data
        div_id = r.data["divisi"][0]["id"]
        r = _god(InstanceDepartemenEndpoint, super_admin, {"divisi_id": div_id, "kode": "GDG", "nama": "Gudang"})
        assert r.status_code == status.HTTP_201_CREATED, r.data

        project = Project.objects.get(workspace=workspace, identifier="GDG")
        assert project.intake_view is True
        assert Intake.objects.filter(project=project, is_default=True).count() == 1

        response = _klien(super_admin).get(URL_INTAKE_ISSUES.format(slug=workspace.slug, project_id=project.id))
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_daftar_intake_menyembuhkan_diri_kalau_barisnya_hilang(self, workspace, anggota):
        project = _project(workspace, anggota)
        assert not Intake.objects.filter(project=project).exists()

        response = _klien(anggota).get(URL_INTAKE_ISSUES.format(slug=workspace.slug, project_id=project.id))

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert Intake.objects.filter(project=project, is_default=True).count() == 1

    @pytest.mark.django_db
    def test_wadah_intake_menyembuhkan_diri(self, workspace, anggota):
        project = _project(workspace, anggota)

        response = _klien(anggota).get(URL_INTAKES.format(slug=workspace.slug, project_id=project.id))

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert response.json()["id"] == str(Intake.objects.get(project=project, is_default=True).id)

    @pytest.mark.django_db
    def test_kirim_ke_intake_tanpa_baris_tidak_meledak(self, workspace, anggota):
        project = _project(workspace, anggota)

        response = _klien(anggota).post(
            URL_INTAKE_ISSUES.format(slug=workspace.slug, project_id=project.id),
            {"issue": {"name": "Cek stok", "priority": "none"}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_intake_dimatikan_tidak_dibuatkan_diam_diam(self, workspace, anggota):
        project = _project(workspace, anggota, intake_view=False)

        response = _klien(anggota).get(URL_INTAKE_ISSUES.format(slug=workspace.slug, project_id=project.id))

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert not Intake.objects.filter(project=project).exists()

    @pytest.mark.django_db
    def test_ensure_default_intake_idempoten(self, workspace, anggota):
        project = _project(workspace, anggota)

        pertama = ensure_default_intake(project)
        kedua = ensure_default_intake(project)

        assert pertama.id == kedua.id
        assert Intake.objects.filter(project=project).count() == 1

    @pytest.mark.django_db
    def test_ensure_default_intake_memakai_baris_yang_sudah_ada(self, workspace, anggota):
        project = _project(workspace, anggota)
        lama = Intake.objects.create(name="Intake Lama", project=project, is_default=True)

        assert ensure_default_intake(project).id == lama.id
        assert Intake.objects.filter(project=project).count() == 1


@pytest.mark.contract
class TestMigrasiIntakeBawaan:
    @pytest.mark.django_db
    def test_menyalakan_intake_dan_membuat_wadah_untuk_semua_project(self, workspace, anggota):
        mati = _project(workspace, anggota, intake_view=False)
        tanpa_baris = _project(workspace, anggota)
        sudah = _project(workspace, anggota)
        wadah_lama = Intake.objects.create(name="Wadah Lama", project=sudah, is_default=True)
        terhapus = _project(workspace, anggota, intake_view=False)
        terhapus.delete()

        migrasi.intake_bawaan(django_apps, None)
        # Dijalankan ulang tidak menggandakan apa pun.
        migrasi.intake_bawaan(django_apps, None)

        for project in (mati, tanpa_baris, sudah):
            assert Project.objects.get(pk=project.pk).intake_view is True
            assert Intake.objects.filter(project=project, is_default=True).count() == 1
        assert Intake.objects.get(project=sudah, is_default=True).id == wadah_lama.id
        assert Project.all_objects.get(pk=terhapus.pk).intake_view is False
        assert not Intake.all_objects.filter(project=terhapus).exists()
