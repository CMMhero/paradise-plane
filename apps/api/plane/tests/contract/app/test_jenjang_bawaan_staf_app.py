# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jenjang bawaan staf + izin buat project
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak 4 Nov 2026.

1. Jenjang bawaan = Staf. Orang tanpa baris jabatan dilaporkan Staf di God Mode,
   dan `tingkat=null` mengembalikan orang ke Staf tanpa tempat.
2. Supervisor/manager yang dicabut dari tempat TERAKHIRNYA jatuh ke Staf
   (`plane/db/penempatan.tingkat_sesudah_cabut`, KEP-86). Masih memegang satu
   departemen atau divisi mana pun = jenjangnya tetap.
3. Staf / member biasa tidak boleh membuat project (web + API v1). Admin workspace,
   Super Admin, dan Supervisor ke atas boleh.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    JabatanOrganisasi,
    Project,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    WorkspaceMember,
)
from plane.tests.contract.app.test_organisasi_app import (  # noqa: F401 (fixture)
    _aktif,
    _god,
    _setel_hierarki,
    _tempat,
    _tempatkan,
    _user,
    org,
    super_admin,
)
from plane.db.penempatan import tingkat_sesudah_cabut
from plane.license.api.views.hierarki import InstanceHierarkiEndpoint
from plane.utils.izin_buat_project import boleh_buat_project


def _tingkat(user, workspace):
    return set(JabatanOrganisasi.objects.filter(workspace=workspace, member=user).values_list("tingkat", flat=True))


# --------------------------------------------------------------------------
# Aturan murni
# --------------------------------------------------------------------------


@pytest.mark.unit
class TestTingkatSesudahCabut:
    def test_tanpa_pencabutan_jenjang_tetap(self):
        assert tingkat_sesudah_cabut(TINGKAT_MANAGER, set(), set(), set(), set()) == TINGKAT_MANAGER

    def test_manager_tanpa_tempat_tersisa_jadi_staf(self):
        assert tingkat_sesudah_cabut(TINGKAT_MANAGER, set(), {"v"}, set(), set()) == TINGKAT_MEMBER

    def test_manager_kehilangan_divisi_tapi_masih_di_departemen_tetap(self):
        assert tingkat_sesudah_cabut(TINGKAT_MANAGER, {"d"}, {"v"}, {"d"}, set()) == TINGKAT_MANAGER

    def test_manager_masih_punya_divisi_lain_tetap(self):
        assert tingkat_sesudah_cabut(TINGKAT_MANAGER, set(), {"v1", "v2"}, set(), {"v2"}) == TINGKAT_MANAGER

    def test_supervisor_tanpa_tempat_tersisa_jadi_staf(self):
        assert tingkat_sesudah_cabut(TINGKAT_SUPERVISOR, {"d"}, set(), set(), set()) == TINGKAT_MEMBER

    def test_supervisor_masih_punya_departemen_lain_tetap(self):
        assert tingkat_sesudah_cabut(TINGKAT_SUPERVISOR, {"a", "b"}, set(), {"b"}, set()) == TINGKAT_SUPERVISOR

    def test_staf_dan_direktur_tidak_berubah(self):
        assert tingkat_sesudah_cabut(TINGKAT_MEMBER, {"d"}, set(), set(), set()) == TINGKAT_MEMBER
        assert tingkat_sesudah_cabut(TINGKAT_DIREKTUR, {"d"}, set(), set(), set()) == TINGKAT_DIREKTUR


# --------------------------------------------------------------------------
# Lewat penulis tunggal (endpoint God Mode)
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestCabutTempatTerakhir:
    @pytest.mark.django_db
    def test_manager_dicabut_dari_satu_satunya_divisi_jadi_staf_tanpa_tempat(self, org, super_admin):
        r = _setel_hierarki(super_admin, {"member_id": str(org.manager.id), "divisi_ids": []})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_MEMBER
        assert _tempat(org.manager, org.ws) == {(None, None)}
        assert _tingkat(org.manager, org.ws) == {TINGKAT_MEMBER}
        assert not _aktif(org.manager, org.p1) and not _aktif(org.manager, org.p2)

    @pytest.mark.django_db
    def test_manager_dua_divisi_dicabut_satu_tetap_manager(self, org, super_admin):
        _tempatkan(org.ws, org.manager, TINGKAT_MANAGER, divisi=org.hrga)
        r = _setel_hierarki(super_admin, {"member_id": str(org.manager.id), "divisi_ids": [str(org.hrga.id)]})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_MANAGER
        assert _tempat(org.manager, org.ws) == {(None, org.hrga.id)}

    @pytest.mark.django_db
    def test_manager_kehilangan_divisi_tetap_manager_di_departemennya(self, org, super_admin):
        _tempatkan(org.ws, org.manager, TINGKAT_MANAGER, departemen=org.hr)
        r = _setel_hierarki(super_admin, {"member_id": str(org.manager.id), "divisi_id": None})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_MANAGER
        assert _tempat(org.manager, org.ws) == {(org.hr.id, None)}
        assert _aktif(org.manager, org.p3)

    @pytest.mark.django_db
    def test_supervisor_dicabut_dari_departemen_terakhir_jadi_staf(self, org, super_admin):
        r = _setel_hierarki(super_admin, {"member_id": str(org.sup1.id), "departemen_ids": []})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_MEMBER
        assert _tempat(org.sup1, org.ws) == {(None, None)}

    @pytest.mark.django_db
    def test_supervisor_dua_departemen_dicabut_satu_tetap_supervisor(self, org, super_admin):
        _tempatkan(org.ws, org.sup1, TINGKAT_SUPERVISOR, departemen=org.smt2)
        r = _setel_hierarki(super_admin, {"member_id": str(org.sup1.id), "departemen_ids": [str(org.smt2.id)]})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_SUPERVISOR
        assert _tempat(org.sup1, org.ws) == {(org.smt2.id, None)}

    @pytest.mark.django_db
    def test_menyetel_manager_tanpa_divisi_tidak_dijatuhkan(self, org, super_admin):
        """Calon manager boleh diberi jenjang dulu, divisi menyusul."""
        orang = _user("calon", org.ws)
        r = _setel_hierarki(super_admin, {"member_id": str(orang.id), "tingkat": TINGKAT_MANAGER})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_MANAGER

    @pytest.mark.django_db
    def test_cabut_jenjang_direktur_kembali_staf(self, org, super_admin):
        orang = _user("dir", org.ws)
        _setel_hierarki(super_admin, {"member_id": str(orang.id), "tingkat": TINGKAT_DIREKTUR})
        r = _setel_hierarki(super_admin, {"member_id": str(orang.id), "tingkat": None})
        assert r.status_code == status.HTTP_200_OK, r.data
        assert r.data["member"]["tingkat"] == TINGKAT_MEMBER
        assert _tempat(orang, org.ws) == {(None, None)}


@pytest.mark.contract
class TestBawaanStafDiGodMode:
    @pytest.mark.django_db
    def test_orang_tanpa_jabatan_dilaporkan_staf(self, org, super_admin):
        baru = _user("baru", org.ws)
        r = _god(InstanceHierarkiEndpoint, "get", super_admin)
        assert r.status_code == status.HTTP_200_OK
        baris = next(a for a in r.data["anggota"] if a["id"] == str(baru.id))
        assert baris["tingkat"] == TINGKAT_MEMBER
        assert baris["tingkat_bawaan"] is True
        staf = next(a for a in r.data["anggota"] if a["id"] == str(org.staf1.id))
        assert staf["tingkat_bawaan"] is False


# --------------------------------------------------------------------------
# Izin membuat project
# --------------------------------------------------------------------------

URL_WEB = "/api/workspaces/{slug}/projects/"
URL_BOLEH = "/api/workspaces/{slug}/boleh-buat-project/"


def _klien(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _buat(user, workspace):
    kode = uuid4().hex[:5].upper()
    return _klien(user).post(
        URL_WEB.format(slug=workspace.slug), {"name": f"Project {kode}", "identifier": f"X{kode}"}, format="json"
    )


@pytest.mark.contract
class TestIzinBuatProject:
    @pytest.mark.django_db
    def test_staf_member_ditolak(self, org):
        r = _buat(org.staf1, org.ws)
        assert r.status_code == status.HTTP_403_FORBIDDEN, r.data
        assert not Project.objects.filter(name__startswith="Project ", workspace=org.ws).exists()

    @pytest.mark.django_db
    def test_member_tanpa_jabatan_dihitung_staf_dan_ditolak(self, org):
        baru = _user("baru", org.ws)
        assert _buat(baru, org.ws).status_code == status.HTTP_403_FORBIDDEN
        assert boleh_buat_project(baru, org.ws.id) is False

    @pytest.mark.django_db
    def test_supervisor_dan_manager_boleh(self, org):
        assert _buat(org.sup1, org.ws).status_code == status.HTTP_201_CREATED
        assert _buat(org.manager, org.ws).status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_admin_workspace_berjenjang_staf_boleh(self, org):
        WorkspaceMember.objects.filter(workspace=org.ws, member=org.staf2).update(role=20)
        assert _buat(org.staf2, org.ws).status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_super_admin_boleh(self, org, super_admin):
        assert boleh_buat_project(super_admin, org.ws.id) is True

    @pytest.mark.django_db
    def test_guest_ditolak_meski_berjenjang(self, org):
        WorkspaceMember.objects.filter(workspace=org.ws, member=org.sup1).update(role=5)
        assert boleh_buat_project(org.sup1, org.ws.id) is False

    @pytest.mark.django_db
    def test_endpoint_boleh_buat_project(self, org):
        r = _klien(org.staf1).get(URL_BOLEH.format(slug=org.ws.slug))
        assert r.status_code == status.HTTP_200_OK
        assert r.data == {"boleh": False}
        r = _klien(org.sup1).get(URL_BOLEH.format(slug=org.ws.slug))
        assert r.data == {"boleh": True}

    @pytest.mark.django_db
    def test_supervisor_dicabut_dari_tempat_terakhir_kehilangan_izin(self, org, super_admin):
        """KEP-86: tanpa tempat tersisa, supervisor jatuh ke Staf, izinnya ikut hilang."""
        assert boleh_buat_project(org.sup1, org.ws.id) is True
        _setel_hierarki(super_admin, {"member_id": str(org.sup1.id), "departemen_ids": []})
        assert boleh_buat_project(org.sup1, org.ws.id) is False

    @pytest.mark.django_db
    def test_supervisor_diturunkan_ke_staf_kehilangan_izin(self, org, super_admin):
        assert boleh_buat_project(org.sup1, org.ws.id) is True
        _setel_hierarki(super_admin, {"member_id": str(org.sup1.id), "tingkat": TINGKAT_MEMBER})
        assert boleh_buat_project(org.sup1, org.ws.id) is False
