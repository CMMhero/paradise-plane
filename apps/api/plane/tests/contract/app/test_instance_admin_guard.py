# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penjaga Super Admin di God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Dua penjaga yang lahir dari RCA God Mode 2026-10-14.

`DELETE /api/instances/admins/<pk>/` dulu tidak punya penjaga sama sekali,
padahal jalur yang dipakai halaman Member (`InstanceMemberEndpoint.patch` dengan
`is_super_admin: false`) punya dua. Terbukti langsung ke instance lokal: satu
panggilan `curl` mencabut Super Admin milik pemanggilnya sendiri dan membalas
204. Kalau dia satu-satunya Super Admin, God Mode terkunci permanen. Endpoint itu
memang tidak dipakai UI mana pun, jadi penjaganya tidak bisa diharapkan datang
dari tombol.

`configure_instance` dijaga PER KEY, bukan "ada salah satu kunci". Penjaga lama
berhenti pada baris pertama yang ketemu, jadi satu baris yang sudah ada
membatalkan pembuatan KETIGA sisanya. Di instance kantor `IS_GITEA_ENABLED` sudah
ada, dan `IS_GITHUB_ENABLED`, `IS_GOOGLE_ENABLED`, `IS_GITLAB_ENABLED` tidak
pernah lahir, akibatnya saklar Authentication di God Mode membalas 200 tanpa
menulis apa pun.
"""

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import User
from plane.license.api.views.admin import InstanceAdminEndpoint
from plane.license.models import Instance, InstanceConfiguration, InstanceAdmin

KUNCI_AUTH = ["IS_GOOGLE_ENABLED", "IS_GITHUB_ENABLED", "IS_GITLAB_ENABLED", "IS_GITEA_ENABLED"]


def _user(email):
    return User.objects.create(email=email, username=email.replace("@", "_").replace(".", "_"))


def _instance():
    return Instance.objects.create(
        instance_name="uji",
        instance_id="uji-penjaga",
        current_version="uji",
        last_checked_at=timezone.now(),
    )


def _hapus(aktor, pk):
    request = APIRequestFactory().delete(f"/api/instances/admins/{pk}/")
    force_authenticate(request, user=aktor)
    return InstanceAdminEndpoint.as_view()(request, pk=pk)


# --- DELETE /api/instances/admins/<pk>/ -------------------------------------


def test_tidak_bisa_mencabut_super_admin_sendiri(db):
    instance = _instance()
    aku = _user("aku@paradise.test")
    baris = InstanceAdmin.objects.create(instance=instance, user=aku, role=20)

    res = _hapus(aku, baris.pk)

    assert res.status_code == 400
    assert InstanceAdmin.objects.filter(pk=baris.pk).exists(), "baris sendiri tidak boleh terhapus"


def test_super_admin_terakhir_tidak_bisa_dicabut(db):
    instance = _instance()
    aku = _user("sendiri@paradise.test")
    baris = InstanceAdmin.objects.create(instance=instance, user=aku, role=20)

    res = _hapus(aku, baris.pk)

    assert res.status_code == 400
    assert InstanceAdmin.objects.filter(instance=instance).count() == 1


def test_mencabut_super_admin_LAIN_tetap_bisa(db):
    """Kontrol positif: penjaganya tidak boleh ikut mematikan fungsi yang sah."""
    instance = _instance()
    aku = _user("aku2@paradise.test")
    orang_lain = _user("lain@paradise.test")
    InstanceAdmin.objects.create(instance=instance, user=aku, role=20)
    baris_lain = InstanceAdmin.objects.create(instance=instance, user=orang_lain, role=20)

    res = _hapus(aku, baris_lain.pk)

    assert res.status_code == 204
    assert not InstanceAdmin.objects.filter(pk=baris_lain.pk).exists()
    assert InstanceAdmin.objects.filter(user=aku).exists(), "baris pemanggil tidak ikut hilang"


def test_pk_yang_tidak_ada_membalas_404_bukan_204(db):
    """204 untuk pk yang tidak ada berarti "berhasil" bagi pemanggilnya."""
    instance = _instance()
    aku = _user("aku3@paradise.test")
    InstanceAdmin.objects.create(instance=instance, user=aku, role=20)

    res = _hapus(aku, "00000000-0000-4000-8000-000000000000")

    assert res.status_code == 404
    assert InstanceAdmin.objects.filter(instance=instance).count() == 1


# --- configure_instance -----------------------------------------------------


@pytest.mark.django_db
def test_configure_instance_melengkapi_kunci_yang_belum_ada():
    """Satu kunci yang sudah ada tidak boleh membatalkan pembuatan kunci lain."""
    InstanceConfiguration.objects.create(key="IS_GITEA_ENABLED", value="1", category="AUTHENTICATION")

    call_command("configure_instance")

    hilang = [k for k in KUNCI_AUTH if not InstanceConfiguration.objects.filter(key=k).exists()]
    assert hilang == [], f"kunci ini tidak pernah dibuat: {hilang}"


@pytest.mark.django_db
def test_configure_instance_tidak_menimpa_nilai_yang_sudah_ada():
    """Idempoten: nilai yang sudah disetel admin lewat God Mode tidak boleh direset."""
    InstanceConfiguration.objects.create(key="IS_GITEA_ENABLED", value="1", category="AUTHENTICATION")
    InstanceConfiguration.objects.create(key="IS_GITHUB_ENABLED", value="1", category="AUTHENTICATION")

    call_command("configure_instance")
    call_command("configure_instance")

    assert InstanceConfiguration.objects.get(key="IS_GITEA_ENABLED").value == "1"
    assert InstanceConfiguration.objects.get(key="IS_GITHUB_ENABLED").value == "1"
