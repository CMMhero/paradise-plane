# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jenjang Asisten Manager (P215)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# ruff: noqa: F811  (fixture diimpor lalu dipakai sebagai parameter, pola pytest)

"""Asisten Manager (25): ditempatkan di departemen seperti supervisor, di atas supervisor, di bawah manager.

Bentuk uji (fixture `org` dari test_aturan_kerja_god_mode) ditambah `asm` di SMT1:

    SALES (manager) -> SMT1 (P1): asm (Asisten Manager), sup + sup_b (Supervisor), staf
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.bgtasks.direktur_digest_task import DataWorkspace, susun_laporan
from plane.db.models import (
    Departemen,
    Divisi,
    Issue,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    TINGKAT_ASISTEN_MANAGER,
    TINGKAT_MANAGER,
    TINGKAT_SUPERVISOR,
)
from plane.db.penempatan import setel_penempatan
from plane.license.api.views.aturan import InstanceRulesEndpoint
from plane.license.api.views.hierarki import InstanceHierarkiEndpoint
from plane.license.models import Instance, InstanceAdmin
from plane.tests.contract.app.test_aturan_kerja_god_mode import (  # noqa: F401
    _anggota,
    _klien,
    _setel,
    _user,
    org,
)
from plane.tests.contract.app.test_daily_digest_peran import HARI_INI, Dunia, _orang
from plane.utils import aturan
from plane.utils import saklar_instance as si
from plane.utils.aturan.area_tugas import APPROVER_MIN_LEVEL
from plane.utils.hierarki import FLAG_GERBANG, divisi_diawasi, tingkat_anggota
from plane.utils.setelan_instance import FRASA_KONFIRMASI


@pytest.fixture
def asm(org, monkeypatch):
    monkeypatch.setenv(FLAG_GERBANG, "1")
    org.asm = _user("asm", org.ws)
    JabatanOrganisasi.objects.create(
        workspace=org.ws, member=org.asm, tingkat=TINGKAT_ASISTEN_MANAGER, departemen=org.smt1
    )
    _anggota(org.p1, org.asm)
    return org


@pytest.fixture
def super_admin(org):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-asm-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user("super", org.ws)
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _url_issues(org):
    return f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/issues/"


def _url_keputusan(org, baris):
    return f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/persetujuan-penugasan/{baris.id}/"


def _buat(org, pembuat, assignee):
    return _klien(pembuat).post(_url_issues(org), {"name": "Tugas", "assignee_ids": [str(assignee.id)]}, format="json")


def _selesaikan_sendiri(org, user):
    """`user` membuat tugasnya sendiri lalu menggesernya ke Done. Pengajuannya, atau None."""
    respon = _buat(org, user, user)
    assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
    issue_id = respon.json()["id"]
    respon = _klien(user).patch(
        f"{_url_issues(org)}{issue_id}/", {"state": str(org.states["completed"].id)}, format="json"
    )
    assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
    return PersetujuanPenugasan.objects.filter(issue_id=issue_id, status="menunggu").first()


@pytest.mark.contract
class TestPenempatan:
    @pytest.mark.django_db
    def test_peran_departemen_25_tersimpan(self, org):
        orang = _user("baru", org.ws)
        setel_penempatan(org.ws, orang, TINGKAT_ASISTEN_MANAGER, [org.smt1.id], [])
        baris = JabatanOrganisasi.objects.get(workspace=org.ws, member=orang)
        assert (baris.tingkat, baris.departemen_id, baris.divisi_id) == (TINGKAT_ASISTEN_MANAGER, org.smt1.id, None)
        assert tingkat_anggota(orang.id, org.ws.id, org.p1.id) == TINGKAT_ASISTEN_MANAGER

    @pytest.mark.django_db
    def test_beberapa_departemen_tidak_pernah_divisi(self, org):
        smt2 = Departemen.objects.create(workspace=org.ws, divisi=org.sales, kode="SMT2", nama="Sales Team 2")
        orang = _user("dua", org.ws)
        dibuang = setel_penempatan(org.ws, orang, TINGKAT_ASISTEN_MANAGER, [org.smt1.id, smt2.id], [org.sales.id])
        assert dibuang == {str(org.sales.id)}
        baris = JabatanOrganisasi.objects.filter(workspace=org.ws, member=orang)
        assert {(b.departemen_id, b.divisi_id, b.tingkat) for b in baris} == {
            (org.smt1.id, None, TINGKAT_ASISTEN_MANAGER),
            (smt2.id, None, TINGKAT_ASISTEN_MANAGER),
        }

    @pytest.mark.django_db
    def test_manager_di_departemen_baru_tetap_supervisor(self, org):
        """Batas peran departemen naik ke 25, tapi bawaan manager di departemen lain tidak ikut naik."""
        hrga = Divisi.objects.create(workspace=org.ws, kode="HRGA", nama="HRGA")
        hr = Departemen.objects.create(workspace=org.ws, divisi=hrga, kode="HR", nama="HR")
        setel_penempatan(org.ws, org.manager, TINGKAT_MANAGER, [hr.id], [org.sales.id])
        assert JabatanOrganisasi.objects.get(member=org.manager, departemen=hr).tingkat == TINGKAT_SUPERVISOR

    @pytest.mark.django_db
    def test_baris_lama_manager_departemen_jadi_supervisor(self, org):
        hrga = Divisi.objects.create(workspace=org.ws, kode="HRGA", nama="HRGA")
        hr = Departemen.objects.create(workspace=org.ws, divisi=hrga, kode="HR", nama="HR")
        JabatanOrganisasi.objects.create(workspace=org.ws, member=org.manager, tingkat=TINGKAT_MANAGER, departemen=hr)
        setel_penempatan(org.ws, org.manager, TINGKAT_MANAGER, [hr.id], [org.sales.id])
        assert JabatanOrganisasi.objects.get(member=org.manager, departemen=hr).tingkat == TINGKAT_SUPERVISOR

    @pytest.mark.django_db
    def test_god_mode_menerima_peran_departemen_25(self, org, super_admin):
        orang = _user("gm", org.ws)
        request = APIRequestFactory().post(
            "/api/instances/hierarki/",
            {
                "member_id": str(orang.id),
                "departemen_ids": [str(org.smt1.id)],
                "peran_departemen": {str(org.smt1.id): TINGKAT_ASISTEN_MANAGER},
            },
            format="json",
        )
        force_authenticate(request, user=super_admin)
        respon = InstanceHierarkiEndpoint.as_view()(request)
        assert respon.status_code == status.HTTP_200_OK, respon.data
        assert respon.data["member"]["tingkat"] == TINGKAT_ASISTEN_MANAGER
        assert respon.data["member"]["tingkat_nama"] == "Asisten Manager"


@pytest.mark.contract
class TestPenugasan:
    @pytest.mark.django_db
    def test_asisten_manager_menugaskan_supervisor(self, asm):
        respon = _buat(asm, asm.asm, asm.sup)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_supervisor_tidak_menugaskan_asisten_manager(self, asm):
        respon = _buat(asm, asm.sup, asm.asm)
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_asisten_manager_tidak_menugaskan_manager(self, asm):
        respon = _buat(asm, asm.asm, asm.manager)
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, getattr(respon, "data", None)


@pytest.mark.contract
class TestPersetujuan:
    @pytest.mark.django_db
    def test_bawaan_asisten_manager_tidak_menunggu(self, asm):
        assert _selesaikan_sendiri(asm, asm.asm) is None

    @pytest.mark.django_db
    def test_pengajuan_staf_bisa_diputuskan_asisten_manager(self, asm):
        baris = _selesaikan_sendiri(asm, asm.staf)
        respon = _klien(asm.asm).post(_url_keputusan(asm, baris), {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_pengajuan_supervisor_diputuskan_asisten_manager(self, asm):
        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_MANAGER)
        baris = _selesaikan_sendiri(asm, asm.sup)
        assert baris is not None
        assert _klien(asm.sup_b).post(_url_keputusan(asm, baris), {"aksi": "setujui"}, format="json").status_code == (
            status.HTTP_403_FORBIDDEN
        )
        respon = _klien(asm.asm).post(_url_keputusan(asm, baris), {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert Issue.objects.get(pk=baris.issue_id).state.group == "completed"

    @pytest.mark.django_db
    def test_pengajuan_asisten_manager_naik_ke_manager(self, asm):
        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_MANAGER)
        baris = _selesaikan_sendiri(asm, asm.asm)
        assert baris is not None
        respon = _klien(asm.sup).post(_url_keputusan(asm, baris), {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        respon = _klien(asm.manager).post(_url_keputusan(asm, baris), {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_ambang_25_menahan_supervisor_bukan_asisten_manager(self, asm):
        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_ASISTEN_MANAGER)
        assert _selesaikan_sendiri(asm, asm.sup) is not None
        assert _selesaikan_sendiri(asm, asm.asm) is None


@pytest.fixture
def dunia(db):
    d = Dunia()
    # Namanya sengaja sesudah "Sup" menurut abjad: urutannya harus datang dari jenjang.
    d.asm = _orang(d.ws, "wulan")
    JabatanOrganisasi.objects.create(
        workspace=d.ws, member=d.asm, tingkat=TINGKAT_ASISTEN_MANAGER, departemen=d.dept["GDG"]
    )
    return d


@pytest.mark.contract
class TestRingkasan:
    @pytest.mark.django_db
    def test_ringkasan_harian_menyebut_asisten_manager(self, dunia):
        r = dunia.ringkasan(dunia.asm)
        assert r.peran == "Asisten Manager" and r.cakupan == "Dept GDG"
        assert r.judul_tim == "Departemen Anda"

    @pytest.mark.django_db
    def test_laporan_direktur_asisten_manager_dulu(self, dunia):
        Issue.objects.filter(workspace=dunia.ws, created_by__isnull=True).update(created_by=dunia.mgr)
        data = DataWorkspace(dunia.ws.id, HARI_INI, timezone.now() - timedelta(hours=24))
        lap = susun_laporan(data, divisi_diawasi(dunia.dir.id, dunia.ws.id), "24 jam terakhir")
        unit = {u.nama: u for d in lap.divisi for u in d.unit}
        assert unit["Dept GDG"].pimpinan == ["Wulan", "Sup"]


@pytest.mark.contract
class TestAturanGodMode:
    @pytest.mark.django_db
    def test_ambang_penyetuju_menerima_25(self, super_admin):
        request = APIRequestFactory().patch(
            "/api/instances/rules/",
            {"values": {APPROVER_MIN_LEVEL: TINGKAT_ASISTEN_MANAGER}, "confirm": FRASA_KONFIRMASI},
            format="json",
        )
        force_authenticate(request, user=super_admin)
        respon = InstanceRulesEndpoint.as_view()(request)
        assert respon.status_code == status.HTTP_200_OK, respon.data
        assert aturan.get_int(APPROVER_MIN_LEVEL) == TINGKAT_ASISTEN_MANAGER
