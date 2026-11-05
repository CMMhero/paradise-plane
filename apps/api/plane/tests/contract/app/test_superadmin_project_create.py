# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Pembuatan project lewat jalur web sudah ditutup untuk semua orang, termasuk
Super Admin (instance admin / God Mode). Departemen, dan project di baliknya,
hanya dibuat di God Mode lewat `_adopsi_atau_buat_project`.

Dulu file ini menjaga regresi keanggotaan ganda saat Super Admin membuat project
lewat view ini. Jalur itu sudah tidak ada, jadi yang dijaga sekarang: ditolak 403
dan tidak ada sisa apa pun di database.
"""

import pytest
from rest_framework import status

from plane.db.models import Project, ProjectMember, ProjectUserProperty, State
from plane.license.models import Instance, InstanceAdmin
from plane.utils.izin_buat_project import PESAN_DEPARTEMEN_DI_GODMODE


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


def _hitung():
    return (
        Project.objects.count(),
        ProjectMember.all_objects.count(),
        ProjectUserProperty.objects.count(),
        State.objects.count(),
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectCreateClosedOnWeb:
    def test_super_admin_is_refused_and_nothing_is_left_behind(self, session_client, workspace, super_admin_user):
        before = _hitung()

        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project oleh Super Admin", "identifier": "SADM"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": PESAN_DEPARTEMEN_DI_GODMODE}
        assert not Project.objects.filter(name="Project oleh Super Admin").exists()
        assert _hitung() == before

    def test_plain_admin_member_is_refused_too(self, session_client, workspace, create_user):
        before = _hitung()

        response = session_client.post(
            projects_url(workspace.slug),
            {"name": "Project biasa", "identifier": "PLAI"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data == {"error": PESAN_DEPARTEMEN_DI_GODMODE}
        assert not Project.objects.filter(name="Project biasa").exists()
        assert _hitung() == before
