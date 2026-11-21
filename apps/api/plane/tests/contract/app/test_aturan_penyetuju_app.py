# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode APPROVER_MIN_LEVEL
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Jenjang terendah yang boleh menyetujui (`APPROVER_MIN_LEVEL`) dijaga API.

Bawaan 20 = perilaku sebelum aturannya ada: supervisor departemen menyetujui
pekerjaan stafnya. Diubah ke 30 di God Mode: supervisor hilang dari calon
penyetuju dan POST keputusannya ditolak 403, manager divisi tetap bisa.

    SALES -> SMT1 (P1): sup1 (20), staf (10); manager (30) di divisi Sales.
"""

import pytest
from rest_framework import status

from plane.db.models import TINGKAT_SUPERVISOR, JabatanOrganisasi
from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_persetujuan_manager_app import (  # noqa: F401 (fixture org)
    URL_PERSETUJUAN,
    _ajukan,
    _klien,
    _user,
    org,
)
from plane.utils.aturan.area_tugas import APPROVER_MIN_LEVEL
from plane.utils.hierarki import FLAG_GERBANG, calon_penyetuju


@pytest.fixture
def kantor(org):
    org.sup1 = _user("sup1", org.ws)
    JabatanOrganisasi.objects.create(workspace=org.ws, member=org.sup1, tingkat=TINGKAT_SUPERVISOR, departemen=org.smt1)
    return org


def _putuskan(org, aktor, baris):
    return _klien(aktor).post(
        URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id) + f"{baris.id}/",
        {"aksi": "setujui"},
        format="json",
    )


def _ambang(nilai):
    InstanceConfiguration.objects.update_or_create(
        key=APPROVER_MIN_LEVEL, defaults={"value": str(nilai), "category": "PARADISE"}
    )


@pytest.mark.contract
class TestJenjangPenyetuju:
    @pytest.mark.django_db
    def test_bawaan_supervisor_departemen_menyetujui(self, kantor, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert str(kantor.sup1.id) in {str(u) for u in calon_penyetuju(kantor.ws.id, kantor.p1.id)}
        _, baris = _ajukan(kantor)
        respon = _putuskan(kantor, kantor.sup1, baris)
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert respon.json()["status"] == "disetujui"

    @pytest.mark.django_db
    def test_ambang_manager_menolak_supervisor(self, kantor, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, baris = _ajukan(kantor)
        _ambang(30)

        calon = {str(u) for u in calon_penyetuju(kantor.ws.id, kantor.p1.id)}
        assert str(kantor.sup1.id) not in calon
        assert str(kantor.manager.id) in calon

        assert _putuskan(kantor, kantor.sup1, baris).status_code == status.HTTP_403_FORBIDDEN
        respon = _putuskan(kantor, kantor.manager, baris)
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    @pytest.mark.django_db
    def test_kembali_ke_20_supervisor_bisa_lagi(self, kantor, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _ambang(30)
        _ambang(20)
        _, baris = _ajukan(kantor)
        assert _putuskan(kantor, kantor.sup1, baris).status_code == status.HTTP_200_OK
