# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: endpoint registri aturan God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""GET/PATCH /api/instances/rules/, POST rules/reset/, `paradise_rules` di
/api/instances/, penolakan kunci aturan di /configurations/, dan aturan bawaan
tampilan yang lewat New member defaults.

Yang dijaga: semua-atau-tidak-sama-sekali, aturan risk=high hanya berubah
dengan frasa konfirmasi (juga saat dikembalikan), setiap perubahan meninggalkan
satu entri audit, dan registri lama tetap dirujuk ke /settings/.
"""

from uuid import uuid4

import pytest
from auditlog.models import LogEntry
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import Profile, User
from plane.license.api.views.aturan import InstanceRulesEndpoint, InstanceRulesResetEndpoint
from plane.license.api.views.bawaan_member import InstanceMemberDefaultsApplyEndpoint, InstanceMemberDefaultsEndpoint
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.api.views.instance import InstanceEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.tests.unit.utils.test_aturan_registri import nilai_lain
from plane.utils import aturan
from plane.utils.aturan.area_obrolan import CHAT_PINS_MAX
from plane.utils.aturan.area_tampilan import ACTIVITY_NEWEST_FIRST
from plane.utils.aturan.area_tugas import APPROVER_MIN_LEVEL
from plane.utils.aturan.area_visibilitas import DIRECTOR_SIDEBAR_HIDES
from plane.utils.aturan.jenis import TINGGI, ke_json
from plane.utils.saklar_instance import STUCK_AFTER_DAYS
from plane.utils.setelan_instance import FRASA_KONFIRMASI

URL = "/api/instances/rules/"
TINGGI_SEMUA = [r for r in aturan.REGISTRI.values() if r.risk == TINGGI]


def _user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-aturan-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    cache.clear()
    yield user
    cache.clear()


def _panggil(view, metode, aktor, badan=None, url=URL):
    pabrik = APIRequestFactory()
    request = getattr(pabrik, metode)(url, badan, format="json") if badan is not None else getattr(pabrik, metode)(url)
    force_authenticate(request, user=aktor)
    return view.as_view()(request)


def _get(aktor):
    return _panggil(InstanceRulesEndpoint, "get", aktor)


def _patch(aktor, badan):
    return _panggil(InstanceRulesEndpoint, "patch", aktor, badan)


def _reset(aktor, badan):
    return _panggil(InstanceRulesResetEndpoint, "post", aktor, badan, url=URL + "reset/")


def _butir(res, kunci):
    return next(d for d in res.data["rules"] if d["key"] == kunci)


def _audit(kunci):
    return LogEntry.objects.filter(object_repr=f"Rule: {kunci}")


@pytest.mark.contract
class TestDaftar:
    @pytest.mark.django_db
    def test_memuat_registri_lalu_setelan_lama(self, super_admin):
        res = _get(super_admin)
        assert res.status_code == status.HTTP_200_OK
        sumber = [d["source"] for d in res.data["rules"]]
        jumlah = len(aturan.REGISTRI)
        assert sumber[:jumlah] == ["registry"] * jumlah
        assert set(sumber[jumlah:]) == {"legacy"}
        assert [d["key"] for d in res.data["rules"][:jumlah]] == list(aturan.REGISTRI)
        assert res.data["confirm_phrase"] == FRASA_KONFIRMASI
        assert {g["id"] for g in res.data["groups"]} >= {r.group for r in aturan.REGISTRI.values()}

    @pytest.mark.django_db
    def test_bentuk_satu_aturan(self, super_admin):
        butir = _butir(_get(super_admin), APPROVER_MIN_LEVEL)
        assert butir == {
            "key": APPROVER_MIN_LEVEL,
            "source": "registry",
            "kind": "level",
            "value": 20,
            "default": 20,
            "changed": False,
            "label": "Lowest level that can approve",
            "help": aturan.REGISTRI[APPROVER_MIN_LEVEL].help,
            "group": "approvals",
            "area": "tugas",
            "risk": "high",
            "applies": "live",
            "web": False,
            "kep": "P29",
            "min": None,
            "max": None,
            "max_length": None,
            "choices": [{"value": 20, "label": "Supervisor (20)"}, {"value": 30, "label": "Manager (30)"}],
            "store": "instance",
            "apply_section": None,
        }

    @pytest.mark.django_db
    def test_setelan_lama_baca_saja_dengan_tanda_berubah(self, super_admin):
        InstanceConfiguration.objects.create(key=STUCK_AFTER_DAYS, value="10", category="PARADISE")
        butir = _butir(_get(super_admin), STUCK_AFTER_DAYS)
        assert (butir["source"], butir["value"], butir["default"], butir["changed"]) == ("legacy", "10", "7", True)

    @pytest.mark.django_db
    def test_bukan_super_admin_ditolak(self, super_admin):
        orang = _user("biasa")
        assert _get(orang).status_code == status.HTTP_403_FORBIDDEN
        assert _patch(orang, {"values": {CHAT_PINS_MAX: 5}}).status_code == status.HTTP_403_FORBIDDEN
        assert _reset(orang, {"keys": [CHAT_PINS_MAX]}).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
class TestUbah:
    @pytest.mark.django_db
    def test_ubah_menulis_baris_dan_audit(self, super_admin):
        res = _patch(super_admin, {"values": {CHAT_PINS_MAX: 5, DIRECTOR_SIDEBAR_HIDES: "none"}})
        assert res.status_code == status.HTTP_200_OK
        assert _butir(res, CHAT_PINS_MAX)["value"] == 5 and _butir(res, CHAT_PINS_MAX)["changed"] is True
        assert InstanceConfiguration.objects.get(key=CHAT_PINS_MAX).value == "5"
        assert aturan.get_int(CHAT_PINS_MAX) == 5
        entri = _audit(CHAT_PINS_MAX).get()
        assert entri.changes == {"value": ["20", "5"]}
        assert entri.actor_id == super_admin.id
        assert entri.additional_data["kind"] == "rule"
        assert _audit(DIRECTOR_SIDEBAR_HIDES).count() == 1

    @pytest.mark.django_db
    def test_nilai_sama_tidak_menulis_apa_pun(self, super_admin):
        assert _patch(super_admin, {"values": {CHAT_PINS_MAX: 20}}).status_code == status.HTTP_200_OK
        assert not InstanceConfiguration.objects.filter(key=CHAT_PINS_MAX).exists()
        assert not _audit(CHAT_PINS_MAX).exists()

    @pytest.mark.django_db
    def test_satu_galat_tidak_ada_yang_ditulis(self, super_admin):
        res = _patch(super_admin, {"values": {CHAT_PINS_MAX: 5, DIRECTOR_SIDEBAR_HIDES: "semua"}})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert set(res.data["errors"]) == {DIRECTOR_SIDEBAR_HIDES}
        assert not InstanceConfiguration.objects.filter(key=CHAT_PINS_MAX).exists()

    @pytest.mark.django_db
    def test_kunci_lama_dan_asing_ditolak(self, super_admin):
        res = _patch(super_admin, {"values": {STUCK_AFTER_DAYS: 10, "TIDAK_ADA": 1}})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data["errors"] == {
            STUCK_AFTER_DAYS: "This setting is changed on its own tab.",
            "TIDAK_ADA": "Unknown rule.",
        }

    @pytest.mark.django_db
    def test_badan_salah_bentuk(self, super_admin):
        assert _patch(super_admin, {"values": {}}).status_code == status.HTTP_400_BAD_REQUEST
        assert _patch(super_admin, {CHAT_PINS_MAX: 5}).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    @pytest.mark.parametrize("rule", TINGGI_SEMUA, ids=[r.key for r in TINGGI_SEMUA])
    def test_aturan_berisiko_tinggi_butuh_frasa(self, super_admin, rule):
        lain = ke_json(rule, nilai_lain(rule))
        res = _patch(super_admin, {"values": {rule.key: lain}})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data == {"error": "confirm_required", "keys": [rule.key]}
        assert aturan.get(rule.key) == rule.default
        assert _patch(super_admin, {"values": {rule.key: lain}, "confirm": "change rules"}).status_code == 400

        res = _patch(super_admin, {"values": {rule.key: lain}, "confirm": FRASA_KONFIRMASI})
        assert res.status_code == status.HTTP_200_OK
        assert _butir(res, rule.key)["value"] == lain

        # Kembali ke bawaan juga mengubah izin: frasa lagi.
        res = _reset(super_admin, {"keys": [rule.key]})
        assert res.data == {"error": "confirm_required", "keys": [rule.key]}
        res = _reset(super_admin, {"keys": [rule.key], "confirm": FRASA_KONFIRMASI})
        assert res.status_code == status.HTTP_200_OK
        assert aturan.get(rule.key) == rule.default
        assert _audit(rule.key).count() == 2

    @pytest.mark.django_db
    def test_aturan_rendah_tanpa_frasa(self, super_admin):
        assert _patch(super_admin, {"values": {DIRECTOR_SIDEBAR_HIDES: "archives_your_work"}}).status_code == 200


@pytest.mark.contract
class TestKembalikan:
    @pytest.mark.django_db
    def test_reset_menghapus_baris_dan_mencatat(self, super_admin):
        _patch(super_admin, {"values": {CHAT_PINS_MAX: 5}})
        res = _reset(super_admin, {"keys": [CHAT_PINS_MAX]})
        assert res.status_code == status.HTTP_200_OK
        assert _butir(res, CHAT_PINS_MAX)["changed"] is False
        assert not InstanceConfiguration.objects.filter(key=CHAT_PINS_MAX).exists()
        terakhir = _audit(CHAT_PINS_MAX).order_by("-timestamp").first()
        assert terakhir.changes == {"value": ["5", "20"]}
        assert terakhir.additional_data["reset"] is True

    @pytest.mark.django_db
    def test_reset_kunci_asing_ditolak(self, super_admin):
        res = _reset(super_admin, {"keys": [STUCK_AFTER_DAYS]})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert _reset(super_admin, {"keys": "x"}).status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestKonfigurasiDanPayloadWeb:
    @pytest.mark.django_db
    def test_configurations_menolak_kunci_aturan(self, super_admin):
        InstanceConfiguration.objects.create(key=APPROVER_MIN_LEVEL, value="20", category="PARADISE")
        url = "/api/instances/configurations/"
        res = _panggil(InstanceConfigurationEndpoint, "patch", super_admin, {APPROVER_MIN_LEVEL: "30"}, url=url)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data["keys"] == [APPROVER_MIN_LEVEL]
        assert InstanceConfiguration.objects.get(key=APPROVER_MIN_LEVEL).value == "20"

    @pytest.mark.django_db
    def test_paradise_rules_hanya_aturan_web(self, super_admin):
        res = _panggil(InstanceEndpoint, "get", _user("tamu"), url="/api/instances/")
        assert res.data["config"]["paradise_rules"] == {
            r.key: ke_json(r, r.default) for r in aturan.REGISTRI.values() if r.web
        }
        assert DIRECTOR_SIDEBAR_HIDES in res.data["config"]["paradise_rules"]
        assert APPROVER_MIN_LEVEL not in res.data["config"]["paradise_rules"]

        _patch(super_admin, {"values": {DIRECTOR_SIDEBAR_HIDES: "none"}})
        res = _panggil(InstanceEndpoint, "get", _user("tamu"), url="/api/instances/")
        assert res.data["config"]["paradise_rules"][DIRECTOR_SIDEBAR_HIDES] == "none"


@pytest.mark.contract
class TestBawaanTampilan:
    """ACTIVITY_NEWEST_FIRST: disimpan di PARADISE_BAWAAN_MEMBER, bukan baris sendiri."""

    def _profil_baru(self):
        user = _user("baru")
        return Profile.objects.get_or_create(user=user)[0]

    @pytest.mark.django_db
    def test_bawaan_akun_baru_tidak_berubah(self, super_admin):
        assert "urutan_aktivitas" not in self._profil_baru().theme

    @pytest.mark.django_db
    def test_diubah_di_rules_berlaku_untuk_akun_baru_saja(self, super_admin):
        lama = self._profil_baru()
        res = _patch(super_admin, {"values": {ACTIVITY_NEWEST_FIRST: False}})
        assert res.status_code == status.HTTP_200_OK
        butir = _butir(res, ACTIVITY_NEWEST_FIRST)
        assert (butir["value"], butir["store"], butir["apply_section"]) == (False, "member_default", "tampilan")
        assert not InstanceConfiguration.objects.filter(key=ACTIVITY_NEWEST_FIRST).exists()

        bawaan = _panggil(InstanceMemberDefaultsEndpoint, "get", super_admin, url="/api/instances/members/defaults/")
        assert bawaan.data["tampilan"] == {"aktivitas_terbaru_di_atas": False}
        assert bawaan.data["pabrik"]["tampilan"] == {"aktivitas_terbaru_di_atas": True}

        assert self._profil_baru().theme["urutan_aktivitas"] == "asc"
        lama.refresh_from_db()
        assert "urutan_aktivitas" not in lama.theme

    @pytest.mark.django_db
    def test_terapkan_ke_semua_lewat_tombol_yang_ada(self, super_admin):
        lama = self._profil_baru()
        Profile.objects.filter(pk=lama.pk).update(theme={"theme": "dark", "urutan_aktivitas": "desc"})
        res = _panggil(
            InstanceMemberDefaultsEndpoint,
            "patch",
            super_admin,
            {"tampilan": {"aktivitas_terbaru_di_atas": False}},
            url="/api/instances/members/defaults/",
        )
        assert res.status_code == status.HTTP_200_OK
        assert aturan.get_bool(ACTIVITY_NEWEST_FIRST) is False

        res = _panggil(
            InstanceMemberDefaultsApplyEndpoint,
            "post",
            super_admin,
            {"sections": ["tampilan"]},
            url="/api/instances/members/defaults/apply/",
        )
        assert res.status_code == status.HTTP_200_OK
        assert res.data["updated"]["tampilan"] >= 1
        lama.refresh_from_db()
        assert lama.theme == {"theme": "dark", "urutan_aktivitas": "asc"}

    @pytest.mark.django_db
    def test_members_defaults_memvalidasi_dengan_registri(self, super_admin):
        res = _panggil(
            InstanceMemberDefaultsEndpoint,
            "patch",
            super_admin,
            {"tampilan": {"aktivitas_terbaru_di_atas": "kadang"}},
            url="/api/instances/members/defaults/",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        res = _panggil(
            InstanceMemberDefaultsEndpoint,
            "patch",
            super_admin,
            {"tampilan": {"kolom_asing": True}},
            url="/api/instances/members/defaults/",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
