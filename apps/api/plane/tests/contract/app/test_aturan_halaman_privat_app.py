# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan God Mode halaman privat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""PRIVATE_PAGE_OVERSEERS dijaga API: halaman project dan pohon Wiki sepakat.

Dunia sama dengan test_wiki_pengelola_app.py (Sales: T1, T2; HRGA). Halaman
privat "Rahasia tim" milik staf T1 di project T1. Bawaan (KEP-95): manager
Sales dan direktur ikut melihat. Disempitkan di God Mode: manager lalu direktur
kehilangan aksesnya, admin Wiki dan pemilik tidak pernah.
"""

import pytest
from rest_framework import status

from plane.license.models import InstanceConfiguration
from plane.tests.contract.app.test_wiki_pengelola_app import (  # noqa: F401 (fixture)
    _daftar,
    _klien,
    _nama,
    _url_project,
    hal,
    proj,
    s3_palsu,
    w,
)
from plane.utils.aturan.area_visibilitas import PRIVATE_PAGE_OVERSEERS

RAHASIA = "Rahasia tim"


def _setel(nilai):
    InstanceConfiguration.objects.update_or_create(
        key=PRIVATE_PAGE_OVERSEERS, defaults={"value": nilai, "category": "PARADISE"}
    )


def _melihat(user, w, proj):
    """(di daftar project, detail project 200, di folder Wiki departemen)."""
    detail = _klien(user).get(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/")).status_code
    pohon = _nama(_klien(user).get(proj.url))
    return RAHASIA in _daftar(user, w, proj.p_t1), detail == status.HTTP_200_OK, RAHASIA in pohon


@pytest.mark.contract
@pytest.mark.django_db
class TestPengawasHalamanPrivat:
    def test_bawaan_manager_divisi_dan_direktur(self, w, proj):
        assert _melihat(w.mgr_sales, w, proj) == (True, True, True)
        assert _melihat(w.direktur, w, proj) == (True, True, True)
        assert _melihat(w.mgr_hrga, w, proj) == (False, False, False)

    def test_tanpa_manager_divisi(self, w, proj):
        _setel("org_wide")
        assert _melihat(w.mgr_sales, w, proj) == (False, False, False)
        assert _melihat(w.direktur, w, proj) == (True, True, True)

    def test_admin_wiki_saja(self, w, proj):
        _setel("wiki_admins")
        assert _melihat(w.mgr_sales, w, proj) == (False, False, False)
        assert _melihat(w.direktur, w, proj) == (False, False, False)
        assert RAHASIA in _nama(_klien(w.admin).get(proj.url))
        # Pemilik dan anggota departemennya di pohon Wiki tidak terpengaruh.
        assert RAHASIA in _daftar(w.staf_t1, w, proj.p_t1)
        assert RAHASIA in _nama(_klien(w.spv_t1).get(proj.url))
