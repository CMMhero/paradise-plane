# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji aturan tenggat di endpoint
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak: siapa boleh menggeser Due Date (tenggat) sebuah tugas.

Aturan dari pemilik instance (`plane/utils/task_access.py`):

    ganti Due Date  HANYA pembuatnya atau Super Admin

Dua hal yang dikunci berkas ini, dan keduanya hanya bisa dibuktikan lewat
endpoint sungguhan — unit test atas helper-nya tidak bisa:

1. **Assignee TIDAK bisa menggeser tenggat**, walau ia boleh mengubah properti
   lain. Kalau aturan ini kabur, biasanya gara-gara seseorang "menyederhanakan"
   hak ubah jadi satu.
2. **Menyertakan `target_date` yang TIDAK berubah bukan pelanggaran.** Beberapa
   layar mengirim ulang seluruh formulir; menolak berdasarkan keberadaan field
   akan mengunci assignee dari semua perubahan.

Pengecualian intake (keputusan user 2026-10-29): selama tugas masih di antrean
triase, penanggung jawab intake (admin project) ikut boleh mengatur tenggat —
karena di antrean itu-lah tenggat dijanjikan pertama kali. Setelah tugas masuk
papan, aturan biasa kembali berlaku.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Intake,
    IntakeIssue,
    Issue,
    IssueAssignee,
    Project,
    ProjectMember,
    State,
    StateGroup,
    User,
    WorkspaceMember,
)
from plane.db.models.api import APIToken

URL_ISSUE = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
URL_TENGGAT_BULK = "/api/workspaces/{slug}/projects/{project_id}/issue-dates/"
URL_INTAKE_APP = "/api/workspaces/{slug}/projects/{project_id}/intake-issues/{issue_id}/"
URL_INTAKE_V1 = "/api/v1/workspaces/{slug}/projects/{project_id}/intake-issues/{issue_id}/"

TENGGAT_LAMA = "2026-11-15"
TENGGAT_BARU = "2026-11-25"


# ---------------------------------------------------------------------------
# Pembantu
# ---------------------------------------------------------------------------


def _buat_user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so",
        username=f"{prefix}_{unik}",
        first_name=prefix.capitalize(),
        last_name="Uji",
    )
    user.set_password("test-password")
    user.save()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _klien_api(user):
    """Klien untuk pintu API v1, yang memakai API token (bukan sesi)."""
    token = f"tenggat-{uuid4().hex[:16]}"
    APIToken.objects.create(label="Tes Tenggat", user=user, token=token)
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token)
    return client


def _tanggal(issue):
    return str(issue.target_date) if issue.target_date else None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pembuat(db, workspace):
    """Pembuat tugas. Anggota project biasa (role 15)."""
    return _buat_user("pembuat", workspace)


@pytest.fixture
def penerima(db, workspace):
    """Assignee tugas, bukan pembuatnya. Role 15, bukan admin project."""
    return _buat_user("penerima", workspace)


@pytest.fixture
def penanggung(db, workspace):
    """Admin project (role 20), bukan pembuat, bukan admin workspace."""
    return _buat_user("penanggung", workspace)


@pytest.fixture
def project(db, workspace, pembuat, penerima, penanggung):
    project = Project.objects.create(name="Proyek Tenggat", identifier="TG", workspace=workspace, created_by=pembuat)
    for user, role in ((pembuat, 15), (penerima, 15), (penanggung, 20)):
        ProjectMember.objects.create(project=project, member=user, workspace=workspace, role=role)
    return project


@pytest.fixture
def state(db, workspace, project):
    return State.objects.create(
        name="Todo",
        group=StateGroup.UNSTARTED.value,
        color="#60646C",
        project=project,
        workspace=workspace,
        default=True,
    )


@pytest.fixture
def tugas(db, workspace, project, state, pembuat, penerima):
    """Tugas yang dibuat `pembuat` dan di-assign ke `penerima`."""
    issue = Issue(
        name="Tugas dengan tenggat",
        workspace=workspace,
        project=project,
        state=state,
        target_date=TENGGAT_LAMA,
    )
    # `BaseModel.save` mengisi `created_by` dari pengguna request (None/anonymous
    # di test), jadi kwarg `created_by=` ke `create` akan ditimpa. Lewat sini.
    issue.save(created_by_id=pembuat.id)
    IssueAssignee.objects.create(issue=issue, assignee=penerima, project=project, workspace=workspace)
    return issue


@pytest.fixture
def intake(db, workspace, project):
    return Intake.objects.create(name="Intake TG", project=project, workspace=workspace, is_default=True)


@pytest.fixture
def tugas_intake(db, workspace, project, state, pembuat, penerima, intake):
    """Tugas yang sama, tapi masih berada di antrean intake."""
    issue = Issue(
        name="Permintaan masuk",
        workspace=workspace,
        project=project,
        state=state,
        target_date=TENGGAT_LAMA,
    )
    issue.save(created_by_id=pembuat.id)
    IssueAssignee.objects.create(issue=issue, assignee=penerima, project=project, workspace=workspace)
    IntakeIssue.objects.create(workspace=workspace, project=project, intake=intake, issue=issue, source="IN_APP")
    return issue


# ---------------------------------------------------------------------------
# Papan: aturan biasa — hanya pembuat yang boleh menggeser
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestAturanTenggatDiPapan:
    @pytest.mark.django_db
    def test_pembuat_boleh_menggeser_tenggat(self, workspace, project, tugas, pembuat):
        response = _klien(pembuat).patch(
            URL_ISSUE.format(slug=workspace.slug, project_id=project.id, issue_id=tugas.id),
            {"target_date": TENGGAT_BARU},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert _tanggal(tugas) == TENGGAT_BARU

    @pytest.mark.django_db
    def test_penerima_atau_siapa_pun_yang_bukan_pembuat_ditolak(self, workspace, project, tugas, penerima):
        """Kontrol negatif: assignee — dan bukan pembuat — TIDAK boleh menggeser."""
        response = _klien(penerima).patch(
            URL_ISSUE.format(slug=workspace.slug, project_id=project.id, issue_id=tugas.id),
            {"target_date": TENGGAT_BARU},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert _tanggal(tugas) == TENGGAT_LAMA, "tenggat tidak boleh berubah walau request sudah ditolak"

    @pytest.mark.django_db
    def test_admin_project_bukan_pembuat_juga_ditolak(self, workspace, project, tugas, penanggung):
        """Hak ganti tenggat sengaja LEBIH KETAT daripada hak hapus."""
        response = _klien(penanggung).patch(
            URL_ISSUE.format(slug=workspace.slug, project_id=project.id, issue_id=tugas.id),
            {"target_date": TENGGAT_BARU},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert _tanggal(tugas) == TENGGAT_LAMA

    @pytest.mark.django_db
    def test_penerima_boleh_mengubah_properti_lain_dengan_tenggat_ikut_terkirim(
        self, workspace, project, tugas, penerima
    ):
        """Kunci kedua: payload yang MENYERTAKAN tenggat tak-berubah bukan pelanggaran."""
        response = _klien(penerima).patch(
            URL_ISSUE.format(slug=workspace.slug, project_id=project.id, issue_id=tugas.id),
            {"priority": "high", "target_date": TENGGAT_LAMA},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert tugas.priority == "high"
        assert _tanggal(tugas) == TENGGAT_LAMA


# ---------------------------------------------------------------------------
# Papan: seret di Gantt/kalender lewat endpoint bulk
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestAturanTenggatBulkDates:
    @pytest.mark.django_db
    def test_penerima_ditolak_di_endpoint_bulk(self, workspace, project, tugas, penerima):
        response = _klien(penerima).post(
            URL_TENGGAT_BULK.format(slug=workspace.slug, project_id=project.id),
            {"updates": [{"id": str(tugas.id), "target_date": TENGGAT_BARU}]},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert _tanggal(tugas) == TENGGAT_LAMA

    @pytest.mark.django_db
    def test_pembuat_boleh_di_endpoint_bulk(self, workspace, project, tugas, pembuat):
        response = _klien(pembuat).post(
            URL_TENGGAT_BULK.format(slug=workspace.slug, project_id=project.id),
            {"updates": [{"id": str(tugas.id), "target_date": TENGGAT_BARU}]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        tugas.refresh_from_db()
        assert _tanggal(tugas) == TENGGAT_BARU


# ---------------------------------------------------------------------------
# Intake: pengecualian triage — penanggung jawab intake ikut boleh
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestAturanTenggatIntake:
    @pytest.mark.django_db
    def test_pembuat_masih_boleh_lewat_pintu_intake(self, workspace, project, tugas_intake, pembuat):
        response = _klien(pembuat).patch(
            URL_INTAKE_APP.format(slug=workspace.slug, project_id=project.id, issue_id=tugas_intake.id),
            {"issue": {"target_date": TENGGAT_BARU}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        tugas_intake.refresh_from_db()
        assert _tanggal(tugas_intake) == TENGGAT_BARU

    @pytest.mark.django_db
    def test_penerima_bukan_pembuat_ditolak_lewat_pintu_app(self, workspace, project, tugas_intake, penerima):
        """Walau jadi assignee, member bukan pembuat dan bukan penanggung jawab.

        Pintu app menolaknya lewat lapisan izin (hanya admin project atau
        pembuat yang boleh menyentuh intake), dan aturan tenggat tetap berlaku
        di belakangnya. Tanggalnya wajib utuh.
        """
        response = _klien(penerima).patch(
            URL_INTAKE_APP.format(slug=workspace.slug, project_id=project.id, issue_id=tugas_intake.id),
            {"issue": {"target_date": TENGGAT_BARU}},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        tugas_intake.refresh_from_db()
        assert _tanggal(tugas_intake) == TENGGAT_LAMA

    @pytest.mark.django_db
    def test_admin_yang_tidak_terlibat_masih_ditahan_gerbang_hierarki(
        self, workspace, project, tugas_intake, penanggung
    ):
        """Gerbang hierarki (KEP-25) berjalan SEBELUM aturan tenggat.

        Admin project yang bukan pembuat, bukan assignee, dan bukan atasannya
        siapa pun yang terlibat tidak boleh menyentuh tugas itu sama sekali —
        jadi pengecualian intake untuk penanggung jawab tidak sempat berlaku di
        pintu app. Pengecualian itu nyata di pintu API v1 (lihat tes di bawah),
        yang tidak melewati serializer hierarki.
        """
        response = _klien(penanggung).patch(
            URL_INTAKE_APP.format(slug=workspace.slug, project_id=project.id, issue_id=tugas_intake.id),
            {"issue": {"target_date": TENGGAT_BARU}},
            format="json",
        )

        assert response.status_code != status.HTTP_200_OK, getattr(response, "data", None)
        tugas_intake.refresh_from_db()
        assert _tanggal(tugas_intake) == TENGGAT_LAMA

    @pytest.mark.django_db
    def test_anggota_biasa_penerima_ditolak_lewat_pintu_api(self, workspace, project, tugas_intake, penerima):
        """Pintu API v1 tidak membatasi peran seperti pintu app — di situlah
        pengecualian intake harus dijaga: member bukan penanggung jawab."""
        response = _klien_api(penerima).patch(
            URL_INTAKE_V1.format(slug=workspace.slug, project_id=project.id, issue_id=tugas_intake.id),
            {"issue": {"target_date": TENGGAT_BARU}},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN, getattr(response, "data", None)
        tugas_intake.refresh_from_db()
        assert _tanggal(tugas_intake) == TENGGAT_LAMA

    @pytest.mark.django_db
    def test_penanggung_jawab_intake_boleh_lewat_pintu_api(self, workspace, project, tugas_intake, penanggung):
        response = _klien_api(penanggung).patch(
            URL_INTAKE_V1.format(slug=workspace.slug, project_id=project.id, issue_id=tugas_intake.id),
            {"issue": {"target_date": TENGGAT_BARU}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        tugas_intake.refresh_from_db()
        assert _tanggal(tugas_intake) == TENGGAT_BARU

    @pytest.mark.django_db
    def test_anggota_biasa_boleh_properti_lain_asal_tenggat_tidak_berubah(
        self, workspace, project, tugas_intake, penerima
    ):
        response = _klien_api(penerima).patch(
            URL_INTAKE_V1.format(slug=workspace.slug, project_id=project.id, issue_id=tugas_intake.id),
            {"issue": {"priority": "high", "target_date": TENGGAT_LAMA}},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        tugas_intake.refresh_from_db()
        assert tugas_intake.priority == "high"
        assert _tanggal(tugas_intake) == TENGGAT_LAMA
