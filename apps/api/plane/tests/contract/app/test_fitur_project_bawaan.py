# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: semua fitur project menyala sejak lahir (KEP-53)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.app.serializers import ProjectSerializer
from plane.db.models import Project

FITUR_NYALA = ("module_view", "issue_views_view", "page_view", "intake_view", "is_time_tracking_enabled")


@pytest.mark.django_db
def test_project_baru_lahir_dengan_semua_fitur_menyala(workspace, create_user):
    # Jalur yang sama dengan project departemen dari God Mode: serializer tanpa flag.
    ser = ProjectSerializer(
        data={"name": "Departemen Uji", "identifier": "DEPUJI", "created_by": str(create_user.id)},
        context={"workspace_id": str(workspace.id)},
    )
    assert ser.is_valid(), ser.errors
    project = ser.save()

    for flag in FITUR_NYALA:
        assert getattr(project, flag) is True, flag


@pytest.mark.django_db
def test_fitur_yang_dicabut_tetap_mati_secara_bawaan(workspace):
    project = Project.objects.create(name="Lama", identifier="LAMA", workspace=workspace)
    assert project.cycle_view is False
    assert project.is_issue_type_enabled is False
