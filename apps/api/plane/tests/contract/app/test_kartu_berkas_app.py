# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kartu berkas di deskripsi dan komentar
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kartu berkas (`<file-component>`) harus selamat dari sanitasi tanpa membawa URL berbahaya."""

import pytest
from rest_framework import status

from plane.db.models import Issue, Project, ProjectMember
from plane.utils.content_validator import validate_html_content


def _bersih(html):
    ok, _, hasil = validate_html_content(html)
    assert ok
    return hasil


@pytest.mark.unit
class TestSanitasiKartuBerkas:
    def test_kartu_dan_atributnya_bertahan(self):
        html = (
            '<file-component id="f1" src="/api/assets/v2/workspaces/w/projects/p/issues/i/attachments/a/" '
            'name="laporan.pdf" size="2048" type="application/pdf">laporan.pdf</file-component>'
        )
        assert _bersih(html) == html

    @pytest.mark.parametrize(
        "src", ["javascript:alert(1)", "JaVaScRiPt:alert(1)", "data:text/html,<script>x</script>", " javascript:x"]
    )
    def test_src_berbahaya_dibuang(self, src):
        hasil = _bersih(f'<file-component src="{src}" name="a.pdf"></file-component>')
        assert "src=" not in hasil
        assert 'name="a.pdf"' in hasil

    def test_atribut_tak_dikenal_dibuang(self):
        hasil = _bersih('<file-component name="a.pdf" onclick="alert(1)"></file-component>')
        assert "onclick" not in hasil


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Test Project", identifier="TP", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def issue(project, workspace, create_user):
    return Issue.objects.create(name="Tugas", project=project, workspace=workspace, created_by=create_user)


@pytest.mark.contract
@pytest.mark.django_db
class TestDeskripsiMenyimpanKartu:
    def test_kartu_tersimpan_di_deskripsi(self, session_client, workspace, project, issue):
        kartu = (
            '<file-component id="f1" src="/api/assets/v2/workspaces/w/projects/p/issues/i/attachments/a/" '
            'name="laporan.pdf" size="2048" type="application/pdf">laporan.pdf</file-component>'
        )
        res = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/",
            {"description_html": f"<p>Lihat:</p>{kartu}"},
            format="json",
        )
        assert res.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), res.data
        issue.refresh_from_db()
        assert kartu in issue.description_html
        assert "laporan.pdf" in issue.description_stripped
