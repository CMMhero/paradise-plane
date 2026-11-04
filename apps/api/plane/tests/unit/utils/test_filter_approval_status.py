# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: filter status persetujuan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Filter `approval_status` di IssueFilterSet (pengganti tombol "Tunggu persetujuan").

Yang dijaga: hanya baris persetujuan TERBARU per tugas yang dihitung, sama
dengan badge di papan. Tugas yang ditolak lalu diajukan ulang punya baris
`ditolak` lama dan `menunggu` baru, dan harus terbaca menunggu.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from plane.db.models import Issue, PersetujuanPenugasan, Project, User, Workspace
from plane.utils.filters.filterset import IssueFilterSet, q_approval_status


@pytest.fixture
def divisi(db):
    pemilik = User.objects.create(email=f"own-{uuid4().hex[:6]}@plane.so", username=f"own_{uuid4().hex[:6]}")
    ws = Workspace.objects.create(name="WS", slug=f"ws-{uuid4().hex[:6]}", owner=pemilik)
    project = Project.objects.create(name="Divisi", identifier="DIVF", workspace=ws, created_by=pemilik)
    return project, pemilik


def _tugas(project, nama):
    return Issue.objects.create(name=nama, project=project, workspace=project.workspace)


def _baris(project, user, issue, status, umur_menit):
    baris = PersetujuanPenugasan.objects.create(
        workspace=project.workspace,
        project=project,
        issue=issue,
        pemohon=user,
        penerima=user,
        status=status,
    )
    # `created_at` auto_now_add: urutan diatur lewat update, bukan argumen create.
    PersetujuanPenugasan.objects.filter(pk=baris.pk).update(created_at=timezone.now() - timedelta(minutes=umur_menit))
    return baris


@pytest.mark.unit
class TestFilterApprovalStatus:
    def test_filterset_declares_approval_status(self):
        assert "approval_status" in IssueFilterSet.base_filters
        assert "approval_status__in" in IssueFilterSet.base_filters

    def test_only_latest_row_counts(self, divisi):
        project, user = divisi
        menunggu = _tugas(project, "menunggu")
        _baris(project, user, menunggu, "menunggu", 5)

        disetujui = _tugas(project, "disetujui")
        _baris(project, user, disetujui, "disetujui", 5)

        diajukan_ulang = _tugas(project, "ditolak lalu diajukan ulang")
        _baris(project, user, diajukan_ulang, "ditolak", 30)
        _baris(project, user, diajukan_ulang, "menunggu", 1)

        tanpa_persetujuan = _tugas(project, "tugas atasan")

        hasil_menunggu = set(Issue.issue_objects.filter(q_approval_status(["menunggu"])).values_list("id", flat=True))
        assert hasil_menunggu == {menunggu.id, diajukan_ulang.id}

        hasil_disetujui = set(Issue.issue_objects.filter(q_approval_status(["disetujui"])).values_list("id", flat=True))
        assert hasil_disetujui == {disetujui.id}

        # Baris "ditolak" yang sudah tertimpa pengajuan ulang tidak boleh terbaca.
        assert not Issue.issue_objects.filter(q_approval_status(["ditolak"])).exists()
        assert tanpa_persetujuan.id not in hasil_menunggu | hasil_disetujui

    def test_in_lookup_combines_statuses(self, divisi):
        project, user = divisi
        a = _tugas(project, "a")
        _baris(project, user, a, "menunggu", 2)
        b = _tugas(project, "b")
        _baris(project, user, b, "disetujui", 2)

        fs = IssueFilterSet(data={"approval_status__in": "menunggu,disetujui"}, queryset=Issue.issue_objects.all())
        ids = set(fs.qs.values_list("id", flat=True))
        assert ids == {a.id, b.id}


@pytest.mark.unit
class TestFilterApprovalStatusTanpa:
    def test_tanpa_matches_issues_without_any_approval_row(self, divisi):
        project, user = divisi
        menunggu = _tugas(project, "menunggu")
        _baris(project, user, menunggu, "menunggu", 5)
        ditolak = _tugas(project, "ditolak")
        _baris(project, user, ditolak, "ditolak", 5)
        tanpa = _tugas(project, "tugas atasan")

        hanya_tanpa = set(Issue.issue_objects.filter(q_approval_status(["tanpa"])).values_list("id", flat=True))
        assert tanpa.id in hanya_tanpa
        assert menunggu.id not in hanya_tanpa and ditolak.id not in hanya_tanpa

        campur = set(
            Issue.issue_objects.filter(q_approval_status(["ditolak", "tanpa"])).values_list("id", flat=True)
        )
        assert {ditolak.id, tanpa.id} <= campur and menunggu.id not in campur

    def test_unknown_value_matches_nothing(self, divisi):
        project, user = divisi
        _baris(project, user, _tugas(project, "a"), "menunggu", 2)
        assert not Issue.issue_objects.filter(q_approval_status(["bukan-status"])).exists()
