# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: KPI dan Pengumuman menyala untuk semua orang
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""KPI (`kinerja`) dan Pengumuman (`pengumuman`) menyala bawaan.

Yang dijaga:
- modulnya (Dashboards untuk KPI, Chat untuk Pengumuman) menyala tanpa baris God Mode;
- akun baru mendapat keduanya tersemat;
- akun lama yang belum punya baris Pengumuman mendapatkannya tersemat saat
  sidebar dimuat, tanpa menyentuh pilihan yang sudah ia buat;
- bawaan God Mode yang tersimpan sebelum Pengumuman ada tetap memberinya tersemat;
- menyematkan atau melepas Pengumuman di "Customize navigation" tersimpan.
"""

import json
from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.app.views.workspace.user_preference import WorkspaceUserPreferenceViewSet
from plane.db.models import User, Workspace, WorkspaceMember, WorkspaceUserPreference
from plane.license.models import InstanceConfiguration
from plane.utils import bawaan_member
from plane.utils import saklar_instance as si


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}")


@pytest.fixture
def ruang(db):
    pemilik = _buat_user("pemilik")
    ws = Workspace.objects.create(name="Uji", owner=pemilik, slug=f"uji-{uuid4().hex[:6]}")
    staf = _buat_user("staf")
    WorkspaceMember.objects.create(workspace=ws, member=staf, role=15)
    return ws, staf


def _sidebar(ws, user):
    request = APIRequestFactory().get(f"/api/workspaces/{ws.slug}/sidebar-preferences/")
    force_authenticate(request, user=user)
    response = WorkspaceUserPreferenceViewSet.as_view()(request, slug=ws.slug)
    assert response.status_code == status.HTTP_200_OK
    return response.data


def _semat(ws, user, kunci, nilai):
    request = APIRequestFactory().patch(
        f"/api/workspaces/{ws.slug}/sidebar-preferences/", [{"key": kunci, "is_pinned": nilai}], format="json"
    )
    force_authenticate(request, user=user)
    return WorkspaceUserPreferenceViewSet.as_view()(request, slug=ws.slug)


@pytest.mark.contract
class TestKpiDanPengumumanBawaan:
    @pytest.mark.django_db
    def test_modulnya_menyala_tanpa_baris_god_mode(self, monkeypatch):
        for kunci in (si.MODUL_APLIKASI["dashboards"], si.MODUL_APLIKASI["chat"]):
            monkeypatch.delenv(kunci, raising=False)
        aktif = si.modul_aktif()
        assert aktif["dashboards"] is True
        assert aktif["chat"] is True

    @pytest.mark.django_db
    def test_akun_baru_tersemat(self, ruang):
        ws, staf = ruang
        data = _sidebar(ws, staf)
        assert data["kinerja"]["is_pinned"] is True
        assert data["pengumuman"]["is_pinned"] is True

    @pytest.mark.django_db
    def test_akun_lama_mendapat_pengumuman_tanpa_mengubah_pilihannya(self, ruang):
        ws, staf = ruang
        lama = [k for k in bawaan_member.NAV_KUNCI if k != "pengumuman"]
        WorkspaceUserPreference.objects.bulk_create(
            [
                WorkspaceUserPreference(
                    workspace=ws, user=staf, key=k, is_pinned=k != "kinerja", sort_order=1000 * (i + 1)
                )
                for i, k in enumerate(lama)
            ]
        )
        data = _sidebar(ws, staf)
        assert data["pengumuman"]["is_pinned"] is True
        # KPI yang sengaja dilepas orangnya tidak disematkan ulang. Menunya tetap
        # tampil di web (menu Paradise selalu tampil), pin hanya mengatur urutan.
        assert data["kinerja"]["is_pinned"] is False

    @pytest.mark.django_db
    def test_bawaan_god_mode_lama_tetap_menyematkan_pengumuman(self, ruang):
        ws, staf = ruang
        InstanceConfiguration.objects.create(
            key=bawaan_member.KUNCI,
            value=json.dumps({"navigasi": {"pinned": {"chat": False}}}),
            category="PARADISE",
        )
        data = _sidebar(ws, staf)
        assert data["chat"]["is_pinned"] is False
        assert data["pengumuman"]["is_pinned"] is True

    @pytest.mark.django_db
    def test_melepas_pengumuman_tersimpan(self, ruang):
        ws, staf = ruang
        _sidebar(ws, staf)
        assert _semat(ws, staf, "pengumuman", False).status_code == status.HTTP_200_OK
        assert _sidebar(ws, staf)["pengumuman"]["is_pinned"] is False
