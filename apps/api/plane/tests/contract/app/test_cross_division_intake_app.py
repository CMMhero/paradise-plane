# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes kontrak permintaan lintas divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak: permintaan tugas lintas divisi.

Yang dibuktikan di sini bukan cuma "yang boleh bisa", tapi juga **yang tidak
boleh memang tidak bisa** -- dan itu bagian yang paling mudah hilang saat
seseorang merapikan kode enam bulan lagi.

Kontrol negatif yang dikunci:

* Peminta (anggota divisi asal) TIDAK bisa membaca daftar Intake divisi tujuan.
* Peminta TIDAK bisa membaca work item divisi tujuan secara langsung.
* Peminta TIDAK bisa mengubah status permintaannya sendiri di divisi tujuan.
* Anggota workspace yang BUKAN anggota divisi asal tidak bisa menulis
  permintaan atas nama divisi itu.
* Divisi tujuan yang mematikan Intake ditolak (yang menyala tapi belum punya
  wadah `Intake` justru diterima: wadahnya dibuat).
* Staf departemen tujuan tidak ikut melihat permintaan yang masuk; hanya atasan.
* Work item di divisi tujuan lahir dengan `created_by = NULL` -- kalau ini
  berubah, peminta mendapat hak `destroy` lewat
  `plane/app/views/intake/base.py:553`.

Rancangan lengkap + alasannya: `.herdr/crossdiv-desain.md`.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    Intake,
    IntakeIssue,
    Issue,
    JabatanOrganisasi,
    PermintaanLintasDivisi,
    Project,
    ProjectMember,
    State,
    StateGroup,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)

URL_PERMINTAAN = "/api/workspaces/{slug}/cross-division/permintaan/"
URL_TUJUAN = "/api/workspaces/{slug}/cross-division/tujuan/"
URL_RINGKASAN = "/api/workspaces/{slug}/cross-division/ringkasan/"
# `IntakeIssueViewSet` memakai id WORK ITEM sebagai `pk`, bukan id intake-issue
# (lihat `issue_id=pk` di plane/app/views/intake/base.py:335).
URL_INTAKE_LIST = "/api/workspaces/{slug}/projects/{project_id}/intake-issues/"
URL_INTAKE_PATCH = "/api/workspaces/{slug}/projects/{project_id}/inbox-issues/{issue_id}/"
URL_ISSUE_TERBACA = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"


def _baris(response):
    """Isi hasil, apa pun bentuk amplop paginasi bawaan Plane."""
    data = response.json()
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    return data


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so",
        username=f"{prefix}_{unik}",
        first_name=prefix.capitalize(),
        last_name="Uji",
    )
    user.set_password("test-password")
    user.save()
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# --------------------------------------------------------------------------
# Fixtures: dua divisi + satu orang luar
# --------------------------------------------------------------------------


@pytest.fixture
def tender_user(db, workspace):
    user = _buat_user("tender")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


@pytest.fixture
def it_user(db, workspace):
    user = _buat_user("it")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=20)
    return user


@pytest.fixture
def outsider_user(db, workspace):
    user = _buat_user("luar")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


@pytest.fixture
def tender_project(db, workspace, tender_user):
    project = Project.objects.create(name="Tender", identifier="TNDR", workspace=workspace, created_by=tender_user)
    ProjectMember.objects.create(project=project, member=tender_user, workspace=workspace, role=15)
    return project


@pytest.fixture
def it_project(db, workspace, it_user):
    """Divisi tujuan yang SUDAH menyalakan Intake."""
    project = Project.objects.create(
        name="Teknologi Informasi", identifier="ITS", workspace=workspace, created_by=it_user
    )
    ProjectMember.objects.create(project=project, member=it_user, workspace=workspace, role=20)
    Intake.objects.create(name="IT Intake", project=project, is_default=True)
    # Dibutuhkan jalur terima bawaan: `IntakeIssueSerializer.update` memindahkan
    # work item dari `triage` ke state `default` project.
    State.objects.create(
        name="Todo",
        group=StateGroup.UNSTARTED.value,
        color="#60646C",
        project=project,
        workspace=workspace,
        default=True,
    )
    return project


@pytest.fixture
def intake_off_project(db, workspace, it_user):
    """Divisi yang mematikan Intake -- bukan tujuan yang sah."""
    project = Project.objects.create(
        name="Intake Mati", identifier="NOI", workspace=workspace, created_by=it_user, intake_view=False
    )
    ProjectMember.objects.create(project=project, member=it_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def no_wadah_project(db, workspace, it_user):
    """Departemen dari God Mode sebelum perbaikan: Intake menyala, baris `Intake` tidak ada."""
    project = Project.objects.create(name="Gudang", identifier="GDG", workspace=workspace, created_by=it_user)
    ProjectMember.objects.create(project=project, member=it_user, workspace=workspace, role=20)
    return project


@pytest.fixture
def tender_client(tender_user):
    return _klien(tender_user)


@pytest.fixture
def it_client(it_user):
    return _klien(it_user)


@pytest.fixture
def outsider_client(outsider_user):
    return _klien(outsider_user)


def _kirim(client, workspace, asal_project, tujuan_project, **tambahan):
    payload = {
        "asal_project": str(asal_project.id),
        "tujuan_project": str(tujuan_project.id),
        "judul": "Siapkan akun dokumen tender",
        "prioritas": "high",
    }
    payload.update(tambahan)
    return client.post(URL_PERMINTAAN.format(slug=workspace.slug), payload, format="json")


# --------------------------------------------------------------------------
# Jalur bahagia
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPermintaanLintasDivisi:
    @pytest.mark.django_db
    def test_staf_tender_mengirim_permintaan_ke_intake_it(
        self, tender_client, workspace, tender_project, it_project, tender_user
    ):
        response = _kirim(
            tender_client,
            workspace,
            tender_project,
            it_project,
            catatan="Nomor tender 123/PP/2026",
        )

        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        data = response.json()
        assert data["status_permintaan"] == "menunggu"
        assert data["status_tugas"] == "belum_diterima"
        assert data["nomor_tugas_tujuan"] is None
        assert data["asal"]["identifier"] == "TNDR"
        assert data["tujuan"]["identifier"] == "ITS"

        intake_issue = IntakeIssue.objects.get(project=it_project, source="CROSSDIV")
        assert intake_issue.created_by_id == tender_user.id
        assert intake_issue.extra["crossdiv"]["asal_identifier"] == "TNDR"

        # Kunci keamanan: work item di divisi tujuan TIDAK punya pembuat, supaya
        # peminta tidak mendapat hak apa pun atasnya (`destroy` memakai
        # `creator=True` tanpa penjaga keanggotaan).
        issue = Issue.objects.get(pk=intake_issue.issue_id)
        assert issue.created_by_id is None, "created_by harus NULL; lihat catatan di views/issue/cross_division.py"
        assert issue.state.group == StateGroup.TRIAGE.value

        permintaan = PermintaanLintasDivisi.objects.get()
        assert permintaan.asal_project_id == tender_project.id
        assert permintaan.tujuan_project_id == it_project.id
        assert permintaan.intake_issue_id == intake_issue.id

    @pytest.mark.django_db
    def test_divisi_tujuan_melihat_permintaan_lewat_inbox_yang_sudah_ada(
        self, tender_client, it_client, workspace, tender_project, it_project
    ):
        assert _kirim(tender_client, workspace, tender_project, it_project).status_code == status.HTTP_201_CREATED
        intake_issue = IntakeIssue.objects.get(project=it_project, source="CROSSDIV")

        response = it_client.get(URL_INTAKE_LIST.format(slug=workspace.slug, project_id=it_project.id))

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        issue_ids = {row["issue"]["id"] for row in _baris(response)}
        assert str(intake_issue.issue_id) in issue_ids

    @pytest.mark.django_db
    def test_divisi_tujuan_menerima_lewat_jalur_intake_lama(
        self, tender_client, it_client, workspace, tender_project, it_project
    ):
        _kirim(tender_client, workspace, tender_project, it_project)
        intake_issue = IntakeIssue.objects.get(project=it_project, source="CROSSDIV")

        response = it_client.patch(
            URL_INTAKE_PATCH.format(slug=workspace.slug, project_id=it_project.id, issue_id=intake_issue.issue_id),
            {"status": 1},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        intake_issue.refresh_from_db()
        assert intake_issue.status == 1
        issue = Issue.objects.get(pk=intake_issue.issue_id)
        assert issue.state.group == StateGroup.UNSTARTED.value, "terima harus memindahkan item keluar dari triage"

        # Peminta melihat kemajuannya, tanpa pernah menyentuh project IT.
        daftar = tender_client.get(URL_PERMINTAAN.format(slug=workspace.slug))
        assert daftar.status_code == status.HTTP_200_OK
        baris = _baris(daftar)
        assert len(baris) == 1
        assert baris[0]["status_permintaan"] == "diterima"
        assert baris[0]["status_tugas"] == "terbuka"
        assert baris[0]["nomor_tugas_tujuan"] == f"ITS-{issue.sequence_id}"

    @pytest.mark.django_db
    def test_daftar_tujuan_hanya_divisi_yang_menyalakan_intake(
        self, tender_client, workspace, it_project, intake_off_project
    ):
        response = tender_client.get(URL_TUJUAN.format(slug=workspace.slug))

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        ids = {row["id"] for row in response.json()}
        assert str(it_project.id) in ids
        assert str(intake_off_project.id) not in ids

    @pytest.mark.django_db
    def test_departemen_tanpa_wadah_intake_tetap_bisa_diminta(
        self, tender_client, workspace, tender_project, no_wadah_project
    ):
        ids = {row["id"] for row in tender_client.get(URL_TUJUAN.format(slug=workspace.slug)).json()}
        assert str(no_wadah_project.id) in ids

        response = _kirim(tender_client, workspace, tender_project, no_wadah_project)

        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)
        intake = Intake.objects.get(project=no_wadah_project, is_default=True)
        assert IntakeIssue.objects.filter(intake=intake, source="CROSSDIV").count() == 1

    @pytest.mark.django_db
    def test_peminta_melihat_arah_keluar(self, tender_client, workspace, tender_project, it_project, tender_user):
        _kirim(tender_client, workspace, tender_project, it_project)

        baris = _baris(tender_client.get(URL_PERMINTAAN.format(slug=workspace.slug)))

        assert len(baris) == 1
        assert baris[0]["arah"] == "keluar"
        assert baris[0]["peminta"] == tender_user.display_name


def _jadikan_departemen(workspace, project, kode):
    divisi = Divisi.objects.create(workspace=workspace, kode=f"D{kode}", nama=f"Divisi {kode}")
    dep = Departemen.objects.create(workspace=workspace, divisi=divisi, kode=kode, nama=f"Departemen {kode}")
    DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=project)
    return divisi, dep


def _tempatkan(workspace, tingkat, departemen=None, divisi=None):
    user = _buat_user(f"t{tingkat}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    JabatanOrganisasi.objects.create(
        workspace=workspace, member=user, tingkat=tingkat, departemen=departemen, divisi=divisi
    )
    return user


@pytest.mark.contract
class TestPermintaanMasukAtasan:
    """Keputusan pemilik produk: atasan departemen tujuan melihat permintaan yang masuk."""

    @pytest.mark.django_db
    def test_supervisor_dan_manager_tujuan_melihat_permintaan_masuk(
        self, tender_client, workspace, tender_project, it_project
    ):
        divisi, dep = _jadikan_departemen(workspace, it_project, "ITS")
        supervisor = _tempatkan(workspace, TINGKAT_SUPERVISOR, departemen=dep)
        manager = _tempatkan(workspace, TINGKAT_MANAGER, divisi=divisi)
        assert _kirim(tender_client, workspace, tender_project, it_project).status_code == status.HTTP_201_CREATED

        for atasan in (supervisor, manager):
            baris = _baris(_klien(atasan).get(URL_PERMINTAAN.format(slug=workspace.slug)))
            assert len(baris) == 1, atasan.email
            assert baris[0]["arah"] == "masuk"
            assert baris[0]["tujuan"]["id"] == str(it_project.id)

    @pytest.mark.django_db
    def test_staf_tujuan_dan_orang_luar_tidak_melihat_permintaan_masuk(
        self, tender_client, outsider_client, workspace, tender_project, it_project
    ):
        _, dep = _jadikan_departemen(workspace, it_project, "ITS")
        staf = _tempatkan(workspace, TINGKAT_MEMBER, departemen=dep)
        _kirim(tender_client, workspace, tender_project, it_project)

        assert _baris(_klien(staf).get(URL_PERMINTAAN.format(slug=workspace.slug))) == []
        assert _baris(outsider_client.get(URL_PERMINTAAN.format(slug=workspace.slug))) == []


# --------------------------------------------------------------------------
# Kontrol negatif
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestKontrolNegatifLintasDivisi:
    @pytest.mark.django_db
    def test_peminta_tidak_bisa_membaca_inbox_divisi_tujuan(self, tender_client, workspace, tender_project, it_project):
        _kirim(tender_client, workspace, tender_project, it_project)

        response = tender_client.get(URL_INTAKE_LIST.format(slug=workspace.slug, project_id=it_project.id))

        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"Peminta menembus inbox divisi tujuan: {getattr(response, 'data', None)!r}"
        )

    @pytest.mark.django_db
    def test_peminta_tidak_bisa_membaca_work_item_divisi_tujuan(
        self, tender_client, workspace, tender_project, it_project
    ):
        _kirim(tender_client, workspace, tender_project, it_project)
        intake_issue = IntakeIssue.objects.get(project=it_project, source="CROSSDIV")

        response = tender_client.get(
            URL_ISSUE_TERBACA.format(slug=workspace.slug, project_id=it_project.id, issue_id=intake_issue.issue_id)
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"Peminta membaca work item divisi tujuan: {getattr(response, 'data', None)!r}"
        )

    @pytest.mark.django_db
    def test_peminta_tidak_bisa_mengubah_status_permintaannya_sendiri(
        self, tender_client, workspace, tender_project, it_project
    ):
        _kirim(tender_client, workspace, tender_project, it_project)
        intake_issue = IntakeIssue.objects.get(project=it_project, source="CROSSDIV")

        response = tender_client.patch(
            URL_INTAKE_PATCH.format(slug=workspace.slug, project_id=it_project.id, issue_id=intake_issue.issue_id),
            {"status": 1},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"Peminta menerima permintaannya sendiri: {getattr(response, 'data', None)!r}"
        )
        intake_issue.refresh_from_db()
        assert intake_issue.status == -2

    @pytest.mark.django_db
    def test_bukan_anggota_divisi_asal_tidak_bisa_mengatasnamakan_divisi_itu(
        self, outsider_client, workspace, tender_project, it_project
    ):
        response = _kirim(outsider_client, workspace, tender_project, it_project)

        assert response.status_code == status.HTTP_403_FORBIDDEN, (
            f"Orang luar menulis atas nama Tender: {getattr(response, 'data', None)!r}"
        )
        assert response.json()["error_code"] == "not_origin_member"
        assert IntakeIssue.objects.filter(project=it_project).count() == 0

    @pytest.mark.django_db
    def test_divisi_tujuan_intake_mati_ditolak(self, tender_client, workspace, tender_project, intake_off_project):
        response = _kirim(tender_client, workspace, tender_project, intake_off_project)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == "intake_off"
        assert response.json()["params"] == {"name": intake_off_project.name}
        assert IntakeIssue.objects.filter(project=intake_off_project).count() == 0
        assert not Intake.objects.filter(project=intake_off_project).exists()

    @pytest.mark.django_db
    def test_tidak_bisa_meminta_ke_divisi_sendiri(self, tender_client, workspace, tender_project):
        response = _kirim(tender_client, workspace, tender_project, tender_project)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_ringkasan_tidak_membocorkan_divisi_lain(
        self, tender_client, it_client, outsider_client, workspace, tender_project, it_project
    ):
        _kirim(tender_client, workspace, tender_project, it_project)

        ringkasan_tender = tender_client.get(URL_RINGKASAN.format(slug=workspace.slug)).json()
        assert ringkasan_tender[str(tender_project.id)]["keluar_menunggu"] == 1
        assert str(it_project.id) not in ringkasan_tender

        ringkasan_it = it_client.get(URL_RINGKASAN.format(slug=workspace.slug)).json()
        assert ringkasan_it[str(it_project.id)]["masuk_menunggu"] == 1
        assert str(tender_project.id) not in ringkasan_it

        assert outsider_client.get(URL_RINGKASAN.format(slug=workspace.slug)).json() == {}

    @pytest.mark.django_db
    def test_ringkasan_memindahkan_hitungan_setelah_diterima(
        self, tender_client, it_client, workspace, tender_project, it_project
    ):
        _kirim(tender_client, workspace, tender_project, it_project)
        intake_issue = IntakeIssue.objects.get(project=it_project, source="CROSSDIV")
        it_client.patch(
            URL_INTAKE_PATCH.format(slug=workspace.slug, project_id=it_project.id, issue_id=intake_issue.issue_id),
            {"status": 1},
            format="json",
        )

        ringkasan = it_client.get(URL_RINGKASAN.format(slug=workspace.slug)).json()
        assert ringkasan[str(it_project.id)]["masuk_menunggu"] == 0
        assert ringkasan[str(it_project.id)]["masuk_terbuka"] == 1
