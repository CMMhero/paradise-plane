# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pengelolaan kanal obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siapa boleh mengelola kanal, dan apa yang terlihat sebelum bergabung.

Pengelola = pembuat kanal, admin workspace, atau Super Admin, dan harus anggota
kanalnya. Anggota biasa hanya melihat dan keluar.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.db.models import Langganan, Ruang, User, Workspace, WorkspaceMember
from plane.license.models import Instance
from plane.db.superadmin import angkat_super_admin


def _orang(nama):
    return User.objects.create(
        id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama, is_active=True
    )


@pytest.fixture
def kantor(db):
    """Workspace berisi pembuat kanal, anggota biasa, admin workspace, dan orang luar kanal."""
    pembuat = _orang("kelola-pembuat")
    workspace = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kelola-uji", owner=pembuat)
    biasa = _orang("kelola-biasa")
    admin = _orang("kelola-admin")
    luar = _orang("kelola-luar")
    for orang, peran in ((pembuat, 15), (biasa, 15), (admin, 20), (luar, 15)):
        WorkspaceMember.objects.create(workspace=workspace, member=orang, role=peran, is_active=True)
    return workspace, pembuat, biasa, admin, luar


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _kanal(kantor, tipe="kanal", nama="umum"):
    """Kanal dibuat lewat API supaya `created_by` terisi seperti di produksi."""
    workspace, pembuat, biasa, admin, _ = kantor
    r = _klien(pembuat).post(
        f"/api/workspaces/{workspace.slug}/chat/ruang/", {"nama": nama, "tipe": tipe}, format="json"
    )
    assert r.status_code == 201
    ruang = Ruang.objects.get(id=r.data["id"])
    Langganan.objects.create(ruang=ruang, user=biasa)
    Langganan.objects.create(ruang=ruang, user=admin)
    return ruang


def _url(workspace, ruang, akhir="kelola/"):
    return f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang.id}/{akhir}"


@pytest.mark.unit
def test_pratinjau_kanal_publik_untuk_bukan_anggota_tanpa_isi(kantor):
    workspace, _, _, _, luar = kantor
    ruang = _kanal(kantor)

    r = _klien(luar).get(_url(workspace, ruang))

    assert r.status_code == 200
    assert r.data["jumlah_anggota"] == 3
    assert r.data["ikut"] is False
    assert r.data["boleh_kelola"] is False
    # Pratinjau tidak membuka isi: hak baca tetap lewat berlangganan.
    assert _klien(luar).get(_url(workspace, ruang, "")).status_code == 404


@pytest.mark.unit
def test_kanal_privat_tidak_terlihat_dari_luar(kantor):
    workspace, _, _, _, luar = kantor
    ruang = _kanal(kantor, tipe="privat", nama="hrd")

    assert _klien(luar).get(_url(workspace, ruang)).status_code == 404
    assert _klien(luar).patch(_url(workspace, ruang), {"nama": "x"}, format="json").status_code == 404


@pytest.mark.unit
def test_boleh_kelola_pembuat_dan_admin_bukan_anggota_biasa(kantor):
    workspace, pembuat, biasa, admin, _ = kantor
    ruang = _kanal(kantor)

    assert _klien(pembuat).get(_url(workspace, ruang)).data["boleh_kelola"] is True
    assert _klien(admin).get(_url(workspace, ruang)).data["boleh_kelola"] is True
    assert _klien(biasa).get(_url(workspace, ruang)).data["boleh_kelola"] is False


@pytest.mark.unit
def test_ubah_nama_dan_topik(kantor):
    workspace, pembuat, biasa, _, _ = kantor
    ruang = _kanal(kantor)

    ditolak = _klien(biasa).patch(_url(workspace, ruang), {"nama": "baru"}, format="json")
    assert ditolak.status_code == 403

    r = _klien(pembuat).patch(_url(workspace, ruang), {"nama": "  Pemasaran ", "topik": "Kampanye Q4"}, format="json")
    assert r.status_code == 200
    ruang.refresh_from_db()
    assert ruang.nama == "Pemasaran"
    assert ruang.topik == "Kampanye Q4"


@pytest.mark.unit
def test_ubah_nama_menolak_kosong_dan_kembar(kantor):
    workspace, pembuat, _, _, _ = kantor
    ruang = _kanal(kantor)
    _kanal(kantor, nama="lain")
    client = _klien(pembuat)

    assert client.patch(_url(workspace, ruang), {"nama": "  "}, format="json").status_code == 400
    assert client.patch(_url(workspace, ruang), {"nama": "LAIN"}, format="json").status_code == 400
    # Nama sendiri (beda huruf besar) bukan kembar.
    assert client.patch(_url(workspace, ruang), {"nama": "Umum"}, format="json").status_code == 200


@pytest.mark.unit
def test_super_admin_anggota_boleh_kelola(kantor):
    workspace, _, _, _, luar = kantor
    ruang = _kanal(kantor)
    instance = Instance.objects.create(
        instance_name="uji", instance_id=f"uji-kelola-{uuid4().hex[:8]}", current_version="uji", last_checked_at=timezone.now()
    )
    angkat_super_admin(instance, luar)
    client = _klien(luar)

    # Super Admin pun harus bergabung dulu: bukan anggota = tidak mengelola.
    assert client.get(_url(workspace, ruang)).data["boleh_kelola"] is False
    Langganan.objects.create(ruang=ruang, user=luar)
    assert client.get(_url(workspace, ruang)).data["boleh_kelola"] is True


@pytest.mark.unit
def test_keluarkan_anggota(kantor):
    workspace, pembuat, biasa, admin, _ = kantor
    ruang = _kanal(kantor)

    # Anggota biasa tidak bisa mengeluarkan siapa pun.
    r = _klien(biasa).delete(_url(workspace, ruang, f"anggota/{admin.id}/"))
    assert r.status_code == 403

    # Mengeluarkan diri sendiri lewat sini ditolak; pakai keluar kanal.
    r = _klien(admin).delete(_url(workspace, ruang, f"anggota/{admin.id}/"))
    assert r.status_code == 400

    r = _klien(admin).delete(_url(workspace, ruang, f"anggota/{biasa.id}/"))
    assert r.status_code == 204
    assert not Langganan.objects.filter(ruang=ruang, user=biasa).exists()
    # Yang dikeluarkan langsung kehilangan hak baca.
    assert _klien(biasa).get(_url(workspace, ruang, "")).status_code == 404

    # Bisa bergabung lagi ke kanal publik (baris lama terhapus lunak, tidak bentrok).
    assert _klien(biasa).post(_url(workspace, ruang, "gabung/")).status_code == 201


@pytest.mark.unit
def test_hapus_kanal_hilang_dari_daftar_semua_anggota(kantor):
    workspace, pembuat, biasa, _, _ = kantor
    ruang = _kanal(kantor)

    assert _klien(biasa).delete(_url(workspace, ruang)).status_code == 403
    assert _klien(pembuat).delete(_url(workspace, ruang)).status_code == 204

    assert not Ruang.objects.filter(id=ruang.id).exists()
    daftar = _klien(biasa).get(f"/api/workspaces/{workspace.slug}/chat/").data
    assert all(baris["id"] != str(ruang.id) for baris in daftar)
    kanal = _klien(biasa).get(f"/api/workspaces/{workspace.slug}/chat/ruang/").data
    assert all(baris["id"] != str(ruang.id) for baris in kanal)


@pytest.mark.unit
def test_undang_ke_kanal_privat_hanya_pengelola(kantor):
    workspace, _, biasa, admin, luar = kantor
    ruang = _kanal(kantor, tipe="privat", nama="hrd")

    r = _klien(biasa).post(_url(workspace, ruang, "anggota/"), {"user": str(luar.id)}, format="json")
    assert r.status_code == 403
    r = _klien(admin).post(_url(workspace, ruang, "anggota/"), {"user": str(luar.id)}, format="json")
    assert r.status_code == 201


@pytest.mark.unit
def test_direktori_memuat_jumlah_anggota(kantor):
    workspace, _, _, _, luar = kantor
    ruang = _kanal(kantor)

    daftar = _klien(luar).get(f"/api/workspaces/{workspace.slug}/chat/ruang/").data
    baris = next(b for b in daftar if b["id"] == str(ruang.id))
    assert baris["jumlah_anggota"] == 3
    assert baris["ikut"] is False
