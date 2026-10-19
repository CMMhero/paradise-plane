# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: urutan daftar instance admin
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""`GET /api/instances/admins/`, urutannya harus tetap, bukan kebetulan.

Halaman General di God Mode menampilkan `instanceAdmins[0]` sebagai "Email"
instance (`apps/admin/app/(all)/(dashboard)/general/form.tsx`). Tanpa ORDER BY
eksplisit, Postgres bebas mengembalikan baris dalam urutan apa pun, dan urutan
itu bisa berubah sendiri sesudah UPDATE atau VACUUM, kolom itu lalu menampilkan
nama admin yang berbeda-beda tanpa ada yang mengubah apa pun.

Ketahuan 2026-08-07: sejak 11 orang IT ditambahkan sebagai instance admin,
kolom itu berhenti menampilkan admin pertama instance dan mulai menampilkan
orang acak. Tidak ada error, tidak ada yang rusak, cuma salah.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import User
from plane.license.api.views.admin import InstanceAdminEndpoint
from plane.license.models import Instance, InstanceAdmin


@pytest.fixture
def instance(db):
    return Instance.objects.create(
        instance_name="uji",
        instance_id="uji-urutan",
        current_version="uji",
        last_checked_at=timezone.now(),
    )


def _admin(instance, email, dibuat):
    """Buat instance admin lalu paksa created_at, auto_now_add mengabaikan nilai di create()."""
    u = User.objects.create(email=email, username=email.replace("@", "_").replace(".", "_"))
    a = InstanceAdmin.objects.create(instance=instance, user=u, role=20)
    InstanceAdmin.objects.filter(pk=a.pk).update(created_at=dibuat)
    return u


def test_admin_pertama_instance_selalu_di_urutan_pertama(instance):
    """Yang paling tua tetap [0] walau dibuat belakangan dan disisipkan di tengah."""
    awal = timezone.now() - timezone.timedelta(days=30)

    # Sengaja dibuat TIDAK berurutan: yang tertua justru disisipkan terakhir.
    _admin(instance, "menyusul1@paradise.test", awal + timezone.timedelta(days=20))
    _admin(instance, "menyusul2@paradise.test", awal + timezone.timedelta(days=25))
    pendiri = _admin(instance, "pendiri@paradise.test", awal)

    request = APIRequestFactory().get("/api/instances/admins/")
    force_authenticate(request, user=pendiri)
    response = InstanceAdminEndpoint.as_view()(request)

    assert response.status_code == 200
    assert len(response.data) == 3
    assert response.data[0]["user_detail"]["email"] == "pendiri@paradise.test"

    # Urutan penuh menaik, bukan cuma elemen pertama yang kebetulan benar.
    emails = [a["user_detail"]["email"] for a in response.data]
    assert emails == [
        "pendiri@paradise.test",
        "menyusul1@paradise.test",
        "menyusul2@paradise.test",
    ]
