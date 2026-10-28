# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengaturan pribadi member dari God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Super Admin mengatur bahasa, awal pekan, dan saklar notifikasi milik member.

Yang dijaga: hanya Super Admin yang boleh, kolom di luar daftar putih tidak
tersentuh, dan masukan tak sah ditolak SEBELUM satu kolom pun ditulis.
"""

from uuid import uuid4

import pytest
from django.test import RequestFactory
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import Profile, User, UserNotificationPreference
from plane.license.api.views.member import InstanceMemberPreferenceEndpoint
from plane.license.models import Instance, InstanceAdmin

URL = "/api/instances/members/{}/preferences/"


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-pref-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _buat_user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


@pytest.fixture
def staf(db):
    return _buat_user("staf")


def _get(aktor, pk):
    request = RequestFactory().get(URL.format(pk))
    if aktor is not None:
        force_authenticate(request, user=aktor)
    return InstanceMemberPreferenceEndpoint.as_view()(request, pk=pk)


def _patch(aktor, pk, badan):
    request = APIRequestFactory().patch(URL.format(pk), badan, format="json")
    if aktor is not None:
        force_authenticate(request, user=aktor)
    return InstanceMemberPreferenceEndpoint.as_view()(request, pk=pk)


@pytest.mark.contract
class TestMemberPreferensiGodMode:
    @pytest.mark.django_db
    def test_super_admin_membaca_bawaan(self, super_admin, staf):
        response = _get(super_admin, staf.id)
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        assert response.data["profile"]["language"] == "en"
        assert response.data["notifications"]["approval"] is True
        assert response.data["notifications"]["daily_digest"] is False

    @pytest.mark.django_db
    def test_anggota_biasa_TIDAK_bisa_membaca_maupun_menulis(self, super_admin, staf):
        lain = _buat_user("lain")
        assert _get(lain, staf.id).status_code == status.HTTP_403_FORBIDDEN
        assert _patch(lain, staf.id, {"profile": {"language": "id"}}).status_code == status.HTTP_403_FORBIDDEN
        assert not Profile.objects.filter(user=staf).exists(), "ditolak = tidak ada yang ditulis, termasuk baris Profile"

    @pytest.mark.django_db
    def test_tanpa_login_ditolak(self, super_admin, staf):
        assert _patch(None, staf.id, {"profile": {"language": "id"}}).status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    @pytest.mark.django_db
    def test_ubah_profil_dan_notifikasi_sekaligus(self, super_admin, staf):
        response = _patch(
            super_admin,
            staf.id,
            {
                "profile": {"language": "id", "start_of_the_week": 1, "notification_view_mode": "compact"},
                "notifications": {"daily_digest": True, "comment": True},
            },
        )
        assert response.status_code == status.HTTP_200_OK, getattr(response, "data", None)
        profil = Profile.objects.get(user=staf)
        assert (profil.language, profil.start_of_the_week, profil.notification_view_mode) == ("id", 1, "compact")
        notif = UserNotificationPreference.objects.get(user=staf, workspace=None, project=None)
        assert notif.daily_digest is True and notif.comment is True
        # yang tidak dikirim tidak disentuh
        assert notif.approval is True and notif.mention is False

    @pytest.mark.django_db
    def test_kolom_di_luar_daftar_putih_diabaikan(self, super_admin, staf):
        response = _patch(
            super_admin, staf.id, {"profile": {"is_onboarded": True, "billing_address_country": "X", "language": "id"}}
        )
        assert response.status_code == status.HTTP_200_OK
        profil = Profile.objects.get(user=staf)
        assert profil.language == "id"
        assert profil.is_onboarded is False and profil.billing_address_country == "INDIA"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "badan",
        [
            {"profile": {"language": "klingon"}},
            {"profile": {"start_of_the_week": 9}},
            {"profile": {"start_of_the_week": True}},
            {"profile": {"notification_view_mode": "huge"}},
            {"notifications": {"comment": "ya"}},
            {"profile": "bukan-objek"},
        ],
    )
    def test_masukan_tak_sah_ditolak_dan_tidak_menulis_apa_pun(self, super_admin, staf, badan):
        # bagian sah ikut dikirim: kalau validasi bocor, `daily_digest` ikut tersimpan
        response = _patch(super_admin, staf.id, {"notifications": {"daily_digest": True}, **badan})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        notif = UserNotificationPreference.objects.filter(user=staf, workspace=None, project=None).first()
        assert notif is None or notif.daily_digest is False

    @pytest.mark.django_db
    def test_akun_tak_ada_404(self, super_admin):
        assert _get(super_admin, uuid4()).status_code == status.HTTP_404_NOT_FOUND
