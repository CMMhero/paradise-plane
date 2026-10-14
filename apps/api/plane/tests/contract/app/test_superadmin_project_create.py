# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Regresi: Super Admin (instance admin / God Mode) harus bisa membuat project.

`plane.db.superadmin` memasang signal `post_save` pada Project yang menambah
seluruh Super Admin ke project yang baru dibuat. View pembuatan project juga
menambah pembuatnya sebagai ProjectMember. Ketika keduanya orang yang sama,
ProjectMember.save() membuat ProjectUserProperty dua kali untuk pasangan
(user, project) yang sama dan constraint uniknya meledak, jadi SELURUH pembuatan
project gagal dengan 400 "The payload is not valid".

Test di file test_project_app.py tidak menangkap ini karena tidak pernah ada
InstanceAdmin di fixture-nya, jadi signal-nya diam saja.
"""

import pytest
from rest_framework import status

from plane.db.models import (
    Project,
    ProjectMember,
    ProjectUserProperty,
    State,
)
from plane.license.models import Instance, InstanceAdmin


def projects_url(workspace_slug: str) -> str:
    return f"/api/workspaces/{workspace_slug}/projects/"


@pytest.fixture
def instance(db):
    """Satu baris Instance. `last_checked_at` wajib diisi, jadi bukan get_or_create telanjang."""
    from django.utils import timezone

    obj = Instance.objects.first()
    if obj is None:
        obj = Instance.objects.create(last_checked_at=timezone.now())
    return obj


@pytest.fixture
def super_admin_user(create_user, instance):
    """Jadikan `create_user` seorang instance admin (Super Admin)."""
    InstanceAdmin.objects.get_or_create(instance=instance, user=create_user)
    return create_user


@pytest.mark.contract
@pytest.mark.django_db
class TestSuperAdminCreatesProject:
    def test_super_admin_can_create_project(self, session_client, workspace, super_admin_user):
        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project oleh Super Admin", "identifier": "SADM"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        assert Project.objects.filter(name="Project oleh Super Admin").exists()

    def test_creator_gets_exactly_one_membership(self, session_client, workspace, super_admin_user):
        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project keanggotaan tunggal", "identifier": "ONEM"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        project = Project.objects.get(name="Project keanggotaan tunggal")

        assert ProjectMember.all_objects.filter(project=project, member=super_admin_user).count() == 1
        assert ProjectUserProperty.objects.filter(project=project, user=super_admin_user).count() == 1

    def test_default_states_are_still_seeded(self, session_client, workspace, super_admin_user):
        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project dengan state", "identifier": "STAT"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        project = Project.objects.get(name="Project dengan state")
        assert State.objects.filter(project=project).count() == 5

    def test_failed_create_leaves_nothing_behind(self, session_client, workspace, super_admin_user):
        """Dulu pembuatan yang gagal meninggalkan sisa; transaksi harus membersihkannya."""
        before_projects = Project.objects.count()
        before_props = ProjectUserProperty.objects.count()

        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project gagal", "identifier": "FAIL"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data

        assert Project.objects.count() == before_projects + 1
        assert ProjectUserProperty.objects.count() == before_props + 1


@pytest.mark.contract
@pytest.mark.django_db
class TestNonSuperAdminCreatesProject:
    """Kontrol: tanpa Super Admin, jalur ini harus tetap seperti sebelumnya."""

    def test_plain_member_can_create_project(self, session_client, workspace, create_user):
        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project biasa", "identifier": "PLAI"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        project = Project.objects.get(name="Project biasa")
        assert ProjectUserProperty.objects.filter(project=project, user=create_user).count() == 1

    def test_other_super_admin_is_added_without_duplicates(
        self, session_client, workspace, super_admin_user, create_user
    ):
        """Super Admin lain di database ikut dapat akses, tapi tidak bikin baris ganda."""
        other = super_admin_user.__class__.objects.create(
            email="other-superadmin@test.local",
            username="other-superadmin@test.local",
            first_name="Other",
            last_name="Super Admin",
        )
        instance = Instance.objects.first()
        InstanceAdmin.objects.create(instance=instance, user=other)

        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project dua super admin", "identifier": "TWOS"},
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        project = Project.objects.get(name="Project dua super admin")

        assert ProjectMember.all_objects.filter(project=project, member=other).count() == 1
        assert ProjectUserProperty.objects.filter(project=project, user=other).count() == 1
        assert ProjectUserProperty.objects.filter(project=project, user=super_admin_user).count() == 1
