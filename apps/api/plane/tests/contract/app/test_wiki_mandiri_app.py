# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes kontrak Wiki mandiri (KEP-94)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kontrak API Wiki yang sudah lepas dari project (`/api/workspaces/<slug>/wiki/`).

Yang dikunci:

- baca = anggota workspace; bukan anggota 403;
- unggah: staf di folder departemennya dan topik di bawahnya, tidak di departemen
  lain; manager di semua departemen divisinya; direktur di mana saja; folder
  General untuk semua anggota;
- struktur folder tingkat atas hanya admin (pengelola divisi/departemen di
  `test_wiki_pengelola_app.py`, KEP-95), dan folder unit tidak
  bisa diganti nama, diarsipkan, atau dihapus lewat Wiki;
- ubah/hapus materi: pengunggah atau admin, orang lain 403;
- tong sampah + pulihkan, berkas 302, dan `pastikan_folder_unit`.
"""

import uuid
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.app.views.wiki_berkas import jenis_pratinjau
from plane.db.models import (
    Departemen,
    Divisi,
    FileAsset,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WikiFolder,
    WikiMaterial,
    WorkspaceMember,
)
from plane.db.penempatan import setel_penempatan
from plane.utils.wiki_mandiri import pastikan_folder_unit

S3 = "plane.app.views.wiki_berkas.S3Storage"
PDF = "application/pdf"


def _user(prefix, workspace, role=15):
    user = User.objects.create(
        email=f"{prefix}-{uuid.uuid4().hex[:8]}@uji.id", username=f"{prefix}-{uuid.uuid4().hex[:6]}"
    )
    if role:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture(autouse=True)
def s3_palsu():
    with mock.patch(S3) as kelas, mock.patch("plane.app.views.wiki_berkas.get_asset_object_metadata"):
        kelas.return_value.generate_presigned_post.return_value = {"url": "https://s3.uji/", "fields": {}}
        kelas.return_value.generate_presigned_url.return_value = "https://s3.uji/berkas"
        yield kelas


@pytest.fixture
def wiki(db, workspace, create_user):
    w = type("Wiki", (), {})()
    w.ws = workspace
    w.base = f"/api/workspaces/{workspace.slug}/wiki/"
    w.admin = create_user
    w.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    w.hrga = Divisi.objects.create(workspace=workspace, kode="HRGA", nama="HRGA")
    w.t1 = Departemen.objects.create(workspace=workspace, divisi=w.sales, kode="T1", nama="Team 1")
    w.t2 = Departemen.objects.create(workspace=workspace, divisi=w.sales, kode="T2", nama="Team 2")
    w.hr = Departemen.objects.create(workspace=workspace, divisi=w.hrga, kode="HR", nama="Human Resources")
    pastikan_folder_unit(workspace.id)

    w.staf1 = _user("staf1", workspace)
    w.staf2 = _user("staf2", workspace)
    w.spv = _user("spv", workspace)
    w.manager = _user("mgr", workspace)
    w.direktur = _user("dir", workspace)
    w.biasa = _user("biasa", workspace)
    w.asing = _user("asing", workspace, role=None)
    setel_penempatan(workspace, w.staf1, TINGKAT_MEMBER, [w.t1.id], [])
    setel_penempatan(workspace, w.staf2, TINGKAT_MEMBER, [w.t2.id], [])
    setel_penempatan(workspace, w.spv, TINGKAT_SUPERVISOR, [w.t1.id], [])
    setel_penempatan(workspace, w.manager, TINGKAT_MANAGER, [], [w.sales.id])
    setel_penempatan(workspace, w.direktur, TINGKAT_DIREKTUR, [], [])

    w.f_sales = WikiFolder.objects.get(divisi=w.sales)
    w.f_hrga = WikiFolder.objects.get(divisi=w.hrga)
    w.f_t1 = WikiFolder.objects.get(departemen=w.t1)
    w.f_t2 = WikiFolder.objects.get(departemen=w.t2)
    w.f_hr = WikiFolder.objects.get(departemen=w.hr)
    w.umum = WikiFolder(workspace=workspace, nama="General", umum=True)
    w.umum.save(created_by_id=w.admin.id)
    w.topik = WikiFolder(workspace=workspace, nama="SOP", parent=w.f_t1)
    w.topik.save(created_by_id=w.admin.id)
    return w


def _unggah(klien, wiki, folder, nama="panduan.pdf", tipe=PDF, ukuran=2048, selesai=True):
    res = klien.post(
        f"{wiki.base}folders/{folder.id}/materials/", {"name": nama, "type": tipe, "size": ukuran}, format="json"
    )
    if res.status_code == status.HTTP_200_OK and selesai:
        konfirmasi = klien.post(f"{wiki.base}materials/{res.data['material']['id']}/uploaded/")
        assert konfirmasi.status_code == status.HTTP_204_NO_CONTENT
    return res


def _materi(wiki, folder, pengunggah, nama="panduan.pdf"):
    res = _unggah(_klien(pengunggah), wiki, folder, nama=nama)
    assert res.status_code == status.HTTP_200_OK, res.data
    return WikiMaterial.objects.get(id=res.data["material"]["id"])


@pytest.mark.contract
@pytest.mark.django_db
class TestBaca:
    def test_anggota_membaca_pohon(self, wiki):
        res = _klien(wiki.biasa).get(wiki.base)
        assert res.status_code == status.HTTP_200_OK
        assert res.data["is_admin"] is False
        ids = {f["id"] for f in res.data["folders"]}
        assert {str(wiki.f_sales.id), str(wiki.f_t1.id), str(wiki.topik.id), str(wiki.umum.id)} <= ids
        t1 = next(f for f in res.data["folders"] if f["id"] == str(wiki.f_t1.id))
        assert t1["parent_id"] == str(wiki.f_sales.id)
        assert t1["departemen_id"] == str(wiki.t1.id)
        assert t1["can_manage"] is False

    def test_bukan_anggota_ditolak(self, wiki):
        assert _klien(wiki.asing).get(wiki.base).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(wiki.asing).get(f"{wiki.base}search/?q=ab").status_code == status.HTTP_403_FORBIDDEN

    def test_anonim_ditolak(self, wiki):
        assert APIClient().get(wiki.base).status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_jumlah_materi_dan_bendera_unggah(self, wiki):
        _materi(wiki, wiki.f_t1, wiki.staf1)
        res = _klien(wiki.staf1).get(wiki.base)
        peta = {f["id"]: f for f in res.data["folders"]}
        assert peta[str(wiki.f_t1.id)]["jumlah_materi"] == 1
        assert peta[str(wiki.f_t1.id)]["can_upload"] is True
        assert peta[str(wiki.f_t2.id)]["can_upload"] is False
        assert peta[str(wiki.umum.id)]["can_upload"] is True

    def test_materi_belum_terunggah_tidak_dihitung_dan_tidak_tampil(self, wiki):
        res = _unggah(_klien(wiki.staf1), wiki, wiki.f_t1, selesai=False)
        assert res.status_code == status.HTTP_200_OK
        daftar = _klien(wiki.biasa).get(f"{wiki.base}folders/{wiki.f_t1.id}/materials/")
        assert daftar.data["materials"] == []
        mid = res.data["material"]["id"]
        assert _klien(wiki.biasa).get(f"{wiki.base}materials/{mid}/").status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.contract
@pytest.mark.django_db
class TestUnggah:
    def test_staf_ke_folder_departemennya_dan_topik_di_bawahnya(self, wiki):
        assert _unggah(_klien(wiki.staf1), wiki, wiki.f_t1).status_code == status.HTTP_200_OK
        res = _unggah(_klien(wiki.staf1), wiki, wiki.topik, nama="sop.pdf")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["upload_data"]["url"] == "https://s3.uji/"
        berkas = FileAsset.objects.get(id=res.data["material"]["id"])
        assert berkas.project_id is None and berkas.page_id is None
        assert berkas.entity_identifier == str(wiki.topik.id)
        assert berkas.created_by_id == wiki.staf1.id
        assert res.data["material"]["url"] == f"/api/workspaces/{wiki.ws.slug}/wiki/files/{berkas.id}/"

    def test_staf_tidak_boleh_ke_departemen_lain(self, wiki):
        for folder in (wiki.f_t2, wiki.f_hr, wiki.f_hrga):
            assert _unggah(_klien(wiki.staf1), wiki, folder).status_code == status.HTTP_403_FORBIDDEN
        # topik di bawah departemen lain
        topik_t2 = WikiFolder(workspace=wiki.ws, nama="Template", parent=wiki.f_t2)
        topik_t2.save(created_by_id=wiki.admin.id)
        assert _unggah(_klien(wiki.staf1), wiki, topik_t2).status_code == status.HTTP_403_FORBIDDEN

    def test_staf_boleh_ke_folder_divisinya_sendiri(self, wiki):
        # Aturan PenilaiWiki: divisi yang disentuh departemennya ikut terjangkau.
        assert _unggah(_klien(wiki.staf1), wiki, wiki.f_sales).status_code == status.HTTP_200_OK

    def test_manager_ke_semua_departemen_divisinya_bukan_divisi_lain(self, wiki):
        for folder in (wiki.f_sales, wiki.f_t1, wiki.f_t2, wiki.topik):
            assert _unggah(_klien(wiki.manager), wiki, folder).status_code == status.HTTP_200_OK
        assert _unggah(_klien(wiki.manager), wiki, wiki.f_hr).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(_klien(wiki.manager), wiki, wiki.f_hrga).status_code == status.HTTP_403_FORBIDDEN

    def test_direktur_di_mana_saja(self, wiki):
        for folder in (wiki.f_sales, wiki.f_hr, wiki.f_t2, wiki.topik):
            assert _unggah(_klien(wiki.direktur), wiki, folder).status_code == status.HTTP_200_OK

    def test_folder_general_untuk_semua_anggota(self, wiki):
        assert _unggah(_klien(wiki.biasa), wiki, wiki.umum).status_code == status.HTTP_200_OK
        assert _unggah(_klien(wiki.biasa), wiki, wiki.f_t1).status_code == status.HTTP_403_FORBIDDEN

    def test_admin_di_mana_saja(self, wiki):
        assert _unggah(_klien(wiki.admin), wiki, wiki.f_hr).status_code == status.HTTP_200_OK

    def test_folder_diarsipkan_menolak_unggahan(self, wiki):
        _klien(wiki.admin).post(f"{wiki.base}folders/{wiki.topik.id}/archive/")
        assert _unggah(_klien(wiki.staf1), wiki, wiki.topik).status_code == status.HTTP_400_BAD_REQUEST

    def test_tipe_berkas_tidak_valid_ditolak(self, wiki):
        res = _unggah(_klien(wiki.staf1), wiki, wiki.f_t1, nama="x.exe", tipe="application/x-msdownload")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in res.data

    def test_unggah_wiki_lewat_endpoint_project_ditolak(self, wiki):
        res = _klien(wiki.admin).post(
            f"/api/assets/v2/workspaces/{wiki.ws.slug}/projects/{uuid.uuid4()}/",
            {
                "name": "x.pdf",
                "type": PDF,
                "size": 10,
                "entity_type": "WIKI_MATERIAL",
                "entity_identifier": str(wiki.f_t1.id),
            },
            format="json",
        )
        # 400 dari kita; 403/404 hanya kalau gerbang project menolak lebih dulu.
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)
        assert not FileAsset.objects.filter(entity_type="WIKI_MATERIAL").exists()

    def test_hanya_pengunggah_yang_mengonfirmasi(self, wiki):
        res = _unggah(_klien(wiki.staf1), wiki, wiki.f_t1, selesai=False)
        mid = res.data["material"]["id"]
        assert _klien(wiki.admin).post(f"{wiki.base}materials/{mid}/uploaded/").status_code == status.HTTP_403_FORBIDDEN
        assert (
            _klien(wiki.staf1).post(f"{wiki.base}materials/{mid}/uploaded/").status_code == status.HTTP_204_NO_CONTENT
        )
        assert FileAsset.objects.get(id=mid).is_uploaded is True


@pytest.mark.contract
@pytest.mark.django_db
class TestStrukturFolder:
    def test_hanya_admin_membuat_folder(self, wiki):
        for u in (wiki.biasa, wiki.manager, wiki.direktur):
            res = _klien(u).post(f"{wiki.base}folders/", {"nama": "Liar"}, format="json")
            assert res.status_code == status.HTTP_403_FORBIDDEN
        res = _klien(wiki.admin).post(
            f"{wiki.base}folders/",
            {"nama": "Topik baru", "parent_id": str(wiki.f_t1.id), "keterangan": "k"},
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["parent_id"] == str(wiki.f_t1.id)
        assert res.data["created_by"] == str(wiki.admin.id)
        assert res.data["can_manage"] is True

    def test_sub_topik_tidak_bisa_bersarang(self, wiki):
        # `wiki.topik` (SOP) sudah sub-topik di bawah departemen: tidak boleh punya anak.
        res = _klien(wiki.admin).post(
            f"{wiki.base}folders/", {"nama": "Terlalu dalam", "parent_id": str(wiki.topik.id)}, format="json"
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "sub-topic" in res.data["error"]
        # Departemen, divisi, dan folder tingkat atas tetap boleh punya sub-topik.
        for induk in (wiki.f_t1, wiki.f_sales, wiki.umum):
            ok = _klien(wiki.admin).post(
                f"{wiki.base}folders/", {"nama": "Sub", "parent_id": str(induk.id)}, format="json"
            )
            assert ok.status_code == status.HTTP_201_CREATED, induk.nama

    def test_umum_hanya_tanpa_induk(self, wiki):
        ok = _klien(wiki.admin).post(f"{wiki.base}folders/", {"nama": "Umum 2", "umum": True}, format="json")
        assert ok.status_code == status.HTTP_201_CREATED and ok.data["umum"] is True
        salah = _klien(wiki.admin).post(
            f"{wiki.base}folders/", {"nama": "X", "umum": True, "parent_id": str(wiki.f_t1.id)}, format="json"
        )
        assert salah.status_code == status.HTTP_400_BAD_REQUEST

    def test_nama_kosong_atau_induk_hilang(self, wiki):
        assert _klien(wiki.admin).post(f"{wiki.base}folders/", {"nama": "  "}, format="json").status_code == 400
        res = _klien(wiki.admin).post(
            f"{wiki.base}folders/", {"nama": "X", "parent_id": str(uuid.uuid4())}, format="json"
        )
        assert res.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_folder_biasa_oleh_admin(self, wiki):
        res = _klien(wiki.admin).patch(
            f"{wiki.base}folders/{wiki.topik.id}/",
            {"nama": "SOP Baru", "keterangan": "ket", "logo_props": {"a": 1}, "urutan": 5},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK
        assert (res.data["nama"], res.data["keterangan"], res.data["urutan"]) == ("SOP Baru", "ket", 5.0)
        # Staf tidak mengelola; manager divisi Sales sekarang boleh (KEP-95, lihat test_wiki_pengelola_app).
        assert (
            _klien(wiki.staf2).patch(f"{wiki.base}folders/{wiki.topik.id}/", {"nama": "x"}, format="json").status_code
            == 403
        )

    def test_ganti_nama_folder_unit_ditolak(self, wiki):
        res = _klien(wiki.admin).patch(f"{wiki.base}folders/{wiki.f_t1.id}/", {"nama": "Lain"}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.data["error"] == "This folder follows its division or department name. Rename it in God Mode."
        # bagian lain folder unit boleh diubah
        ok = _klien(wiki.admin).patch(f"{wiki.base}folders/{wiki.f_t1.id}/", {"keterangan": "ket"}, format="json")
        assert ok.status_code == status.HTTP_200_OK

    def test_umum_tidak_boleh_untuk_folder_beranak_induk(self, wiki):
        res = _klien(wiki.admin).patch(f"{wiki.base}folders/{wiki.topik.id}/", {"umum": True}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_folder_unit_tidak_bisa_diarsip_atau_dihapus(self, wiki):
        assert _klien(wiki.admin).post(f"{wiki.base}folders/{wiki.f_t1.id}/archive/").status_code == 400
        assert _klien(wiki.admin).delete(f"{wiki.base}folders/{wiki.f_sales.id}/").status_code == 400

    def test_arsip_menyeret_keturunan_dan_buka_arsip_hanya_yang_sama_capnya(self, wiki):
        anak = WikiFolder(workspace=wiki.ws, nama="Anak", parent=wiki.topik)
        anak.save(created_by_id=wiki.admin.id)
        lama = WikiFolder(workspace=wiki.ws, nama="Lama", parent=wiki.topik)
        lama.save(created_by_id=wiki.admin.id)
        assert _klien(wiki.admin).post(f"{wiki.base}folders/{lama.id}/archive/").status_code == 200
        lama.refresh_from_db()
        cap_lama = lama.archived_at

        res = _klien(wiki.admin).post(f"{wiki.base}folders/{wiki.topik.id}/archive/")
        assert res.status_code == status.HTTP_200_OK
        for f in (wiki.topik, anak, lama):
            f.refresh_from_db()
        assert wiki.topik.archived_at is not None and anak.archived_at == wiki.topik.archived_at
        assert lama.archived_at == cap_lama

        # anak tidak bisa dibuka arsipnya selama induknya terarsip
        assert _klien(wiki.admin).delete(f"{wiki.base}folders/{anak.id}/archive/").status_code == 400
        assert _klien(wiki.admin).delete(f"{wiki.base}folders/{wiki.topik.id}/archive/").status_code == 200
        for f in (wiki.topik, anak, lama):
            f.refresh_from_db()
        assert wiki.topik.archived_at is None and anak.archived_at is None
        assert lama.archived_at == cap_lama

    def test_hapus_folder_harus_diarsip_dan_kosong(self, wiki):
        url = f"{wiki.base}folders/{wiki.topik.id}/"
        assert _klien(wiki.admin).delete(url).status_code == 400  # belum diarsip
        _materi(wiki, wiki.topik, wiki.staf1)
        _klien(wiki.admin).post(f"{url}archive/")
        assert _klien(wiki.admin).delete(url).status_code == status.HTTP_409_CONFLICT  # ada materi
        anak = WikiFolder(workspace=wiki.ws, nama="Anak", parent=wiki.topik)
        anak.save(created_by_id=wiki.admin.id)
        assert _klien(wiki.biasa).delete(url).status_code == 403

    def test_hapus_folder_kosong_masuk_sampah_dan_bisa_dipulihkan(self, wiki):
        kosong = WikiFolder(workspace=wiki.ws, nama="Kosong")
        kosong.save(created_by_id=wiki.admin.id)
        url = f"{wiki.base}folders/{kosong.id}/"
        _klien(wiki.admin).post(f"{url}archive/")
        assert _klien(wiki.admin).delete(url).status_code == status.HTTP_204_NO_CONTENT
        assert not WikiFolder.objects.filter(id=kosong.id).exists()
        assert _klien(wiki.admin).get(f"{wiki.base}folders/{kosong.id}/materials/").status_code == 404

        sampah = _klien(wiki.admin).get(f"{wiki.base}trash/")
        assert [f["id"] for f in sampah.data["folders"]] == [str(kosong.id)]
        assert sampah.data["folders"][0]["deleted_at"] is not None
        assert _klien(wiki.biasa).get(f"{wiki.base}trash/").data["folders"] == []
        assert _klien(wiki.biasa).post(f"{wiki.base}trash/folders/{kosong.id}/restore/").status_code == 403

        assert _klien(wiki.admin).post(f"{wiki.base}trash/folders/{kosong.id}/restore/").status_code == 200
        assert WikiFolder.objects.filter(id=kosong.id).exists()

    def test_pulihkan_folder_dengan_induk_terhapus_ditolak(self, wiki):
        induk = WikiFolder(workspace=wiki.ws, nama="Induk")
        induk.save(created_by_id=wiki.admin.id)
        anak = WikiFolder(workspace=wiki.ws, nama="Anak", parent=induk)
        anak.save(created_by_id=wiki.admin.id)
        WikiFolder.objects.filter(id__in=[induk.id, anak.id]).update(deleted_at="2026-11-01T00:00:00Z")
        res = _klien(wiki.admin).post(f"{wiki.base}trash/folders/{anak.id}/restore/")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
@pytest.mark.django_db
class TestMateri:
    def test_daftar_dan_detail_dengan_jejak(self, wiki):
        materi = _materi(wiki, wiki.topik, wiki.staf1)
        daftar = _klien(wiki.biasa).get(f"{wiki.base}folders/{wiki.topik.id}/materials/")
        assert daftar.status_code == status.HTTP_200_OK
        assert daftar.data["can_upload"] is False
        item = daftar.data["materials"][0]
        assert item["id"] == str(materi.id) and item["name"] == "panduan.pdf" and item["type"] == PDF
        assert item["has_preview"] is False

        detail = _klien(wiki.biasa).get(f"{wiki.base}materials/{materi.id}/")
        assert [j["nama"] for j in detail.data["jejak"]] == ["Sales", "Team 1", "SOP"]

    def test_ubah_judul_oleh_pengunggah_admin_bukan_orang_lain(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        url = f"{wiki.base}materials/{materi.id}/"
        res = _klien(wiki.staf1).patch(url, {"judul": "  Judul baru  "}, format="json")
        assert res.status_code == status.HTTP_200_OK and res.data["judul"] == "Judul baru"
        assert res.data["name"] == "panduan.pdf"
        assert _klien(wiki.admin).patch(url, {"judul": "Admin"}, format="json").status_code == 200
        assert (
            _klien(wiki.staf2).patch(url, {"judul": "Curang"}, format="json").status_code == status.HTTP_403_FORBIDDEN
        )
        assert _klien(wiki.staf1).patch(url, {"judul": " "}, format="json").status_code == 400
        assert _klien(wiki.staf1).patch(url, {"judul": "x" * 256}, format="json").status_code == 400

    def test_pindah_ke_sub_topik_oleh_pengunggah(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        url = f"{wiki.base}materials/{materi.id}/"
        res = _klien(wiki.staf1).patch(url, {"folder_id": str(wiki.topik.id)}, format="json")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["folder_id"] == str(wiki.topik.id)
        materi.refresh_from_db()
        assert materi.folder_id == wiki.topik.id
        assert materi.judul == "panduan.pdf"
        assert FileAsset.objects.get(id=materi.berkas_id).entity_identifier == str(wiki.topik.id)

    def test_pindah_ke_folder_yang_tak_boleh_diunggah_ditolak(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        res = _klien(wiki.staf1).patch(
            f"{wiki.base}materials/{materi.id}/", {"folder_id": str(wiki.f_t2.id)}, format="json"
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN
        materi.refresh_from_db()
        assert materi.folder_id == wiki.f_t1.id

    def test_pindah_materi_orang_lain_ditolak(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        res = _klien(wiki.staf2).patch(
            f"{wiki.base}materials/{materi.id}/", {"folder_id": str(wiki.topik.id)}, format="json"
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_pindah_ke_folder_sendiri_tak_mengubah_apa_apa(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        res = _klien(wiki.staf1).patch(
            f"{wiki.base}materials/{materi.id}/", {"folder_id": str(wiki.f_t1.id)}, format="json"
        )
        assert res.status_code == status.HTTP_200_OK and res.data["folder_id"] == str(wiki.f_t1.id)

    def test_hapus_oleh_pengunggah_dan_orang_lain_ditolak(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        url = f"{wiki.base}materials/{materi.id}/"
        assert _klien(wiki.staf2).delete(url).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(wiki.biasa).delete(url).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(wiki.staf1).delete(url).status_code == status.HTTP_204_NO_CONTENT
        assert not WikiMaterial.objects.filter(id=materi.id).exists()
        berkas = FileAsset.all_objects.get(id=materi.id)
        assert berkas.is_deleted is True and berkas.deleted_at is not None
        assert _klien(wiki.staf1).get(url).status_code == status.HTTP_404_NOT_FOUND

    def test_admin_boleh_hapus_materi_orang(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        res = _klien(wiki.admin).delete(f"{wiki.base}materials/{materi.id}/")
        assert res.status_code == status.HTTP_204_NO_CONTENT

    def test_sampah_materi_dan_pulihkan(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        _klien(wiki.staf1).delete(f"{wiki.base}materials/{materi.id}/")

        punya = _klien(wiki.staf1).get(f"{wiki.base}trash/")
        assert [m["id"] for m in punya.data["materials"]] == [str(materi.id)]
        assert _klien(wiki.staf2).get(f"{wiki.base}trash/").data["materials"] == []
        assert [m["id"] for m in _klien(wiki.admin).get(f"{wiki.base}trash/").data["materials"]] == [str(materi.id)]

        restore = f"{wiki.base}trash/materials/{materi.id}/restore/"
        assert _klien(wiki.staf2).post(restore).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(wiki.staf1).post(restore).status_code == status.HTTP_200_OK
        assert WikiMaterial.objects.filter(id=materi.id).exists()
        berkas = FileAsset.objects.get(id=materi.id)
        assert berkas.is_deleted is False and berkas.deleted_at is None
        assert _klien(wiki.staf1).post(restore).status_code == status.HTTP_400_BAD_REQUEST  # sudah pulih

    def test_pulihkan_materi_di_folder_terhapus_ditolak(self, wiki):
        materi = _materi(wiki, wiki.topik, wiki.staf1)
        _klien(wiki.staf1).delete(f"{wiki.base}materials/{materi.id}/")
        WikiFolder.objects.filter(id=wiki.topik.id).update(deleted_at="2026-11-01T00:00:00Z")
        res = _klien(wiki.admin).post(f"{wiki.base}trash/materials/{materi.id}/restore/")
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_cari_judul_dan_nama_berkas(self, wiki):
        materi = _materi(wiki, wiki.topik, wiki.staf1, nama="laporan-gudang.pdf")
        WikiMaterial.objects.filter(id=materi.id).update(judul="Stok Opname")
        klien = _klien(wiki.biasa)
        for q in ("opname", "GUDANG"):
            hasil = klien.get(f"{wiki.base}search/", {"q": q}).data["materials"]
            assert [h["id"] for h in hasil] == [str(materi.id)]
            assert [j["nama"] for j in hasil[0]["jejak"]] == ["Sales", "Team 1", "SOP"]
        assert klien.get(f"{wiki.base}search/", {"q": "o"}).data == {"materials": [], "pages": []}
        assert klien.get(f"{wiki.base}search/", {"q": "tidakada"}).data["materials"] == []

    def test_cari_isi_dokumen_dengan_cuplikan(self, wiki):
        materi = _materi(wiki, wiki.topik, wiki.staf1, nama="scan-001.pdf")
        isi = "Prosedur pengiriman barang ke gudang Surabaya wajib melampirkan surat jalan yang ditandatangani."
        WikiMaterial.objects.filter(id=materi.id).update(isi_teks=isi)
        hasil = _klien(wiki.biasa).get(f"{wiki.base}search/", {"q": "surat jalan"}).data["materials"]
        assert [h["id"] for h in hasil] == [str(materi.id)]
        assert "surat jalan" in hasil[0]["cuplikan"]
        assert set(hasil[0]["sorot"]) == {"surat", "jalan"}

    def test_cari_memaafkan_salah_ketik(self, wiki):
        judul = _materi(wiki, wiki.topik, wiki.staf1, nama="a.pdf")
        WikiMaterial.objects.filter(id=judul.id).update(judul="Laporan Keuangan Bulanan")
        isi = _materi(wiki, wiki.topik, wiki.staf1, nama="b.pdf")
        WikiMaterial.objects.filter(id=isi.id).update(judul="b.pdf", isi_teks="Rekapitulasi pengeluaran departemen.")
        klien = _klien(wiki.biasa)
        # Salah ketik di judul dan di isi sama-sama ketemu.
        assert [h["id"] for h in klien.get(f"{wiki.base}search/", {"q": "keuagan"}).data["materials"]] == [str(judul.id)]
        hasil = klien.get(f"{wiki.base}search/", {"q": "pengeluran"}).data["materials"]
        assert [h["id"] for h in hasil] == [str(isi.id)]
        assert hasil[0]["sorot"] == ["pengeluaran"]

    def test_cari_judul_lebih_dulu_dari_isi(self, wiki):
        hanya_isi = _materi(wiki, wiki.topik, wiki.staf1, nama="x.pdf")
        WikiMaterial.objects.filter(id=hanya_isi.id).update(judul="x.pdf", isi_teks="catatan kontrak vendor")
        di_judul = _materi(wiki, wiki.topik, wiki.staf1, nama="y.pdf")
        WikiMaterial.objects.filter(id=di_judul.id).update(judul="Kontrak vendor 2026")
        hasil = _klien(wiki.biasa).get(f"{wiki.base}search/", {"q": "kontrak vendor"}).data["materials"]
        assert [h["id"] for h in hasil] == [str(di_judul.id), str(hanya_isi.id)]

    def test_pratinjau_pdf_dan_tipe_tanpa_konversi(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        res = _klien(wiki.biasa).get(f"{wiki.base}materials/{materi.id}/preview/")
        assert res.status_code == status.HTTP_200_OK
        assert res.data["kind"] == "pdf"
        assert res.data["url"] == f"/api/workspaces/{wiki.ws.slug}/wiki/files/{materi.id}/?disposition=inline"
        assert res.data["download_url"] == f"/api/workspaces/{wiki.ws.slug}/wiki/files/{materi.id}/"

    def test_pratinjau_dokumen_tanpa_gotenberg_memberi_alasan(self, wiki, settings):
        settings.GOTENBERG_URL = ""
        materi = _materi(
            wiki,
            wiki.f_t1,
            wiki.staf1,
            nama="a.docx",
        )
        FileAsset.objects.filter(id=materi.id).update(
            attributes={"name": "a.docx", "type": "application/msword", "size": 1}
        )
        res = _klien(wiki.biasa).get(f"{wiki.base}materials/{materi.id}/preview/")
        assert res.status_code == 200 and res.data["kind"] == "none" and res.data["reason"]

    def test_jenis_pratinjau(self):
        assert jenis_pratinjau(PDF) == "pdf"
        assert jenis_pratinjau("image/png") == "image"
        assert jenis_pratinjau("video/mp4") == "video"
        assert jenis_pratinjau("video/x-matroska") == "none"
        assert jenis_pratinjau("audio/mpeg") == "audio"
        assert jenis_pratinjau("text/plain") == "text"
        assert jenis_pratinjau("application/msword") == "konversi"
        assert jenis_pratinjau("application/zip") == "none"


@pytest.mark.contract
@pytest.mark.django_db
class TestBerkas:
    def test_anggota_dialihkan_ke_url_presigned(self, wiki, s3_palsu):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        res = _klien(wiki.biasa).get(f"{wiki.base}files/{materi.id}/?disposition=inline")
        assert res.status_code == status.HTTP_302_FOUND
        assert res["Location"] == "https://s3.uji/berkas"
        assert s3_palsu.return_value.generate_presigned_url.call_args.kwargs["disposition"] == "inline"
        res = _klien(wiki.biasa).get(f"{wiki.base}files/{materi.id}/")
        assert s3_palsu.return_value.generate_presigned_url.call_args.kwargs["disposition"] == "attachment"

    def test_bukan_anggota_ditolak(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        assert _klien(wiki.asing).get(f"{wiki.base}files/{materi.id}/").status_code == status.HTTP_403_FORBIDDEN

    def test_materi_terhapus_atau_belum_terunggah_404(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        belum = _unggah(_klien(wiki.staf1), wiki, wiki.f_t1, selesai=False).data["material"]["id"]
        assert _klien(wiki.biasa).get(f"{wiki.base}files/{belum}/").status_code == status.HTTP_404_NOT_FOUND
        _klien(wiki.staf1).delete(f"{wiki.base}materials/{materi.id}/")
        assert _klien(wiki.biasa).get(f"{wiki.base}files/{materi.id}/").status_code == status.HTTP_404_NOT_FOUND

    def test_aset_lain_bukan_wiki_tidak_disajikan(self, wiki):
        lain = FileAsset.objects.create(
            attributes={"name": "a.png"},
            asset="x/a.png",
            workspace=wiki.ws,
            entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
            is_uploaded=True,
        )
        assert _klien(wiki.biasa).get(f"{wiki.base}files/{lain.id}/").status_code == status.HTTP_404_NOT_FOUND

    def test_asset_url_model_menunjuk_wiki_files(self, wiki):
        materi = _materi(wiki, wiki.f_t1, wiki.staf1)
        assert materi.berkas.asset_url == f"/api/workspaces/{wiki.ws.slug}/wiki/files/{materi.id}/"


@pytest.mark.contract
@pytest.mark.django_db
class TestFolderUnit:
    def test_membuat_folder_per_divisi_dan_departemen(self, wiki):
        assert wiki.f_t1.parent_id == wiki.f_sales.id
        assert wiki.f_hr.parent_id == wiki.f_hrga.id
        assert wiki.f_sales.parent_id is None and wiki.f_sales.nama == "Sales"

    def test_idempoten(self, wiki):
        sebelum = WikiFolder.objects.count()
        pastikan_folder_unit(wiki.ws.id)
        assert WikiFolder.objects.count() == sebelum

    def test_ganti_nama_divisi_dan_departemen_diikuti(self, wiki):
        Divisi.objects.filter(id=wiki.sales.id).update(nama="Penjualan")
        Departemen.objects.filter(id=wiki.t1.id).update(nama="Tim Satu")
        pastikan_folder_unit(wiki.ws.id)
        wiki.f_sales.refresh_from_db()
        wiki.f_t1.refresh_from_db()
        assert (wiki.f_sales.nama, wiki.f_t1.nama) == ("Penjualan", "Tim Satu")

    def test_pindah_departemen_antar_divisi_memindah_folder(self, wiki):
        Departemen.objects.filter(id=wiki.t1.id).update(divisi=wiki.hrga)
        pastikan_folder_unit(wiki.ws.id)
        wiki.f_t1.refresh_from_db()
        assert wiki.f_t1.parent_id == wiki.f_hrga.id

    def test_divisi_baru_dan_departemen_baru_mendapat_folder(self, wiki):
        div = Divisi.objects.create(workspace=wiki.ws, kode="IT", nama="IT")
        dep = Departemen.objects.create(workspace=wiki.ws, divisi=div, kode="DEV", nama="Dev")
        pastikan_folder_unit(wiki.ws.id)
        f_div = WikiFolder.objects.get(divisi=div)
        assert WikiFolder.objects.get(departemen=dep).parent_id == f_div.id

    def test_unit_dihapus_folder_tetap_tapi_hanya_admin_yang_mengisi(self, wiki):
        Departemen.all_objects.filter(id=wiki.t1.id).delete()
        pastikan_folder_unit(wiki.ws.id)
        assert WikiFolder.objects.filter(id=wiki.f_t1.id).exists()
        # tanpa unit, folder jadi tertutup bagi staf
        assert _unggah(_klien(wiki.staf1), wiki, wiki.f_t1).status_code == status.HTTP_403_FORBIDDEN
