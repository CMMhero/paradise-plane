# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: urutan linimasa aktivitas per akun
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Urutan linimasa aktivitas disimpan di `Profile.theme["urutan_aktivitas"]`.

Tanpa migrasi: `theme` adalah JSONField. Yang dijaga di sini: kunci baru itu
lolos `ProfileEndpoint.patch`, kunci tema lain di sampingnya tidak tertimpa,
dan akun lain tidak ikut berubah.
"""

import pytest
from rest_framework import status

from plane.db.models import Profile

URL = "/api/users/me/profile/"


@pytest.fixture
def profil(create_user):
    return Profile.objects.get_or_create(user=create_user)[0]


@pytest.mark.contract
class TestUrutanAktivitas:
    @pytest.mark.django_db
    def test_kunci_baru_tersimpan_dan_terbaca_kembali(self, session_client, create_user, profil):
        res = session_client.patch(URL, {"theme": {"theme": "dark", "urutan_aktivitas": "asc"}}, format="json")
        assert res.status_code == status.HTTP_200_OK

        res = session_client.get(URL)
        assert res.data["theme"]["urutan_aktivitas"] == "asc"
        assert res.data["theme"]["theme"] == "dark"
        assert Profile.objects.get(user=create_user).theme["urutan_aktivitas"] == "asc"

    @pytest.mark.django_db
    def test_kunci_tema_lain_ikut_terkirim_bersama(self, session_client, create_user, profil):
        Profile.objects.filter(user=create_user).update(theme={"theme": "dark", "volume_suara": 40, "gerak": "kurangi"})
        profil = session_client.get(URL).data["theme"]

        res = session_client.patch(URL, {"theme": {**profil, "urutan_aktivitas": "desc"}}, format="json")

        assert res.status_code == status.HTTP_200_OK
        tersimpan = Profile.objects.get(user=create_user).theme
        assert tersimpan == {"theme": "dark", "volume_suara": 40, "gerak": "kurangi", "urutan_aktivitas": "desc"}

    @pytest.mark.django_db
    def test_akun_lain_tidak_berubah(self, session_client, create_user, create_bot_user, profil):
        session_client.patch(URL, {"theme": {"urutan_aktivitas": "asc"}}, format="json")
        lain = Profile.objects.get_or_create(user=create_bot_user)[0]
        assert "urutan_aktivitas" not in lain.theme
