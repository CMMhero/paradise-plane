# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: auto-assign, penempatan assignee, komentar ikut hak ubah
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# ruff: noqa: F811  (fixture `org` diimpor lalu dipakai sebagai parameter, pola pytest)

"""Tiga keputusan user 2026-11-17.

Bentuk uji (fixture `org` dari test_persetujuan_manager_app):

    SALES -> SMT1 (P1) · SMT2 (P2)
    manager di divisi Sales, staf di SMT1, sup2 di SMT2, direktur tanpa tempat

ditambah tiga orang dengan akses tetapi tanpa penempatan di SMT1:

    admin_ws     admin workspace, anggota eksplisit P1, TIDAK ditempatkan
    sa           Super Admin, anggota P1 lewat sinkron, TIDAK ditempatkan
    admin_staf   admin workspace yang JUGA staf di SMT1

Yang dikunci:

1. Auto-assign: pembuat tanpa assignee jadi assignee-nya, untuk semua orang yang
   sah di project itu, tanpa bergantung pada katup gerbang. Yang tidak sah (admin
   tanpa penempatan) tetap bisa membuat tugas, hanya tanpa auto-assign.
2. Komentar, balasan, dan reaksi mengikuti hak ubah (`galat_ubah_tugas`).
3. Penerima tugas harus ditempatkan di departemen/divisi project itu, juga saat
   yang menugaskan admin workspace atau Super Admin. Assignee lama tidak
   diperiksa ulang.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Issue,
    IssueAssignee,
    IssueComment,
    JabatanOrganisasi,
    ProjectMember,
    TINGKAT_MEMBER,
    WorkspaceMember,
)
from plane.db.superadmin import sinkronkan_super_admin
from plane.license.models import Instance, InstanceAdmin
from plane.tests.contract.app.test_persetujuan_manager_app import (  # noqa: F401
    URL_ISSUE_DETAIL,
    URL_ISSUES,
    _klien,
    _user,
    org,
)
from plane.utils.hierarki import (
    FLAG_GERBANG,
    ditempatkan_ids,
    galat_penugasan,
    penerima_otomatis,
)

URL_KOMENTAR = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/comments/"
URL_REAKSI = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/reactions/"
URL_REAKSI_KOMENTAR = "/api/workspaces/{slug}/projects/{project_id}/comments/{comment_id}/reactions/"
URL_KUASA = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/bisa-ditugaskan/"
URL_V1_ISSUES = "/api/v1/workspaces/{slug}/projects/{project_id}/issues/"


def _jadikan_admin_ws(org, user):
    WorkspaceMember.objects.filter(workspace=org.ws, member=user).update(role=20)


@pytest.fixture
def akses(org):
    """Tiga orang dengan akses ke P1 tanpa (atau dengan) penempatan di SMT1."""
    a = type("Akses", (), {})()
    a.admin_ws = _user("adminws", org.ws)
    _jadikan_admin_ws(org, a.admin_ws)
    ProjectMember.objects.update_or_create(
        project=org.p1, member=a.admin_ws, workspace=org.ws, defaults={"role": 20, "is_active": True}
    )

    a.admin_staf = _user("adminstaf", org.ws)
    _jadikan_admin_ws(org, a.admin_staf)
    JabatanOrganisasi.objects.create(workspace=org.ws, member=a.admin_staf, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
    ProjectMember.objects.update_or_create(
        project=org.p1, member=a.admin_staf, workspace=org.ws, defaults={"role": 15, "is_active": True}
    )

    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-tempat-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    a.sa = _user("sa", org.ws)
    InstanceAdmin.objects.create(instance=instance, user=a.sa, role=20)
    sinkronkan_super_admin(a.sa.id)
    return a


def _buat(client, org, data=None, project=None):
    return client.post(
        URL_ISSUES.format(slug=org.ws.slug, project_id=(project or org.p1).id),
        {"name": "Tugas uji", **(data or {})},
        format="json",
    )


def _assignee(issue_id):
    return set(IssueAssignee.objects.filter(issue_id=issue_id).values_list("assignee_id", flat=True))


def _tugas(org, pembuat, assignee=None):
    issue = Issue(name="Tugas", workspace=org.ws, project=org.p1, state=org.states["started"])
    issue.save()
    Issue.objects.filter(pk=issue.pk).update(created_by=pembuat)
    issue.refresh_from_db()
    if assignee is not None:
        IssueAssignee.objects.create(issue=issue, assignee=assignee, project=org.p1, workspace=org.ws)
    return issue


# --------------------------------------------------------------------------
# 1. Auto-assign
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestAutoAssign:
    def test_staf_otomatis_walau_katup_mati(self, org, monkeypatch):
        """Akar masalah: dulu auto-assign hanya hidup kalau katup gerbang menyala."""
        monkeypatch.setenv(FLAG_GERBANG, "0")
        respon = _buat(_klien(org.staf), org)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == {org.staf.id}

    def test_staf_otomatis_dengan_katup_nyala(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respon = _buat(_klien(org.staf), org)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == {org.staf.id}

    def test_admin_workspace_yang_ditempatkan_ikut_otomatis(self, org, akses, monkeypatch):
        """Dulu admin workspace dikecualikan dari auto-assign."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respon = _buat(_klien(akses.admin_staf), org)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == {akses.admin_staf.id}

    def test_manager_otomatis_jadi_miliknya(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respon = _buat(_klien(org.manager), org)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == {org.manager.id}

    @pytest.mark.parametrize("siapa", ["admin_ws", "sa"])
    def test_admin_tanpa_penempatan_tanpa_galat_dan_tanpa_auto_assign(self, org, akses, siapa, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respon = _buat(_klien(getattr(akses, siapa)), org)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert getattr(akses, siapa).id not in _assignee(respon.json()["id"])

    def test_assignee_eksplisit_tidak_diubah(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respon = _buat(_klien(org.manager), org, {"assignee_ids": [str(org.staf.id)]})
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == {org.staf.id}

    def test_api_v1_ikut_otomatis(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        token = APIToken.objects.create(user=org.staf, label=f"uji-{uuid4().hex[:6]}", user_type=0)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token.token)
        respon = client.post(
            URL_V1_ISSUES.format(slug=org.ws.slug, project_id=org.p1.id), {"name": "Lewat token"}, format="json"
        )
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == {org.staf.id}

    def test_penerima_otomatis_menolak_yang_tidak_ditempatkan(self, org, akses):
        assert penerima_otomatis(org.p1.id, org.staf) == org.staf.id
        assert penerima_otomatis(org.p1.id, akses.admin_ws) is None
        assert penerima_otomatis(org.p1.id, akses.sa) is None
        # sup2 duduk di SMT2: bukan tempatnya P1.
        assert penerima_otomatis(org.p1.id, org.sup2) is None


# --------------------------------------------------------------------------
# 2. Komentar dan reaksi ikut hak ubah
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestKomentarIkutHakUbah:
    def _komentar(self, client, org, issue, **ekstra):
        return client.post(
            URL_KOMENTAR.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=issue.id),
            {"comment_html": "<p>Halo</p>", **ekstra},
            format="json",
        )

    def test_staf_tidak_terlibat_ditolak(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        rekan = _user("rekan", org.ws)
        JabatanOrganisasi.objects.create(workspace=org.ws, member=rekan, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
        tugas = _tugas(org, org.staf, org.staf)
        respon = self._komentar(_klien(rekan), org, tugas)
        assert respon.status_code == status.HTTP_403_FORBIDDEN, getattr(respon, "data", None)
        assert "error" in respon.json()

    def test_assignee_pembuat_dan_atasan_boleh(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        # Dibuat dan dipegang staf: staf (pemilik) dan manager divisinya (atasan) boleh.
        tugas = _tugas(org, org.staf, org.staf)
        for orang in (org.staf, org.manager):
            respon = self._komentar(_klien(orang), org, tugas)
            assert respon.status_code == status.HTTP_201_CREATED, (orang, getattr(respon, "data", None))
        # Pemberi tugas yang bukan atasan: pembuat (created_by) tetap boleh.
        tugas_dir = _tugas(org, org.direktur, org.staf)
        respon = self._komentar(_klien(org.direktur), org, tugas_dir)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    def test_admin_workspace_dan_super_admin_boleh(self, org, akses, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        tugas = _tugas(org, org.staf, org.staf)
        for orang in (akses.admin_ws, akses.sa):
            respon = self._komentar(_klien(orang), org, tugas)
            assert respon.status_code == status.HTTP_201_CREATED, (orang, getattr(respon, "data", None))

    def test_balasan_ikut_aturan_yang_sama(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        rekan = _user("rekan", org.ws)
        JabatanOrganisasi.objects.create(workspace=org.ws, member=rekan, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
        tugas = _tugas(org, org.staf, org.staf)
        induk = IssueComment.objects.create(
            issue=tugas, project=org.p1, workspace=org.ws, actor=org.staf, comment_html="<p>induk</p>"
        )
        respon = self._komentar(_klien(rekan), org, tugas, parent=str(induk.id))
        assert respon.status_code == status.HTTP_403_FORBIDDEN, getattr(respon, "data", None)

    def test_reaksi_tugas_dan_komentar_ditolak_untuk_yang_tidak_terlibat(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        rekan = _user("rekan", org.ws)
        JabatanOrganisasi.objects.create(workspace=org.ws, member=rekan, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
        tugas = _tugas(org, org.staf, org.staf)
        komentar = IssueComment.objects.create(
            issue=tugas, project=org.p1, workspace=org.ws, actor=org.staf, comment_html="<p>x</p>"
        )
        client = _klien(rekan)
        respon = client.post(
            URL_REAKSI.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=tugas.id),
            {"reaction": "128077"},
            format="json",
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN, getattr(respon, "data", None)
        respon = client.post(
            URL_REAKSI_KOMENTAR.format(slug=org.ws.slug, project_id=org.p1.id, comment_id=komentar.id),
            {"reaction": "128077"},
            format="json",
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN, getattr(respon, "data", None)
        # Assignee-nya sendiri boleh bereaksi.
        respon = _klien(org.staf).post(
            URL_REAKSI.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=tugas.id),
            {"reaction": "128077"},
            format="json",
        )
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    def test_katup_mati_komentar_bebas(self, org, monkeypatch):
        """Sama dengan hak ubah: katup tertutup = tidak ada kunci per tugas."""
        monkeypatch.setenv(FLAG_GERBANG, "0")
        rekan = _user("rekan", org.ws)
        JabatanOrganisasi.objects.create(workspace=org.ws, member=rekan, tingkat=TINGKAT_MEMBER, departemen=org.smt1)
        tugas = _tugas(org, org.staf, org.staf)
        respon = self._komentar(_klien(rekan), org, tugas)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)


# --------------------------------------------------------------------------
# 3. Penempatan assignee
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestPenempatanAssignee:
    def test_hanya_yang_ditempatkan(self, org, akses):
        tempat = ditempatkan_ids(org.ws.id, org.p1.id)
        # Departemen, divisi (manager), dan direktur (seluruh organisasi).
        assert {org.staf.id, org.manager.id, org.direktur.id, akses.admin_staf.id} <= tempat
        assert akses.admin_ws.id not in tempat
        assert akses.sa.id not in tempat
        assert org.sup2.id not in tempat

    @pytest.mark.parametrize("katup", ["0", "1"])
    def test_super_admin_tidak_bisa_menugaskan_admin_tanpa_penempatan(self, org, akses, katup, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, katup)
        assert galat_penugasan(org.p1.id, [akses.admin_ws.id], actor=akses.sa)
        assert galat_penugasan(org.p1.id, [org.staf.id], actor=akses.sa) is None

    def test_admin_tanpa_penempatan_tidak_bisa_assign_diri_sendiri(self, org, akses, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert galat_penugasan(org.p1.id, [akses.admin_ws.id], actor=akses.admin_ws)
        respon = _buat(_klien(akses.admin_ws), org, {"assignee_ids": [str(akses.admin_ws.id)]})
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, getattr(respon, "data", None)

    def test_admin_workspace_setara_direktur_untuk_yang_ditempatkan(self, org, akses, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert galat_penugasan(org.p1.id, [org.manager.id, org.staf.id], actor=akses.admin_ws) is None

    def test_atasan_tetap_hanya_ke_bawah(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert galat_penugasan(org.p1.id, [org.direktur.id], actor=org.manager)

    def test_assignee_lama_tanpa_penempatan_tidak_memblokir_ubah(self, org, akses, monkeypatch):
        """Tugas lama yang sudah dipegang admin tanpa penempatan tetap bisa disunting."""
        monkeypatch.setenv(FLAG_GERBANG, "1")
        tugas = _tugas(org, org.manager, akses.admin_ws)
        url = URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=tugas.id)
        respon = _klien(akses.sa).patch(url, {"priority": "high"}, format="json")
        assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
        respon = _klien(akses.sa).patch(
            url, {"assignee_ids": [str(akses.admin_ws.id), str(org.staf.id)]}, format="json"
        )
        assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
        assert _assignee(tugas.id) == {akses.admin_ws.id, org.staf.id}

    @pytest.mark.parametrize("siapa", ["sa", "admin_ws"])
    def test_dropdown_tanpa_admin_yang_tidak_ditempatkan(self, org, akses, siapa, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        data = _klien(getattr(akses, siapa)).get(URL_KUASA.format(slug=org.ws.slug, project_id=org.p1.id)).json()
        assert data["mode"] == "semua"
        assert data["admin_penuh"] is True
        ids = set(data["user_ids"])
        assert str(org.staf.id) in ids
        assert str(akses.admin_staf.id) in ids
        assert str(akses.admin_ws.id) not in ids
        assert str(akses.sa.id) not in ids

    def test_dropdown_manager_hanya_bawahan_yang_ditempatkan(self, org, akses, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        data = _klien(org.manager).get(URL_KUASA.format(slug=org.ws.slug, project_id=org.p1.id)).json()
        ids = {u["id"] for u in data["users"]}
        assert str(org.staf.id) in ids
        assert str(akses.admin_ws.id) not in ids
