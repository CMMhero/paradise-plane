# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji laporan tugas selesai untuk pimpinan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak laporan tugas selesai di Dashboard Divisi (KEP-62).

Yang dijaga:

1. Jendela periode dihitung dalam hari kantor (WIB), akhir eksklusif, dengan
   pembanding sepanjang periode yang sama tepat sebelumnya.
2. Hanya tugas grup `completed` yang selesai di dalam periode, dari project yang
   user anggotai, yang dihitung dan didaftar (judul + penanggung jawab).
3. Tepat waktu / terlambat / tanpa tenggat memakai tanggal selesai WIB.
4. Periode tak dikenal = 400; `?unduh=csv` mengirim semua baris.
"""

from datetime import date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueAssignee,
    Project,
    ProjectMember,
    State,
    StateGroup,
    User,
    WorkspaceMember,
)
from plane.utils.laporan_selesai import (
    PERIODE_30_HARI,
    PERIODE_7_HARI,
    PERIODE_BULAN_INI,
    PERIODE_BULAN_LALU,
    TANPA_TENGGAT,
    TEPAT_WAKTU,
    TERLAMBAT,
    ketepatan,
    rentang_periode,
)

URL = "/api/workspaces/{slug}/divisi-dashboard/laporan/"
WIB = ZoneInfo("Asia/Jakarta")


def _wib(hari, jam=10):
    return datetime(hari.year, hari.month, hari.day, jam, tzinfo=WIB)


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


def _tugas(project, state, nama=None, tenggat=None, selesai_pada=None, penanggung_jawab=()):
    issue = Issue(
        name=nama or f"Tugas {uuid4().hex[:6]}",
        workspace=project.workspace,
        project=project,
        state=state,
        target_date=tenggat,
    )
    issue.save()
    # update(), bukan save(): save() mengisi tenggat otomatis dan completed_at = sekarang.
    Issue.objects.filter(pk=issue.pk).update(completed_at=selesai_pada, target_date=tenggat)
    for user in penanggung_jawab:
        IssueAssignee.objects.create(issue=issue, assignee=user, project=project, workspace=project.workspace)
    return issue


@pytest.fixture
def direktur(db, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"dir-{unik}@plane.so", username=f"dir_{unik}", display_name=f"Direktur {unik}"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=20)
    return user


@pytest.fixture
def klien(direktur):
    client = APIClient()
    client.force_authenticate(user=direktur)
    return client


@pytest.fixture
def organisasi(db, workspace, direktur):
    """Gudang (divisi Supply Chain): 3 selesai minggu ini (tepat, terlambat, tanpa
    tenggat), 1 selesai 10 hari lalu, 1 dibatalkan, 1 belum selesai.
    Asing: selesai minggu ini, tapi direktur bukan anggotanya."""
    hari_ini = datetime.now(WIB).date()
    kemarin = hari_ini - timedelta(days=1)

    scm = Divisi.objects.create(workspace=workspace, kode="SCM", nama="Supply Chain")
    gudang_dep = Departemen.objects.create(workspace=workspace, divisi=scm, kode="SCM-WH", nama="Gudang")
    p_gudang, s = _project(workspace, "Gudang", "WH", [direktur])
    p_asing, s2 = _project(workspace, "Asing", "AS", [])
    DepartemenProject.objects.create(workspace=workspace, departemen=gudang_dep, project=p_gudang)

    selesai, belum, batal = (StateGroup.COMPLETED.value, StateGroup.UNSTARTED.value, StateGroup.CANCELLED.value)
    tepat = _tugas(
        p_gudang, s[selesai], "Stok opname", tenggat=hari_ini, selesai_pada=_wib(kemarin), penanggung_jawab=[direktur]
    )
    _tugas(p_gudang, s[selesai], "Kirim PO", tenggat=kemarin - timedelta(days=1), selesai_pada=_wib(kemarin, 9))
    _tugas(p_gudang, s[selesai], "Rapikan rak", selesai_pada=_wib(hari_ini, 8))
    _tugas(p_gudang, s[selesai], "Lama", selesai_pada=_wib(hari_ini - timedelta(days=10)))
    _tugas(p_gudang, s[batal], "Dibatalkan", selesai_pada=_wib(kemarin))
    _tugas(p_gudang, s[belum], "Belum")
    _tugas(p_asing, s2[selesai], "Rahasia", selesai_pada=_wib(kemarin))
    return {"gudang": p_gudang, "asing": p_asing, "tepat": tepat}


@pytest.mark.unit
class TestRentangPeriode:
    def test_tujuh_hari_termasuk_hari_ini(self):
        (awal, akhir), (awal_lalu, akhir_lalu) = rentang_periode(PERIODE_7_HARI, date(2026, 11, 3))
        assert (awal, akhir) == (date(2026, 10, 28), date(2026, 11, 4))
        assert (awal_lalu, akhir_lalu) == (date(2026, 10, 21), date(2026, 10, 28))

    def test_tiga_puluh_hari(self):
        (awal, akhir), _ = rentang_periode(PERIODE_30_HARI, date(2026, 11, 3))
        assert (akhir - awal).days == 30

    def test_bulan_ini_dan_pembandingnya(self):
        (awal, akhir), (awal_lalu, akhir_lalu) = rentang_periode(PERIODE_BULAN_INI, date(2026, 3, 15))
        assert (awal, akhir) == (date(2026, 3, 1), date(2026, 3, 16))
        assert (awal_lalu, akhir_lalu) == (date(2026, 2, 1), date(2026, 3, 1))

    def test_bulan_lalu_melewati_tahun(self):
        (awal, akhir), (awal_lalu, _) = rentang_periode(PERIODE_BULAN_LALU, date(2026, 1, 10))
        assert (awal, akhir) == (date(2025, 12, 1), date(2026, 1, 1))
        assert awal_lalu == date(2025, 11, 1)

    def test_periode_asing_ditolak(self):
        with pytest.raises(ValueError):
            rentang_periode("1y", date(2026, 1, 1))

    @pytest.mark.parametrize(
        "selesai, tenggat, harapan",
        [
            (date(2026, 1, 5), date(2026, 1, 5), TEPAT_WAKTU),
            (date(2026, 1, 6), date(2026, 1, 5), TERLAMBAT),
            (date(2026, 1, 6), None, TANPA_TENGGAT),
        ],
    )
    def test_ketepatan(self, selesai, tenggat, harapan):
        assert ketepatan(selesai, tenggat) == harapan


@pytest.mark.contract
class TestLaporanSelesai:
    @pytest.mark.django_db
    def test_angka_dan_daftar_tujuh_hari(self, klien, workspace, organisasi):
        response = klien.get(URL.format(slug=workspace.slug), {"periode": PERIODE_7_HARI})
        assert response.status_code == status.HTTP_200_OK, response.data
        data = response.data

        totals = data["totals"]
        assert totals["completed"] == 3
        assert (totals["on_time"], totals["late"], totals["no_due_date"]) == (1, 1, 1)
        # Tanpa tenggat tidak masuk penyebut: 1 dari 2.
        assert totals["on_time_rate"] == 50
        assert data["previous"]["completed"] == 1
        assert data["items_truncated"] is False

        judul = {i["name"] for i in data["items"]}
        assert judul == {"Stok opname", "Kirim PO", "Rapikan rak"}
        # Terbaru dulu.
        assert data["items"][0]["name"] == "Rapikan rak"
        stok = next(i for i in data["items"] if i["name"] == "Stok opname")
        assert stok["timing"] == TEPAT_WAKTU
        assert stok["project_identifier"] == "WH"
        assert len(stok["assignees"]) == 1

        [divisi] = data["divisions"]
        assert divisi["name"] == "Supply Chain"
        assert divisi["completed"] == 3
        assert divisi["projects"][0]["department"]["code"] == "SCM-WH"

    @pytest.mark.django_db
    def test_project_bukan_anggota_tidak_ikut(self, klien, workspace, organisasi):
        data = klien.get(URL.format(slug=workspace.slug)).data
        assert "Rahasia" not in {i["name"] for i in data["items"]}
        assert str(organisasi["asing"].id) not in {i["project_id"] for i in data["items"]}

    @pytest.mark.django_db
    def test_tiga_puluh_hari_memuat_yang_lama(self, klien, workspace, organisasi):
        data = klien.get(URL.format(slug=workspace.slug), {"periode": PERIODE_30_HARI}).data
        assert data["totals"]["completed"] == 4

    @pytest.mark.django_db
    def test_periode_salah_400(self, klien, workspace, organisasi):
        response = klien.get(URL.format(slug=workspace.slug), {"periode": "1y"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_csv_berisi_semua_baris(self, klien, workspace, organisasi):
        response = klien.get(URL.format(slug=workspace.slug), {"periode": PERIODE_7_HARI, "unduh": "csv"})
        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("text/csv")
        isi = response.content.decode("utf-8-sig").strip().splitlines()
        assert isi[0].startswith("Divisi,Departemen,Project,Nomor,Judul")
        assert len(isi) == 4
        assert any("Stok opname" in b and "Tepat waktu" in b and "Supply Chain" in b for b in isi)
