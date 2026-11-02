# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: notifikasi granular (inbox + email + bagian ringkasan)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keputusan user 2026-11-02: tiap jenis kabar punya saklar inbox DAN email, dan
ringkasan harian bisa dipilih per bagian. Satu daftar kunci (`SAKLAR_NOTIFIKASI`)
dipakai profil, God Mode per member, dan tabel bawaan jabatan.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.app.views.notification.base import UserNotificationPreferenceEndpoint
from plane.bgtasks.daily_digest_task import TugasWorkspace, penerima_dan_saklar, susun_ringkasan
from plane.bgtasks.deadline_reminder_task import FIELD_TENGGAT, tulis_inbox_tenggat
from plane.db.models import (
    Issue,
    IssueAssignee,
    Notification,
    PesanLangsung,
    Project,
    State,
    User,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)
from plane.utils.bawaan_member import periksa_perubahan
from plane.utils.chat_ruang import ruang_dm
from plane.utils.inbox_chat import ENTITY_CHAT, catat_pesan_dm, tandai_chat_terbaca
from plane.utils.preferensi_email import SAKLAR_NOTIFIKASI, boleh, penyaring

URL = "/api/users/me/notification-preferences/"
HARI_INI = timezone.localtime(timezone.now()).date()


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email=f"owner-{uuid4().hex[:8]}@uji.id", username=f"owner_{uuid4().hex[:8]}")
    return Workspace.objects.create(name="WS", slug=f"ws-gran-{uuid4().hex[:6]}", owner=pemilik)


def _orang(workspace, prefix):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}", display_name=prefix)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _patch(user, badan):
    request = APIRequestFactory().patch(URL, badan, format="json")
    force_authenticate(request, user=user)
    return UserNotificationPreferenceEndpoint.as_view()(request)


def _tugas(workspace, selisih, assignee):
    kode = uuid4().hex[:4].upper()
    project = Project.objects.create(name=f"P {kode}", identifier=kode, workspace=workspace)
    state = State.objects.create(project=project, workspace=workspace, name="Todo", group="unstarted")
    issue = Issue.objects.create(
        workspace=workspace,
        project=project,
        name=f"Tugas {selisih}",
        state=state,
        target_date=HARI_INI + timedelta(days=selisih),
    )
    IssueAssignee.objects.create(issue=issue, assignee=assignee, project=project, workspace=workspace)
    return issue


@pytest.mark.contract
class TestEndpoint:
    @pytest.mark.django_db
    def test_get_memuat_semua_saklar(self, workspace):
        res = _patch(_orang(workspace, "a"), {})
        assert res.status_code == 200
        assert set(SAKLAR_NOTIFIKASI) <= set(res.data)
        assert res.data["inbox_chat"] is True and res.data["digest_tim"] is True

    @pytest.mark.django_db
    def test_saklar_inbox_dan_bagian_bisa_diubah(self, workspace):
        orang = _orang(workspace, "b")
        res = _patch(orang, {"inbox_comment": False, "digest_depan": False})
        assert res.status_code == 200
        assert res.data["inbox_comment"] is False and res.data["digest_depan"] is False
        assert boleh(orang.id, "inbox_comment") is False
        assert boleh(orang.id, "inbox_mention") is True

    @pytest.mark.django_db
    def test_penyaring_satu_kueri_untuk_banyak_orang(self, workspace):
        a, b = _orang(workspace, "c"), _orang(workspace, "d")
        _patch(b, {"chat": False})
        assert penyaring([a.id, b.id], "chat") == {a.id}

    @pytest.mark.django_db
    def test_bawaan_god_mode_menerima_saklar_baru(self):
        bawaan, galat = periksa_perubahan({"email": {"staf": {"inbox_deadline": False, "digest_tim": False}}})
        assert galat is None
        assert bawaan["email"]["staf"]["inbox_deadline"] is False
        _, galat = periksa_perubahan({"email": {"staf": {"tidak_ada": True}}})
        assert galat


@pytest.mark.contract
class TestInboxObrolan:
    def _pesan(self, workspace, dari, ke, isi="halo"):
        ruang = ruang_dm(workspace.id, dari.id, ke.id)
        pesan = PesanLangsung.objects.create(workspace=workspace, ruang=ruang, pengirim=dari, penerima=ke, isi=isi)
        catat_pesan_dm(pesan)
        return ruang

    @pytest.mark.django_db
    def test_satu_baris_per_percakapan(self, workspace):
        dari, ke = _orang(workspace, "dari"), _orang(workspace, "ke")
        self._pesan(workspace, dari, ke, "satu")
        ruang = self._pesan(workspace, dari, ke, "dua")
        baris = Notification.objects.filter(receiver=ke, entity_name=ENTITY_CHAT)
        assert baris.count() == 1
        assert baris.first().data["chat"]["jumlah"] == 2
        assert baris.first().data["issue_activity"]["new_value"] == "dua"

        tandai_chat_terbaca(ke.id, ruang.id)
        assert baris.first().read_at is not None
        # Pesan sesudah dibaca = baris baru.
        self._pesan(workspace, dari, ke, "tiga")
        assert baris.count() == 2

    @pytest.mark.django_db
    def test_saklar_mati_tidak_menulis(self, workspace):
        dari, ke = _orang(workspace, "dari"), _orang(workspace, "ke")
        _patch(ke, {"inbox_chat": False})
        self._pesan(workspace, dari, ke)
        assert not Notification.objects.filter(receiver=ke, entity_name=ENTITY_CHAT).exists()


@pytest.mark.contract
class TestInboxTenggat:
    @pytest.mark.django_db
    def test_terlambat_masuk_inbox_sekali(self, workspace):
        orang = _orang(workspace, "telat")
        issue = _tugas(workspace, -1, orang)
        assert tulis_inbox_tenggat(HARI_INI) >= 1
        baris = Notification.objects.filter(receiver=orang, entity_identifier=issue.id)
        assert baris.count() == 1
        assert baris.first().data["issue_activity"]["field"] == FIELD_TENGGAT
        assert baris.first().data["issue_activity"]["verb"] == "overdue"
        # Dijalankan ulang pada hari yang sama: tidak ada duplikat.
        tulis_inbox_tenggat(HARI_INI)
        assert baris.count() == 1

    @pytest.mark.django_db
    def test_saklar_mati_dan_titik_lain_dilewati(self, workspace):
        mati = _orang(workspace, "mati")
        _patch(mati, {"inbox_deadline": False})
        _tugas(workspace, 0, mati)
        lain = _orang(workspace, "lain")
        _tugas(workspace, 4, lain)  # H-4 bukan titik inbox
        tulis_inbox_tenggat(HARI_INI)
        assert not Notification.objects.filter(receiver__in=[mati, lain]).exists()


@pytest.mark.contract
class TestBagianRingkasan:
    @pytest.mark.django_db
    def test_hanya_bagian_yang_dipilih(self, workspace):
        orang = _orang(workspace, "ringkas")
        _tugas(workspace, -2, orang)
        _tugas(workspace, 0, orang)
        _tugas(workspace, 3, orang)
        _patch(orang, {"digest_hari_ini": False, "digest_depan": False})

        (_, saklar), *_ = [p for p in penerima_dan_saklar(workspace.id) if p[0].id == orang.id]
        r = susun_ringkasan(orang, workspace.id, TugasWorkspace(workspace.id, HARI_INI), HARI_INI, saklar)
        assert len(r.sendiri.lewat) == 1 and not r.sendiri.hari and not r.sendiri.depan

    @pytest.mark.django_db
    def test_semua_bagian_mati_tidak_ada_email(self, workspace):
        orang = _orang(workspace, "kosong")
        _tugas(workspace, -2, orang)
        _patch(orang, {"digest_terlambat": False, "digest_hari_ini": False, "digest_depan": False})
        saklar = dict(penerima_dan_saklar(workspace.id))[orang]
        assert not susun_ringkasan(orang, workspace.id, TugasWorkspace(workspace.id, HARI_INI), HARI_INI, saklar)

    @pytest.mark.django_db
    def test_preferensi_tersimpan(self, workspace):
        orang = _orang(workspace, "simpan")
        _patch(orang, {"digest_tim": False})
        assert UserNotificationPreference.objects.get(user=orang, workspace=None, project=None).digest_tim is False
