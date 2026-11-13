# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan navigasi, tata letak, dan project di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bawaan navigasi sidebar, tata letak work item, dan project baru dari God Mode.

Yang dijaga:
- pabrik tata letak = Board (kanban, dikelompokkan per state);
- bawaan hanya mengenai baris BARU; akun lama disamakan lewat tombol "apply";
- preferensi satu member bisa dibaca dan diubah Super Admin;
- project baru mengikuti bawaan visibilitas dsb. kecuali pemanggil memilih lain;
- masukan tak sah ditolak tanpa menulis apa pun.
"""

import json
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import (
    Profile,
    Project,
    ProjectUserProperty,
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceUserPreference,
    WorkspaceUserProperties,
)
from plane.license.api.views.bawaan_member import (
    InstanceMemberDefaultsApplyEndpoint,
    InstanceMemberDefaultsEndpoint,
    InstanceProjectDefaultsEndpoint,
)
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.api.views.member import InstanceMemberPreferenceEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils import bawaan_member, bawaan_project
from plane.utils.bawaan_project import lengkapi_data_project


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-nav-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _buat_user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


@pytest.fixture
def ruang(db, super_admin):
    """Workspace + satu member + satu project tempat member itu bergabung."""
    ws = Workspace.objects.create(name="Uji", owner=super_admin, slug=f"uji-{uuid4().hex[:6]}")
    staf = _buat_user("staf")
    WorkspaceMember.objects.create(workspace=ws, member=staf, role=15)
    project = Project.objects.create(name="Proyek", identifier=f"P{uuid4().hex[:4].upper()}", workspace=ws)
    return ws, staf, project


def _panggil(view, metode, aktor, badan=None, url="/api/instances/", **kw):
    request = getattr(APIRequestFactory(), metode)(url, badan, format="json")
    if aktor is not None:
        force_authenticate(request, user=aktor)
    return view.as_view()(request, **kw)


@pytest.mark.contract
class TestBawaanTataLetak:
    @pytest.mark.django_db
    def test_pabrik_board_dikelompokkan_per_state(self, ruang):
        ws, staf, project = ruang
        prop = ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        assert prop.display_filters["layout"] == "kanban"
        assert prop.display_filters["group_by"] == "state"

    @pytest.mark.django_db
    def test_bawaan_god_mode_dipakai_baris_baru(self, super_admin, ruang):
        ws, staf, project = ruang
        response = _panggil(InstanceMemberDefaultsEndpoint, "patch", super_admin, {"work_items": {"layout": "list"}})
        assert response.status_code == status.HTTP_200_OK
        prop = ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        assert prop.display_filters["layout"] == "list"
        assert prop.display_filters["group_by"] is None

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "badan",
        [
            {"work_items": {"layout": "gantt_chart"}},
            {"work_items": {"layout": "kanban", "lain": 1}},
            {"navigasi": {"pinned": {"bukan_menu": True}}},
            {"navigasi": {"pinned": {"chat": "ya"}}},
            {"navigasi": {"project_mode": "SIDEWAYS"}},
            {"navigasi": {"project_limit": 51}},
            {"navigasi": {"project_limit": True}},
        ],
    )
    def test_masukan_tak_sah_ditolak(self, super_admin, badan):
        response = _panggil(InstanceMemberDefaultsEndpoint, "patch", super_admin, badan)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not InstanceConfiguration.objects.filter(key=bawaan_member.KUNCI).exists()


@pytest.mark.contract
class TestBawaanNavigasi:
    @pytest.mark.django_db
    def test_pabrik_bertab_tanpa_batas_semua_tersemat(self, ruang):
        """Tanpa setelan God Mode: project bertab, semua project tampil, semua menu tersemat."""
        ws, staf, _ = ruang
        properti = WorkspaceUserProperties.objects.create(user=staf, workspace=ws)
        assert (properti.navigation_control_preference, properti.navigation_project_limit) == ("TABBED", 0)

        from plane.app.views.workspace.user_preference import WorkspaceUserPreferenceViewSet

        request = APIRequestFactory().get("/")
        force_authenticate(request, user=staf)
        response = WorkspaceUserPreferenceViewSet.as_view()(request, slug=ws.slug)
        assert all(response.data[kunci]["is_pinned"] for kunci in bawaan_member.NAV_KUNCI)

    @pytest.mark.django_db
    def test_batas_project_bisa_dimatikan(self, ruang):
        """Regresi: mencentang lalu mematikan "Show limited projects" harus tersimpan sebagai 0."""
        from plane.app.views.workspace.user import WorkspaceUserPropertiesEndpoint

        ws, staf, _ = ruang
        url = f"/api/workspaces/{ws.slug}/user-properties/"
        for nilai in (10, 0):
            request = APIRequestFactory().patch(url, {"navigation_project_limit": nilai}, format="json")
            force_authenticate(request, user=staf)
            response = WorkspaceUserPropertiesEndpoint.as_view()(request, slug=ws.slug)
            assert response.status_code == status.HTTP_200_OK
            assert response.data["navigation_project_limit"] == nilai
        assert WorkspaceUserProperties.objects.get(user=staf, workspace=ws).navigation_project_limit == 0

    @pytest.mark.django_db
    def test_baris_semat_baru_ikut_god_mode(self, super_admin, ruang):
        ws, staf, _ = ruang
        _panggil(
            InstanceMemberDefaultsEndpoint,
            "patch",
            super_admin,
            {"navigasi": {"pinned": {"chat": True, "drafts": False}, "project_mode": "TABBED", "project_limit": 0}},
        )
        from plane.app.views.workspace.user_preference import WorkspaceUserPreferenceViewSet

        request = APIRequestFactory().get(f"/api/workspaces/{ws.slug}/sidebar-preferences/")
        force_authenticate(request, user=staf)
        response = WorkspaceUserPreferenceViewSet.as_view()(request, slug=ws.slug)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["chat"]["is_pinned"] is True
        assert response.data["drafts"]["is_pinned"] is False
        assert response.data["your_work"]["is_pinned"] is True

        properti = WorkspaceUserProperties.objects.create(user=staf, workspace=ws)
        assert properti.navigation_control_preference == "TABBED"
        assert properti.navigation_project_limit == 0

    @pytest.mark.django_db
    def test_kunci_baru_untuk_akun_lama_di_ujung_urutan(self, ruang):
        ws, staf, _ = ruang
        WorkspaceUserPreference.objects.create(workspace=ws, user=staf, key="drafts", is_pinned=True, sort_order=500000)
        from plane.app.views.workspace.user_preference import WorkspaceUserPreferenceViewSet

        request = APIRequestFactory().get("/")
        force_authenticate(request, user=staf)
        response = WorkspaceUserPreferenceViewSet.as_view()(request, slug=ws.slug)
        assert response.data["wiki"]["sort_order"] > 500000

    @pytest.mark.django_db
    def test_apply_menyamakan_akun_lama(self, super_admin, ruang):
        ws, staf, project = ruang
        WorkspaceUserPreference.objects.create(workspace=ws, user=staf, key="wiki", is_pinned=False)
        WorkspaceUserProperties.objects.create(
            user=staf, workspace=ws, navigation_control_preference="TABBED", navigation_project_limit=3
        )
        prop = ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        prop.display_filters = {**prop.display_filters, "layout": "list", "group_by": None}
        prop.save()
        _panggil(InstanceMemberDefaultsEndpoint, "patch", super_admin, {"navigasi": {"pinned": {"wiki": True}}})

        response = _panggil(
            InstanceMemberDefaultsApplyEndpoint, "post", super_admin, {"sections": ["navigasi", "work_items"]}
        )
        assert response.status_code == status.HTTP_200_OK
        assert WorkspaceUserPreference.objects.get(user=staf, key="wiki").is_pinned is True
        properti = WorkspaceUserProperties.objects.get(user=staf, workspace=ws)
        assert (properti.navigation_control_preference, properti.navigation_project_limit) == ("TABBED", 0)
        prop.refresh_from_db()
        assert prop.display_filters["layout"] == "kanban"
        assert prop.display_filters["group_by"] == "state"

    @pytest.mark.django_db
    @pytest.mark.parametrize("badan", [{}, {"sections": []}, {"sections": ["profile"]}, {"sections": "navigasi"}])
    def test_apply_menolak_bagian_lain(self, super_admin, badan):
        response = _panggil(InstanceMemberDefaultsApplyEndpoint, "post", super_admin, badan)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_apply_hanya_super_admin(self, ruang):
        _, staf, _ = ruang
        response = _panggil(InstanceMemberDefaultsApplyEndpoint, "post", staf, {"sections": ["work_items"]})
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


@pytest.mark.contract
class TestPreferensiTampilanMember:
    @pytest.mark.django_db
    def test_baca_dan_ubah_satu_member(self, super_admin, ruang):
        ws, staf, project = ruang
        ProjectUserProperty.objects.create(user=staf, project=project, workspace=ws)
        url = f"/api/instances/members/{staf.id}/preferences/"

        response = _panggil(InstanceMemberPreferenceEndpoint, "get", super_admin, url=url, pk=staf.id)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["work_items"]["layout"] == "kanban"
        assert response.data["navigasi"]["pinned"]["your_work"] is True

        response = _panggil(
            InstanceMemberPreferenceEndpoint,
            "patch",
            super_admin,
            {"navigasi": {"pinned": {"wiki": True}, "project_mode": "TABBED"}, "work_items": {"layout": "calendar"}},
            url=url,
            pk=staf.id,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["navigasi"]["pinned"]["wiki"] is True
        assert response.data["navigasi"]["project_mode"] == "TABBED"
        assert response.data["work_items"]["layout"] == "calendar"
        assert WorkspaceUserPreference.objects.get(user=staf, workspace=ws, key="wiki").is_pinned is True
        assert ProjectUserProperty.objects.get(user=staf, project=project).display_filters["layout"] == "calendar"

    @pytest.mark.django_db
    def test_masukan_tak_sah_tidak_menulis_apa_pun(self, super_admin, ruang):
        ws, staf, _ = ruang
        url = f"/api/instances/members/{staf.id}/preferences/"
        response = _panggil(
            InstanceMemberPreferenceEndpoint,
            "patch",
            super_admin,
            {"profile": {"language": "id"}, "work_items": {"layout": "papan"}},
            url=url,
            pk=staf.id,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not Profile.objects.filter(user=staf, language="id").exists()


@pytest.mark.contract
class TestBawaanProject:
    @pytest.mark.django_db
    def test_pabrik_dan_simpan(self, super_admin):
        response = _panggil(InstanceProjectDefaultsEndpoint, "get", super_admin)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["network"] == 0
        assert response.data["pabrik"] == bawaan_project.PABRIK

        response = _panggil(
            InstanceProjectDefaultsEndpoint, "patch", super_admin, {"network": 0, "timezone": "Asia/Jakarta"}
        )
        assert response.status_code == status.HTTP_200_OK
        tersimpan = json.loads(InstanceConfiguration.objects.get(key=bawaan_project.KUNCI).value)
        assert tersimpan["network"] == 0
        assert tersimpan["timezone"] == "Asia/Jakarta"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "badan",
        [
            {"network": 1},
            {"network": True},
            {"timezone": "Mars/Base"},
            {"archive_in": 13},
            {"close_in": -1},
            {"guest_view_all_features": "ya"},
            {"warna": "merah"},
            {},
        ],
    )
    def test_masukan_tak_sah_ditolak(self, super_admin, badan):
        response = _panggil(InstanceProjectDefaultsEndpoint, "patch", super_admin, badan)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not InstanceConfiguration.objects.filter(key=bawaan_project.KUNCI).exists()

    @pytest.mark.django_db
    def test_lengkapi_hanya_kolom_yang_tak_dikirim(self, super_admin):
        _panggil(InstanceProjectDefaultsEndpoint, "patch", super_admin, {"network": 0, "archive_in": 3})
        data = lengkapi_data_project({"name": "X", "network": 2})
        assert data["network"] == 2
        assert data["archive_in"] == 3

    @pytest.mark.django_db
    def test_kunci_ditolak_di_patch_umum(self, super_admin):
        response = _panggil(
            InstanceConfigurationEndpoint, "patch", super_admin, {bawaan_project.KUNCI: json.dumps({"network": 1})}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
