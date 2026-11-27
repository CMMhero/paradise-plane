# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pratinjau lampiran inline
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pratinjau kartu berkas butuh lampiran yang bisa disajikan inline, tanpa membuka jalan bagi skrip."""

from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import FileAsset, Issue, Project, ProjectMember
from plane.utils.tipe_unggahan import disposisi_sajian

S3_ISSUE_ATTACHMENT = "plane.app.views.issue.attachment.S3Storage"
S3_ASSET = "plane.app.views.asset.v2.S3Storage"


@pytest.mark.unit
class TestDisposisiSajian:
    @pytest.mark.parametrize(
        "tipe", ["application/pdf", "text/plain; charset=utf-8", "image/png", "video/mp4", "audio/mpeg"]
    )
    def test_tipe_aman_boleh_inline(self, tipe):
        assert disposisi_sajian(tipe, "inline") == "inline"

    @pytest.mark.parametrize(
        "tipe",
        [
            "image/svg+xml",
            "text/html",
            "application/xhtml+xml",
            "text/xml",
            "application/javascript",
            "application/atom+xml",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "",
            None,
        ],
    )
    def test_tipe_lain_selalu_diunduh(self, tipe):
        assert disposisi_sajian(tipe, "inline") == "attachment"

    @pytest.mark.parametrize("diminta", [None, "", "attachment", "INLINE"])
    def test_tanpa_permintaan_inline_diunduh(self, diminta):
        assert disposisi_sajian("application/pdf", diminta) == "attachment"


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Test Project", identifier="TP", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def issue(project, workspace, create_user):
    return Issue.objects.create(name="Tugas", project=project, workspace=workspace, created_by=create_user)


def _aset(workspace, project, issue, tipe, entitas=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT):
    return FileAsset.objects.create(
        attributes={"name": "berkas", "type": tipe, "size": 10},
        asset=f"{workspace.id}/berkas",
        entity_type=entitas,
        workspace=workspace,
        project=project,
        issue=issue,
        is_uploaded=True,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestLampiranInline:
    def _ambil(self, client, workspace, project, issue, aset, query=""):
        with mock.patch(S3_ISSUE_ATTACHMENT) as s3:
            s3.return_value.generate_presigned_url.return_value = "https://minio.example/obj"
            res = client.get(
                f"/api/assets/v2/workspaces/{workspace.slug}/projects/{project.id}"
                f"/issues/{issue.id}/attachments/{aset.id}/{query}"
            )
        return res, s3.return_value.generate_presigned_url.call_args

    def test_pdf_inline_bila_diminta(self, session_client, workspace, project, issue):
        aset = _aset(workspace, project, issue, "application/pdf")
        res, panggilan = self._ambil(session_client, workspace, project, issue, aset, "?disposition=inline")
        assert res.status_code == status.HTTP_302_FOUND
        assert panggilan.kwargs["disposition"] == "inline"

    def test_default_tetap_unduhan(self, session_client, workspace, project, issue):
        aset = _aset(workspace, project, issue, "application/pdf")
        _, panggilan = self._ambil(session_client, workspace, project, issue, aset)
        assert panggilan.kwargs["disposition"] == "attachment"

    @pytest.mark.parametrize("tipe", ["image/svg+xml", "text/html", "text/xml"])
    def test_tipe_berskrip_tetap_unduhan(self, session_client, workspace, project, issue, tipe):
        aset = _aset(workspace, project, issue, tipe)
        _, panggilan = self._ambil(session_client, workspace, project, issue, aset, "?disposition=inline")
        assert panggilan.kwargs["disposition"] == "attachment"

    def test_aset_deskripsi_svg_tidak_inline(self, session_client, workspace, project, issue):
        aset = _aset(workspace, project, issue, "image/svg+xml", FileAsset.EntityTypeContext.ISSUE_DESCRIPTION)
        with mock.patch(S3_ASSET) as s3:
            s3.return_value.generate_presigned_url.return_value = "https://minio.example/obj"
            res = session_client.get(
                f"/api/assets/v2/workspaces/{workspace.slug}/projects/{project.id}/{aset.id}/?disposition=inline"
            )
        assert res.status_code == status.HTTP_302_FOUND
        assert s3.return_value.generate_presigned_url.call_args.kwargs["disposition"] == "attachment"
