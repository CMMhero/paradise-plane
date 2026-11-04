# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: akun terhapus di Trash God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Hapus akun -> hilang dari daftar -> muncul di Trash -> pulihkan / buang.

Yang dijaga:
- akun terhapus tidak muncul di daftar member God Mode
- rujukannya tetap ada dan bertanda `is_deleted` ("Deleted account")
- pemulihan mengembalikan identitas asli dan HANYA keanggotaan yang aktif
  saat dihapus, tanpa Super Admin
- pemulihan ditolak (409) kalau emailnya sudah dipakai akun lain
- buang permanen memusnahkan identitas, baris User tetap ada
- Trashbin project tidak pernah bisa menjangkau akun
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.app.serializers import UserLiteSerializer
from plane.db.models import AkunTerhapus, User, Workspace, WorkspaceMember
from plane.license.api.views.member import InstanceMemberEndpoint
from plane.license.api.views.trash import InstanceTrashEndpoint
from plane.license.models import Instance, InstanceAdmin
from plane.utils.trash import ambil, kumpulkan

PERAN_MEMBER = 15


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email="owner@paradise.test", username="owner_paradise_test")
    return Workspace.objects.create(name="Paradise", slug="paradise", owner=pemilik)


@pytest.fixture
def admin(db):
    u = User.objects.create(email="admin@paradise.test", username="admin_paradise_test")
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id="uji-1",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    InstanceAdmin.objects.create(instance=instance, user=u, role=20, is_verified=True)
    return u


@pytest.fixture
def target(db, workspace):
    u = User.objects.create(
        email="budi@paradise.test",
        username="budi_paradise_test",
        display_name="Budi Santoso",
        first_name="Budi",
        last_name="Santoso",
    )
    WorkspaceMember.objects.create(workspace=workspace, member=u, role=PERAN_MEMBER)
    return u


def _panggil(view, method, admin, path, data=None, **kwargs):
    request = getattr(APIRequestFactory(), method)(path, data, format="json")
    force_authenticate(request, user=admin)
    return view.as_view()(request, **kwargs)


def _hapus(admin, user):
    return _panggil(
        InstanceMemberEndpoint, "delete", admin, f"/api/instances/members/{user.pk}/",
        {"konfirmasi": user.display_name}, pk=user.pk,
    )


def _pulihkan(admin, user):
    return _panggil(
        InstanceTrashEndpoint, "post", admin, f"/api/instances/trash/account/{user.pk}/",
        trash_type="account", pk=user.pk,
    )


def _buang(admin, user):
    return _panggil(
        InstanceTrashEndpoint, "delete", admin, f"/api/instances/trash/account/{user.pk}/",
        trash_type="account", pk=user.pk,
    )


@pytest.mark.django_db
def test_akun_terhapus_hilang_dari_daftar_member_dan_masuk_trash(admin, target):
    assert _hapus(admin, target).status_code == 200

    daftar = _panggil(InstanceMemberEndpoint, "get", admin, "/api/instances/members/")
    assert str(target.pk) not in [r["id"] for r in daftar.data["results"]]

    sampah = kumpulkan(tipe="account")
    assert [s["id"] for s in sampah] == [str(target.pk)]
    assert "budi@paradise.test" in sampah[0]["name"]
    assert sampah[0]["deleted_by"]["email"] == "admin@paradise.test"


@pytest.mark.django_db
def test_rujukan_akun_terhapus_bertanda_deleted(admin, target):
    _hapus(admin, target)
    target.refresh_from_db()

    data = UserLiteSerializer(target).data
    assert data["is_deleted"] is True
    assert data["display_name"] == "Deleted account"
    assert UserLiteSerializer(admin).data["is_deleted"] is False


@pytest.mark.django_db
def test_pulihkan_mengembalikan_identitas_dan_keanggotaan_tanpa_super_admin(admin, target, workspace):
    lama = WorkspaceMember.objects.create(
        workspace=Workspace.objects.create(name="Lama", slug="lama", owner=admin),
        member=target,
        role=PERAN_MEMBER,
        is_active=False,
    )
    InstanceAdmin.objects.create(instance=Instance.objects.first(), user=target, role=20, is_verified=True)
    _hapus(admin, target)

    res = _pulihkan(admin, target)

    assert res.status_code == 200, getattr(res, "data", None)
    target.refresh_from_db()
    assert target.email == "budi@paradise.test"
    assert target.display_name == "Budi Santoso"
    assert target.is_active is True
    assert WorkspaceMember.objects.get(workspace=workspace, member=target).is_active is True
    lama.refresh_from_db()
    assert lama.is_active is False, "keanggotaan yang sudah nonaktif sebelum dihapus tidak ikut hidup"
    assert not InstanceAdmin.objects.filter(user=target).exists()
    assert not AkunTerhapus.objects.filter(user=target).exists()


@pytest.mark.django_db
def test_pulihkan_ditolak_kalau_email_sudah_dipakai(admin, target):
    _hapus(admin, target)
    User.objects.create(email="budi@paradise.test", username="budi_baru")

    res = _pulihkan(admin, target)

    assert res.status_code == 409
    target.refresh_from_db()
    assert target.is_active is False
    assert AkunTerhapus.objects.filter(user=target).exists(), "potretnya tetap, bisa dicoba lagi"


@pytest.mark.django_db
def test_buang_permanen_memusnahkan_identitas_tapi_baris_user_tetap(admin, target):
    _hapus(admin, target)

    assert _buang(admin, target).status_code == 204

    assert User.objects.filter(pk=target.pk).exists()
    assert not AkunTerhapus.objects.filter(user=target).exists()
    assert kumpulkan(tipe="account") == []


@pytest.mark.django_db
def test_hapus_dua_kali_ditolak(admin, target):
    _hapus(admin, target)
    target.refresh_from_db()

    res = _hapus(admin, target)

    assert res.status_code in (400, 404)
    assert AkunTerhapus.objects.filter(user=target).count() == 1


@pytest.mark.django_db
def test_akun_terhapus_tidak_bisa_disunting(admin, target):
    _hapus(admin, target)

    res = _panggil(
        InstanceMemberEndpoint, "patch", admin, f"/api/instances/members/{target.pk}/",
        {"is_active": True}, pk=target.pk,
    )

    assert res.status_code == 404
    target.refresh_from_db()
    assert target.is_active is False


@pytest.mark.django_db
def test_trashbin_project_tidak_menjangkau_akun(admin, target):
    _hapus(admin, target)

    obj, _ = ambil("account", target.pk, project_id="00000000-0000-0000-0000-000000000000")

    assert obj is None


def _departemen(workspace):
    from plane.db.models import Departemen, Divisi

    divisi = Divisi.objects.create(workspace=workspace, kode="RND", nama="Research and Development")
    return Departemen.objects.create(
        workspace=workspace, divisi=divisi, kode="RND-RND", nama="Research and Development"
    )


def test_hapus_akun_mencabut_penempatan_dan_pulihkan_mengembalikannya(admin, target, workspace):
    from plane.db.models import JabatanOrganisasi, TINGKAT_MANAGER
    from plane.license.api.views.organisasi import pohon_organisasi

    dep = _departemen(workspace)
    JabatanOrganisasi.objects.create(workspace=workspace, member=target, departemen=dep, tingkat=TINGKAT_MANAGER)

    assert _hapus(admin, target).status_code == 200
    assert not JabatanOrganisasi.objects.filter(member=target).exists()
    anggota = pohon_organisasi(workspace)["divisi"][0]["departemen"][0]["anggota"]
    assert anggota == []

    assert _pulihkan(admin, target).status_code == 200
    assert JabatanOrganisasi.objects.filter(member=target, departemen=dep).exists()


def test_pohon_organisasi_tidak_menampilkan_akun_terhapus_lama(workspace):
    """Sisa dari sebelum 2.3.0: akun sudah digosok tapi barisnya masih hidup."""
    from plane.db.models import JabatanOrganisasi, TINGKAT_MANAGER, email_akun_terhapus
    from plane.license.api.views.organisasi import pohon_organisasi

    dep = _departemen(workspace)
    u = User.objects.create(email="x@paradise.test", username="x_paradise_test", is_active=False)
    User.objects.filter(pk=u.pk).update(email=email_akun_terhapus(u.id))
    JabatanOrganisasi.objects.create(workspace=workspace, member=u, departemen=dep, tingkat=TINGKAT_MANAGER)

    dep_data = pohon_organisasi(workspace)["divisi"][0]["departemen"][0]
    assert dep_data["anggota"] == []
    assert dep_data["jumlah_orang"] == 0
