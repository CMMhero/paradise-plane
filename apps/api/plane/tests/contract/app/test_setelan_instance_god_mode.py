# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: endpoint setelan God Mode (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""GET/PATCH /api/instances/settings/, penolakan kunci sensitif di /configurations/,
`paradise_limits` di /api/instances/, `locked_by_admin` di preferensi notifikasi,
dan `email_aktif()`.

Yang dijaga: PATCH semua-atau-tidak-sama-sekali, aturan sensitif hanya berubah
dengan frasa konfirmasi, setiap kunci yang berubah meninggalkan tepat satu entri
audit yang terbaca dari God Mode > Logs > Audit log, dan menyalakan saklar yang
dikunci admin diabaikan tanpa membuang pilihan orangnya.
"""

from uuid import uuid4

import pytest
from auditlog.models import LogEntry
from django.core.cache import cache
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.app.views.notification.base import UserNotificationPreferenceEndpoint
from plane.db.models import (
    TINGKAT_DIREKTUR,
    JabatanOrganisasi,
    User,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)
from plane.license.api.views.audit_log import InstanceAuditLogEndpoint
from plane.license.api.views.configuration import InstanceConfigurationEndpoint
from plane.license.api.views.instance import InstanceEndpoint
from plane.license.api.views.setelan import InstanceSettingsEndpoint
from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration
from plane.license.utils.instance_value import email_aktif
from plane.utils import saklar_instance as si
from plane.utils import setelan_instance as st

URL = "/api/instances/settings/"


def _buat_user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}")


@pytest.fixture
def super_admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-kep78-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    user = _buat_user("super")
    InstanceAdmin.objects.create(instance=instance, user=user, role=20)
    cache.clear()
    yield user
    cache.clear()


def _get(aktor):
    request = APIRequestFactory().get(URL)
    force_authenticate(request, user=aktor)
    return InstanceSettingsEndpoint.as_view()(request)


def _patch(aktor, badan):
    request = APIRequestFactory().patch(URL, badan, format="json")
    force_authenticate(request, user=aktor)
    return InstanceSettingsEndpoint.as_view()(request)


def _nilai(res, kunci):
    return next(d for d in res.data["settings"] if d["key"] == kunci)["value"]


def _baris(kunci):
    return InstanceConfiguration.objects.filter(key=kunci).values_list("value", flat=True).first()


def _simpan(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(key=kunci, defaults={"value": nilai, "category": "PARADISE"})


def _audit(kunci):
    return LogEntry.objects.filter(content_type__model="instanceconfiguration", object_repr=kunci)


@pytest.mark.contract
class TestSettingsEndpoint:
    @pytest.mark.django_db
    def test_get_memuat_registri(self, super_admin):
        res = _get(super_admin)
        assert res.status_code == status.HTTP_200_OK
        kunci = [d["key"] for d in res.data["settings"]]
        assert kunci == st.semua_kunci()
        butir = next(d for d in res.data["settings"] if d["key"] == st.DIGEST_WEEKDAYS)
        assert butir == {
            "key": st.DIGEST_WEEKDAYS,
            "kind": "weekday_set",
            "default": "1,2,3,4,5",
            "value": "1,2,3,4,5",
            "min": None,
            "max": None,
            "choices": None,
            "sensitive": False,
        }

    @pytest.mark.django_db
    def test_bukan_super_admin_ditolak(self, super_admin):
        orang = _buat_user("biasa")
        assert _get(orang).status_code == status.HTTP_403_FORBIDDEN
        assert _patch(orang, {"values": {si.STUCK_AFTER_DAYS: 10}}).status_code == status.HTTP_403_FORBIDDEN
        assert _baris(si.STUCK_AFTER_DAYS) is None

    @pytest.mark.django_db
    def test_patch_menulis_dinormalkan_dan_audit(self, super_admin):
        res = _patch(
            super_admin,
            {"values": {si.STUCK_AFTER_DAYS: "10", st.DIGEST_MORNING_TIME: "7:45", st.DIGEST_WEEKDAYS: [5, 1]}},
        )
        assert res.status_code == status.HTTP_200_OK, res.data
        assert _baris(si.STUCK_AFTER_DAYS) == "10"
        assert _baris(st.DIGEST_MORNING_TIME) == "07:45"
        assert _baris(st.DIGEST_WEEKDAYS) == "1,5"
        assert _nilai(res, st.DIGEST_MORNING_TIME) == "07:45"
        entri = _audit(si.STUCK_AFTER_DAYS).get()
        assert entri.changes == {"value": ["7", "10"]}
        assert entri.actor_id == super_admin.id
        assert entri.action == LogEntry.Action.UPDATE

    @pytest.mark.django_db
    def test_nilai_sama_tidak_diaudit(self, super_admin):
        res = _patch(super_admin, {"values": {si.STUCK_AFTER_DAYS: 7}})
        assert res.status_code == status.HTTP_200_OK
        assert not _audit(si.STUCK_AFTER_DAYS).exists()

    @pytest.mark.django_db
    def test_semua_atau_tidak_sama_sekali(self, super_admin):
        res = _patch(
            super_admin,
            {"values": {si.STUCK_AFTER_DAYS: 10, st.DIGEST_MORNING_TIME: "25:00", "BUKAN_KUNCI": "1"}},
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert set(res.data["errors"]) == {st.DIGEST_MORNING_TIME, "BUKAN_KUNCI"}
        assert _baris(si.STUCK_AFTER_DAYS) is None
        assert not LogEntry.objects.filter(content_type__model="instanceconfiguration").exists()

    @pytest.mark.django_db
    def test_body_salah_bentuk(self, super_admin):
        assert _patch(super_admin, {si.STUCK_AFTER_DAYS: 10}).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_sensitif_tanpa_konfirmasi_ditolak(self, super_admin):
        for badan in (
            {"values": {si.TASK_DELETE_RULE: 1, si.STUCK_AFTER_DAYS: 10}},
            {"values": {si.TASK_DELETE_RULE: 1}, "confirm": "change rules"},
        ):
            res = _patch(super_admin, badan)
            assert res.status_code == status.HTTP_400_BAD_REQUEST
            assert res.data == {"error": "confirm_required", "keys": [si.TASK_DELETE_RULE]}
        assert _baris(si.TASK_DELETE_RULE) is None
        assert _baris(si.STUCK_AFTER_DAYS) is None

    @pytest.mark.django_db
    @pytest.mark.gerbang_bawaan
    def test_sensitif_dengan_konfirmasi(self, super_admin):
        res = _patch(super_admin, {"values": {si.HIERARKI_GERBANG_TUGAS: False}, "confirm": "CHANGE RULES"})
        assert res.status_code == status.HTTP_200_OK, res.data
        assert _baris(si.HIERARKI_GERBANG_TUGAS) == "0"
        entri = _audit(si.HIERARKI_GERBANG_TUGAS).get()
        assert entri.changes == {"value": ["1", "0"]}
        assert entri.additional_data == {"key": si.HIERARKI_GERBANG_TUGAS, "sensitive": True}

    @pytest.mark.django_db
    def test_sensitif_yang_tidak_berubah_tak_butuh_konfirmasi(self, super_admin):
        # God Mode mengirim seluruh tab; nilai sensitif yang sama tidak dihitung berubah.
        res = _patch(super_admin, {"values": {si.ASSIGN_DOWN_ONLY: "1", si.STUCK_AFTER_DAYS: 9}})
        assert res.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_audit_terbaca_dari_god_mode(self, super_admin):
        _patch(super_admin, {"values": {si.STUCK_AFTER_DAYS: 12}})
        request = APIRequestFactory().get("/api/instances/audit-logs/", {"model": "instanceconfiguration"})
        force_authenticate(request, user=super_admin)
        res = InstanceAuditLogEndpoint.as_view()(request)
        assert res.status_code == status.HTTP_200_OK
        assert [r["object_repr"] for r in res.data["results"]] == [si.STUCK_AFTER_DAYS]


def _patch_konfigurasi(aktor, badan):
    request = APIRequestFactory().patch("/api/instances/configurations/", badan, format="json")
    force_authenticate(request, user=aktor)
    return InstanceConfigurationEndpoint.as_view()(request)


@pytest.mark.contract
class TestConfigurationsLama:
    @pytest.mark.django_db
    def test_kunci_sensitif_ditolak(self, super_admin):
        res = _patch_konfigurasi(super_admin, {si.HIERARKI_GERBANG_TUGAS: "1", si.STUCK_AFTER_DAYS: "9"})
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data["keys"] == [si.HIERARKI_GERBANG_TUGAS]
        assert _baris(si.STUCK_AFTER_DAYS) is None

    @pytest.mark.django_db
    def test_jenis_baru_divalidasi_dan_dinormalkan(self, super_admin):
        assert _patch_konfigurasi(super_admin, {st.DIGEST_WEEKDAYS: "8"}).status_code == 400
        res = _patch_konfigurasi(super_admin, {st.DIGEST_WEEKDAYS: "3,1", st.OFFICE_TIMEZONE: "Asia/Makassar"})
        assert res.status_code == status.HTTP_200_OK
        assert _baris(st.DIGEST_WEEKDAYS) == "1,3"
        assert _baris(st.OFFICE_TIMEZONE) == "Asia/Makassar"


@pytest.mark.contract
class TestPayloadPublik:
    @pytest.mark.django_db
    def test_paradise_limits(self, super_admin):
        _simpan(si.UPLOAD_MAX_MB, "3")
        _simpan(si.CHAT_MESSAGE_MAX_LENGTH, "800")
        _simpan(st.OFFICE_TIMEZONE, "Asia/Jayapura")
        res = InstanceEndpoint.as_view()(APIRequestFactory().get("/api/instances/"))
        config = res.data["config"]
        assert config["paradise_limits"] == {
            "upload_max_mb": 3,
            "chat_message_max_length": 800,
            "chat_attachments_max": 5,
            "chat_edit_window_hours": 24,
            "auto_archive_done_days": 90,
            "chat_delete_window_hours": 24,
            "office_timezone": "Asia/Jayapura",
        }
        assert config["file_size_limit"] == 3 * 1024 * 1024

    @pytest.mark.django_db
    def test_batas_unggah_bawaan_sama_dengan_server(self, super_admin, settings, monkeypatch):
        # Env bukan kelipatan MiB: web harus menerima batas byte yang persis dijaga
        # server (batas_unggah_byte), bukan angka MiB yang dibulatkan ke bawah.
        from plane.utils.plan_limits import batas_unggah_byte

        monkeypatch.setenv("FILE_SIZE_LIMIT", "5000000")
        settings.FILE_SIZE_LIMIT = 5000000
        monkeypatch.setitem(si.SETELAN_ANGKA, si.UPLOAD_MAX_MB, (4, 1, 4))
        res = InstanceEndpoint.as_view()(APIRequestFactory().get("/api/instances/"))
        config = res.data["config"]
        assert config["file_size_limit"] == batas_unggah_byte() == 5000000
        assert config["paradise_limits"]["upload_max_mb"] == 4


@pytest.mark.contract
class TestEmailAktif:
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "host,smtp,harapan",
        # ENABLE_SMTP tidak ikut menentukan: benihnya "0", jadi host dari env
        # tetap harus mengirim. Yang mematikan email = host dikosongkan.
        [("smtp.uji.id", "1", True), ("smtp.uji.id", None, True), ("smtp.uji.id", "0", True), ("", "1", False)],
    )
    def test_hanya_host_yang_menentukan(self, monkeypatch, host, smtp, harapan):
        monkeypatch.delenv("EMAIL_HOST", raising=False)
        monkeypatch.delenv("ENABLE_SMTP", raising=False)
        InstanceConfiguration.objects.update_or_create(key="EMAIL_HOST", defaults={"value": host, "category": "SMTP"})
        if smtp is not None:
            InstanceConfiguration.objects.update_or_create(
                key="ENABLE_SMTP", defaults={"value": smtp, "category": "SMTP"}
            )
        assert email_aktif() is harapan


URL_PREF = "/api/users/me/notification-preferences/"


def _pref_get(user):
    request = APIRequestFactory().get(URL_PREF)
    force_authenticate(request, user=user)
    return UserNotificationPreferenceEndpoint.as_view()(request)


def _pref_patch(user, badan):
    request = APIRequestFactory().patch(URL_PREF, badan, format="json")
    force_authenticate(request, user=user)
    return UserNotificationPreferenceEndpoint.as_view()(request)


@pytest.fixture
def workspace(db):
    pemilik = _buat_user("pemilik")
    return Workspace.objects.create(name="WS", slug=f"ws-kunci-{uuid4().hex[:6]}", owner=pemilik)


def _orang(workspace, prefix, tingkat=None):
    user = _buat_user(prefix)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    if tingkat is not None:
        JabatanOrganisasi.objects.create(workspace=workspace, member=user, tingkat=tingkat)
    return user


@pytest.mark.contract
class TestLockedByAdmin:
    @pytest.mark.django_db
    def test_saklar_induk_mati_mengunci(self, workspace, monkeypatch):
        monkeypatch.delenv("ENABLE_DEADLINE_REMINDER", raising=False)
        monkeypatch.delenv("ENABLE_CHAT_EMAIL", raising=False)
        _simpan("ENABLE_DEADLINE_REMINDER", "0")
        _simpan("ENABLE_CHAT_EMAIL", "1")
        staf = _orang(workspace, "staf")
        res = _pref_get(staf)
        assert res.data["locked_by_admin"] == {"deadline_reminder": "instance_switch_off"}
        assert res.data["deadline_reminder"] is False

    @pytest.mark.django_db
    def test_menyalakan_yang_terkunci_diabaikan_pilihan_tetap(self, workspace):
        staf = _orang(workspace, "staf")
        _simpan("ENABLE_DEADLINE_REMINDER", "1")
        _pref_patch(staf, {"deadline_reminder": True})
        _simpan("ENABLE_DEADLINE_REMINDER", "0")

        res = _pref_patch(staf, {"deadline_reminder": True, "comment": True})
        assert res.status_code == status.HTTP_200_OK
        assert res.data["deadline_reminder"] is False
        assert res.data["comment"] is True
        assert res.data["locked_by_admin"]["deadline_reminder"] == "instance_switch_off"
        # Pilihan orangnya tidak dibuang: induk menyala lagi = berlaku lagi.
        assert UserNotificationPreference.objects.get(user=staf).deadline_reminder is True
        _simpan("ENABLE_DEADLINE_REMINDER", "1")
        assert _pref_get(staf).data["deadline_reminder"] is True

    @pytest.mark.django_db
    def test_menyalakan_terkunci_saat_ikut_bawaan_tidak_membekukan(self, workspace):
        staf = _orang(workspace, "staf")
        _simpan("ENABLE_DEADLINE_REMINDER", "0")
        res = _pref_patch(staf, {"deadline_reminder": True})
        assert res.data["ikut_bawaan_jabatan"] is True
        assert UserNotificationPreference.objects.get(user=staf).ikut_bawaan_jabatan is True

    @pytest.mark.django_db
    def test_batas_direktur(self, workspace):
        _simpan("ENABLE_DEADLINE_REMINDER", "1")
        _simpan("ENABLE_CHAT_EMAIL", "1")
        direktur = _orang(workspace, "dir", TINGKAT_DIREKTUR)
        terkunci = _pref_get(direktur).data["locked_by_admin"]
        assert terkunci["approval"] == "director_cap"
        assert "mention" not in terkunci
        assert set(terkunci.values()) == {"director_cap"}
