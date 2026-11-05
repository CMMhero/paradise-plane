# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: filter, cari, dan urutan daftar God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Filter ala work item di God Mode: audit log dan riwayat masuk.

Halaman God Mode mengirim kondisi sebagai query string (`?actor=a,b`,
`?model_not=page`, `?date_from=`, `?sort=-actor`). Yang dijaga di sini: nilai
ganda dan negasi benar-benar menyaring, aktor `system` menangkap entri tanpa
aktor, dan urutan yang tidak dikenal tidak memecah endpoint.
"""

from datetime import timedelta

import pytest
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import Issue, LoginActivity, Project, User
from plane.license.api.views import InstanceAuditLogEndpoint, InstanceLoginHistoryEndpoint
from plane.license.models import Instance, InstanceAdmin


def _user(email, nama=""):
    return User.objects.create(
        email=email, username=email.replace("@", "_").replace(".", "_"), display_name=nama or email
    )


@pytest.fixture
def admin(db):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id="uji-filter-godmode",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    u = _user("admin@paradise.test", "Admin")
    InstanceAdmin.objects.create(instance=instance, user=u, role=20)
    return u


def _get(view, admin, params):
    req = APIRequestFactory().get("/", params)
    force_authenticate(req, user=admin)
    return view.as_view()(req)


def _log(model, aksi, aktor=None, repr_="obj", changes=None, ip=None, umur_hari=0):
    e = LogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(model),
        object_pk="1",
        object_repr=repr_,
        action=aksi,
        actor=aktor,
        changes=changes or {},
        remote_addr=ip,
    )
    if umur_hari:
        LogEntry.objects.filter(pk=e.pk).update(timestamp=timezone.now() - timedelta(days=umur_hari))
    return e


@pytest.mark.django_db
class TestAuditLogFilter:
    @pytest.fixture
    def entri(self, admin):
        budi = _user("budi@paradise.test", "Budi")
        return {
            "budi": budi,
            "a": _log(Issue, LogEntry.Action.UPDATE, budi, "Task A", {"state": ["x", "y"]}, "10.0.0.5"),
            "b": _log(Issue, LogEntry.Action.CREATE, admin, "Task B", {"name": [None, "B"]}, "10.0.0.6"),
            "c": _log(Project, LogEntry.Action.DELETE, None, "Proyek C", {}, None, umur_hari=10),
        }

    def _ids(self, admin, params):
        r = _get(InstanceAuditLogEndpoint, admin, params)
        assert r.status_code == 200
        return {e["object_repr"] for e in r.data["results"]}

    def test_aktor_ganda_dan_system(self, admin, entri):
        assert self._ids(admin, {"actor": f"{entri['budi'].id},system"}) == {"Task A", "Proyek C"}

    def test_aktor_negasi(self, admin, entri):
        assert self._ids(admin, {"actor_not": "system"}) == {"Task A", "Task B"}

    def test_model_dan_aksi_ganda(self, admin, entri):
        assert self._ids(admin, {"model": "issue", "action": "create,delete"}) == {"Task B"}
        assert self._ids(admin, {"model_not": "issue"}) == {"Proyek C"}

    def test_kolom_yang_berubah(self, admin, entri):
        assert self._ids(admin, {"field": "state"}) == {"Task A"}
        assert self._ids(admin, {"field_not": "state"}) == {"Task B", "Proyek C"}

    def test_ip_dan_tanggal(self, admin, entri):
        assert self._ids(admin, {"ip": "0.0.6"}) == {"Task B"}
        sejak = (timezone.now() - timedelta(days=2)).date().isoformat()
        assert self._ids(admin, {"date_from": sejak}) == {"Task A", "Task B"}

    def test_cari_nama_aktor(self, admin, entri):
        assert self._ids(admin, {"search": "budi"}) == {"Task A"}

    def test_urutan_dan_urutan_tak_dikenal(self, admin, entri):
        r = _get(InstanceAuditLogEndpoint, admin, {"sort": "object"})
        assert [e["object_repr"] for e in r.data["results"]] == ["Proyek C", "Task A", "Task B"]
        r = _get(InstanceAuditLogEndpoint, admin, {"sort": "lol; drop"})
        assert r.status_code == 200
        assert r.data["results"][0]["object_repr"] != "Proyek C"  # bawaan: terbaru dulu


@pytest.mark.django_db
class TestLoginHistoryFilter:
    @pytest.fixture
    def peristiwa(self, admin):
        budi = _user("budi@paradise.test", "Budi")
        sari = _user("sari@paradise.test", "Sari")
        LoginActivity.objects.create(user=budi, jenis="LOGIN", ip="10.0.0.1", medium="email", permukaan="web")
        LoginActivity.objects.create(user=budi, jenis="LOGOUT", ip="10.0.0.1", medium="", permukaan="web")
        LoginActivity.objects.create(user=sari, jenis="LOGIN", ip="192.168.1.9", medium="google", permukaan="admin")
        return {"budi": budi, "sari": sari}

    def _hasil(self, admin, params):
        r = _get(InstanceLoginHistoryEndpoint, admin, {"hari": 30, **params})
        assert r.status_code == 200
        return r.data

    def test_orang_ganda_dan_negasi(self, admin, peristiwa):
        assert self._hasil(admin, {"user_id": str(peristiwa["sari"].id)})["count"] == 1
        assert self._hasil(admin, {"user_id_not": str(peristiwa["sari"].id)})["count"] == 2

    def test_medium_kosong_lewat_none(self, admin, peristiwa):
        assert self._hasil(admin, {"medium": "none"})["count"] == 1
        assert self._hasil(admin, {"medium": "email,google"})["count"] == 2

    def test_permukaan_ip_cari(self, admin, peristiwa):
        assert self._hasil(admin, {"permukaan": "admin"})["count"] == 1
        assert self._hasil(admin, {"ip": "192.168"})["count"] == 1
        assert self._hasil(admin, {"search": "budi"})["count"] == 2

    def test_pilihan_ikut_respons(self, admin, peristiwa):
        pilihan = self._hasil(admin, {"jenis": "LOGOUT"})["pilihan"]
        # Opsi dihitung dari jendela waktu, bukan dari hasil yang sudah disaring.
        assert pilihan["permukaan"] == ["admin", "web"]
        assert pilihan["medium"] == ["", "email", "google"]

    def test_urutan_orang(self, admin, peristiwa):
        hasil = self._hasil(admin, {"sort": "-person"})["results"]
        assert hasil[0]["display_name"] == "Sari"


@pytest.mark.django_db
class TestAuditLabels:
    """Setiap baris audit punya jenis objek dan nama objek yang terbaca."""

    def _semua(self, admin):
        r = _get(InstanceAuditLogEndpoint, admin, {})
        assert r.status_code == 200
        return r.data["results"]

    def test_baris_lama_tanpa_nama_jatuh_ke_label_umum(self, admin):
        from plane.license.models import InstanceConfiguration

        # Bentuk baris lama: content type instanceconfiguration, object_repr kosong.
        _log(InstanceConfiguration, LogEntry.Action.UPDATE, admin, repr_="", changes={"value": ["0", "1"]})
        [e] = self._semua(admin)
        assert e["model_label"] == "Instance setting"
        assert e["object_label"] == "System setting"

    def test_baris_lama_membaca_kunci_dari_additional_data(self, admin):
        from plane.license.models import InstanceConfiguration

        entry = _log(InstanceConfiguration, LogEntry.Action.UPDATE, admin, repr_="")
        LogEntry.objects.filter(pk=entry.pk).update(additional_data={"key": "ENABLE_X"})
        [e] = self._semua(admin)
        assert e["object_label"] == "Instance setting: ENABLE_X"

    def test_model_terdaftar_memakai_verbose_name(self, admin):
        _log(Issue, LogEntry.Action.CREATE, admin, "Task A")
        [e] = self._semua(admin)
        assert e["model_label"] and e["object_label"] == "Task A"

    def test_catat_godmode_selalu_berlabel(self, admin):
        from plane.license.audit_godmode import JENIS_LABEL, catat_godmode

        req = APIRequestFactory().patch("/")
        force_authenticate(req, user=admin)
        req.user = admin
        for kind in JENIS_LABEL:
            catat_godmode(req, kind=kind, label="", changes={"a": ["1", "2"]})
        hasil = self._semua(admin)
        assert len(hasil) == len(JENIS_LABEL)
        for e in hasil:
            assert e["model_label"] in JENIS_LABEL.values()
            assert e["object_label"] == "System setting"
            assert e["actor"]["email"] == admin.email

    def test_patch_bawaan_member_dan_project_tercatat_berlabel(self, admin):
        from plane.license.api.views.bawaan_member import (
            InstanceMemberDefaultsEndpoint,
            InstanceProjectDefaultsEndpoint,
        )
        from plane.utils.bawaan_member import baca_bawaan

        req = APIRequestFactory().patch("/", {"profile": baca_bawaan()["profile"]}, format="json")
        force_authenticate(req, user=admin)
        assert InstanceMemberDefaultsEndpoint.as_view()(req).status_code == 200

        req = APIRequestFactory().patch("/", {}, format="json")
        force_authenticate(req, user=admin)
        InstanceProjectDefaultsEndpoint.as_view()(req)

        labels = {(e["model_label"], e["object_label"]) for e in self._semua(admin)}
        assert ("Member defaults", "Member defaults") in labels
