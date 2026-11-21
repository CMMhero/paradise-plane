# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes aturan God Mode area E (obrolan, wiki, quick link)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Setiap aturan area E: tanpa baris database perilakunya sama dengan sebelum
aturannya ada, dan satu baris `InstanceConfiguration` mengubah respons API.

Bawaan yang dijaga: staf boleh membuat kanal dan memakai @all, hanya admin
menulis di Announcements dan mengatur quick link bersama, Direktur mengelola
semua folder unit, anggota unit boleh mengunggah ke foldernya, tanpa batas
quick link pribadi, nama kanal 80, sebutan 20.
"""

import uuid
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    KUNCI_PENGUMUMAN,
    Departemen,
    Divisi,
    Langganan,
    PesanLangsung,
    Ruang,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WikiFolder,
    WorkspaceMember,
)
from plane.db.penempatan import setel_penempatan
from plane.license.models import InstanceConfiguration
from plane.utils import aturan
from plane.utils.aturan import area_obrolan as a
from plane.utils.kanal_organisasi import kunci_departemen, sinkronkan_kanal_organisasi
from plane.utils.kanal_sistem import ikutkan_ke_kanal_sistem, pastikan_kanal_sistem
from plane.utils.wiki_mandiri import pastikan_folder_unit

PDF = "application/pdf"


def _user(prefix, workspace, role=15):
    user = User.objects.create(
        email=f"{prefix}-{uuid.uuid4().hex[:8]}@uji.id", username=f"{prefix}-{uuid.uuid4().hex[:6]}"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


def _atur(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": aturan.ke_teks(aturan.REGISTRI[kunci], nilai), "category": "PARADISE"}
    )


@pytest.fixture(autouse=True)
def s3_palsu():
    with (
        mock.patch("plane.app.views.wiki_berkas.S3Storage") as kelas,
        mock.patch("plane.app.views.wiki_berkas.get_asset_object_metadata"),
    ):
        kelas.return_value.generate_presigned_post.return_value = {"url": "https://s3.uji/", "fields": {}}
        yield kelas


@pytest.fixture
def o(db, workspace, create_user):
    """Sales (T1) dengan staf, supervisor, manager, plus Direktur tanpa penempatan dan satu admin."""
    x = type("O", (), {})()
    x.ws = workspace
    x.slug = workspace.slug
    x.admin = create_user  # role 20 dari fixture `workspace`
    x.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    x.t1 = Departemen.objects.create(workspace=workspace, divisi=x.sales, kode="T1", nama="Team 1")
    x.staf = _user("staf", workspace)
    x.spv = _user("spv", workspace)
    x.mgr = _user("mgr", workspace)
    x.dir = _user("dir", workspace)
    setel_penempatan(workspace, x.staf, TINGKAT_MEMBER, [x.t1.id], [])
    setel_penempatan(workspace, x.spv, TINGKAT_SUPERVISOR, [x.t1.id], [])
    setel_penempatan(workspace, x.mgr, TINGKAT_MANAGER, [], [x.sales.id])
    setel_penempatan(workspace, x.dir, TINGKAT_DIREKTUR, [], [])
    return x


def _kanal(o, anggota, nama="umum"):
    ruang = Ruang.objects.create(workspace=o.ws, tipe=Ruang.Tipe.KANAL, nama=nama)
    Langganan.objects.bulk_create([Langganan(ruang=ruang, user=u) for u in anggota])
    return ruang


def _kirim(user, o, ruang, **isi):
    return _klien(user).post(f"/api/workspaces/{o.slug}/chat/ruang/{ruang.id}/", {"isi": "halo", **isi}, format="json")


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestPengumuman:
    def _ruang(self, o):
        ruang = pastikan_kanal_sistem(o.ws.id)[KUNCI_PENGUMUMAN]
        ikutkan_ke_kanal_sistem(o.ws.id)
        return ruang

    def test_bawaan_hanya_admin_yang_menulis(self, o):
        ruang = self._ruang(o)
        for u in (o.staf, o.spv, o.mgr, o.dir):
            assert _kirim(u, o, ruang).status_code == status.HTTP_403_FORBIDDEN
        with mock.patch("plane.app.views.chat.kirim_email_pengumuman"):
            assert _kirim(o.admin, o, ruang).status_code == status.HTTP_201_CREATED

    def test_jenjang_terpilih_ikut_boleh_menulis(self, o):
        ruang = self._ruang(o)
        _atur(a.CHAT_ANNOUNCE_POSTERS, a.MANAGER)
        with mock.patch("plane.app.views.chat.kirim_email_pengumuman"):
            assert _kirim(o.mgr, o, ruang).status_code == status.HTTP_201_CREATED
            assert _kirim(o.dir, o, ruang).status_code == status.HTTP_201_CREATED
        for u in (o.staf, o.spv):
            assert _kirim(u, o, ruang).status_code == status.HTTP_403_FORBIDDEN
        daftar = _klien(o.mgr).get(f"/api/workspaces/{o.slug}/chat/ruang/").json()
        pengumuman = next(r for r in daftar if r["kunci_sistem"] == KUNCI_PENGUMUMAN)
        assert pengumuman["boleh_kirim"] is True


@pytest.mark.contract
@pytest.mark.django_db
class TestBuatKanal:
    def _buat(self, user, o, nama="proyek"):
        return _klien(user).post(f"/api/workspaces/{o.slug}/chat/ruang/", {"nama": nama}, format="json")

    def test_bawaan_staf_boleh(self, o):
        assert self._buat(o.staf, o).status_code == status.HTTP_201_CREATED

    def test_jenjang_manager_menolak_di_bawahnya(self, o):
        _atur(a.CHAT_CHANNEL_CREATORS, a.MANAGER)
        for n, u in enumerate((o.staf, o.spv)):
            assert self._buat(u, o, f"x{n}").status_code == status.HTTP_403_FORBIDDEN
        for n, u in enumerate((o.mgr, o.dir, o.admin)):
            assert self._buat(u, o, f"y{n}").status_code == status.HTTP_201_CREATED

    def test_hanya_admin(self, o):
        _atur(a.CHAT_CHANNEL_CREATORS, a.ADMIN)
        assert self._buat(o.dir, o, "d").status_code == status.HTTP_403_FORBIDDEN
        assert self._buat(o.admin, o, "e").status_code == status.HTTP_201_CREATED


@pytest.mark.contract
@pytest.mark.django_db
class TestNamaKanal:
    def _buat(self, o, nama):
        return _klien(o.staf).post(f"/api/workspaces/{o.slug}/chat/ruang/", {"nama": nama}, format="json")

    def test_bawaan_80(self, o):
        assert self._buat(o, "a" * 80).status_code == status.HTTP_201_CREATED
        assert self._buat(o, "b" * 81).status_code == status.HTTP_400_BAD_REQUEST

    def test_batas_dari_god_mode_berlaku_untuk_buat_dan_ganti_nama(self, o):
        _atur(a.CHAT_CHANNEL_NAME_MAX, 30)
        assert self._buat(o, "a" * 31).status_code == status.HTTP_400_BAD_REQUEST
        res = self._buat(o, "a" * 30)
        assert res.status_code == status.HTTP_201_CREATED
        ganti = _klien(o.staf).patch(
            f"/api/workspaces/{o.slug}/chat/ruang/{res.json()['id']}/kelola/", {"nama": "c" * 31}, format="json"
        )
        assert ganti.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
@pytest.mark.django_db
class TestSebutan:
    def _anggota(self, o):
        return [o.staf, o.spv, o.mgr, o.dir]

    def test_bawaan_semua_orang_tersebut(self, o):
        ruang = _kanal(o, [o.admin, *self._anggota(o)])
        res = _kirim(o.admin, o, ruang, sebut=[str(u.id) for u in self._anggota(o)])
        assert res.status_code == status.HTTP_201_CREATED
        assert len(PesanLangsung.objects.get(id=res.json()["id"]).muatan["sebut"]) == 4

    def test_batas_sebutan_dari_god_mode(self, o):
        _atur(a.CHAT_MENTIONS_MAX, 2)
        ruang = _kanal(o, [o.admin, *self._anggota(o)])
        res = _kirim(o.admin, o, ruang, sebut=[str(u.id) for u in self._anggota(o)])
        assert res.status_code == status.HTTP_201_CREATED
        assert len(PesanLangsung.objects.get(id=res.json()["id"]).muatan["sebut"]) == 2

    def test_all_bawaan_staf_boleh(self, o):
        ruang = _kanal(o, [o.staf, o.mgr])
        res = _kirim(o.staf, o, ruang, semua=True)
        assert res.status_code == status.HTTP_201_CREATED
        assert PesanLangsung.objects.get(id=res.json()["id"]).muatan["semua"] is True

    def test_all_dibatasi_jenjang(self, o):
        _atur(a.CHAT_ALL_MENTION_WHO, a.MANAGER)
        ruang = _kanal(o, [o.staf, o.mgr, o.admin])
        assert _kirim(o.staf, o, ruang, semua=True).status_code == status.HTTP_403_FORBIDDEN
        assert _kirim(o.mgr, o, ruang, semua=True).status_code == status.HTTP_201_CREATED
        # Pesan biasa dari staf tetap lolos, dan DM tidak kena aturan @all.
        assert _kirim(o.staf, o, ruang).status_code == status.HTTP_201_CREATED
        dm = _klien(o.staf).post(
            f"/api/workspaces/{o.slug}/chat/{o.mgr.id}/", {"isi": "hai", "semua": True}, format="json"
        )
        assert dm.status_code == status.HTTP_201_CREATED


@pytest.mark.contract
@pytest.mark.django_db
class TestPanggilan:
    def _mulai(self, user, o, ruang):
        return _klien(user).post(
            f"/api/workspaces/{o.slug}/chat/ruang/{ruang.id}/panggilan-log/", {"peristiwa": "mulai"}, format="json"
        )

    def _token(self, user, o, ruang):
        return _klien(user).post(f"/api/workspaces/{o.slug}/chat/ruang/{ruang.id}/panggilan/")

    def test_bawaan_staf_boleh_memulai_dan_masuk(self, o):
        ruang = _kanal(o, [o.staf, o.mgr])
        assert self._mulai(o.staf, o, ruang).status_code != status.HTTP_403_FORBIDDEN
        assert self._token(o.staf, o, ruang).status_code != status.HTTP_403_FORBIDDEN

    def test_jenjang_manager_hanya_manager_memulai_tapi_semua_bisa_masuk(self, o):
        _atur(a.CHAT_CALLS_WHO, a.MANAGER)
        ruang = _kanal(o, [o.staf, o.mgr])
        assert self._token(o.staf, o, ruang).status_code == status.HTTP_403_FORBIDDEN
        assert self._mulai(o.staf, o, ruang).status_code == status.HTTP_403_FORBIDDEN
        assert self._mulai(o.mgr, o, ruang).status_code != status.HTTP_403_FORBIDDEN
        # Panggilan sudah berjalan: staf boleh masuk.
        assert self._token(o.staf, o, ruang).status_code != status.HTTP_403_FORBIDDEN

    def test_nobody_mematikan_panggilan_untuk_semua(self, o):
        _atur(a.CHAT_CALLS_WHO, a.TIDAK_ADA)
        ruang = _kanal(o, [o.admin, o.mgr])
        for u in (o.admin, o.mgr):
            assert self._mulai(u, o, ruang).status_code == status.HTTP_403_FORBIDDEN
            assert self._token(u, o, ruang).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
@pytest.mark.django_db
class TestPemimpinMasukKanalUnit:
    def _anggota(self, o):
        ruang = Ruang.objects.get(workspace=o.ws, kunci_sistem=kunci_departemen(o.t1.id))
        return set(Langganan.objects.filter(ruang=ruang).values_list("user_id", flat=True))

    def test_bawaan_direktur_tidak_ikut(self, o):
        sinkronkan_kanal_organisasi(o.ws.id)
        assert o.dir.id not in self._anggota(o)
        assert {o.staf.id, o.spv.id, o.mgr.id} <= self._anggota(o)

    def test_menyala_direktur_ikut_dan_mati_keluar_lagi(self, o):
        _atur(a.CHAT_LEADERS_JOIN_UNIT_CHANNELS, True)
        sinkronkan_kanal_organisasi(o.ws.id)
        assert o.dir.id in self._anggota(o)
        _atur(a.CHAT_LEADERS_JOIN_UNIT_CHANNELS, False)
        sinkronkan_kanal_organisasi(o.ws.id)
        assert o.dir.id not in self._anggota(o)


# --------------------------------------------------------------------------
# Wiki
# --------------------------------------------------------------------------


def _unggah(user, o, folder, nama="a.pdf"):
    return _klien(user).post(
        f"/api/workspaces/{o.slug}/wiki/folders/{folder.id}/materials/",
        {"name": nama, "type": PDF, "size": 10},
        format="json",
    )


def _subfolder(user, o, induk):
    return _klien(user).post(
        f"/api/workspaces/{o.slug}/wiki/folders/", {"nama": "Baru", "parent_id": str(induk.id)}, format="json"
    )


@pytest.fixture
def folder(o):
    pastikan_folder_unit(o.ws.id)
    o.f_sales = WikiFolder.objects.get(divisi=o.sales)
    o.f_t1 = WikiFolder.objects.get(departemen=o.t1)
    o.f_umum = WikiFolder(workspace=o.ws, nama="Umum", umum=True)
    o.f_umum.save(created_by_id=o.admin.id)
    return o


@pytest.mark.contract
@pytest.mark.django_db
class TestWiki:
    def test_bawaan_umum_semua_anggota_unit_hanya_penghuninya(self, folder):
        o = folder
        assert _unggah(o.staf, o, o.f_umum).status_code == status.HTTP_200_OK
        assert _unggah(o.staf, o, o.f_t1).status_code == status.HTTP_200_OK
        luar = _user("luar", o.ws)
        assert _unggah(luar, o, o.f_t1).status_code == status.HTTP_403_FORBIDDEN

    def test_unggah_umum_hanya_admin(self, folder):
        o = folder
        _atur(a.WIKI_GENERAL_UPLOAD, a.ADMIN)
        assert _unggah(o.staf, o, o.f_umum).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(o.mgr, o, o.f_umum).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(o.admin, o, o.f_umum).status_code == status.HTTP_200_OK
        # Folder unit tidak ikut berubah.
        assert _unggah(o.staf, o, o.f_t1).status_code == status.HTTP_200_OK

    def test_unggah_unit_hanya_pengelola(self, folder):
        o = folder
        _atur(a.WIKI_UNIT_UPLOAD, a.UNGGAH_PENGELOLA)
        assert _unggah(o.staf, o, o.f_t1).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(o.spv, o, o.f_t1).status_code == status.HTTP_200_OK
        assert _unggah(o.mgr, o, o.f_t1).status_code == status.HTTP_200_OK
        assert _unggah(o.admin, o, o.f_t1).status_code == status.HTTP_200_OK
        assert _unggah(o.staf, o, o.f_umum).status_code == status.HTTP_200_OK

    def test_bawaan_direktur_mengelola_semua_folder_unit(self, folder):
        o = folder
        assert _subfolder(o.dir, o, o.f_t1).status_code == status.HTTP_201_CREATED

    def test_direktur_dicabut_kuasanya(self, folder):
        o = folder
        _atur(a.WIKI_DIRECTORS_MANAGE_ALL, False)
        assert _subfolder(o.dir, o, o.f_t1).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(o.dir, o, o.f_t1).status_code == status.HTTP_403_FORBIDDEN
        # Manager divisi tetap mengelola wilayahnya sendiri.
        assert _subfolder(o.mgr, o, o.f_t1).status_code == status.HTTP_201_CREATED

    def test_bawaan_admin_workspace_adalah_admin_wiki(self, folder):
        o = folder
        res = _klien(o.admin).post(f"/api/workspaces/{o.slug}/wiki/folders/", {"nama": "Teratas"}, format="json")
        assert res.status_code == status.HTTP_201_CREATED

    def test_admin_wiki_hanya_super_admin(self, folder):
        o = folder
        _atur(a.WIKI_ADMIN_WHO, a.WIKI_ADMIN_SUPER)
        res = _klien(o.admin).post(f"/api/workspaces/{o.slug}/wiki/folders/", {"nama": "Teratas"}, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN


# --------------------------------------------------------------------------
# Quick link
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestQuickLinkBersama:
    def _tambah(self, user, o):
        return _klien(user).post(
            f"/api/workspaces/{o.slug}/quick-links/shared/", {"url": "https://contoh.id"}, format="json"
        )

    def test_bawaan_hanya_admin(self, o):
        for u in (o.staf, o.spv, o.mgr, o.dir):
            assert self._tambah(u, o).status_code == status.HTTP_403_FORBIDDEN
        assert self._tambah(o.admin, o).status_code == status.HTTP_201_CREATED

    def test_jenjang_manager_ikut_mengatur(self, o):
        _atur(a.QUICK_LINK_SHARED_MANAGERS, a.MANAGER)
        assert self._tambah(o.spv, o).status_code == status.HTTP_403_FORBIDDEN
        assert self._tambah(o.mgr, o).status_code == status.HTTP_201_CREATED
        lihat = _klien(o.mgr).get(f"/api/workspaces/{o.slug}/quick-links/shared/").json()
        assert lihat["boleh_kelola"] is True
        assert _klien(o.spv).get(f"/api/workspaces/{o.slug}/quick-links/shared/").json()["boleh_kelola"] is False


@pytest.mark.contract
@pytest.mark.django_db
class TestQuickLinkPribadi:
    def _tambah(self, user, o, n):
        return _klien(user).post(f"/api/workspaces/{o.slug}/quick-links/", {"url": f"https://c{n}.id"}, format="json")

    def test_bawaan_tanpa_batas(self, o):
        for n in range(5):
            assert self._tambah(o.staf, o, n).status_code == status.HTTP_201_CREATED

    def test_batas_per_orang(self, o):
        _atur(a.QUICK_LINK_PERSONAL_MAX, 2)
        assert self._tambah(o.staf, o, 0).status_code == status.HTTP_201_CREATED
        assert self._tambah(o.staf, o, 1).status_code == status.HTTP_201_CREATED
        assert self._tambah(o.staf, o, 2).status_code == status.HTTP_400_BAD_REQUEST
        # Batas per orang: orang lain masih punya jatah.
        assert self._tambah(o.spv, o, 0).status_code == status.HTTP_201_CREATED
