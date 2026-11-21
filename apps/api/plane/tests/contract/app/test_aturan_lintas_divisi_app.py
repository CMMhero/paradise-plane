# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode permintaan lintas divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""`CROSS_DIVISION_NOTE_MAX` dan `CROSS_DIVISION_MIN_LEVEL` dijaga API.

Bawaan = perilaku sebelum aturannya ada: catatan sampai 2000 karakter, dan
anggota divisi asal mana pun (jenjang kosong = staf) boleh mengirim.
"""

import pytest
from rest_framework import status

from plane.db.models import JabatanOrganisasi, PermintaanLintasDivisi, WorkspaceMember
from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_cross_division_intake_app import (  # noqa: F401 (fixture)
    _jadikan_departemen,
    _kirim,
    it_project,
    it_user,
    tender_client,
    tender_project,
    tender_user,
)
from plane.utils.aturan.area_keputusan import CROSS_DIVISION_MIN_LEVEL, CROSS_DIVISION_NOTE_MAX


def _atur(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": str(nilai), "category": "PARADISE"})


def _beri_jenjang(workspace, user, project, tingkat):
    _, departemen = _jadikan_departemen(workspace, project, "TND")
    JabatanOrganisasi.objects.create(workspace=workspace, member=user, tingkat=tingkat, departemen=departemen)


@pytest.mark.contract
class TestBatasCatatan:
    @pytest.mark.django_db
    def test_bawaan_2000_karakter(self, tender_client, workspace, tender_project, it_project):
        lewat = _kirim(tender_client, workspace, tender_project, it_project, catatan="x" * 2001)
        assert lewat.status_code == status.HTTP_400_BAD_REQUEST
        assert lewat.json()["error_code"] == "note_too_long"
        assert lewat.json()["params"] == {"max": 2000}

        pas = _kirim(tender_client, workspace, tender_project, it_project, catatan="x" * 2000)
        assert pas.status_code == status.HTTP_201_CREATED, getattr(pas, "data", None)

    @pytest.mark.django_db
    def test_batas_dari_god_mode(self, tender_client, workspace, tender_project, it_project):
        _atur(CROSS_DIVISION_NOTE_MAX, 300)

        lewat = _kirim(tender_client, workspace, tender_project, it_project, catatan="x" * 301)
        assert lewat.status_code == status.HTTP_400_BAD_REQUEST
        assert lewat.json()["params"] == {"max": 300}
        assert PermintaanLintasDivisi.objects.count() == 0

        pas = _kirim(tender_client, workspace, tender_project, it_project, catatan="x" * 300)
        assert pas.status_code == status.HTTP_201_CREATED, getattr(pas, "data", None)

    @pytest.mark.django_db
    def test_batas_dinaikkan(self, tender_client, workspace, tender_project, it_project):
        _atur(CROSS_DIVISION_NOTE_MAX, 5000)
        respon = _kirim(tender_client, workspace, tender_project, it_project, catatan="x" * 4000)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)


@pytest.mark.contract
class TestJenjangPengirim:
    @pytest.mark.django_db
    def test_bawaan_jenjang_kosong_boleh_mengirim(self, tender_client, workspace, tender_project, it_project):
        respon = _kirim(tender_client, workspace, tender_project, it_project)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_jenjang_di_bawah_batas_ditolak(self, tender_client, workspace, tender_project, it_project):
        _atur(CROSS_DIVISION_MIN_LEVEL, 20)

        respon = _kirim(tender_client, workspace, tender_project, it_project)

        assert respon.status_code == status.HTTP_403_FORBIDDEN
        assert respon.json()["error_code"] == "level_too_low"
        assert "Supervisor" in respon.json()["error"]
        assert PermintaanLintasDivisi.objects.count() == 0

    @pytest.mark.django_db
    def test_jenjang_sama_atau_lebih_tinggi_lolos(
        self, tender_client, tender_user, workspace, tender_project, it_project
    ):
        _atur(CROSS_DIVISION_MIN_LEVEL, 20)
        _beri_jenjang(workspace, tender_user, tender_project, 30)

        respon = _kirim(tender_client, workspace, tender_project, it_project)

        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_staf_berjenjang_10_ditolak_saat_batas_leader(
        self, tender_client, tender_user, workspace, tender_project, it_project
    ):
        _atur(CROSS_DIVISION_MIN_LEVEL, 12)
        _beri_jenjang(workspace, tender_user, tender_project, 10)

        respon = _kirim(tender_client, workspace, tender_project, it_project)

        assert respon.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_workspace_selalu_boleh(self, tender_client, tender_user, workspace, tender_project, it_project):
        _atur(CROSS_DIVISION_MIN_LEVEL, 30)
        WorkspaceMember.objects.filter(workspace=workspace, member=tender_user).update(role=20)

        respon = _kirim(tender_client, workspace, tender_project, it_project)

        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
