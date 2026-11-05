# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tautan & gambar deskripsi/komentar di Links/Attachments (KEP-88)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# ruff: noqa: F811 (fixture pytest diimpor dari modul lain lalu dipakai sebagai argumen tes)

"""Tes kontrak: daftar Links dan Attachments memuat isi deskripsi & komentar.

Yang dikunci:

* Tautan di deskripsi & komentar muncul berpenanda `sumber`, link manual `link`.
* URL yang sudah jadi link manual tidak diulang.
* Gambar deskripsi/komentar ikut di Attachments; gambar yang sudah dibuang dari teks tidak.
* Gambar deskripsi TIDAK bisa dihapus lewat endpoint lampiran (deskripsi rusak).
* Pratinjau tautan menolak skema selain http(s).
"""

import pytest
from rest_framework import status

from plane.db.models import FileAsset, IssueComment, IssueLink

from plane.tests.contract.app.test_hierarki_app import (  # noqa: F401
    _klien,
    bos_divisi_a,
    bos_divisi_b,
    direktur,
    divisi_a,
    jenjang,
    staf_a,
    staf_a2,
    staf_b,
)
from plane.tests.contract.app.test_kepemilikan_sub_sumber_app import _tugas, _url

URL_TAUTAN = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/issue-links/"
URL_LAMPIRAN = "/api/assets/v2/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/attachments/"


def _aset(tugas, jenis, **kaitan):
    return FileAsset.objects.create(
        attributes={"name": "gambar.png", "type": "image/png", "size": 10},
        asset=f"{tugas.workspace_id}/gambar.png",
        size=10,
        workspace_id=tugas.workspace_id,
        project_id=tugas.project_id,
        entity_type=jenis,
        is_uploaded=True,
        **kaitan,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestTurunanKonten:
    def test_links_include_description_and_comment(self, workspace, staf_a, divisi_a, jenjang):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        tugas.description_html = '<p><a href="https://a.test/x">a</a> <a href="https://manual.test/">m</a></p>'
        tugas.save()
        IssueLink.objects.create(url="https://manual.test/", issue=tugas, project=divisi_a, workspace=workspace)
        IssueComment.objects.create(
            issue=tugas,
            project=divisi_a,
            workspace=workspace,
            actor=staf_a,
            comment_html='<p><a href="https://c.test/">c</a></p>',
        )

        response = _klien(staf_a).get(_url(URL_TAUTAN, workspace, divisi_a, tugas))
        assert response.status_code == status.HTTP_200_OK, response.data
        per_url = {row["url"]: row["sumber"] for row in response.data}
        assert per_url == {
            "https://manual.test/": "link",
            "https://a.test/x": "description",
            "https://c.test/": "comment",
        }

    def test_attachments_include_referenced_images_only(self, workspace, staf_a, divisi_a, jenjang):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        dipakai = _aset(tugas, FileAsset.EntityTypeContext.ISSUE_DESCRIPTION, issue=tugas)
        dibuang = _aset(tugas, FileAsset.EntityTypeContext.ISSUE_DESCRIPTION, issue=tugas)
        tugas.description_html = f'<image-component src="{dipakai.id}"></image-component>'
        tugas.save()
        komentar = IssueComment.objects.create(
            issue=tugas, project=divisi_a, workspace=workspace, actor=staf_a, comment_html="<p></p>"
        )
        di_komentar = _aset(tugas, FileAsset.EntityTypeContext.COMMENT_DESCRIPTION, comment=komentar)
        komentar.comment_html = f'<image-component src="{di_komentar.id}"></image-component>'
        komentar.save()

        response = _klien(staf_a).get(_url(URL_LAMPIRAN, workspace, divisi_a, tugas))
        assert response.status_code == status.HTTP_200_OK, response.data
        per_id = {str(row["id"]): row["sumber"] for row in response.data}
        assert per_id == {str(dipakai.id): "description", str(di_komentar.id): "comment"}
        assert str(dibuang.id) not in per_id

    def test_description_image_cannot_be_deleted_as_attachment(self, workspace, staf_a, divisi_a, jenjang):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        aset = _aset(tugas, FileAsset.EntityTypeContext.ISSUE_DESCRIPTION, issue=tugas)
        response = _klien(staf_a).delete(_url(URL_LAMPIRAN, workspace, divisi_a, tugas) + f"{aset.id}/")
        assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        aset.refresh_from_db()
        assert aset.is_deleted is False

    def test_link_preview_rejects_non_http(self, workspace, staf_a, divisi_a, jenjang):
        response = _klien(staf_a).get(
            f"/api/workspaces/{workspace.slug}/link-preview/", {"url": "javascript:alert(1)"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
