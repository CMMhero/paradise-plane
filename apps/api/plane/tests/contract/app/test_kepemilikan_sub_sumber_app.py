# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kepemilikan edit di sub-sumber tugas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak: pintu samping tugas ikut aturan edit KEP-25.

Laporan user 2 Nov 2026: tugas orang lain masih bisa "disunting" dari halaman
detail. PATCH tugasnya sendiri sudah dijaga, tapi tautan, sub-issue, dan seret
tanggal tidak. Penjaganya kini `KepemilikanTugasMixin` di base view.

Kontrol negatif yang dikunci:

* Komentar TETAP terbuka untuk semua anggota (melihat dan bertanya boleh).
* Pemilik (assignee) dan atasannya tetap bisa bekerja.
* Gerbang mati = tidak ada kunci (katup darurat).
"""

from uuid import uuid4

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueAssignee, IssueLink
from plane.utils.hierarki import FLAG_GERBANG

# Fixture dipakai ulang dari tes hierarki supaya dunia ujinya satu.
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

URL_TUGAS = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
URL_TAUTAN = URL_TUGAS + "issue-links/"
URL_SUB = URL_TUGAS + "sub-issues/"
URL_KOMENTAR = URL_TUGAS + "comments/"
URL_TANGGAL = "/api/workspaces/{slug}/projects/{project_id}/issue-dates/"
URL_KUASA = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/bisa-ditugaskan/"


def _tugas(project, pembuat, assignee, nama="Tugas uji"):
    # `save(created_by_id=...)`, BUKAN `objects.create(created_by=...)`: BaseModel
    # menimpa created_by dari crum, dan di tes itu jadi None (KEP-36 butir 3).
    issue = Issue(name=nama, project=project, workspace=project.workspace)
    issue.save(created_by_id=pembuat.id)
    IssueAssignee.objects.create(
        issue=issue, assignee=assignee, project=project, workspace=project.workspace
    )
    return issue


def _url(pola, workspace, project, issue=None):
    return pola.format(slug=workspace.slug, project_id=project.id, issue_id=getattr(issue, "id", None))


def _tautan(client, workspace, project, issue):
    return client.post(
        _url(URL_TAUTAN, workspace, project, issue),
        {"url": f"https://contoh.test/{uuid4().hex[:6]}"},
        format="json",
    )


@pytest.fixture
def gerbang_nyala(monkeypatch):
    monkeypatch.setenv(FLAG_GERBANG, "1")


@pytest.mark.contract
@pytest.mark.django_db
class TestPintuSamping:
    def test_staf_lain_DITOLAK_menambah_tautan(self, workspace, staf_a, staf_a2, divisi_a, jenjang, gerbang_nyala):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        response = _tautan(_klien(staf_a2), workspace, divisi_a, tugas)
        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        assert "error" in response.json()
        assert not IssueLink.objects.filter(issue=tugas).exists()

    def test_assignee_boleh_menambah_tautan(self, workspace, staf_a, divisi_a, jenjang, gerbang_nyala):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        response = _tautan(_klien(staf_a), workspace, divisi_a, tugas)
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    def test_atasan_boleh_menambah_tautan_ke_tugas_bawahan(
        self, workspace, staf_a, bos_divisi_a, divisi_a, jenjang, gerbang_nyala
    ):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        response = _tautan(_klien(bos_divisi_a), workspace, divisi_a, tugas)
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    def test_staf_lain_DITOLAK_menggantung_sub_issue(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, gerbang_nyala
    ):
        induk = _tugas(divisi_a, staf_a, staf_a, nama="Induk")
        milik_sendiri = _tugas(divisi_a, staf_a2, staf_a2, nama="Anak")
        response = _klien(staf_a2).post(
            _url(URL_SUB, workspace, divisi_a, induk),
            {"sub_issue_ids": [str(milik_sendiri.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        milik_sendiri.refresh_from_db()
        assert milik_sendiri.parent_id is None

    def test_staf_lain_DITOLAK_menyeret_tanggal_mulai(
        self, workspace, staf_a, staf_a2, divisi_a, jenjang, gerbang_nyala
    ):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        response = _klien(staf_a2).post(
            _url(URL_TANGGAL, workspace, divisi_a),
            {"updates": [{"id": str(tugas.id), "start_date": "2026-11-03"}]},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert tugas.start_date is None

    def test_staf_lain_DITOLAK_PATCH_judul(self, workspace, staf_a, staf_a2, divisi_a, jenjang, gerbang_nyala):
        tugas = _tugas(divisi_a, staf_a, staf_a, nama="Asli")
        response = _klien(staf_a2).patch(
            _url(URL_TUGAS, workspace, divisi_a, tugas), {"name": "Diubah orang lain"}, format="json"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert tugas.name == "Asli"

    def test_komentar_TETAP_terbuka(self, workspace, staf_a, staf_a2, divisi_a, jenjang, gerbang_nyala):
        tugas = _tugas(divisi_a, staf_a, staf_a)
        response = _klien(staf_a2).post(
            _url(URL_KOMENTAR, workspace, divisi_a, tugas),
            {"comment_html": "<p>Boleh tanya?</p>"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    def test_gerbang_mati_tidak_mengunci(self, workspace, staf_a, staf_a2, divisi_a, jenjang, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "0")
        tugas = _tugas(divisi_a, staf_a, staf_a)
        response = _tautan(_klien(staf_a2), workspace, divisi_a, tugas)
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)


@pytest.mark.contract
@pytest.mark.django_db
class TestKuasaUntukTampilan:
    """Klien mencerminkan server lewat `bisa-ditugaskan/`, jadi bentuknya dikunci."""

    def test_supervisor_menerima_bawahan_ids(
        self, workspace, staf_a, staf_a2, bos_divisi_a, divisi_a, jenjang, gerbang_nyala
    ):
        data = _klien(bos_divisi_a).get(_url(URL_KUASA, workspace, divisi_a)).json()
        assert data["gerbang_aktif"] is True
        assert {str(staf_a.id), str(staf_a2.id)} <= set(data["bawahan_ids"])
        assert str(bos_divisi_a.id) not in data["bawahan_ids"]

    def test_staf_tidak_punya_bawahan(self, workspace, staf_a, divisi_a, jenjang, gerbang_nyala):
        data = _klien(staf_a).get(_url(URL_KUASA, workspace, divisi_a)).json()
        assert data["gerbang_aktif"] is True
        assert data["bawahan_ids"] == []

    def test_gerbang_mati_dilaporkan(self, workspace, staf_a, divisi_a, jenjang, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "0")
        data = _klien(staf_a).get(_url(URL_KUASA, workspace, divisi_a)).json()
        assert data["gerbang_aktif"] is False
