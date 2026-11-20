# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: editor folder Wiki
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Folder Wiki terbatas editor (mis. "QMS": hanya Sarah yang menulis).

Yang dikunci:

- admin membuat folder tingkat atas tanpa unit dan memasang editor;
- editor mengunggah, membuat sub-folder, mengubah, memindah, dan menghapus;
- staf lain, supervisor departemen, dan pengunggah berkas lama tetap bisa
  membaca tapi 403 saat menulis;
- sub-folder mewarisi; editor sub-folder sendiri menggantikan induknya;
- editor terakhir dilepas = kembali ke aturan unit;
- hanya admin yang mengubah daftar editor.
"""

import pytest
from rest_framework import status

from plane.db.models import WikiFolder, WikiFolderEditor
from plane.tests.contract.app.test_wiki_mandiri_app import (  # noqa: F401
    _klien,
    _materi,
    _unggah,
    _user,
    s3_palsu,
    wiki,
)


@pytest.fixture
def qms(wiki):
    wiki.sarah = _user("sarah", wiki.ws)
    res = _klien(wiki.admin).post(f"{wiki.base}folders/", {"nama": "QMS"}, format="json")
    assert res.status_code == status.HTTP_201_CREATED, res.data
    wiki.qms = WikiFolder.objects.get(id=res.data["id"])
    pasang = _klien(wiki.admin).post(
        f"{wiki.base}folders/{wiki.qms.id}/editors/", {"user_id": str(wiki.sarah.id)}, format="json"
    )
    assert pasang.status_code == status.HTTP_201_CREATED, pasang.data
    wiki.url_editor = f"{wiki.base}folders/{wiki.qms.id}/editors/"
    return wiki


def _peta(klien, wiki):
    return {f["id"]: f for f in klien.get(wiki.base).data["folders"]}


@pytest.mark.contract
@pytest.mark.django_db
class TestEditorMenulis:
    def test_payload_memuat_editor_pembatas_dan_can_write(self, qms):
        res = _klien(qms.sarah).get(qms.base)
        folder = next(f for f in res.data["folders"] if f["id"] == str(qms.qms.id))
        assert [e["id"] for e in folder["editors"]] == [str(qms.sarah.id)]
        assert folder["editors"][0]["display_name"]
        assert folder["restricted_by"] == str(qms.qms.id)
        assert folder["can_write"] is True
        lain = _peta(_klien(qms.biasa), qms)[str(qms.qms.id)]
        assert lain["can_write"] is False and lain["can_upload"] is False
        assert lain["restricted_by"] == str(qms.qms.id)
        # Folder lain tidak berubah.
        assert _peta(_klien(qms.biasa), qms)[str(qms.umum.id)]["restricted_by"] is None
        assert _peta(_klien(qms.biasa), qms)[str(qms.umum.id)]["can_write"] is True

    def test_editor_tanpa_unit_mengunggah_dan_mengubah(self, qms):
        res = _unggah(_klien(qms.sarah), qms, qms.qms)
        assert res.status_code == status.HTTP_200_OK
        mid = res.data["material"]["id"]
        ubah = _klien(qms.sarah).patch(f"{qms.base}materials/{mid}/", {"judul": "Manual Mutu"}, format="json")
        assert ubah.status_code == status.HTTP_200_OK
        assert ubah.data["can_manage"] is True and ubah.data["can_delete"] is True
        assert _klien(qms.sarah).delete(f"{qms.base}materials/{mid}/").status_code == status.HTTP_204_NO_CONTENT

    def test_editor_mengubah_materi_orang_lain_dan_admin_tetap_bisa(self, qms):
        materi = _materi(qms, qms.qms, qms.admin)
        url = f"{qms.base}materials/{materi.id}/"
        assert _klien(qms.sarah).patch(url, {"judul": "Dari Sarah"}, format="json").status_code == 200
        assert _klien(qms.admin).patch(url, {"judul": "Dari admin"}, format="json").status_code == 200

    def test_editor_membuat_dan_mengelola_sub_folder(self, qms):
        res = _klien(qms.sarah).post(
            f"{qms.base}folders/", {"nama": "Prosedur", "parent_id": str(qms.qms.id)}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED
        anak = res.data["id"]
        assert res.data["restricted_by"] == str(qms.qms.id)
        assert (
            _klien(qms.sarah).patch(f"{qms.base}folders/{anak}/", {"nama": "Prosedur 2"}, format="json").status_code
            == 200
        )
        assert _klien(qms.sarah).post(f"{qms.base}folders/{anak}/archive/").status_code == 200
        assert _klien(qms.sarah).delete(f"{qms.base}folders/{anak}/").status_code == status.HTTP_204_NO_CONTENT

    def test_editor_tidak_membongkar_folder_tingkat_atasnya(self, qms):
        sarah = _klien(qms.sarah)
        assert sarah.patch(f"{qms.base}folders/{qms.qms.id}/", {"nama": "Lain"}, format="json").status_code == 403
        assert sarah.post(f"{qms.base}folders/{qms.qms.id}/archive/").status_code == 403
        assert sarah.delete(f"{qms.base}folders/{qms.qms.id}/").status_code == 403

    def test_editor_tidak_mendapat_hak_di_folder_lain(self, qms):
        assert _unggah(_klien(qms.sarah), qms, qms.f_t2).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(_klien(qms.sarah), qms, qms.f_t1).status_code == status.HTTP_403_FORBIDDEN

    def test_materi_tidak_bisa_dipindah_masuk_oleh_non_editor_tapi_editor_bisa_memindah_keluar(self, qms):
        keluar = _materi(qms, qms.qms, qms.admin)
        masuk = _materi(qms, qms.umum, qms.staf1)
        res = _klien(qms.staf1).patch(f"{qms.base}materials/{masuk.id}/", {"folder_id": str(qms.qms.id)}, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN
        res = _klien(qms.sarah).patch(
            f"{qms.base}materials/{keluar.id}/", {"folder_id": str(qms.umum.id)}, format="json"
        )
        assert res.status_code == status.HTTP_200_OK


@pytest.mark.contract
@pytest.mark.django_db
class TestBukanEditor:
    def test_membaca_tetap_bisa(self, qms):
        materi = _materi(qms, qms.qms, qms.sarah)
        for klien in (_klien(qms.staf1), _klien(qms.spv), _klien(qms.manager), _klien(qms.direktur)):
            daftar = klien.get(f"{qms.base}folders/{qms.qms.id}/materials/")
            assert daftar.status_code == status.HTTP_200_OK
            assert [m["id"] for m in daftar.data["materials"]] == [str(materi.id)]
            assert daftar.data["can_upload"] is False
            assert klien.get(f"{qms.base}materials/{materi.id}/").status_code == status.HTTP_200_OK

    def test_staf_supervisor_manager_direktur_tidak_bisa_menulis(self, qms):
        for orang in (qms.staf1, qms.spv, qms.manager, qms.direktur, qms.biasa):
            klien = _klien(orang)
            assert _unggah(klien, qms, qms.qms).status_code == status.HTTP_403_FORBIDDEN
            res = klien.post(f"{qms.base}folders/", {"nama": "Anak", "parent_id": str(qms.qms.id)}, format="json")
            assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_pengunggah_lama_kehilangan_hak_ubah_dan_hapus(self, qms):
        topik = WikiFolder(workspace=qms.ws, nama="Dokumen", parent=qms.f_t1)
        topik.save(created_by_id=qms.admin.id)
        materi = _materi(qms, topik, qms.staf1)
        url = f"{qms.base}materials/{materi.id}/"
        assert _klien(qms.staf1).patch(url, {"judul": "Boleh"}, format="json").status_code == 200

        res = _klien(qms.admin).post(
            f"{qms.base}folders/{topik.id}/editors/", {"user_id": str(qms.sarah.id)}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert _klien(qms.staf1).patch(url, {"judul": "Tidak"}, format="json").status_code == 403
        assert _klien(qms.staf1).delete(url).status_code == 403
        assert _klien(qms.spv).delete(url).status_code == 403
        assert _klien(qms.sarah).patch(url, {"judul": "Sarah"}, format="json").status_code == 200
        lihat = _klien(qms.staf1).get(url)
        assert lihat.status_code == 200
        assert lihat.data["can_manage"] is False and lihat.data["can_delete"] is False

    def test_pengunggah_lama_tidak_bisa_memulihkan_dari_sampah(self, qms):
        materi = _materi(qms, qms.qms, qms.admin)
        assert _klien(qms.sarah).delete(f"{qms.base}materials/{materi.id}/").status_code == 204
        pulih = f"{qms.base}trash/materials/{materi.id}/restore/"
        assert _klien(qms.staf1).post(pulih).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(qms.sarah).post(pulih).status_code == status.HTTP_200_OK

    def test_tidak_bisa_mengubah_atau_mengarsip_folder(self, qms):
        anak = WikiFolder(workspace=qms.ws, nama="Anak", parent=qms.qms)
        anak.save(created_by_id=qms.admin.id)
        klien = _klien(qms.manager)
        assert klien.patch(f"{qms.base}folders/{anak.id}/", {"nama": "x"}, format="json").status_code == 403
        assert klien.post(f"{qms.base}folders/{anak.id}/archive/").status_code == 403


@pytest.mark.contract
@pytest.mark.django_db
class TestWarisan:
    def test_sub_folder_mewarisi(self, qms):
        anak = WikiFolder(workspace=qms.ws, nama="Anak", parent=qms.qms, umum=False)
        anak.save(created_by_id=qms.admin.id)
        cucu = WikiFolder(workspace=qms.ws, nama="Cucu", parent=anak)
        cucu.save(created_by_id=qms.admin.id)
        peta = _peta(_klien(qms.staf1), qms)
        assert peta[str(anak.id)]["restricted_by"] == str(qms.qms.id)
        assert peta[str(cucu.id)]["restricted_by"] == str(qms.qms.id)
        assert peta[str(anak.id)]["editors"] == []
        assert _unggah(_klien(qms.staf1), qms, cucu).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(_klien(qms.sarah), qms, cucu).status_code == status.HTTP_200_OK

    def test_sub_folder_departemen_terbatas_tidak_menyentuh_induknya(self, qms):
        res = _klien(qms.admin).post(
            f"{qms.base}folders/{qms.topik.id}/editors/", {"user_id": str(qms.sarah.id)}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert _unggah(_klien(qms.staf1), qms, qms.topik).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(_klien(qms.staf1), qms, qms.f_t1).status_code == status.HTTP_200_OK
        assert _unggah(_klien(qms.sarah), qms, qms.topik).status_code == status.HTTP_200_OK

    def test_editor_terdekat_menang_tanpa_digabung(self, qms):
        budi = _user("budi", qms.ws)
        anak = WikiFolder(workspace=qms.ws, nama="Anak", parent=qms.qms)
        anak.save(created_by_id=qms.admin.id)
        _klien(qms.admin).post(f"{qms.base}folders/{anak.id}/editors/", {"user_id": str(budi.id)}, format="json")
        assert _unggah(_klien(budi), qms, anak).status_code == status.HTTP_200_OK
        assert _unggah(_klien(qms.sarah), qms, anak).status_code == status.HTTP_403_FORBIDDEN
        assert _unggah(_klien(budi), qms, qms.qms).status_code == status.HTTP_403_FORBIDDEN
        peta = _peta(_klien(qms.staf1), qms)
        assert peta[str(anak.id)]["restricted_by"] == str(anak.id)

    def test_editor_terakhir_dilepas_kembali_ke_aturan_unit(self, qms):
        pasang = _klien(qms.admin).post(
            f"{qms.base}folders/{qms.topik.id}/editors/", {"user_id": str(qms.sarah.id)}, format="json"
        )
        assert pasang.status_code == status.HTTP_201_CREATED
        assert _unggah(_klien(qms.staf1), qms, qms.topik).status_code == status.HTTP_403_FORBIDDEN
        lepas = _klien(qms.admin).delete(f"{qms.base}folders/{qms.topik.id}/editors/{qms.sarah.id}/")
        assert lepas.status_code == status.HTTP_200_OK
        assert lepas.data["restricted_by"] is None and lepas.data["editors"] == []
        assert _unggah(_klien(qms.staf1), qms, qms.topik).status_code == status.HTTP_200_OK
        assert WikiFolderEditor.all_objects.filter(folder=qms.topik).count() == 1  # soft delete

    def test_pasang_ulang_setelah_lepas(self, qms):
        _klien(qms.admin).delete(f"{qms.base}folders/{qms.qms.id}/editors/{qms.sarah.id}/")
        res = _klien(qms.admin).post(
            f"{qms.base}folders/{qms.qms.id}/editors/", {"user_id": str(qms.sarah.id)}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert WikiFolderEditor.objects.filter(folder=qms.qms).count() == 1


@pytest.mark.contract
@pytest.mark.django_db
class TestKelolaEditor:
    def test_pasang_dua_kali_tidak_menggandakan(self, qms):
        _klien(qms.admin).post(qms.url_editor, {"user_id": str(qms.sarah.id)}, format="json")
        assert WikiFolderEditor.objects.filter(folder=qms.qms).count() == 1

    def test_hanya_admin_mengubah_editor(self, qms):
        for orang in (qms.sarah, qms.manager, qms.direktur, qms.spv, qms.biasa):
            klien = _klien(orang)
            assert klien.get(qms.url_editor).status_code == 403
            assert klien.post(qms.url_editor, {"user_id": str(orang.id)}, format="json").status_code == 403
            assert klien.delete(f"{qms.url_editor}{qms.sarah.id}/").status_code == 403
        assert WikiFolderEditor.objects.filter(folder=qms.qms).count() == 1

    def test_daftar_editor_untuk_admin(self, qms):
        res = _klien(qms.admin).get(qms.url_editor)
        assert res.status_code == 200
        assert [e["id"] for e in res.data] == [str(qms.sarah.id)]

    def test_editor_harus_anggota_aktif_workspace(self, qms):
        for user_id in (str(qms.asing.id), "bukan-uuid", None, "00000000-0000-0000-0000-000000000000"):
            res = _klien(qms.admin).post(qms.url_editor, {"user_id": user_id}, format="json")
            assert res.status_code == status.HTTP_400_BAD_REQUEST, user_id

    def test_lepas_orang_yang_bukan_editor_404(self, qms):
        assert _klien(qms.admin).delete(f"{qms.url_editor}{qms.biasa.id}/").status_code == 404
