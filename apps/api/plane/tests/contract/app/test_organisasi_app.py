# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes kontrak struktur divisi -> departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak KEP-29: perusahaan -> divisi -> departemen -> project.

Bentuk uji (dua divisi, tiga departemen, empat project):

    SALES  -> SMT1 (P1) · SMT2 (P2)
    HRGA   -> HR   (P3)

P1B warisan tak-terpetakan (bekas payung, bukan milik siapa-siapa).

Kontrol negatif yang dikunci:

* Struktur kosong = TIDAK ADA keanggotaan yang dibuat atau dicabut.
* Supervisor SMT1 tidak melihat dan tidak menugaskan di SMT2.
* Staf melihat semua project departemennya, tapi tidak bisa mengubah tugas orang lain.
* Divisi manager TIDAK ditebak dari keanggotaan project.
* Pindah departemen mencabut akses lama, keanggotaan eksplisit tetap selamat.
* Hapus departemen/divisi yang masih berisi ditolak (409), bukan kaskade.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from plane.db.jangkauan import sinkronkan_workspace
from plane.db.models import (
    AksesHierarki,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueAssignee,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)
from plane.license.api.views.hierarki import InstanceHierarkiEndpoint
from plane.license.api.views.organisasi import (
    InstanceDepartemenEndpoint,
    InstanceDivisiEndpoint,
    InstanceOrganisasiEndpoint,
)
from plane.license.models import Instance, InstanceAdmin
from plane.utils.hierarki import (
    FLAG_GERBANG,
    calon_penyetuju,
    divisi_diawasi,
    jangkauan_hierarki,
    struktur_aktif,
)

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_ISSUE_DETAIL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"


def _user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_name="Uji"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _aktif(user, project):
    return ProjectMember.objects.filter(member=user, project=project, is_active=True).exists()


def _role(user, project):
    return ProjectMember.objects.get(member=user, project=project, is_active=True).role


def _tempatkan(workspace, user, tingkat, departemen=None, divisi=None):
    return JabatanOrganisasi.objects.create(
        workspace=workspace, member=user, tingkat=tingkat, departemen=departemen, divisi=divisi
    )


@pytest.fixture
def org(db, workspace, create_user):
    """Struktur + orang. Dibuat lewat model.save(), jadi signal sinkron ikut teruji."""
    o = type("Org", (), {})()
    o.ws = workspace
    o.p1, o.p1b, o.p2, o.p3 = (
        Project.objects.create(name=n, identifier=i, workspace=workspace, created_by=create_user)
        for n, i in (("SMT1 Board", "P1"), ("SMT1 Admin", "P1B"), ("SMT2 Board", "P2"), ("HR Board", "P3"))
    )
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.hrga = Divisi.objects.create(workspace=workspace, kode="HRGA", nama="HRGA")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="Sales Team 1")
    o.smt2 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT2", nama="Sales Team 2")
    o.hr = Departemen.objects.create(workspace=workspace, divisi=o.hrga, kode="HR", nama="Human Resources")
    # 1:1 (0146, keputusan user 2026-10-23): satu departemen tepat satu project.
    # P1B sengaja TAK dipetakan: ia warisan payung untuk menguji jalur tak-terpetakan.
    for dep, p in ((o.smt1, o.p1), (o.smt2, o.p2), (o.hr, o.p3)):
        DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=p)

    o.manager = _user("mgr", workspace)
    o.sup1 = _user("sup1", workspace)
    o.staf1 = _user("staf1", workspace)
    o.staf1b = _user("staf1b", workspace)
    o.staf2 = _user("staf2", workspace)
    _tempatkan(workspace, o.manager, TINGKAT_MANAGER, divisi=o.sales)
    _tempatkan(workspace, o.sup1, TINGKAT_SUPERVISOR, departemen=o.smt1)
    _tempatkan(workspace, o.staf1, TINGKAT_MEMBER, departemen=o.smt1)
    _tempatkan(workspace, o.staf1b, TINGKAT_MEMBER, departemen=o.smt1)
    _tempatkan(workspace, o.staf2, TINGKAT_MEMBER, departemen=o.smt2)
    return o


@pytest.fixture
def super_admin(db, workspace):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-org-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user("super", workspace)
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _god(view, method, aktor, data=None, **kwargs):
    request = getattr(APIRequestFactory(), method)("/api/instances/organisasi/", data, format="json")
    force_authenticate(request, user=aktor)
    return view.as_view()(request, **kwargs)


# --------------------------------------------------------------------------
# Struktur kosong = perilaku lama
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestStrukturKosong:
    @pytest.mark.django_db
    def test_tanpa_divisi_jangkauan_kosong_dan_tidak_ada_keanggotaan_dibuat(self, workspace, create_user):
        p = Project.objects.create(name="Lama", identifier="LAMA", workspace=workspace, created_by=create_user)
        staf = _user("staf", workspace)
        JabatanOrganisasi.objects.create(workspace=workspace, member=staf, tingkat=TINGKAT_MEMBER)
        assert not struktur_aktif(workspace.id)
        assert jangkauan_hierarki(staf.id, workspace.id) == {}
        assert sinkronkan_workspace(workspace.id) == 0
        assert not _aktif(staf, p)

    @pytest.mark.django_db
    def test_tanpa_divisi_supervisor_tetap_memakai_keanggotaan_project(self, workspace, create_user):
        p = Project.objects.create(name="Lama", identifier="LAMA", workspace=workspace, created_by=create_user)
        sup = _user("sup", workspace)
        ProjectMember.objects.create(project=p, member=sup, workspace=workspace, role=20)
        JabatanOrganisasi.objects.create(workspace=workspace, member=sup, tingkat=TINGKAT_SUPERVISOR)
        assert divisi_diawasi(sup.id, workspace.id) == {p.id}


# --------------------------------------------------------------------------
# Jangkauan lihat
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestJangkauanLihat:
    @pytest.mark.django_db
    def test_staf_melihat_semua_project_departemennya_saja(self, org):
        assert _aktif(org.staf1, org.p1)
        assert _role(org.staf1, org.p1) == 15
        assert not _aktif(org.staf1, org.p2)
        assert not _aktif(org.staf1, org.p3)

    @pytest.mark.django_db
    def test_supervisor_hanya_departemennya(self, org):
        assert _aktif(org.sup1, org.p1)
        assert _role(org.sup1, org.p1) == 20
        assert not _aktif(org.sup1, org.p2)

    @pytest.mark.django_db
    def test_manager_semua_departemen_di_divisinya_tidak_divisi_lain(self, org):
        for p in (org.p1, org.p2):
            assert _aktif(org.manager, p) and _role(org.manager, p) == 20
        assert not _aktif(org.manager, org.p3)

    @pytest.mark.django_db
    def test_divisi_manager_tidak_ditebak_dari_keanggotaan_project(self, org):
        """Manager tanpa `divisi` = tanpa jangkauan, walau ia anggota project SMT1."""
        mgr = _user("mgr2", org.ws)
        ProjectMember.objects.create(project=org.p1, member=mgr, workspace=org.ws, role=20)
        _tempatkan(org.ws, mgr, TINGKAT_MANAGER, departemen=org.smt1)
        assert divisi_diawasi(mgr.id, org.ws.id) == set()
        assert not _aktif(mgr, org.p2)

    @pytest.mark.django_db
    def test_project_baru_di_departemen_langsung_terjangkau(self, org, create_user):
        # 1:1: project baru untuk departemen baru (bukan project kedua di smt2).
        smt3 = Departemen.objects.create(workspace=org.ws, divisi=org.sales, kode="SMT3", nama="Sales Team 3")
        baris = JabatanOrganisasi.objects.get(member=org.staf2)
        baris.departemen = smt3
        baris.save()
        baru = Project.objects.create(name="SMT3 Board", identifier="P3B", workspace=org.ws, created_by=create_user)
        DepartemenProject.objects.create(workspace=org.ws, departemen=smt3, project=baru)
        assert _aktif(org.staf2, baru) and _aktif(org.manager, baru)
        assert not _aktif(org.staf1, baru)


# --------------------------------------------------------------------------
# Wewenang
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestWewenang:
    @pytest.mark.django_db
    def test_divisi_diawasi_per_jenjang(self, org):
        assert divisi_diawasi(org.manager.id, org.ws.id) == {org.p1.id, org.p2.id}
        assert divisi_diawasi(org.sup1.id, org.ws.id) == {org.p1.id}
        assert divisi_diawasi(org.staf1.id, org.ws.id) == set()

    @pytest.mark.django_db
    def test_manager_jadi_calon_penyetuju_di_departemen_lain_divisinya(self, org):
        penyetuju = calon_penyetuju(org.ws.id, org.p2.id, tingkat_pembuat=TINGKAT_MEMBER)
        assert org.manager.id in penyetuju
        assert org.sup1.id not in penyetuju

    @pytest.mark.django_db
    def test_supervisor_smt1_tidak_bisa_menugaskan_di_smt2(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        response = _klien(org.sup1).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p2.id),
            {"name": "Lintas departemen", "assignee_ids": [str(org.staf2.id)]},
            format="json",
        )
        assert response.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN)
        assert not IssueAssignee.objects.filter(assignee=org.staf2).exists()

    @pytest.mark.django_db
    def test_manager_bisa_menugaskan_di_smt2(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        response = _klien(org.manager).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p2.id),
            {"name": "Dari manager", "assignee_ids": [str(org.staf2.id)]},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, getattr(response, "data", None)

    @pytest.mark.django_db
    def test_staf_melihat_tugas_rekan_tapi_tidak_bisa_mengubahnya(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        tugas = Issue.objects.create(workspace=org.ws, project=org.p1, name="Milik rekan", created_by=org.staf1b)
        IssueAssignee.objects.create(issue=tugas, assignee=org.staf1b, project=org.p1, workspace=org.ws)
        client = _klien(org.staf1)
        url = URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=tugas.id)
        assert client.get(url).status_code == status.HTTP_200_OK
        assert client.patch(url, {"priority": "urgent"}, format="json").status_code == status.HTTP_403_FORBIDDEN


# --------------------------------------------------------------------------
# Perubahan penempatan
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPerubahanPenempatan:
    @pytest.mark.django_db
    def test_pindah_departemen_mencabut_akses_lama(self, org):
        baris = JabatanOrganisasi.objects.get(member=org.staf1)
        baris.departemen = org.smt2
        baris.save()
        assert not _aktif(org.staf1, org.p1)
        assert _aktif(org.staf1, org.p2)

    @pytest.mark.django_db
    def test_manager_pindah_divisi_mencabut_divisi_lama(self, org):
        baris = JabatanOrganisasi.objects.get(member=org.manager)
        baris.divisi = org.hrga
        baris.save()
        assert not _aktif(org.manager, org.p2)
        assert _aktif(org.manager, org.p3)

    @pytest.mark.django_db
    def test_jenjang_dicabut_mencabut_akses(self, org):
        JabatanOrganisasi.objects.get(member=org.staf2).delete()
        assert not _aktif(org.staf2, org.p2)

    @pytest.mark.django_db
    def test_keanggotaan_eksplisit_selamat_saat_pindah(self, org):
        """Pengecualian eksplisit (KEP-29) tidak tercatat di AksesHierarki, jadi tidak dicabut."""
        ProjectMember.objects.create(project=org.p3, member=org.staf1, workspace=org.ws, role=15)
        baris = JabatanOrganisasi.objects.get(member=org.staf1)
        baris.departemen = org.smt2
        baris.save()
        assert _aktif(org.staf1, org.p3)
        assert not AksesHierarki.objects.filter(member=org.staf1, project=org.p3).exists()

    @pytest.mark.django_db
    def test_keanggotaan_eksplisit_di_project_departemen_tidak_diubah_rolenya(self, workspace, create_user):
        p = Project.objects.create(name="X", identifier="PX", workspace=workspace, created_by=create_user)
        staf = _user("staf", workspace)
        ProjectMember.objects.create(project=p, member=staf, workspace=workspace, role=20)
        div = Divisi.objects.create(workspace=workspace, kode="D", nama="D")
        dep = Departemen.objects.create(workspace=workspace, divisi=div, kode="X", nama="X")
        DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=p)
        _tempatkan(workspace, staf, TINGKAT_MEMBER, departemen=dep)
        assert _role(staf, p) == 20
        assert not AksesHierarki.objects.filter(member=staf, project=p).exists()

    @pytest.mark.django_db
    def test_sinkron_ulang_idempoten(self, org):
        assert sinkronkan_workspace(org.ws.id) == 0


# --------------------------------------------------------------------------
# God Mode
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestGodModeOrganisasi:
    @pytest.mark.django_db
    def test_orang_biasa_tidak_bisa_membaca_struktur(self, org):
        response = _god(InstanceOrganisasiEndpoint, "get", org.staf1)
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    @pytest.mark.django_db
    def test_alur_lengkap_dari_god_mode(self, workspace, create_user, super_admin):
        p = Project.objects.create(name="Fin", identifier="FINX", workspace=workspace, created_by=create_user)
        staf = _user("fin", workspace)

        r = _god(InstanceDivisiEndpoint, "post", super_admin, {"kode": "fin", "nama": "Finance"})
        assert r.status_code == status.HTTP_201_CREATED, r.data
        div_id = r.data["divisi"][0]["id"]
        assert r.data["divisi"][0]["kode"] == "FIN"

        r = _god(InstanceDepartemenEndpoint, "post", super_admin, {"divisi_id": div_id, "kode": "ACC", "nama": "Acc"})
        assert r.status_code == status.HTTP_201_CREATED, r.data
        dep_id = r.data["divisi"][0]["departemen"][0]["id"]

        r = _god(InstanceDepartemenEndpoint, "patch", super_admin, {"project_ids": [str(p.id)]}, pk=dep_id)
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["divisi"][0]["departemen"][0]["projects"][0]["id"] == str(p.id)

        request = APIRequestFactory().post(
            "/api/instances/hierarki/",
            {"member_id": str(staf.id), "tingkat": TINGKAT_MEMBER, "departemen_id": dep_id},
            format="json",
        )
        force_authenticate(request, user=super_admin)
        r = InstanceHierarkiEndpoint.as_view()(request)
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["departemen_id"] == dep_id
        assert _aktif(staf, p)

    @pytest.mark.django_db
    def test_penempatan_tanpa_jenjang_ditolak(self, org, super_admin):
        orang = _user("baru", org.ws)
        request = APIRequestFactory().post(
            "/api/instances/hierarki/", {"member_id": str(orang.id), "departemen_id": str(org.smt1.id)}, format="json"
        )
        force_authenticate(request, user=super_admin)
        r = InstanceHierarkiEndpoint.as_view()(request)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_hapus_departemen_berisi_ditolak(self, org, super_admin):
        r = _god(InstanceDepartemenEndpoint, "delete", super_admin, pk=org.smt1.id)
        assert r.status_code == status.HTTP_409_CONFLICT
        assert Departemen.objects.filter(pk=org.smt1.id).exists()

    @pytest.mark.django_db
    def test_hapus_divisi_berisi_ditolak(self, org, super_admin):
        r = _god(InstanceDivisiEndpoint, "delete", super_admin, pk=org.sales.id)
        assert r.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.django_db
    def test_kode_ganda_ditolak(self, org, super_admin):
        r = _god(InstanceDivisiEndpoint, "post", super_admin, {"kode": "sales", "nama": "Lagi"})
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_project_pindah_departemen_lewat_god_mode(self, org, super_admin):
        """Pindah project antar departemen: p2 (milik smt2) dipindah ke smt1.

        smt2 jadi tanpa project (transien, diperbaiki lewat adopsi), akses menyesuaikan."""
        r = _god(
            InstanceDepartemenEndpoint, "patch", super_admin, {"project_ids": [str(org.p2.id)]}, pk=org.smt1.id
        )
        assert r.status_code == status.HTTP_200_OK, r.data
        assert DepartemenProject.objects.get(project=org.p2).departemen_id == org.smt1.id
        assert not DepartemenProject.objects.filter(project=org.p1).exists()
        assert not _aktif(org.staf1, org.p1) and _aktif(org.staf1, org.p2)

    @pytest.mark.django_db
    def test_departemen_menolak_project_kedua(self, org, super_admin):
        """KEP-32: satu departemen tepat satu project. Project kedua DITOLAK (400)."""
        # smt1 sudah memegang p1. Menambah p2 (milik smt2) lewat API ditolak.
        r = _god(
            InstanceDepartemenEndpoint,
            "patch",
            super_admin,
            {"project_ids": [str(org.p1.id), str(org.p2.id)]},
            pk=org.smt1.id,
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert DepartemenProject.objects.get(project=org.p2).departemen_id == org.smt2.id

    @pytest.mark.django_db
    def test_departemen_menolak_project_kedua_lewat_db(self, org):
        """0146: penegakan di database, bukan cuma validasi endpoint."""
        from django.db import IntegrityError, transaction

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                DepartemenProject.objects.create(workspace=org.ws, departemen=org.smt1, project=org.p2)


# --------------------------------------------------------------------------
# Sidebar web
# --------------------------------------------------------------------------

URL_STRUKTUR = "/api/workspaces/{slug}/struktur-organisasi/"


@pytest.mark.contract
class TestStrukturSidebar:
    @pytest.mark.django_db
    def test_tanpa_struktur_tidak_aktif(self, workspace, create_user):
        response = _klien(create_user).get(URL_STRUKTUR.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"aktif": False, "divisi": []}

    @pytest.mark.django_db
    def test_staf_hanya_menerima_project_yang_ia_ikuti(self, org):
        data = _klien(org.staf1).get(URL_STRUKTUR.format(slug=org.ws.slug)).json()
        assert data["aktif"] is True
        assert [v["kode"] for v in data["divisi"]] == ["SALES"]
        departemen = data["divisi"][0]["departemen"]
        assert [d["kode"] for d in departemen] == ["SMT1"]
        assert set(departemen[0]["project_ids"]) == {str(org.p1.id)}

    @pytest.mark.django_db
    def test_manager_melihat_semua_departemen_divisinya(self, org):
        data = _klien(org.manager).get(URL_STRUKTUR.format(slug=org.ws.slug)).json()
        assert [d["kode"] for d in data["divisi"][0]["departemen"]] == ["SMT1", "SMT2"]


@pytest.mark.contract
class TestGantiKeanggotaanTidakMengalahkanHierarki:
    @pytest.mark.django_db
    def test_daftar_kosong_dari_god_mode_tidak_mencabut_akses_departemen(self, org, super_admin):
        from plane.license.api.views.divisi import InstanceDivisiAnggotaEndpoint

        request = APIRequestFactory().post(
            "/api/instances/divisi-anggota/", {"member_id": str(org.staf1.id), "divisi": []}, format="json"
        )
        force_authenticate(request, user=super_admin)
        r = InstanceDivisiAnggotaEndpoint.as_view()(request)
        assert r.status_code == status.HTTP_200_OK, r.data
        assert _aktif(org.staf1, org.p1)


@pytest.mark.contract
class TestPohonMemuatOrang:
    @pytest.mark.django_db
    def test_pohon_berisi_anggota_departemen_dan_manager_divisi(self, org, super_admin):
        r = _god(InstanceOrganisasiEndpoint, "get", super_admin)
        sales = next(v for v in r.data["divisi"] if v["kode"] == "SALES")
        assert [m["id"] for m in sales["manager"]] == [str(org.manager.id)]
        smt1 = next(d for d in sales["departemen"] if d["kode"] == "SMT1")
        ids = [a["id"] for a in smt1["anggota"]]
        # Supervisor di depan (tingkat tertinggi), manager TIDAK dihitung sebagai anggota departemen.
        assert ids[0] == str(org.sup1.id)
        assert set(ids) == {str(org.sup1.id), str(org.staf1.id), str(org.staf1b.id)}
        assert smt1["jumlah_orang"] == 3


@pytest.mark.contract
class TestJadikanDepartemenDariProject:
    """Project lama (struktur "divisi = project") diubah jadi departemen beserta orangnya."""

    def _kirim(self, aktor, data):
        from plane.license.api.views.organisasi import InstanceDepartemenDariProjectEndpoint

        request = APIRequestFactory().post("/api/instances/organisasi/departemen/dari-project/", data, format="json")
        force_authenticate(request, user=aktor)
        return InstanceDepartemenDariProjectEndpoint.as_view()(request)

    @pytest.fixture
    def lama(self, org, create_user):
        """Project LAMA dengan anggota eksplisit (belum tercatat hierarki)."""
        p = Project.objects.create(name="Legal", identifier="LEGAL", workspace=org.ws, created_by=create_user)
        orang = _user("legal", org.ws)
        ProjectMember.objects.create(project=p, member=orang, workspace=org.ws, role=15)
        return p, orang

    @pytest.mark.django_db
    def test_buat_departemen_dan_tempatkan_anggota_lama(self, org, super_admin, lama):
        p, orang = lama
        r = self._kirim(super_admin, {"project_id": str(p.id), "divisi_id": str(org.hrga.id), "member_ids": [str(orang.id)]})
        assert r.status_code == status.HTTP_201_CREATED, r.data
        dep = Departemen.objects.get(kode="LEGAL")
        assert dep.divisi_id == org.hrga.id and dep.nama == "Legal"
        assert DepartemenProject.objects.get(project=p).departemen_id == dep.id
        j = JabatanOrganisasi.objects.get(member=orang)
        assert j.departemen_id == dep.id and j.tingkat == TINGKAT_MEMBER
        # Diadopsi: keanggotaan lamanya kini tercatat, jadi ikut dicabut saat pindah.
        assert AksesHierarki.objects.filter(member=orang, project=p).exists()
        j.departemen = org.hr
        j.save()
        assert not _aktif(orang, p)
        assert _aktif(orang, org.p3)

    @pytest.mark.django_db
    def test_manager_dilewati_dan_bukan_anggota_ditolak(self, org, super_admin, lama):
        p, _ = lama
        ProjectMember.objects.create(project=p, member=org.manager, workspace=org.ws, role=20)
        r = self._kirim(super_admin, {"project_id": str(p.id), "divisi_id": str(org.hrga.id), "member_ids": [str(org.manager.id)]})
        assert r.status_code == status.HTTP_201_CREATED and r.data["dilewati"] == 1
        assert JabatanOrganisasi.objects.get(member=org.manager).departemen_id is None

        p2 = Project.objects.create(name="GA", identifier="GA", workspace=org.ws, created_by=org.manager)
        r = self._kirim(super_admin, {"project_id": str(p2.id), "divisi_id": str(org.hrga.id), "member_ids": [str(org.staf2.id)]})
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert not Departemen.objects.filter(kode="GA").exists()

    @pytest.mark.django_db
    def test_project_yang_sudah_berdepartemen_ditolak(self, org, super_admin):
        r = self._kirim(super_admin, {"project_id": str(org.p1.id), "divisi_id": str(org.sales.id), "member_ids": []})
        assert r.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestDepartemenSatuProject:
    """KEP-32: project mengikuti departemen. Buat departemen = dapat satu project."""

    @pytest.mark.django_db
    def test_buat_departemen_otomatis_buat_project(self, org, super_admin):
        r = _god(
            InstanceDepartemenEndpoint,
            "post",
            super_admin,
            {"divisi_id": str(org.sales.id), "kode": "SM-QA", "nama": "Quality Assurance"},
        )
        assert r.status_code == status.HTTP_201_CREATED, r.data
        dep = Departemen.objects.get(kode="SM-QA")
        # Strip penghubung dilarang di identifier: SM-QA -> SMQA.
        proj = Project.objects.get(identifier="SMQA")
        assert DepartemenProject.objects.get(project=proj).departemen_id == dep.id
        assert proj.name == "Quality Assurance"
        # Penempatan lalu memberi akses ke project yang baru dibuat.
        orang = _user("qa", org.ws)
        _tempatkan(org.ws, orang, TINGKAT_MEMBER, departemen=dep)
        assert _aktif(orang, proj)

    @pytest.mark.django_db
    def test_buat_departemen_mengadopsi_project_tanpa_dep(self, org, create_user, super_admin):
        Project.objects.create(name="Warisan", identifier="LEG", workspace=org.ws, created_by=create_user)
        r = _god(
            InstanceDepartemenEndpoint,
            "post",
            super_admin,
            {"divisi_id": str(org.sales.id), "kode": "L-EG", "nama": "Legacy"},
        )
        assert r.status_code == status.HTTP_201_CREATED, r.data
        proj = Project.objects.get(identifier="LEG")
        assert DepartemenProject.objects.get(project=proj).departemen.kode == "L-EG"
        assert Project.objects.filter(identifier="LEG").count() == 1

    @pytest.mark.django_db
    def test_buat_departemen_identifier_bentrok_ditolak(self, org, super_admin):
        # SM-T1 -> SMT1? tidak ada project SMT1 di fixture; pakai P1: kode "P-1" -> "P1".
        r = _god(
            InstanceDepartemenEndpoint,
            "post",
            super_admin,
            {"divisi_id": str(org.hrga.id), "kode": "P-1", "nama": "Tabrakan"},
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        assert not Departemen.objects.filter(kode="P-1").exists()

    @pytest.mark.django_db
    def test_hapus_departemen_kosong_mengarsipkan_project(self, org, super_admin):
        dep = Departemen.objects.create(workspace=org.ws, divisi=org.sales, kode="TMP", nama="Sementara")
        proj = Project.objects.create(name="Sementara", identifier="TMP", workspace=org.ws, created_by=super_admin)
        DepartemenProject.objects.create(workspace=org.ws, departemen=dep, project=proj)
        r = _god(InstanceDepartemenEndpoint, "delete", super_admin, pk=dep.id)
        assert r.status_code == status.HTTP_200_OK, r.data
        assert not Departemen.objects.filter(pk=dep.id).exists()
        assert Project.objects.get(pk=proj.id).archived_at is not None

    @pytest.mark.django_db
    def test_hapus_departemen_berisi_tugas_ditolak(self, org, create_user, super_admin):
        dep = Departemen.objects.create(workspace=org.ws, divisi=org.sales, kode="TMP2", nama="Sementara 2")
        proj = Project.objects.create(name="Sementara 2", identifier="TMP2", workspace=org.ws, created_by=create_user)
        DepartemenProject.objects.create(workspace=org.ws, departemen=dep, project=proj)
        Issue.objects.create(workspace=org.ws, project=proj, name="Tugas", created_by=create_user)
        r = _god(InstanceDepartemenEndpoint, "delete", super_admin, pk=dep.id)
        assert r.status_code == status.HTTP_409_CONFLICT
        assert Departemen.objects.filter(pk=dep.id).exists()
        assert Project.objects.get(pk=proj.id).archived_at is None

    @pytest.mark.django_db
    def test_hapus_departemen_ada_orang_ditolak(self, org, super_admin):
        r = _god(InstanceDepartemenEndpoint, "delete", super_admin, pk=org.smt1.id)
        assert r.status_code == status.HTTP_409_CONFLICT


@pytest.mark.contract
class TestSupervisorMultiDepartemen:
    """2026-10-23: supervisor ditempatkan di beberapa departemen (satu baris
    jabatan per departemen, tanpa konsep utama/tambahan)."""

    @pytest.mark.django_db
    def test_supervisor_melihat_dua_departemen(self, org):
        from plane.utils.hierarki import divisi_diawasi, jangkauan_hierarki

        JabatanOrganisasi.objects.create(
            workspace=org.ws, member=org.sup1, tingkat=TINGKAT_SUPERVISOR, departemen=org.smt2
        )
        assert org.p2.id in jangkauan_hierarki(org.sup1.id, org.ws.id)
        assert org.p2.id in divisi_diawasi(org.sup1.id, org.ws.id)
        assert org.p3.id not in divisi_diawasi(org.sup1.id, org.ws.id)
        # Sinkron signal memberi keanggotaan project departemen kedua.
        assert _aktif(org.sup1, org.p2) and _role(org.sup1, org.p2) == 20
        assert not _aktif(org.staf1, org.p2)  # staf tidak ikut melebar

    @pytest.mark.django_db
    def test_setel_dan_cabut_multi_lewat_god_mode(self, org, super_admin):
        from plane.license.api.views.hierarki import InstanceHierarkiEndpoint

        def _setel(data):
            request = APIRequestFactory().post("/api/instances/hierarki/", data, format="json")
            force_authenticate(request, user=super_admin)
            return InstanceHierarkiEndpoint.as_view()(request)

        # departemen_ids = pengganti penuh: kirim lengkap, bukan tambah-satu.
        r = _setel({"member_id": str(org.sup1.id), "departemen_ids": [str(org.smt1.id), str(org.smt2.id)]})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert set(r.data["member"]["departemen_ids"]) == {str(org.smt1.id), str(org.smt2.id)}
        assert _aktif(org.sup1, org.p2)

        r = _setel({"member_id": str(org.sup1.id), "departemen_ids": [str(org.smt1.id)]})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["departemen_ids"] == [str(org.smt1.id)]
        assert not _aktif(org.sup1, org.p2)
        assert _aktif(org.sup1, org.p1)

        r = _setel({"member_id": str(org.sup1.id), "departemen_ids": []})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["departemen_ids"] == []
        assert not _aktif(org.sup1, org.p1)

    @pytest.mark.django_db
    def test_multi_departemen_hanya_supervisor(self, org, super_admin):
        from plane.license.api.views.hierarki import InstanceHierarkiEndpoint

        request = APIRequestFactory().post(
            "/api/instances/hierarki/",
            {"member_id": str(org.staf1.id), "departemen_ids": [str(org.smt1.id), str(org.smt2.id)]},
            format="json",
        )
        force_authenticate(request, user=super_admin)
        r = InstanceHierarkiEndpoint.as_view()(request)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_turun_jenjang_dengan_multi_departemen_ditolak(self, org, super_admin):
        from plane.license.api.views.hierarki import InstanceHierarkiEndpoint

        JabatanOrganisasi.objects.create(
            workspace=org.ws, member=org.sup1, tingkat=TINGKAT_SUPERVISOR, departemen=org.smt2
        )
        request = APIRequestFactory().post(
            "/api/instances/hierarki/",
            {"member_id": str(org.sup1.id), "tingkat": TINGKAT_MEMBER},
            format="json",
        )
        force_authenticate(request, user=super_admin)
        r = InstanceHierarkiEndpoint.as_view()(request)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_multi_tampil_di_pohon_tanpa_flag_tambahan(self, org, super_admin):
        JabatanOrganisasi.objects.create(
            workspace=org.ws, member=org.sup1, tingkat=TINGKAT_SUPERVISOR, departemen=org.smt2
        )
        r = _god(InstanceOrganisasiEndpoint, "get", super_admin)
        assert r.status_code == status.HTTP_200_OK
        sales = next(v for v in r.data["divisi"] if v["kode"] == "SALES")
        smt2 = next(d for d in sales["departemen"] if d["kode"] == "SMT2")
        sup = next(a for a in smt2["anggota"] if a["id"] == str(org.sup1.id))
        assert "tambahan" not in sup
