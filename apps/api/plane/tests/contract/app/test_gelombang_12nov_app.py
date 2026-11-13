# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes kontrak gelombang 12 Nov (KEP-98)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Lima perilaku yang diminta user pada 12 Nov 2026.

1. Assignee anak ikut jadi assignee induknya dan anggota module-nya.
2. Staf yang terlibat di salah satu anak boleh menambah sub-work item di induknya.
3. Project/departemen baru privat sejak lahir.
4. Direktur hanya melihat pengajuan untuk tugas buatan manager ke atas.
5. Nama project dan ikon folder Wiki mengikuti departemen (termasuk data lama, migrasi 0174).
6. Super Admin berjenjang staf boleh menugaskan siapa pun (susulan 12 Nov).
"""
# ruff: noqa: F401, F811  (fixture `org` dan `super_admin` diimpor dari berkas tes lain)

import importlib

import pytest
from django.apps import apps as django_apps
from rest_framework import status

from plane.db.models import (
    Departemen,
    DepartemenProject,
    Issue,
    IssueAssignee,
    Module,
    ModuleIssue,
    ModuleMember,
    PersetujuanPenugasan,
    Project,
    WikiFolder,
)
from plane.license.api.views.organisasi import InstanceDepartemenEndpoint, _adopsi_atau_buat_project
from plane.tests.contract.app.test_organisasi_app import _god, super_admin
from plane.tests.contract.app.test_persetujuan_manager_app import (  # noqa: F401
    URL_ISSUE_DETAIL,
    URL_ISSUES,
    URL_PERSETUJUAN,
    _ajukan,
    _klien,
    _user,
    org,
)
from plane.utils.hierarki import FLAG_GERBANG, TINGKAT_MEMBER, peta_tingkat, saring_penyetuju
from plane.utils.naik_assignee import naikkan_assignee

URL_SUB = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/sub-issues/"


def _tugas(org, pembuat, nama, assignee=None, parent=None):
    issue = Issue(name=nama, workspace=org.ws, project=org.p1, parent=parent, state=org.states["started"])
    issue.save()
    # BaseModel.save() mengisi created_by dari crum (kosong di tes), jadi ditimpa.
    Issue.objects.filter(pk=issue.pk).update(created_by=pembuat)
    issue.refresh_from_db()
    if assignee:
        IssueAssignee.objects.create(issue=issue, assignee=assignee, project=org.p1, workspace=org.ws)
    return issue


def _ajukan_tugas_manager(org):
    """Tugas dibuat manager untuk staf; staf menggesernya ke Done lalu jadi pengajuan."""
    tugas = _tugas(org, org.manager, "Tugas manager", assignee=org.staf)
    respon = _klien(org.staf).patch(
        URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=tugas.id),
        {"state": str(org.states["completed"].id)},
        format="json",
    )
    assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
    return tugas, PersetujuanPenugasan.objects.get(issue_id=tugas.id, status="menunggu")


# --------------------------------------------------------------------------
# 1. Assignee anak naik ke induk dan module
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestAssigneeAnakNaik:
    @pytest.mark.django_db
    def test_assignee_anak_ikut_ke_induk_berantai(self, org):
        kakek = _tugas(org, org.manager, "Kakek", assignee=org.manager)
        induk = _tugas(org, org.manager, "Induk", parent=kakek)
        anak = _tugas(org, org.manager, "Anak", assignee=org.staf, parent=induk)

        assert naikkan_assignee(anak.id) == (2, 0)
        for atas in (induk, kakek):
            assert IssueAssignee.objects.filter(issue=atas, assignee=org.staf).exists()
        # Assignee lama induk tetap ada, dan tidak ada yang digandakan.
        assert IssueAssignee.objects.filter(issue=kakek).count() == 2
        assert naikkan_assignee(anak.id) == (0, 0)

    @pytest.mark.django_db
    def test_melepas_assignee_anak_tidak_mencabut_dari_induk(self, org):
        induk = _tugas(org, org.manager, "Induk")
        anak = _tugas(org, org.manager, "Anak", assignee=org.staf, parent=induk)
        naikkan_assignee(anak.id)
        IssueAssignee.objects.filter(issue=anak).delete()
        naikkan_assignee(anak.id)
        assert IssueAssignee.objects.filter(issue=induk, assignee=org.staf).exists()

    @pytest.mark.django_db
    def test_assignee_jadi_anggota_module_anak_dan_induk(self, org):
        induk = _tugas(org, org.manager, "Induk")
        anak = _tugas(org, org.manager, "Anak", assignee=org.staf, parent=induk)
        modul_anak = Module.objects.create(name="Modul anak", project=org.p1, workspace=org.ws)
        modul_induk = Module.objects.create(name="Modul induk", project=org.p1, workspace=org.ws)
        ModuleIssue.objects.create(module=modul_anak, issue=anak, project=org.p1, workspace=org.ws)
        ModuleIssue.objects.create(module=modul_induk, issue=induk, project=org.p1, workspace=org.ws)

        assert naikkan_assignee(anak.id) == (1, 2)
        for modul in (modul_anak, modul_induk):
            assert ModuleMember.objects.filter(module=modul, member=org.staf).exists()

    @pytest.mark.django_db
    def test_membuat_anak_lewat_api_menaikkan_assignee(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        induk = _tugas(org, org.manager, "Induk")
        respon = _klien(org.staf).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p1.id),
            {"name": "Anak staf", "parent_id": str(induk.id)},
            format="json",
        )
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert IssueAssignee.objects.filter(issue=induk, assignee=org.staf).exists()


# --------------------------------------------------------------------------
# 2. Staf yang terlibat di anak boleh menambah sub-work item di induk
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestTambahSubItemDiIndukOrangLain:
    def _siapkan(self, org):
        induk = _tugas(org, org.manager, "Induk manager", assignee=org.manager)
        anak = _tugas(org, org.manager, "Anak untuk staf", assignee=org.staf, parent=induk)
        milik_staf = _tugas(org, org.staf, "Tugas staf", assignee=org.staf)
        return induk, anak, milik_staf

    @pytest.mark.django_db
    def test_terlibat_di_anak_boleh_menambah_sub_item(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        induk, _, milik_staf = self._siapkan(org)
        respon = _klien(org.staf).post(
            URL_SUB.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=induk.id),
            {"sub_issue_ids": [str(milik_staf.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        milik_staf.refresh_from_db()
        assert milik_staf.parent_id == induk.id

    @pytest.mark.django_db
    def test_tidak_terlibat_di_anak_tetap_ditolak(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        induk, _, _ = self._siapkan(org)
        orang_lain = _user("lain", org.ws)
        from plane.db.models import JabatanOrganisasi  # noqa: PLC0415

        JabatanOrganisasi.objects.create(
            workspace=org.ws, member=orang_lain, tingkat=TINGKAT_MEMBER, departemen=org.smt1
        )
        punya_lain = _tugas(org, orang_lain, "Tugas lain", assignee=orang_lain)
        respon = _klien(orang_lain).post(
            URL_SUB.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=induk.id),
            {"sub_issue_ids": [str(punya_lain.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_tugas_orang_lain_tidak_bisa_dijadikan_anak(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        induk, _, _ = self._siapkan(org)
        punya_manager = _tugas(org, org.manager, "Bukan milik staf", assignee=org.manager)
        respon = _klien(org.staf).post(
            URL_SUB.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=induk.id),
            {"sub_issue_ids": [str(punya_manager.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_induk_tetap_hanya_lihat_untuk_sunting_lain(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        induk, _, _ = self._siapkan(org)
        # Assignee anak naik ke induk (KEP-98) tapi pembuat induk tetap manager;
        # staf yang BUKAN assignee induk dan hanya terlibat di anak tidak boleh ubah judul.
        IssueAssignee.objects.filter(issue=induk, assignee=org.staf).delete()
        respon = _klien(org.staf).patch(
            URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=induk.id),
            {"name": "Judul dibajak"},
            format="json",
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN


# --------------------------------------------------------------------------
# 3. Project / departemen baru privat
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPrivatSejakLahir:
    @pytest.mark.django_db
    def test_project_departemen_baru_privat(self, org, create_user):
        dep = Departemen.objects.create(workspace=org.ws, divisi=org.sales, kode="BARU", nama="Departemen Baru")
        project = _adopsi_atau_buat_project(dep, create_user, org.ws)
        assert project.network == 0

    @pytest.mark.django_db
    def test_bawaan_pabrik_privat(self, db):
        from plane.utils import bawaan_project  # noqa: PLC0415

        assert bawaan_project.PABRIK["network"] == 0
        assert bawaan_project.baca_bawaan()["network"] == 0


# --------------------------------------------------------------------------
# 4. Direktur hanya untuk tugas buatan manager ke atas
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestDirekturHanyaTugasManager:
    @pytest.mark.django_db
    def test_saring_penyetuju_membuang_direktur_untuk_tugas_biasa(self, org):
        peta = peta_tingkat(org.ws.id, org.p1.id)
        calon = [org.manager.id, org.direktur.id]
        assert saring_penyetuju(calon, peta, org.staf.id, pembuat_id=org.staf.id) == [org.manager.id]
        assert saring_penyetuju(calon, peta, org.staf.id, pembuat_id=None) == [org.manager.id]
        assert saring_penyetuju(calon, peta, org.staf.id, pembuat_id=org.manager.id) == calon
        assert saring_penyetuju(calon, peta, org.staf.id, pembuat_id=org.direktur.id) == calon

    @pytest.mark.django_db
    def test_tugas_buatan_staf_tidak_muncul_di_direktur(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, baris = _ajukan(org)  # staf membuat tugasnya sendiri
        url = URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id)

        respon = _klien(org.direktur).get(url + "?peran=penyetuju")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert respon.json()["hasil"] == []
        respon = _klien(org.direktur).post(url + f"{baris.id}/", {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        # Manager tetap penyetujunya.
        respon = _klien(org.manager).get(url + "?peran=penyetuju")
        assert [h["id"] for h in respon.json()["hasil"]] == [str(baris.id)]

    @pytest.mark.django_db
    def test_tugas_buatan_manager_muncul_dan_bisa_diputuskan_direktur(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, baris = _ajukan_tugas_manager(org)
        url = URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id)

        respon = _klien(org.direktur).get(url + "?peran=penyetuju")
        assert [h["id"] for h in respon.json()["hasil"]] == [str(baris.id)]
        assert respon.json()["hasil"][0]["boleh_saya_putuskan"] is True
        respon = _klien(org.direktur).post(url + f"{baris.id}/", {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_widget_perhatian_direktur_memilah_menurut_pembuat(self, org, monkeypatch):
        from plane.utils.perhatian import susun_perhatian  # noqa: PLC0415

        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, baris_staf = _ajukan(org)
        _, baris_manager = _ajukan_tugas_manager(org)
        hasil = susun_perhatian(org.direktur, org.ws.slug)
        grup = {g["key"]: g for g in hasil["groups"]}
        ids = {i["id"] for i in grup["decide"]["items"]} if "decide" in grup else set()
        assert str(baris_manager.issue_id) in ids
        assert str(baris_staf.issue_id) not in ids


# --------------------------------------------------------------------------
# 5. Departemen -> nama project + ikon folder Wiki
# --------------------------------------------------------------------------

LOGO = {"in_use": "emoji", "emoji": {"value": "128512"}}


@pytest.mark.contract
class TestDepartemenMengikuti:
    @pytest.mark.django_db
    def test_ganti_nama_departemen_mengganti_nama_project_dan_folder(self, org, super_admin):
        r = _god(InstanceDepartemenEndpoint, "patch", super_admin, {"nama": "Tim Penjualan Satu"}, pk=org.smt1.id)
        assert r.status_code == status.HTTP_200_OK, r.data
        org.p1.refresh_from_db()
        assert org.p1.name == "Tim Penjualan Satu"
        assert WikiFolder.objects.get(departemen=org.smt1).nama == "Tim Penjualan Satu"

    @pytest.mark.django_db
    def test_ikon_folder_mengikuti_ikon_project(self, org, super_admin):
        Project.objects.filter(pk=org.p1.pk).update(logo_props=LOGO)
        r = _god(InstanceDepartemenEndpoint, "patch", super_admin, {"nama": "Tim Penjualan Satu"}, pk=org.smt1.id)
        assert r.status_code == status.HTTP_200_OK, r.data
        assert WikiFolder.objects.get(departemen=org.smt1).logo_props == LOGO
        # Ikon project diganti: folder menyusul saat Wiki dibaca atau struktur berubah.
        baru = {"in_use": "emoji", "emoji": {"value": "128640"}}
        Project.objects.filter(pk=org.p1.pk).update(logo_props=baru)
        from plane.utils.wiki_mandiri import pastikan_folder_unit  # noqa: PLC0415

        assert pastikan_folder_unit(org.ws.id) == 1
        assert WikiFolder.objects.get(departemen=org.smt1).logo_props == baru
        assert pastikan_folder_unit(org.ws.id) == 0

    @pytest.mark.django_db
    def test_nama_yang_dipakai_project_lain_ditolak(self, org, super_admin):
        r = _god(InstanceDepartemenEndpoint, "patch", super_admin, {"nama": org.p2.name}, pk=org.smt1.id)
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        org.smt1.refresh_from_db()
        assert org.smt1.nama == "Sales Team 1"

    @pytest.mark.django_db
    def test_migrasi_menyamakan_data_lama(self, org):
        Project.objects.filter(pk=org.p1.pk).update(logo_props=LOGO)
        # Nama p2 sengaja bentrok dengan departemen lain: dilewati, bukan gagal.
        Project.objects.filter(pk=org.p2.pk).update(name="Sales Team 1")
        modul = importlib.import_module("plane.db.migrations.0174_sinkron_departemen_project")
        WikiFolder.objects.create(workspace=org.ws, nama="x", departemen=org.smt1)

        modul.samakan(django_apps, None)

        org.p1.refresh_from_db()
        org.p2.refresh_from_db()
        assert org.p1.name == "Sales Team 1" or org.p2.name == "Sales Team 1"
        assert DepartemenProject.objects.filter(project=org.p2).exists()
        assert WikiFolder.objects.get(departemen=org.smt1).logo_props == LOGO
        # Idempoten.
        modul.samakan(django_apps, None)


# --------------------------------------------------------------------------
# 6. Super Admin berjenjang staf tidak dibatasi aturan "staf hanya ajak rekan"
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestSuperAdminBerjenjangStaf:
    def _super_staf(self, org, super_admin):
        from plane.db.models import JabatanOrganisasi, ProjectMember  # noqa: PLC0415

        JabatanOrganisasi.objects.create(
            workspace=org.ws, member=super_admin, tingkat=TINGKAT_MEMBER, departemen=org.smt1
        )
        ProjectMember.objects.update_or_create(
            project=org.p1, member=super_admin, workspace=org.ws, defaults={"role": 20, "is_active": True}
        )
        return super_admin

    @pytest.mark.django_db
    def test_super_admin_staf_bisa_menambah_assignee_jenjang_lain(self, org, super_admin, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        sa = self._super_staf(org, super_admin)
        tugas = _tugas(org, org.manager, "Tugas dengan induk", parent=_tugas(org, org.manager, "Induk"))
        respon = _klien(sa).patch(
            URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=tugas.id),
            {"assignee_ids": [str(org.manager.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert IssueAssignee.objects.filter(issue=tugas, assignee=org.manager).exists()

    @pytest.mark.django_db
    def test_staf_biasa_tetap_hanya_boleh_ajak_rekan(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        tugas = _tugas(org, org.staf, "Tugas staf", assignee=org.staf)
        respon = _klien(org.staf).patch(
            URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=tugas.id),
            {"assignee_ids": [str(org.staf.id), str(org.manager.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
