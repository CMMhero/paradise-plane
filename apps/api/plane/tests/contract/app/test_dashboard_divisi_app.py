# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji Dashboard Divisi untuk pimpinan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak Dashboard Divisi versi ringkas (KEP-60).

Yang dijaga:

1. Status kesehatan dihitung dari porsi tugas AKTIF yang lewat tenggat, dengan
   ambang dari God Mode, dan ambang yang tertukar tidak membalik hasilnya.
2. Project dikelompokkan ke divisinya lewat departemen (KEP-29), divisi paling
   bermasalah di urutan pertama, project tanpa departemen di kelompok terakhir.
3. Hanya project yang user anggotai yang ikut dihitung.
4. Field lama (`totals.projects`, `issues_open`, `worklog_minutes_*`) tetap ada.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    State,
    StateGroup,
    TINGKAT_DIREKTUR,
    TINGKAT_MEMBER,
    User,
    WorkspaceMember,
)
from plane.license.models import InstanceConfiguration
from plane.utils.hierarki import boleh_memutuskan, project_boleh_diputuskan
from plane.utils.ringkasan_divisi import KRITIS, LANCAR, PERHATIAN, ambang_kesehatan, status_kesehatan
from plane.utils.saklar_instance import DASHBOARD_KRITIS_PERSEN, DASHBOARD_PERHATIAN_PERSEN

URL = "/api/workspaces/{slug}/divisi-dashboard/"


def _simpan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": nilai, "category": "PARADISE"})


def _project(workspace, nama, identifier, anggota):
    project = Project.objects.create(name=nama, identifier=identifier, workspace=workspace)
    for user in anggota:
        ProjectMember.objects.get_or_create(project=project, member=user, workspace=workspace, defaults={"role": 20})
    states = {
        grup: State.objects.create(
            name=grup, group=grup, color="#000000", project=project, workspace=workspace, default=grup == "unstarted"
        )
        for grup in (StateGroup.UNSTARTED.value, StateGroup.COMPLETED.value, StateGroup.CANCELLED.value)
    }
    return project, states


def _tugas(project, state, tenggat=None):
    issue = Issue(
        name=f"Tugas {uuid4().hex[:6]}",
        workspace=project.workspace,
        project=project,
        state=state,
        target_date=tenggat,
    )
    issue.save()
    return issue


@pytest.fixture
def direktur(db, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"dir-{unik}@plane.so", username=f"dir_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=20)
    return user


@pytest.fixture
def klien(direktur):
    client = APIClient()
    client.force_authenticate(user=direktur)
    return client


@pytest.fixture
def organisasi(db, workspace, direktur):
    """Supply Chain (1 dari 4 tugas aktif terlambat = 25%), HR (lancar),
    satu project tanpa departemen, dan satu project yang direktur bukan anggotanya."""
    kemarin = timezone.localdate() - timedelta(days=1)
    besok = timezone.localdate() + timedelta(days=1)

    scm = Divisi.objects.create(workspace=workspace, kode="SCM", nama="Supply Chain")
    hr = Divisi.objects.create(workspace=workspace, kode="HR", nama="Human Resources")
    gudang = Departemen.objects.create(workspace=workspace, divisi=scm, kode="SCM-WH", nama="Gudang")
    rekrut = Departemen.objects.create(workspace=workspace, divisi=hr, kode="HR-RC", nama="Rekrutmen")

    p_gudang, s1 = _project(workspace, "Gudang", "WH", [direktur])
    p_rekrut, s2 = _project(workspace, "Rekrutmen", "RC", [direktur])
    p_lepas, s3 = _project(workspace, "Lepas", "LP", [direktur])
    p_asing, s4 = _project(workspace, "Asing", "AS", [])
    DepartemenProject.objects.create(workspace=workspace, departemen=gudang, project=p_gudang)
    DepartemenProject.objects.create(workspace=workspace, departemen=rekrut, project=p_rekrut)

    belum, selesai, batal = (StateGroup.UNSTARTED.value, StateGroup.COMPLETED.value, StateGroup.CANCELLED.value)
    # Gudang: 4 aktif (1 terlambat), 1 selesai, 1 batal yang terlambat (tidak dihitung).
    _tugas(p_gudang, s1[belum], kemarin)
    for _ in range(3):
        _tugas(p_gudang, s1[belum], besok)
    _tugas(p_gudang, s1[selesai], kemarin)
    _tugas(p_gudang, s1[batal], kemarin)
    # Rekrutmen: 2 aktif, tidak ada yang terlambat.
    _tugas(p_rekrut, s2[belum], besok)
    _tugas(p_rekrut, s2[belum])
    # Lepas: 1 aktif.
    _tugas(p_lepas, s3[belum], besok)
    # Asing: banyak terlambat, tapi bukan urusan direktur ini.
    for _ in range(5):
        _tugas(p_asing, s4[belum], kemarin)

    return {"gudang": p_gudang, "rekrut": p_rekrut, "lepas": p_lepas, "asing": p_asing, "scm": scm, "hr": hr}


@pytest.mark.unit
class TestStatusKesehatan:
    @pytest.mark.parametrize(
        "terlambat, aktif, harapan",
        [(0, 10, LANCAR), (0, 0, LANCAR), (5, 0, LANCAR), (1, 25, LANCAR), (1, 20, PERHATIAN), (3, 20, KRITIS)],
    )
    def test_ambang_bawaan(self, terlambat, aktif, harapan):
        assert status_kesehatan(terlambat, aktif, 5, 15) == harapan


@pytest.mark.contract
class TestAmbang:
    @pytest.mark.django_db
    def test_bawaan_lima_dan_lima_belas(self):
        InstanceConfiguration.objects.filter(key__in=[DASHBOARD_PERHATIAN_PERSEN, DASHBOARD_KRITIS_PERSEN]).delete()
        assert ambang_kesehatan() == (5, 15)

    @pytest.mark.django_db
    def test_ambang_tertukar_diurutkan(self):
        _simpan(DASHBOARD_PERHATIAN_PERSEN, "40")
        _simpan(DASHBOARD_KRITIS_PERSEN, "10")
        assert ambang_kesehatan() == (10, 40)


@pytest.mark.contract
class TestDashboardDivisi:
    @pytest.mark.django_db
    def test_dikelompokkan_per_divisi_dan_diurutkan(self, klien, workspace, organisasi):
        _simpan(DASHBOARD_PERHATIAN_PERSEN, "5")
        _simpan(DASHBOARD_KRITIS_PERSEN, "15")
        response = klien.get(URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data

        assert data["thresholds"] == {"attention": 5, "critical": 15}
        nama = [d["name"] for d in data["divisions"]]
        # Supply Chain kritis (25%) dulu, HR lancar, project tanpa departemen terakhir.
        assert nama == ["Supply Chain", "Human Resources", ""]

        scm = data["divisions"][0]
        assert scm["health"] == KRITIS
        assert scm["issues_active"] == 4
        assert scm["issues_overdue"] == 1
        assert scm["project_ids"] == [str(organisasi["gudang"].id)]
        # 1 selesai dari 5 (batal tidak masuk penyebut).
        assert scm["completion_rate"] == 20

        assert data["divisions"][1]["health"] == LANCAR
        assert data["divisions"][2]["id"] is None

    @pytest.mark.django_db
    def test_hanya_project_yang_dianggotai(self, klien, workspace, organisasi):
        data = klien.get(URL.format(slug=workspace.slug)).data
        ids = {p["id"] for p in data["projects"]}
        assert str(organisasi["asing"].id) not in ids
        assert data["totals"]["projects"] == 3
        assert data["totals"]["issues_overdue"] == 1

    @pytest.mark.django_db
    def test_wiki_tidak_dihitung(self, klien, workspace, direktur, organisasi):
        wiki, _ = _project(workspace, "Wiki", "WIKI", [direktur])
        data = klien.get(URL.format(slug=workspace.slug)).data
        assert str(wiki.id) not in {p["id"] for p in data["projects"]}
        assert data["totals"]["projects"] == 3

    @pytest.mark.django_db
    def test_field_lama_tetap_ada(self, klien, workspace, organisasi):
        data = klien.get(URL.format(slug=workspace.slug)).data
        for kunci in ("projects", "issues_total", "issues_open", "issues_completed", "worklog_minutes_month"):
            assert kunci in data["totals"]
        gudang = next(p for p in data["projects"] if p["identifier"] == "WH")
        assert gudang["department"]["code"] == "SCM-WH"
        assert gudang["overdue_oldest_days"] == 1
        assert gudang["issues_open"] == 5  # total 6 - selesai 1, perilaku lama
        assert gudang["completed_7d"] == 1

    @pytest.mark.django_db
    def test_ambang_dari_god_mode_mengubah_status(self, klien, workspace, organisasi):
        _simpan(DASHBOARD_PERHATIAN_PERSEN, "20")
        _simpan(DASHBOARD_KRITIS_PERSEN, "50")
        data = klien.get(URL.format(slug=workspace.slug)).data
        assert data["divisions"][0]["health"] == PERHATIAN


@pytest.mark.contract
class TestWewenangBorongan:
    """`project_boleh_diputuskan` harus memberi jawaban yang sama dengan
    `boleh_memutuskan` per project; ia hanya versi murahnya."""

    @pytest.mark.django_db
    @pytest.mark.parametrize("tingkat", [TINGKAT_DIREKTUR, TINGKAT_MEMBER, None])
    def test_sama_dengan_satu_per_satu(self, workspace, direktur, organisasi, tingkat):
        if tingkat is not None:
            JabatanOrganisasi.objects.create(workspace=workspace, member=direktur, tingkat=tingkat)
        ids = [p.id for p in Project.objects.filter(workspace=workspace)]
        satu = {pid for pid in ids if boleh_memutuskan(direktur, workspace.id, pid)}
        assert project_boleh_diputuskan(direktur, workspace.id, ids) == satu
        if tingkat == TINGKAT_DIREKTUR:
            assert satu == set(ids)

    @pytest.mark.django_db
    def test_tanpa_project(self, direktur, workspace):
        assert project_boleh_diputuskan(direktur, workspace.id, []) == set()
