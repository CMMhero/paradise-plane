# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: cabang dan Direktur Cabang (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak cabang (Plant Cilegon) dan Direktur Cabang (tingkat 33).

Bentuk uji:

    Kantor pusat  SALES -> SMT (P_HO)                manager mgr_ho, spv_ho, staf_ho
    Cabang CLG    PC    -> ENG (P_ENG), HRC (P_HRC)  manager mgr_pc, spv_eng, staf_eng, staf_hrc
                                                      Direktur Cabang bd
    Tanpa tempat  sekretaris sek, direktur dir

Yang dikunci: Direktur Cabang melihat, menyetujui, menugaskan, dan mendapat KPI
hanya di cabangnya. Kantor pusat tidak mendapat apa pun di cabang. Sekretaris dan
direktur tetap menjangkau keduanya. Konversi divisi jadi cabang tidak
menghilangkan departemen, keanggotaan, atau tugas.
"""

from io import StringIO
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from plane.db.models import (
    AksesHierarki,
    Cabang,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueAssignee,
    JabatanOrganisasi,
    Langganan,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    Ruang,
    State,
    TINGKAT_CABANG,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SEKRETARIS,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)
from plane.db.penempatan import setel_penempatan
from plane.license.api.views.hierarki import InstanceHierarkiEndpoint
from plane.license.api.views.organisasi import (
    InstanceCabangEndpoint,
    InstanceDivisiEndpoint,
    InstanceOrganisasiEndpoint,
)
from plane.license.models import Instance, InstanceAdmin
from plane.utils.hierarki import (
    FLAG_GERBANG,
    _bawahan_ids,
    calon_penyetuju,
    divisi_diawasi,
    galat_penugasan,
    tingkat_anggota,
)
from plane.utils.kanal_organisasi import kunci_cabang

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_BISA = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/bisa-ditugaskan/"
URL_ANTREAN = "/api/workspaces/{slug}/persetujuan/"
URL_KPI = "/api/workspaces/{slug}/kinerja/"
URL_KPI_LINGKUP = "/api/workspaces/{slug}/kinerja/lingkup/"


def _user(ws, nama):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{nama}-{unik}@plane.so", username=f"{nama}_{unik}", display_name=nama)
    WorkspaceMember.objects.create(workspace=ws, member=user, role=15)
    return user


def _orang(ws, nama, tingkat, departemen=None, divisi=None, cabang=None):
    user = _user(ws, nama)
    JabatanOrganisasi.objects.create(
        workspace=ws, member=user, tingkat=tingkat, departemen=departemen, divisi=divisi, cabang=cabang
    )
    return user


def _departemen(ws, divisi, kode):
    dep = Departemen.objects.create(workspace=ws, divisi=divisi, kode=kode, nama=f"Dept {kode}")
    project = Project.objects.create(name=f"Dept {kode}", identifier=kode.replace("-", ""), workspace=ws)
    DepartemenProject.objects.create(workspace=ws, departemen=dep, project=project)
    for grup in ("unstarted", "completed"):
        State.objects.create(
            name=grup, group=grup, color="#000000", project=project, workspace=ws, default=grup == "unstarted"
        )
    return dep, project


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


def _aktif(user, project):
    return ProjectMember.objects.filter(member=user, project=project, is_active=True).exists()


def _tugas(project, pembuat, nama):
    issue = Issue(
        name=nama,
        workspace=project.workspace,
        project=project,
        state=State.objects.get(project=project, group="unstarted"),
    )
    issue.save(created_by_id=pembuat.id)
    return issue


def _ajukan_selesai(project, staf, nama):
    issue = _tugas(project, staf, nama)
    IssueAssignee.objects.create(issue=issue, assignee=staf, project=project, workspace=project.workspace)
    PersetujuanPenugasan.objects.create(
        workspace=project.workspace, project=project, issue=issue, pemohon=staf, penerima=staf, status="menunggu"
    )
    return issue


@pytest.fixture
def org(db, workspace):
    o = type("Org", (), {})()
    o.ws = workspace
    o.clg = Cabang.objects.create(workspace=workspace, kode="CLG", nama="Plant Cilegon")
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.pc = Divisi.objects.create(workspace=workspace, kode="PC", nama="Plant Cilegon", cabang=o.clg)
    o.smt, o.p_ho = _departemen(workspace, o.sales, "SMT")
    o.eng, o.p_eng = _departemen(workspace, o.pc, "ENG")
    o.hrc, o.p_hrc = _departemen(workspace, o.pc, "HRC")
    o.mgr_ho = _orang(workspace, "mgrho", TINGKAT_MANAGER, divisi=o.sales)
    o.spv_ho = _orang(workspace, "spvho", TINGKAT_SUPERVISOR, departemen=o.smt)
    o.staf_ho = _orang(workspace, "stafho", TINGKAT_MEMBER, departemen=o.smt)
    o.mgr_pc = _orang(workspace, "mgrpc", TINGKAT_MANAGER, divisi=o.pc)
    o.spv_eng = _orang(workspace, "spveng", TINGKAT_SUPERVISOR, departemen=o.eng)
    o.staf_eng = _orang(workspace, "stafeng", TINGKAT_MEMBER, departemen=o.eng)
    o.staf_hrc = _orang(workspace, "stafhrc", TINGKAT_MEMBER, departemen=o.hrc)
    o.bd = _orang(workspace, "bd", TINGKAT_CABANG, cabang=o.clg)
    o.sek = _orang(workspace, "sek", TINGKAT_SEKRETARIS)
    o.dir = _orang(workspace, "dir", TINGKAT_DIREKTUR)
    return o


@pytest.fixture
def super_admin(db, workspace):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-cabang-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user(workspace, "super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _god(view, method, aktor, data=None, **kwargs):
    request = getattr(APIRequestFactory(), method)("/api/instances/organisasi/", data, format="json")
    force_authenticate(request, user=aktor)
    return view.as_view()(request, **kwargs)


def _setel_hierarki(aktor, data):
    request = APIRequestFactory().post("/api/instances/hierarki/", data, format="json")
    force_authenticate(request, user=aktor)
    return InstanceHierarkiEndpoint.as_view()(request)


# --------------------------------------------------------------------------
# Lihat
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestJangkauanCabang:
    @pytest.mark.django_db
    def test_direktur_cabang_anggota_project_cabangnya_saja(self, org):
        assert _aktif(org.bd, org.p_eng) and _aktif(org.bd, org.p_hrc)
        assert ProjectMember.objects.get(member=org.bd, project=org.p_eng).role == 20
        assert not _aktif(org.bd, org.p_ho)
        assert AksesHierarki.objects.filter(member=org.bd, project=org.p_eng).exists()

    @pytest.mark.django_db
    def test_kantor_pusat_tidak_melihat_cabang(self, org):
        for orang in (org.mgr_ho, org.spv_ho, org.staf_ho):
            assert not _aktif(orang, org.p_eng)
            assert not _aktif(orang, org.p_hrc)
        assert divisi_diawasi(org.mgr_ho.id, org.ws.id) == {org.p_ho.id}

    @pytest.mark.django_db
    def test_sekretaris_dan_direktur_melihat_keduanya(self, org):
        for orang in (org.sek, org.dir):
            assert _aktif(orang, org.p_ho) and _aktif(orang, org.p_eng)
            assert {org.p_ho.id, org.p_eng.id, org.p_hrc.id} <= divisi_diawasi(orang.id, org.ws.id)

    @pytest.mark.django_db
    def test_daftar_tugas_lewat_api(self, org):
        _tugas(org.p_eng, org.staf_eng, "Pompa")
        _tugas(org.p_ho, org.staf_ho, "Kunjungan")
        assert _klien(org.bd).get(URL_ISSUES.format(slug=org.ws.slug, project_id=org.p_eng.id)).status_code == 200
        assert _klien(org.bd).get(URL_ISSUES.format(slug=org.ws.slug, project_id=org.p_ho.id)).status_code != 200
        assert _klien(org.mgr_ho).get(URL_ISSUES.format(slug=org.ws.slug, project_id=org.p_eng.id)).status_code != 200

    @pytest.mark.django_db
    def test_divisi_baru_di_cabang_ikut_terjangkau(self, org):
        divisi = Divisi.objects.create(workspace=org.ws, kode="LOG", nama="Logistics", cabang=org.clg)
        _, p_log = _departemen(org.ws, divisi, "LOG")
        # Signal DepartemenProject menyinkronkan ulang workspace.
        assert _aktif(org.bd, p_log)
        assert not _aktif(org.mgr_ho, p_log)


# --------------------------------------------------------------------------
# Menyetujui
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPersetujuanCabang:
    @pytest.mark.django_db
    def test_calon_penyetuju(self, org):
        calon = calon_penyetuju(org.ws.id, org.p_eng.id, TINGKAT_MEMBER)
        assert org.bd.id in calon and org.mgr_pc.id in calon and org.spv_eng.id in calon
        assert org.mgr_ho.id not in calon
        assert org.bd.id not in calon_penyetuju(org.ws.id, org.p_ho.id, TINGKAT_MEMBER)

    @pytest.mark.django_db
    def test_halaman_persetujuan_hanya_cabangnya_dengan_nama_cabang(self, org):
        _ajukan_selesai(org.p_eng, org.staf_eng, "Selesai pompa")
        _ajukan_selesai(org.p_ho, org.staf_ho, "Selesai kunjungan")

        data = _klien(org.bd).get(URL_ANTREAN.format(slug=org.ws.slug)).json()
        assert [i["tugas"]["judul"] for i in data["hasil"]] == ["Selesai pompa"]
        (baris,) = data["hasil"]
        assert baris["cabang"] == {"id": str(org.clg.id), "kode": "CLG", "nama": "Plant Cilegon"}
        assert baris["divisi"]["kode"] == "PC"

        kantor = _klien(org.mgr_ho).get(URL_ANTREAN.format(slug=org.ws.slug)).json()
        assert [i["tugas"]["judul"] for i in kantor["hasil"]] == ["Selesai kunjungan"]
        assert kantor["hasil"][0]["cabang"] is None

    @pytest.mark.django_db
    def test_menyetujui_lewat_endpoint_project(self, org):
        _ajukan_selesai(org.p_eng, org.staf_eng, "Selesai pompa")
        pk = _klien(org.bd).get(URL_ANTREAN.format(slug=org.ws.slug)).json()["hasil"][0]["id"]
        respon = _klien(org.bd).post(
            f"/api/workspaces/{org.ws.slug}/projects/{org.p_eng.id}/persetujuan-penugasan/{pk}/",
            {"aksi": "setujui"},
            format="json",
        )
        assert respon.status_code == status.HTTP_200_OK, respon.data


# --------------------------------------------------------------------------
# Menugaskan
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPenugasanCabang:
    @pytest.mark.django_db
    def test_menugaskan_di_bawah_33_di_cabang(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert galat_penugasan(org.p_eng.id, [org.staf_eng.id], actor=org.bd) is None
        assert galat_penugasan(org.p_eng.id, [org.mgr_pc.id], actor=org.bd) is None
        respon = _klien(org.bd).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p_eng.id),
            {"name": "Ganti seal", "assignee_ids": [str(org.spv_eng.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_201_CREATED, respon.data

    @pytest.mark.django_db
    def test_tidak_bisa_menugaskan_sekretaris_atau_direktur(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        for atasan in (org.sek, org.dir):
            assert galat_penugasan(org.p_eng.id, [atasan.id], actor=org.bd) is not None
        ids = {
            u["id"]
            for u in _klien(org.bd).get(URL_BISA.format(slug=org.ws.slug, project_id=org.p_eng.id)).json()["users"]
        }  # noqa: E501
        assert str(org.staf_eng.id) in ids and str(org.mgr_pc.id) in ids
        assert str(org.sek.id) not in ids and str(org.dir.id) not in ids

    @pytest.mark.django_db
    def test_tidak_bisa_menugaskan_di_kantor_pusat(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert galat_penugasan(org.p_ho.id, [org.staf_ho.id], actor=org.bd) is not None
        respon = _klien(org.bd).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p_ho.id),
            {"name": "Lintas", "assignee_ids": [str(org.staf_ho.id)]},
            format="json",
        )
        assert respon.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN)

    @pytest.mark.django_db
    def test_manager_kantor_pusat_tidak_menugaskan_di_cabang(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert galat_penugasan(org.p_eng.id, [org.staf_eng.id], actor=org.mgr_ho) is not None

    @pytest.mark.django_db
    def test_bawahan_dan_jenjang_lokal(self, org):
        bawahan = _bawahan_ids(org.bd.id, org.ws.id, org.p_eng.id)
        assert {org.mgr_pc.id, org.spv_eng.id, org.staf_eng.id} <= bawahan
        assert not {org.sek.id, org.dir.id, org.bd.id} & bawahan
        assert _bawahan_ids(org.bd.id, org.ws.id, org.p_ho.id) == set()
        assert tingkat_anggota(org.bd.id, org.ws.id, org.p_eng.id) == TINGKAT_CABANG


# --------------------------------------------------------------------------
# KPI
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestKpiCabang:
    @pytest.mark.django_db
    def test_pilihan_lingkup_direktur_cabang(self, org):
        data = _klien(org.bd).get(URL_KPI_LINGKUP.format(slug=org.ws.slug)).json()
        assert [c["code"] for c in data["branches"]] == ["CLG"]
        assert [d["code"] for d in data["divisions"]] == ["PC"]
        orang = {p["id"] for p in data["people"]}
        assert str(org.staf_eng.id) in orang and str(org.mgr_pc.id) in orang
        assert str(org.staf_ho.id) not in orang
        assert data["organisation"] is False

    @pytest.mark.django_db
    def test_lingkup_cabang(self, org):
        respon = _klien(org.bd).get(URL_KPI.format(slug=org.ws.slug), {"lingkup": "cabang", "id": str(org.clg.id)})
        assert respon.status_code == status.HTTP_200_OK, respon.data
        data = respon.json()
        assert data["scope"]["kind"] == "cabang"
        assert data["scope"]["name"] == "Plant Cilegon"
        assert data["breakdown"]["kind"] == "divisi"
        assert [b["code"] for b in data["breakdown"]["rows"]] == ["PC"]

    @pytest.mark.django_db
    def test_kantor_pusat_ditolak_lingkup_cabang(self, org):
        for orang in (org.mgr_ho, org.mgr_pc):
            respon = _klien(orang).get(URL_KPI.format(slug=org.ws.slug), {"lingkup": "cabang", "id": str(org.clg.id)})
            assert respon.status_code == status.HTTP_403_FORBIDDEN
        respon = _klien(org.bd).get(URL_KPI.format(slug=org.ws.slug), {"lingkup": "divisi", "id": str(org.sales.id)})
        assert respon.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_direktur_melihat_semua_cabang(self, org):
        data = _klien(org.dir).get(URL_KPI_LINGKUP.format(slug=org.ws.slug)).json()
        assert [c["code"] for c in data["branches"]] == ["CLG"]
        respon = _klien(org.dir).get(URL_KPI.format(slug=org.ws.slug), {"lingkup": "cabang", "id": str(org.clg.id)})
        assert respon.status_code == status.HTTP_200_OK


# --------------------------------------------------------------------------
# Penempatan dan kanal
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPenempatanCabang:
    def _tempat(self, user, ws):
        return set(
            JabatanOrganisasi.objects.filter(workspace=ws, member=user).values_list(
                "tingkat", "departemen_id", "divisi_id", "cabang_id"
            )
        )

    @pytest.mark.django_db
    def test_manager_dinaikkan_jadi_direktur_cabang(self, org):
        setel_penempatan(org.ws, org.mgr_pc, TINGKAT_CABANG, set(), {str(org.pc.id)}, cabang_ids={str(org.clg.id)})
        # Divisi di dalam cabang yang ia pimpin dilepas: cabangnya sudah menjangkau.
        assert self._tempat(org.mgr_pc, org.ws) == {(TINGKAT_CABANG, None, None, org.clg.id)}
        assert _aktif(org.mgr_pc, org.p_hrc)

    @pytest.mark.django_db
    def test_cabang_dibuang_di_bawah_direktur_cabang(self, org):
        setel_penempatan(org.ws, org.bd, TINGKAT_MANAGER, set(), {str(org.pc.id)})
        assert self._tempat(org.bd, org.ws) == {(TINGKAT_MANAGER, None, org.pc.id, None)}

    @pytest.mark.django_db
    def test_cabang_tetap_kalau_pemanggil_tidak_menyebutnya(self, org):
        setel_penempatan(org.ws, org.bd, TINGKAT_CABANG, {str(org.smt.id)}, set())
        assert (TINGKAT_CABANG, None, None, org.clg.id) in self._tempat(org.bd, org.ws)

    @pytest.mark.django_db
    def test_cabang_terakhir_dicabut_jatuh_ke_staf(self, org):
        setel_penempatan(org.ws, org.bd, TINGKAT_CABANG, set(), set(), cabang_ids=set())
        assert self._tempat(org.bd, org.ws) == {(TINGKAT_MEMBER, None, None, None)}
        assert not _aktif(org.bd, org.p_eng)

    @pytest.mark.django_db
    def test_kanal_cabang(self, org):
        ruang = Ruang.objects.get(workspace=org.ws, kunci_sistem=kunci_cabang(org.clg.id))
        anggota = set(Langganan.objects.filter(ruang=ruang).values_list("user_id", flat=True))
        assert {org.bd.id, org.mgr_pc.id, org.spv_eng.id, org.staf_eng.id, org.staf_hrc.id} <= anggota
        assert not {org.mgr_ho.id, org.staf_ho.id, org.dir.id} & anggota
        assert ruang.nama == "Plant Cilegon"


# --------------------------------------------------------------------------
# God Mode
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestGodModeCabang:
    @pytest.mark.django_db
    def test_buat_ubah_hapus_cabang(self, org, super_admin):
        r = _god(InstanceCabangEndpoint, "post", super_admin, {"kode": "sby", "nama": "Plant Surabaya"})
        assert r.status_code == status.HTTP_201_CREATED, r.data
        sby = next(c for c in r.data["cabang"] if c["kode"] == "SBY")
        assert _god(InstanceCabangEndpoint, "post", super_admin, {"kode": "SBY", "nama": "Lagi"}).status_code == 400

        r = _god(InstanceCabangEndpoint, "patch", super_admin, {"nama": "Plant Sidoarjo"}, pk=sby["id"])
        assert r.status_code == status.HTTP_200_OK
        assert {c["nama"] for c in r.data["cabang"]} == {"Plant Cilegon", "Plant Sidoarjo"}

        r = _god(InstanceCabangEndpoint, "delete", super_admin, pk=sby["id"])
        assert r.status_code == status.HTTP_200_OK
        assert not Cabang.objects.filter(kode="SBY").exists()

    @pytest.mark.django_db
    def test_hapus_cabang_berisi_ditolak(self, org, super_admin):
        r = _god(InstanceCabangEndpoint, "delete", super_admin, pk=org.clg.id)
        assert r.status_code == status.HTTP_409_CONFLICT
        org.pc.cabang = None
        org.pc.save()
        r = _god(InstanceCabangEndpoint, "delete", super_admin, pk=org.clg.id)
        assert r.status_code == status.HTTP_409_CONFLICT, "Direktur Cabang masih ditempatkan"
        assert Cabang.objects.filter(pk=org.clg.id).exists()

    @pytest.mark.django_db
    def test_pohon_mengelompokkan_cabang(self, org, super_admin):
        r = _god(InstanceOrganisasiEndpoint, "get", super_admin)
        (cabang,) = r.data["cabang"]
        assert cabang["kode"] == "CLG"
        assert [d["id"] for d in cabang["direktur"]] == [str(org.bd.id)]
        per_divisi = {v["kode"]: v["cabang_id"] for v in r.data["divisi"]}
        assert per_divisi == {"SALES": None, "PC": str(org.clg.id)}

    @pytest.mark.django_db
    def test_buat_divisi_di_cabang_dan_pindah_ke_kantor_pusat(self, org, super_admin):
        r = _god(
            InstanceDivisiEndpoint,
            "post",
            super_admin,
            {"kode": "LOG", "nama": "Logistics", "cabang_id": str(org.clg.id)},
        )  # noqa: E501
        assert r.status_code == status.HTTP_201_CREATED, r.data
        assert Divisi.objects.get(kode="LOG").cabang_id == org.clg.id

        r = _god(InstanceDivisiEndpoint, "patch", super_admin, {"cabang_id": None}, pk=org.pc.id)
        assert r.status_code == status.HTTP_200_OK, r.data
        org.pc.refresh_from_db()
        assert org.pc.cabang_id is None
        # Jangkauan Direktur Cabang ikut berubah lewat sinkron hierarki.
        assert not _aktif(org.bd, org.p_eng)
        assert _aktif(org.staf_eng, org.p_eng)

        r = _god(InstanceDivisiEndpoint, "patch", super_admin, {"cabang_id": str(org.clg.id)}, pk=org.sales.id)
        assert r.status_code == status.HTTP_200_OK
        assert _aktif(org.bd, org.p_ho)

    @pytest.mark.django_db
    def test_cabang_asing_ditolak(self, org, super_admin):
        r = _god(InstanceDivisiEndpoint, "patch", super_admin, {"cabang_id": str(uuid4())}, pk=org.pc.id)
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_tempatkan_direktur_cabang_lewat_hierarki(self, org, super_admin):
        r = _setel_hierarki(super_admin, {"member_id": str(org.spv_eng.id), "cabang_id": str(org.clg.id)})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_CABANG
        assert r.data["member"]["cabang_ids"] == [str(org.clg.id)]
        assert _aktif(org.spv_eng, org.p_hrc)

        r = _setel_hierarki(
            super_admin, {"member_id": str(org.staf_ho.id), "tingkat": TINGKAT_SUPERVISOR, "cabang_id": str(org.clg.id)}
        )
        assert r.status_code == status.HTTP_400_BAD_REQUEST
        r = _setel_hierarki(super_admin, {"member_id": str(org.dir.id), "cabang_id": str(org.clg.id)})
        assert r.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_get_hierarki_membawa_cabang(self, org, super_admin):
        request = APIRequestFactory().get("/api/instances/hierarki/")
        force_authenticate(request, user=super_admin)
        data = InstanceHierarkiEndpoint.as_view()(request).data
        assert data["cabang_pilihan"] == [{"id": str(org.clg.id), "kode": "CLG", "nama": "Plant Cilegon"}]
        assert {v["kode"]: v["cabang_id"] for v in data["divisi_pilihan"]}["PC"] == str(org.clg.id)
        bd = next(a for a in data["anggota"] if a["id"] == str(org.bd.id))
        assert bd["cabang_ids"] == [str(org.clg.id)] and bd["tingkat"] == TINGKAT_CABANG


# --------------------------------------------------------------------------
# Konversi Plant Cilegon
# --------------------------------------------------------------------------


@pytest.fixture
def cilegon(db, workspace):
    """Keadaan produksi hari ini: PC adalah divisi kantor pusat dengan departemennya sendiri."""
    o = type("Cilegon", (), {})()
    o.ws = workspace
    o.pc = Divisi.objects.create(workspace=workspace, kode="PC", nama="Plant Cilegon")
    o.eng, o.p_eng = _departemen(workspace, o.pc, "ENG-ENG")
    o.ga, o.p_ga = _departemen(workspace, o.pc, "GA")
    o.yenyen = _orang(workspace, "yenyen", TINGKAT_MANAGER, divisi=o.pc)
    o.yohanes = _orang(workspace, "yohanes", TINGKAT_MANAGER, divisi=o.pc)
    o.staf = _orang(workspace, "staf", TINGKAT_MEMBER, departemen=o.eng)
    # Anggota eksplisit (tanpa AksesHierarki) harus selamat.
    o.tamu = _user(workspace, "tamu")
    ProjectMember.objects.create(project=o.p_ga, member=o.tamu, workspace=workspace, role=15)
    o.issue = _tugas(o.p_eng, o.staf, "Kalibrasi")
    _tugas(o.p_ga, o.staf, "Kebersihan")
    return o


def _jalankan(*args):
    keluar = StringIO()
    call_command("jadikan_cabang", *args, stdout=keluar)
    return keluar.getvalue()


def _potret(o):
    return (
        set(Departemen.objects.filter(divisi=o.pc).values_list("id", flat=True)),
        set(
            ProjectMember.objects.filter(project__in=[o.p_eng, o.p_ga], is_active=True).values_list(
                "project_id", "member_id", "role"
            )
        ),
        set(Issue.issue_objects.filter(project__in=[o.p_eng, o.p_ga]).values_list("id", "project_id")),
    )


@pytest.mark.contract
class TestJadikanCabang:
    ARGS = ("--divisi", "PC", "--kode", "CLG", "--nama", "Plant Cilegon")

    @pytest.mark.django_db
    def test_dry_run_tidak_menulis(self, cilegon):
        sebelum = _potret(cilegon)
        keluar = _jalankan(*self.ARGS, "--direktur-cabang", cilegon.yenyen.email, "--dry-run")
        assert "Create branch CLG Plant Cilegon." in keluar
        assert "Dry run" in keluar
        assert not Cabang.objects.exists()
        assert _potret(cilegon) == sebelum
        assert tingkat_anggota(cilegon.yenyen.id, cilegon.ws.id) == TINGKAT_MANAGER

    @pytest.mark.django_db
    def test_konversi_menjaga_departemen_keanggotaan_dan_tugas(self, cilegon):
        deps, anggota, tugas = _potret(cilegon)
        _jalankan(*self.ARGS, "--direktur-cabang", cilegon.yenyen.email)

        cabang = Cabang.objects.get(kode="CLG")
        cilegon.pc.refresh_from_db()
        assert cilegon.pc.cabang_id == cabang.id
        deps_baru, anggota_baru, tugas_baru = _potret(cilegon)
        assert deps_baru == deps
        assert tugas_baru == tugas
        # Semua keanggotaan lama tetap; yang lain tidak dicabut.
        assert anggota <= anggota_baru
        assert _aktif(cilegon.tamu, cilegon.p_ga)
        # Yenyen sekarang Direktur Cabang yang menjangkau seluruh PC.
        assert tingkat_anggota(cilegon.yenyen.id, cilegon.ws.id) == TINGKAT_CABANG
        assert set(JabatanOrganisasi.objects.filter(member=cilegon.yenyen).values_list("divisi_id", "cabang_id")) == {
            (None, cabang.id)
        }
        assert divisi_diawasi(cilegon.yenyen.id, cilegon.ws.id) == {cilegon.p_eng.id, cilegon.p_ga.id}
        # Yohanes tetap manager PC.
        assert tingkat_anggota(cilegon.yohanes.id, cilegon.ws.id) == TINGKAT_MANAGER
        assert divisi_diawasi(cilegon.yohanes.id, cilegon.ws.id) == {cilegon.p_eng.id, cilegon.p_ga.id}

    @pytest.mark.django_db
    def test_jalan_ulang_tidak_mengubah_apa_pun(self, cilegon):
        _jalankan(*self.ARGS, "--direktur-cabang", cilegon.yenyen.email)
        sesudah = _potret(cilegon)
        jabatan = set(JabatanOrganisasi.objects.values_list("id", "tingkat", "departemen_id", "divisi_id", "cabang_id"))

        keluar = _jalankan(*self.ARGS, "--direktur-cabang", cilegon.yenyen.email)

        assert "Nothing to change." in keluar
        assert Cabang.objects.count() == 1
        assert _potret(cilegon) == sesudah
        assert (
            set(JabatanOrganisasi.objects.values_list("id", "tingkat", "departemen_id", "divisi_id", "cabang_id"))
            == jabatan
        )  # noqa: E501

    @pytest.mark.django_db
    def test_divisi_di_cabang_lain_ditolak(self, cilegon):
        from django.core.management.base import CommandError

        lain = Cabang.objects.create(workspace=cilegon.ws, kode="SBY", nama="Surabaya")
        cilegon.pc.cabang = lain
        cilegon.pc.save()
        with pytest.raises(CommandError):
            _jalankan(*self.ARGS)
