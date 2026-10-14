# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Regresi untuk `manage.py create_project_member`.

Perintah ini dulu mencari baris lama dengan manager bawaan, yang tidak melihat
baris ter-soft-delete. Untuk anggota yang keanggotaannya pernah dicabut,
`ProjectMember.objects.create()` karena itu membuat baris BARU, dan baris baru
itu menabrak constraint unik `ProjectUserProperty` milik baris lama yang masih
hidup. Gagalnya bukan `CommandError`, melainkan traceback `IntegrityError`.

Perintah ini adalah pintu "tambah anggota" yang dipakai operator, jadi ia harus
sama amannya dengan jalur view.
"""

import pytest
from django.core.management import call_command
from django.utils import timezone

from plane.db.models import Project, ProjectMember, ProjectUserProperty, State


@pytest.fixture
def project(workspace):
    p = Project.objects.create(name="Project Command", identifier="PCMD", workspace=workspace)
    State.objects.create(name="Todo", color="#000000", project=p, workspace=workspace, sequence=1, group="backlog")
    return p


@pytest.mark.django_db
def test_menghidupkan_keanggotaan_yang_pernah_dicabut(workspace, create_user, project):
    baris = ProjectMember.objects.create(project=project, member=create_user, role=5)
    ProjectMember.all_objects.filter(pk=baris.pk).update(deleted_at=timezone.now(), is_active=False)

    call_command("create_project_member", project_id=str(project.id), user_email=create_user.email, role=20)

    semua = ProjectMember.all_objects.filter(project=project, member=create_user)
    assert semua.count() == 1, "keanggotaan lama harus dihidupkan, bukan digandakan"
    assert semua.first().deleted_at is None
    assert semua.first().is_active is True
    assert semua.first().role == 20
    assert ProjectUserProperty.all_objects.filter(project=project, user=create_user).count() == 1


@pytest.mark.django_db
def test_anggota_yang_sudah_aktif_tidak_digandakan(workspace, create_user, project):
    ProjectMember.objects.create(project=project, member=create_user, role=5)

    call_command("create_project_member", project_id=str(project.id), user_email=create_user.email, role=20)

    assert ProjectMember.all_objects.filter(project=project, member=create_user).count() == 1
    assert ProjectMember.objects.get(project=project, member=create_user).role == 20
