# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bawaan member baru di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Bawaan akun baru (KEP-44): bahasa, zona waktu, tema, email per jabatan,
hak akses workspace, jabatan.

Yang dijaga: hanya Super Admin; masukan tak sah ditolak tanpa menulis apa pun;
bawaan profil DAN email hanya mengenai akun BARU (akun lama tetap ikut jabatannya
dengan tabel miliknya sendiri); akun dari God Mode lahir dengan peran & jabatan bawaan.
"""

import json
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import (
    TINGKAT_SUPERVISOR,
    JabatanOrganisasi,
    Profile,
    User,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)
from plane.license.api.views.bawaan_member import InstanceMemberDefaultsEndpoint
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.api.views.member import InstanceMemberEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.utils.bawaan_member import KUNCI, PABRIK
from plane.utils.preferensi_email import saklar_untuk, terapkan_perubahan

URL = "/api/instances/members/defaults/"


def _buat_user(prefix, **kolom):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", **kolom)


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-bawaan-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _buat_user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    return user


def _panggil(view, metode, aktor, badan=None, url=URL):
    request = getattr(APIRequestFactory(), metode)(url, badan, format="json")
    if aktor is not None:
        force_authenticate(request, user=aktor)
    return view.as_view()(request)


def _ubah(aktor, badan):
    return _panggil(InstanceMemberDefaultsEndpoint, "patch", aktor, badan)


def _tersimpan():
    mentah = InstanceConfiguration.objects.filter(key=KUNCI).values_list("value", flat=True).first()
    return json.loads(mentah) if mentah else None


@pytest.mark.contract
class TestEndpointBawaanMember:
    @pytest.mark.django_db
    def test_tanpa_baris_membalas_pabrik(self, super_admin):
        response = _panggil(InstanceMemberDefaultsEndpoint, "get", super_admin)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["profile"] == PABRIK["profile"]
        assert response.data["keanggotaan"] == {"workspace_role": 15, "tingkat": 10}
        assert response.data["pabrik"] == PABRIK

    @pytest.mark.django_db
    def test_bukan_super_admin_ditolak(self, super_admin):
        lain = _buat_user("lain")
        assert _panggil(InstanceMemberDefaultsEndpoint, "get", lain).status_code == status.HTTP_403_FORBIDDEN
        assert _ubah(lain, {"profile": {"language": "id"}}).status_code == status.HTTP_403_FORBIDDEN
        assert _tersimpan() is None

    @pytest.mark.django_db
    def test_patch_parsial_digabung_dengan_yang_ada(self, super_admin):
        assert _ubah(super_admin, {"profile": {"language": "id"}}).status_code == status.HTTP_200_OK
        response = _ubah(super_admin, {"email": {"staf": {"comment": True}}})
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["profile"]["language"] == "id"
        assert response.data["email"]["staf"]["comment"] is True
        # Saklar staf lain dan seluruh pimpinan tidak tersentuh.
        assert response.data["email"]["staf"]["approval"] is True
        assert response.data["email"]["pimpinan"] == PABRIK["email"]["pimpinan"]
        assert _tersimpan()["profile"]["language"] == "id"

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "badan",
        [
            {},
            {"tema": {}},
            {"profile": {"language": "xx"}},
            {"profile": {"timezone": "Mars/Olympus"}},
            {"profile": {"theme": "custom"}},
            {"profile": {"start_of_the_week": True}},
            {"profile": {"warna": "merah"}},
            # KEP-64: nilai tampilan di luar pilihannya.
            {"profile": {"gerak": "terang"}},
            {"profile": {"skema": True}},
            {"profile": {"gerak": None}},
            {"profile": {"skema": "pelangi"}},
            {"profile": {"font": "Comic Sans"}},
            {"email": {"komisaris": {}}},
            {"email": {"staf": {"spam": True}}},
            {"email": {"staf": {"comment": "ya"}}},
            # Admin workspace dan direktur untuk setiap akun baru = lubang.
            {"keanggotaan": {"workspace_role": 20}},
            {"keanggotaan": {"tingkat": 40}},
            {"keanggotaan": {"tingkat": 15}},
            # Bagian sah + bagian salah: tidak ada yang ditulis.
            {"profile": {"language": "id"}, "keanggotaan": {"workspace_role": 20}},
        ],
    )
    def test_masukan_tak_sah_ditolak_tanpa_menulis(self, super_admin, badan):
        response = _ubah(super_admin, badan)
        assert response.status_code == status.HTTP_400_BAD_REQUEST, badan
        assert _tersimpan() is None

    @pytest.mark.django_db
    def test_jabatan_boleh_dikosongkan(self, super_admin):
        response = _ubah(super_admin, {"keanggotaan": {"tingkat": None, "workspace_role": 5}})
        assert response.status_code == status.HTTP_200_OK, response.data
        assert response.data["keanggotaan"] == {"workspace_role": 5, "tingkat": None}

    @pytest.mark.django_db
    def test_patch_konfigurasi_umum_tidak_bisa_melewati_pemeriksaan(self, super_admin):
        response = _panggil(
            InstanceConfigurationEndpoint,
            "patch",
            super_admin,
            {KUNCI: '{"keanggotaan": {"workspace_role": 20}}'},
            url="/api/instances/configurations/",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert _tersimpan() is None


@pytest.mark.contract
class TestBawaanDiterapkan:
    @pytest.mark.django_db
    def test_akun_baru_memakai_bawaan_akun_lama_tidak(self, super_admin):
        lama = _buat_user("lama")
        Profile.objects.create(user=lama)
        _ubah(
            super_admin,
            {"profile": {"language": "id", "timezone": "Asia/Jakarta", "theme": "dark", "start_of_the_week": 1}},
        )

        baru = _buat_user("baru")
        profil = Profile.objects.create(user=baru)
        baru.refresh_from_db()
        profil.refresh_from_db()
        assert baru.user_timezone == "Asia/Jakarta"
        assert profil.language == "id"
        assert profil.start_of_the_week == 1
        assert profil.theme == {
            "theme": "dark",
            "skema": "bara",
            "font": "jakarta",
            "gerak": "halus",
            "volume_suara": 80,
            "suara_bisu": False,
        }

        lama.refresh_from_db()
        assert lama.user_timezone == "UTC"
        assert Profile.objects.get(user=lama).language == "en"

    @pytest.mark.django_db
    def test_akun_baru_memakai_bawaan_tampilan(self, super_admin):
        """KEP-64: bawaan skema/font/gerak dari God Mode ikut ke akun baru."""
        response = _ubah(super_admin, {"profile": {"skema": "sumi", "font": "inter", "gerak": "kurangi"}})
        assert response.status_code == status.HTTP_200_OK, response.data
        profil = Profile.objects.create(user=_buat_user("tampilan"))
        profil.refresh_from_db()
        assert profil.theme == {
            "theme": "system",
            "skema": "sumi",
            "font": "inter",
            "gerak": "kurangi",
            "volume_suara": 80,
            "suara_bisu": False,
        }

    @pytest.mark.django_db
    def test_nilai_yang_diberikan_pemanggil_menang(self, super_admin):
        _ubah(super_admin, {"profile": {"language": "id", "timezone": "Asia/Jakarta"}})
        u = _buat_user("eksplisit", user_timezone="Europe/Paris")
        profil = Profile.objects.create(user=u, language="ja", theme={"theme": "light"})
        assert u.user_timezone == "Europe/Paris"
        assert profil.language == "ja"
        assert profil.theme == {"theme": "light"}

    @pytest.mark.django_db
    def test_email_bawaan_hanya_mengenai_akun_baru(self, super_admin):
        lama = _buat_user("lama")
        pilih = _buat_user("pilih")
        UserNotificationPreference.objects.filter(user=pilih, workspace=None, project=None).update(
            ikut_bawaan_jabatan=False, comment=False
        )
        _ubah(super_admin, {"email": {"staf": {"comment": True, "approval": False}}})
        baru = _buat_user("baru")

        # Akun lama yang masih ikut bawaan jabatan TIDAK ikut berubah.
        assert saklar_untuk(lama.id)["comment"] is False
        assert saklar_untuk(lama.id)["approval"] is True
        assert saklar_untuk(pilih.id)["comment"] is False
        assert saklar_untuk(baru.id)["comment"] is True
        assert saklar_untuk(baru.id)["approval"] is False

    @pytest.mark.django_db
    def test_akun_lama_tetap_ikut_naik_jabatan_dengan_tabelnya_sendiri(self, super_admin):
        ws = Workspace.objects.create(name="WS", slug=f"ws-{uuid4().hex[:6]}", owner=super_admin)
        lama = _buat_user("naik")
        _ubah(super_admin, {"email": {"pimpinan": {"comment": True}}})
        JabatanOrganisasi.objects.create(workspace=ws, member=lama, tingkat=TINGKAT_SUPERVISOR)

        assert saklar_untuk(lama.id) == PABRIK["email"]["pimpinan"]

    @pytest.mark.django_db
    def test_kembali_ke_bawaan_memotret_tabel_god_mode_hari_ini(self, super_admin):
        lama = _buat_user("reset")
        _ubah(super_admin, {"email": {"staf": {"comment": True}}})
        pref = UserNotificationPreference.objects.get(user=lama, workspace=None, project=None)
        kolom = terapkan_perubahan(pref, {"ikut_bawaan_jabatan": True})
        pref.save(update_fields=[*kolom, "updated_at"])

        assert saklar_untuk(lama.id)["comment"] is True


@pytest.fixture
def workspace(super_admin):
    return Workspace.objects.create(name="Paradise", slug=f"paradise-{uuid4().hex[:6]}", owner=super_admin)


def _buat_akun(aktor, email):
    return _panggil(
        InstanceMemberEndpoint,
        "post",
        aktor,
        {"email": email, "display_name": "Budi Santoso", "password": "sandi-panjang-sekali"},
        url="/api/instances/members/",
    )


@pytest.mark.contract
class TestAkunDariGodMode:
    @pytest.mark.django_db
    def test_bawaan_pabrik_member_staf(self, super_admin, workspace):
        response = _buat_akun(super_admin, "budi@paradise.test")
        assert response.status_code == status.HTTP_201_CREATED, response.data
        u = User.objects.get(email="budi@paradise.test")
        assert WorkspaceMember.objects.get(workspace=workspace, member=u).role == 15
        jabatan = JabatanOrganisasi.objects.get(workspace=workspace, member=u)
        assert jabatan.tingkat == 10
        assert jabatan.departemen_id is None and jabatan.divisi_id is None
        # Profil lahir bersama akunnya, bukan saat login pertama.
        assert Profile.objects.filter(user=u).exists()

    @pytest.mark.django_db
    def test_bawaan_diatur(self, super_admin, workspace):
        _ubah(
            super_admin,
            {
                "profile": {"language": "id", "timezone": "Asia/Jakarta"},
                "keanggotaan": {"workspace_role": 5, "tingkat": None},
            },
        )
        assert _buat_akun(super_admin, "sari@paradise.test").status_code == status.HTTP_201_CREATED
        u = User.objects.get(email="sari@paradise.test")
        assert u.user_timezone == "Asia/Jakarta"
        assert Profile.objects.get(user=u).language == "id"
        assert WorkspaceMember.objects.get(workspace=workspace, member=u).role == 5
        assert not JabatanOrganisasi.objects.filter(member=u).exists()
