# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode tugas privat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""PRIVATE_VISIBLE_TO_WORKSPACE_ADMINS dan PRIVATE_VISIBLE_TO_CREATOR_SUPERIOR dijaga API.

Bawaan keduanya mati = P29 #8 apa adanya (test_tugas_privat_app.py): admin
workspace tidak melihat, atasan pembuat tidak melihat. Dinyalakan di God Mode:
daftar, detail, dan penerima notifikasi ikut terbuka bagi mereka saja.

Bentuk dunia sama dengan test_tugas_privat_app.py. Tugas tambahan `ke_atas`:
dibuat staf `pembuat`, ditugaskan ke `manager`. Supervisor SMT1 bukan atasan
manager, jadi ia hanya bisa melihatnya sebagai atasan pembuat.
"""

import pytest
from rest_framework import status

from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_persetujuan_manager_app import _klien
from plane.tests.contract.app.test_tugas_privat_app import (  # noqa: F401 (fixture o)
    URL_DETAIL,
    URL_ISSUES,
    _ada,
    _tugas,
    o,
)
from plane.utils.akses_privat import penonton_tugas_ids
from plane.utils.aturan.area_visibilitas import (
    PRIVATE_VISIBLE_TO_CREATOR_SUPERIOR,
    PRIVATE_VISIBLE_TO_WORKSPACE_ADMINS,
)


def _nyalakan(kunci):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": "1", "category": "PARADISE"})


def _lihat(o, peran, issue):
    """(terlihat di daftar, status detail) untuk satu peran."""
    klien = _klien(o.user[peran])
    daftar = _ada(klien.get(URL_ISSUES.format(slug=o.ws.slug, project_id=o.p1.id)), issue)
    detail = klien.get(URL_DETAIL.format(slug=o.ws.slug, project_id=o.p1.id, issue_id=issue.id)).status_code
    return daftar, detail


@pytest.mark.contract
class TestAdminWorkspace:
    def test_bawaan_admin_workspace_tidak_melihat(self, o):
        assert _lihat(o, "admin_ws", o.tugas) == (False, status.HTTP_404_NOT_FOUND)
        assert str(o.user["admin_ws"].id) not in {str(u) for u in penonton_tugas_ids(o.tugas, [o.user["admin_ws"].id])}

    def test_dinyalakan_admin_workspace_melihat_dan_dikabari(self, o):
        _nyalakan(PRIVATE_VISIBLE_TO_WORKSPACE_ADMINS)
        assert _lihat(o, "admin_ws", o.tugas) == (True, status.HTTP_200_OK)
        assert penonton_tugas_ids(o.tugas, [o.user["admin_ws"].id]) == [o.user["admin_ws"].id]
        # Yang bukan admin tetap tidak.
        for peran in ("rekan", "luar"):
            assert _lihat(o, peran, o.tugas) == (False, status.HTTP_404_NOT_FOUND), peran


@pytest.mark.contract
class TestAtasanPembuat:
    @pytest.fixture
    def ke_atas(self, o):
        return _tugas(o, "Privat ke atas", o.user["pembuat"], [o.user["manager"]], privat=True)

    def test_bawaan_atasan_pembuat_tidak_melihat(self, o, ke_atas):
        assert _lihat(o, "sup", ke_atas) == (False, status.HTTP_404_NOT_FOUND)
        assert penonton_tugas_ids(ke_atas, [o.user["sup"].id]) == []

    def test_dinyalakan_atasan_pembuat_melihat_dan_dikabari(self, o, ke_atas):
        _nyalakan(PRIVATE_VISIBLE_TO_CREATOR_SUPERIOR)
        assert _lihat(o, "sup", ke_atas) == (True, status.HTTP_200_OK)
        assert penonton_tugas_ids(ke_atas, [o.user["sup"].id]) == [o.user["sup"].id]
        # Rekan setingkat pembuat bukan atasannya; admin workspace tetap tertutup.
        for peran in ("rekan", "admin_ws"):
            assert _lihat(o, peran, ke_atas) == (False, status.HTTP_404_NOT_FOUND), peran
