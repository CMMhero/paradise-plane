# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan email menurut jabatan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keputusan user 2026-10-30: pimpinan tanpa email bawaan, staf dapat yang penting."""

from uuid import uuid4

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.app.views.notification.base import UserNotificationPreferenceEndpoint
from plane.bgtasks.deadline_reminder_task import _penerima
from plane.db.models import (
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    Issue,
    IssueAssignee,
    JabatanOrganisasi,
    Project,
    User,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)
from plane.utils.preferensi_email import (
    BAWAAN_PIMPINAN,
    BAWAAN_STAF,
    SAKLAR_EMAIL,
    SAKLAR_INBOX,
    SAKLAR_RINGKASAN,
    boleh_email,
    saklar_untuk,
)

URL = "/api/users/me/notification-preferences/"


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email=f"owner-{uuid4().hex[:8]}@uji.id", username=f"owner_{uuid4().hex[:8]}")
    return Workspace.objects.create(name="WS", slug=f"ws-email-{uuid4().hex[:6]}", owner=pemilik)


def _orang(workspace, prefix, tingkat=None):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    if tingkat is not None:
        JabatanOrganisasi.objects.create(workspace=workspace, member=user, tingkat=tingkat)
    return user


def _get(user):
    request = APIRequestFactory().get(URL)
    force_authenticate(request, user=user)
    return UserNotificationPreferenceEndpoint.as_view()(request)


def _patch(user, badan):
    request = APIRequestFactory().patch(URL, badan, format="json")
    force_authenticate(request, user=user)
    return UserNotificationPreferenceEndpoint.as_view()(request)


@pytest.mark.contract
class TestBawaanJabatan:
    @pytest.mark.django_db
    def test_staf_dan_jenjang_kosong_dapat_bawaan_staf(self, workspace):
        assert saklar_untuk(_orang(workspace, "staf", TINGKAT_MEMBER).id) == BAWAAN_STAF
        assert saklar_untuk(_orang(workspace, "kosong").id) == BAWAAN_STAF
        assert BAWAAN_STAF["daily_digest"] and BAWAAN_STAF["approval"] and BAWAAN_STAF["issue_completed"]
        # Ringkasan harian menggantikan pengingat per tugas (putaran 2, 2026-10-30).
        assert not BAWAAN_STAF["comment"] and not BAWAAN_STAF["deadline_reminder"]

    @pytest.mark.django_db
    @pytest.mark.parametrize("tingkat", [TINGKAT_SUPERVISOR, TINGKAT_MANAGER])
    def test_pimpinan_hanya_ringkasan_harian(self, workspace, tingkat):
        assert saklar_untuk(_orang(workspace, "pimpinan", tingkat).id) == BAWAAN_PIMPINAN
        # Email pimpinan: ringkasan pagi + sore + obrolan; inbox & bagian ringkasan hidup semua.
        assert [k for k in SAKLAR_EMAIL if BAWAAN_PIMPINAN[k]] == ["daily_digest", "daily_digest_sore", "chat"]
        assert all(BAWAAN_PIMPINAN[k] for k in SAKLAR_INBOX + SAKLAR_RINGKASAN)

    @pytest.mark.django_db
    def test_naik_jabatan_langsung_ikut_tanpa_menyentuh_preferensi(self, workspace):
        orang = _orang(workspace, "naik", TINGKAT_MEMBER)
        assert boleh_email(orang.id, "approval") is True
        JabatanOrganisasi.objects.filter(member=orang).update(tingkat=TINGKAT_SUPERVISOR)
        assert boleh_email(orang.id, "approval") is False


@pytest.mark.contract
class TestEndpointProfil:
    @pytest.mark.django_db
    def test_get_mengembalikan_saklar_yang_berlaku(self, workspace):
        res = _get(_orang(workspace, "staf", TINGKAT_MEMBER))
        assert res.status_code == 200
        assert res.data["ikut_bawaan_jabatan"] is True
        assert res.data["daily_digest"] is True and res.data["deadline_reminder"] is False
        assert res.data["mention"] is False

    @pytest.mark.django_db
    def test_ubah_satu_saklar_membekukan_sisanya(self, workspace):
        orang = _orang(workspace, "ubah", TINGKAT_MEMBER)
        res = _patch(orang, {"comment": True})
        assert res.status_code == 200
        pref = UserNotificationPreference.objects.get(user=orang, workspace=None, project=None)
        assert pref.ikut_bawaan_jabatan is False
        assert pref.comment is True and pref.approval is True and pref.daily_digest is True
        assert pref.deadline_reminder is False

        # Sesudah dibekukan, naik jabatan TIDAK mengubah pilihan orangnya.
        JabatanOrganisasi.objects.filter(member=orang).update(tingkat=TINGKAT_SUPERVISOR)
        assert boleh_email(orang.id, "approval") is True

    @pytest.mark.django_db
    def test_kembali_ke_bawaan(self, workspace):
        orang = _orang(workspace, "reset", TINGKAT_SUPERVISOR)
        _patch(orang, {"approval": True})
        assert boleh_email(orang.id, "approval") is True
        res = _patch(orang, {"ikut_bawaan_jabatan": True})
        assert res.data["ikut_bawaan_jabatan"] is True
        assert boleh_email(orang.id, "approval") is False

    @pytest.mark.django_db
    def test_nilai_bukan_boolean_ditolak(self, workspace):
        orang = _orang(workspace, "salah")
        assert _patch(orang, {"comment": "ya"}).status_code == 400
        assert UserNotificationPreference.objects.get(user=orang).ikut_bawaan_jabatan is True


@pytest.mark.contract
class TestPengingatTenggat:
    @pytest.mark.django_db
    def test_staf_yang_menyalakan_diingatkan_pemberi_tugas_pimpinan_tidak(self, workspace):
        # Saklar induk God Mode menyala: kalau mati, menyalakan saklar pribadinya
        # diabaikan (locked_by_admin, KEP-83).
        from plane.license.models import InstanceConfiguration

        InstanceConfiguration.objects.update_or_create(
            key="ENABLE_DEADLINE_REMINDER", defaults={"value": "1", "category": "PARADISE"}
        )
        staf = _orang(workspace, "dikerjai", TINGKAT_MEMBER)
        _patch(staf, {"deadline_reminder": True})
        atasan = _orang(workspace, "pemberi", TINGKAT_SUPERVISOR)
        project = Project.objects.create(name="P", identifier=f"P{uuid4().hex[:4].upper()}", workspace=workspace)
        issue = Issue.objects.create(workspace=workspace, project=project, name="T")
        # Lewat update(): BaseModel.save() menolkan created_by di luar request.
        Issue.objects.filter(pk=issue.pk).update(created_by=atasan)
        issue.refresh_from_db()
        assert issue.created_by_id == atasan.id
        IssueAssignee.objects.create(issue=issue, assignee=staf, project=project, workspace=workspace)

        assert _penerima(issue) == {staf}

    @pytest.mark.django_db
    def test_bawaan_staf_tidak_diingatkan_per_tugas(self, workspace):
        staf = _orang(workspace, "matikan", TINGKAT_MEMBER)
        project = Project.objects.create(name="P", identifier=f"Q{uuid4().hex[:4].upper()}", workspace=workspace)
        issue = Issue.objects.create(workspace=workspace, project=project, name="T")
        # Lewat update(): BaseModel.save() menolkan created_by di luar request.
        Issue.objects.filter(pk=issue.pk).update(created_by=staf)
        issue.refresh_from_db()
        IssueAssignee.objects.create(issue=issue, assignee=staf, project=project, workspace=workspace)

        assert _penerima(issue) == set()
