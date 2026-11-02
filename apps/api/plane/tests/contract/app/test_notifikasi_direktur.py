# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kebijakan notifikasi direktur
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keputusan user 2026-11-02: direktur hanya menerima penyebutan, obrolan, dan ringkasan.

Baris direktur di God Mode adalah bawaan SEKALIGUS batas atas: pilihan pribadi
lama yang menyalakan persetujuan atau komentar tidak bisa menembusnya.
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.app.views.notification.base import UserNotificationPreferenceEndpoint
from plane.db.models import (
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    JabatanOrganisasi,
    User,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)
from plane.utils.bawaan_member import PABRIK, baca_bawaan, simpan_bawaan
from plane.utils.preferensi_email import (
    BAWAAN_DIREKTUR,
    BAWAAN_PIMPINAN,
    SAKLAR_NOTIFIKASI,
    dikunci,
    kelompok_jabatan,
    penyaring,
    saklar_untuk,
)

URL = "/api/users/me/notification-preferences/"
BOLEH_DIREKTUR = {
    "mention",
    "chat",
    "inbox_mention",
    "inbox_chat",
    "daily_digest",
    "daily_digest_sore",
    "digest_terlambat",
    "digest_hari_ini",
    "digest_depan",
    "digest_diberikan",
    "digest_tim",
}


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email=f"owner-{uuid4().hex[:8]}@uji.id", username=f"owner_{uuid4().hex[:8]}")
    return Workspace.objects.create(name="WS", slug=f"ws-dir-{uuid4().hex[:6]}", owner=pemilik)


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


@pytest.mark.contract
class TestKelompok:
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ("tingkat", "harapan"),
        [
            (None, "staf"),
            (TINGKAT_MEMBER, "staf"),
            (TINGKAT_SUPERVISOR, "pimpinan"),
            (TINGKAT_MANAGER, "pimpinan"),
            (TINGKAT_DIREKTUR, "direktur"),
        ],
    )
    def test_kelompok_dari_jabatan(self, workspace, tingkat, harapan):
        assert kelompok_jabatan(_orang(workspace, "x", tingkat).id) == harapan

    @pytest.mark.django_db
    def test_jabatan_tertinggi_antar_workspace_menang(self, workspace):
        orang = _orang(workspace, "dua", TINGKAT_MANAGER)
        lain = Workspace.objects.create(name="Lain", slug=f"ws-lain-{uuid4().hex[:6]}", owner=workspace.owner)
        JabatanOrganisasi.objects.create(workspace=lain, member=orang, tingkat=TINGKAT_DIREKTUR)
        assert kelompok_jabatan(orang.id) == "direktur"


@pytest.mark.contract
class TestBawaanDirektur:
    def test_isi_bawaan_hanya_penyebutan_obrolan_ringkasan(self):
        assert {k for k in SAKLAR_NOTIFIKASI if BAWAAN_DIREKTUR[k]} == BOLEH_DIREKTUR

    @pytest.mark.django_db
    def test_direktur_baru_ikut_bawaan_direktur(self, workspace):
        assert saklar_untuk(_orang(workspace, "dir", TINGKAT_DIREKTUR).id) == BAWAAN_DIREKTUR

    @pytest.mark.django_db
    def test_leader_tetap_bawaan_pimpinan(self, workspace):
        assert saklar_untuk(_orang(workspace, "mgr", TINGKAT_MANAGER).id) == BAWAAN_PIMPINAN

    @pytest.mark.django_db
    def test_pilihan_pribadi_lama_tidak_menembus_batas(self, workspace):
        direktur = _orang(workspace, "dir", TINGKAT_DIREKTUR)
        UserNotificationPreference.objects.update_or_create(
            user=direktur,
            workspace=None,
            project=None,
            defaults={k: True for k in SAKLAR_NOTIFIKASI} | {"ikut_bawaan_jabatan": False},
        )
        nilai = saklar_untuk(direktur.id)
        assert {k for k, v in nilai.items() if v} == BOLEH_DIREKTUR
        assert penyaring([direktur.id], "inbox_approval") == set()
        assert penyaring([direktur.id], "inbox_mention") == {direktur.id}

    @pytest.mark.django_db
    def test_potret_lama_tanpa_kelompok_direktur(self, workspace):
        direktur = _orang(workspace, "dir", TINGKAT_DIREKTUR)
        UserNotificationPreference.objects.filter(user=direktur).update(
            bawaan_email={"staf": PABRIK["email"]["staf"], "pimpinan": PABRIK["email"]["pimpinan"]}
        )
        assert saklar_untuk(direktur.id) == BAWAAN_DIREKTUR

    @pytest.mark.django_db
    def test_god_mode_mengatur_batas_seketika(self, workspace):
        direktur = _orang(workspace, "dir", TINGKAT_DIREKTUR)
        bawaan = baca_bawaan()
        bawaan["email"]["direktur"]["approval"] = True
        bawaan["email"]["direktur"]["inbox_approval"] = True
        simpan_bawaan(bawaan)
        assert saklar_untuk(direktur.id)["inbox_approval"] is True
        assert "inbox_approval" not in dikunci(direktur.id)

    @pytest.mark.django_db
    def test_endpoint_profil_mengirim_daftar_kunci(self, workspace):
        direktur = _orang(workspace, "dir", TINGKAT_DIREKTUR)
        staf = _orang(workspace, "staf", TINGKAT_MEMBER)
        res = _get(direktur)
        assert set(res.data["dikunci"]) == set(SAKLAR_NOTIFIKASI) - BOLEH_DIREKTUR
        assert res.data["inbox_comment"] is False
        assert _get(staf).data["dikunci"] == []
