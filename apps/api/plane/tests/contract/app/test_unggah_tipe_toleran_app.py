# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: unggahan dengan tipe kosong dari peramban
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Permintaan URL presigned dengan `type` kosong.

`File.type` peramban kosong untuk .md/.csv/.mkv di sebagian komputer. Dulu
titik unggah menjawab 400 "Invalid file type", jadi berkas yang sama kadang
bisa dilampirkan dan kadang tidak. Sekarang server menebak dari ekstensi,
tetapi tetap menolak tipe spesifik yang tidak dikenal dan entitas gambar-saja.
"""

from unittest import mock

import pytest
from rest_framework import status

from plane.db.models import FileAsset, Issue, Project, ProjectMember

S3_ASSET = "plane.app.views.asset.v2.S3Storage"
S3_ISSUE_ATTACHMENT = "plane.app.views.issue.attachment.S3Storage"
PRESIGNED = {"url": "https://minio.example/bucket", "fields": {"key": "k"}}


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(name="Test Project", identifier="TP", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=project, member=create_user, workspace=workspace, role=20)
    return project


def _meminta(client, slug, nama, tipe, entitas):
    return client.post(
        f"/api/assets/v2/workspaces/{slug}/",
        {"name": nama, "type": tipe, "size": 1024, "entity_type": entitas, "entity_identifier": ""},
        format="json",
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestTipeUnggahanToleran:
    def test_lampiran_obrolan_tipe_kosong_ditebak_dari_ekstensi(self, session_client, workspace):
        with mock.patch(S3_ASSET) as s3:
            s3.return_value.generate_presigned_post.return_value = PRESIGNED
            res = _meminta(session_client, workspace.slug, "catatan.md", "", "CHAT_ATTACHMENT")
        assert res.status_code == status.HTTP_200_OK, res.data
        assert s3.return_value.generate_presigned_post.call_args.kwargs["file_type"] == "text/markdown"
        asset = FileAsset.objects.get(id=res.data["asset_id"])
        assert asset.attributes["type"] == "text/markdown"

    def test_entitas_gambar_saja_menolak_pdf_bertipe_kosong(self, session_client, workspace):
        with mock.patch(S3_ASSET):
            res = _meminta(session_client, workspace.slug, "dok.pdf", "", "COMMENT_DESCRIPTION")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid file type" in res.data["error"]

    def test_tipe_spesifik_tak_dikenal_tetap_ditolak(self, session_client, workspace):
        with mock.patch(S3_ASSET):
            res = _meminta(session_client, workspace.slug, "a.exe", "application/x-msdownload", "CHAT_ATTACHMENT")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_lampiran_work_item_tipe_kosong_diterima(self, session_client, workspace, project, create_user):
        issue = Issue.objects.create(name="Tugas", project=project, workspace=workspace, created_by=create_user)
        with mock.patch(S3_ISSUE_ATTACHMENT) as s3:
            s3.return_value.generate_presigned_post.return_value = PRESIGNED
            res = session_client.post(
                f"/api/assets/v2/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/attachments/",
                {"name": "data.csv", "type": "", "size": 1024},
                format="json",
            )
        assert res.status_code == status.HTTP_200_OK, res.data
        assert s3.return_value.generate_presigned_post.call_args.kwargs["file_type"] == "text/csv"
