# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: riwayat aktivitas tugas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Tes kontrak: endpoint riwayat tugas tidak menggandakan baris.

Join ke `project_projectmember` melipatgandakan tiap aktivitas kalau pengguna
punya lebih dari satu baris anggota yang lolos filter (keanggotaan lama yang
di-soft-delete tapi `is_active` masih True).
"""

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import Issue, IssueActivity, Project, ProjectMember, State

URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/history/"


@pytest.fixture
def tugas(db, workspace, create_user):
    project = Project.objects.create(name="Riwayat", identifier="RW", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    state = State.objects.create(name="Todo", project=project, workspace=workspace, group="unstarted")
    issue = Issue.objects.create(name="Tugas", project=project, workspace=workspace, state=state)
    return project, issue


def _tulis_aktivitas(project, issue, user):
    IssueActivity.objects.create(
        workspace_id=project.workspace_id,
        project_id=project.id,
        issue_id=issue.id,
        actor=user,
        verb="requested",
        field="approval",
        epoch=int(timezone.now().timestamp()),
    )


@pytest.mark.contract
def test_riwayat_tidak_ganda_walau_ada_keanggotaan_lama(session_client, workspace, create_user, tugas):
    project, issue = tugas
    _tulis_aktivitas(project, issue, create_user)
    # Baris anggota lama: soft-deleted tapi masih is_active.
    # bulk_create melewati sinyal yang membuat ProjectUserProperty (kunci unik).
    ProjectMember.objects.bulk_create(
        [
            ProjectMember(
                project=project,
                workspace=project.workspace,
                member=create_user,
                role=20,
                is_active=True,
                deleted_at=timezone.now(),
            )
        ]
    )

    response = session_client.get(URL.format(slug=workspace.slug, project_id=project.id, issue_id=issue.id), {"activity_type": "issue-property"})

    assert response.status_code == status.HTTP_200_OK
    ids = [str(item["id"]) for item in response.data]
    assert len(ids) == len(set(ids))
    assert sum(1 for item in response.data if item.get("field") == "approval") == 1


@pytest.mark.contract
def test_riwayat_kosong_untuk_non_anggota(session_client, workspace, create_user, tugas):
    project, issue = tugas
    _tulis_aktivitas(project, issue, create_user)
    ProjectMember.objects.filter(project=project, member=create_user).update(is_active=False)

    response = session_client.get(URL.format(slug=workspace.slug, project_id=project.id, issue_id=issue.id), {"activity_type": "issue-property"})

    assert response.status_code in (status.HTTP_200_OK, status.HTTP_403_FORBIDDEN)
    if response.status_code == status.HTTP_200_OK:
        assert response.data == []
