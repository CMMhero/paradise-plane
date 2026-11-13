# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes pengelola Wiki & halaman departemen (KEP-95)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Yang dikunci:

- matriks hak kelola: manager divisi mengelola folder divisinya dan semua di
  bawahnya (termasuk folder departemen), supervisor hanya folder departemen
  tempat ia berperan Supervisor (peran per tempat, KEP-93), staf tidak sama
  sekali; tingkat atas tetap admin;
- pengelola mengubah/menghapus/memulihkan materi siapa pun di wilayahnya;
- wilayah mengikuti struktur (departemen pindah divisi = pindah pengelola);
- folder unit menyusul sendiri saat pohon dibaca;
- halaman project departemen: publik untuk semua anggota, privat hanya untuk
  anggota departemen, manager divisinya, direktur, admin, dan pemiliknya;
  tidak bocor lewat detail, pencarian, atau pohon.
"""

import datetime
import uuid
from unittest import mock

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    JabatanOrganisasi,
    Page,
    Project,
    ProjectMember,
    ProjectPage,
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


def _topik(w, induk, nama="SOP"):
    f = WikiFolder(workspace=w.ws, nama=nama, parent=induk)
    f.save(created_by_id=w.admin.id)
    return f


@pytest.fixture
def w(db, workspace, create_user):
    """Sales (T1, T2) dan HRGA (HR). Folder unit dibuat `pastikan_folder_unit`."""
    o = type("W", (), {})()
    o.ws = workspace
    o.base = f"/api/workspaces/{workspace.slug}/wiki/"
    o.admin = create_user
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.hrga = Divisi.objects.create(workspace=workspace, kode="HRGA", nama="HRGA")
    o.t1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="T1", nama="Team 1")
    o.t2 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="T2", nama="Team 2")
    o.hr = Departemen.objects.create(workspace=workspace, divisi=o.hrga, kode="HR", nama="Human Resources")
    pastikan_folder_unit(workspace.id)

    o.mgr_sales = _user("mgrs", workspace)
    o.mgr_hrga = _user("mgrh", workspace)
    o.spv_t1 = _user("spv1", workspace)
    o.staf_t1 = _user("staf1", workspace)
    o.staf_t2 = _user("staf2", workspace)
    o.campur = _user("campur", workspace)  # Supervisor di T1, Staf di T2
    o.direktur = _user("dir", workspace)
    o.biasa = _user("biasa", workspace)
    o.asing = _user("asing", workspace, role=None)
    setel_penempatan(workspace, o.mgr_sales, TINGKAT_MANAGER, [], [o.sales.id])
    setel_penempatan(workspace, o.mgr_hrga, TINGKAT_MANAGER, [], [o.hrga.id])
    setel_penempatan(workspace, o.spv_t1, TINGKAT_SUPERVISOR, [o.t1.id], [])
    setel_penempatan(workspace, o.staf_t1, TINGKAT_MEMBER, [o.t1.id], [])
    setel_penempatan(workspace, o.staf_t2, TINGKAT_MEMBER, [o.t2.id], [])
    setel_penempatan(
        workspace,
        o.campur,
        TINGKAT_SUPERVISOR,
        [o.t1.id, o.t2.id],
        [],
        peran_departemen={str(o.t1.id): TINGKAT_SUPERVISOR, str(o.t2.id): TINGKAT_MEMBER},
    )
    setel_penempatan(workspace, o.direktur, TINGKAT_DIREKTUR, [], [])

    o.f_sales = WikiFolder.objects.get(divisi=o.sales)
    o.f_hrga = WikiFolder.objects.get(divisi=o.hrga)
    o.f_t1 = WikiFolder.objects.get(departemen=o.t1)
    o.f_t2 = WikiFolder.objects.get(departemen=o.t2)
    o.f_hr = WikiFolder.objects.get(departemen=o.hr)
    o.topik_t1 = _topik(o, o.f_t1, "SOP T1")
    o.topik_t2 = _topik(o, o.f_t2, "SOP T2")
    return o


def _buat_folder(user, w, induk=None, nama="Baru"):
    data = {"nama": nama}
    if induk is not None:
        data["parent_id"] = str(induk.id)
    return _klien(user).post(f"{w.base}folders/", data, format="json")


def _materi(w, folder, pengunggah, nama="panduan.pdf"):
    klien = _klien(pengunggah)
    res = klien.post(f"{w.base}folders/{folder.id}/materials/", {"name": nama, "type": PDF, "size": 10}, format="json")
    assert res.status_code == status.HTTP_200_OK, res.data
    mid = res.data["material"]["id"]
    assert klien.post(f"{w.base}materials/{mid}/uploaded/").status_code == status.HTTP_204_NO_CONTENT
    return WikiMaterial.objects.get(id=mid)


@pytest.mark.contract
@pytest.mark.django_db
class TestMatriksKelolaFolder:
    def test_manager_membuat_subfolder_di_seluruh_divisinya(self, w):
        for induk in (w.f_sales, w.f_t1, w.f_t2):
            res = _buat_folder(w.mgr_sales, w, induk)
            assert res.status_code == status.HTTP_201_CREATED, (induk.nama, res.data)
            assert res.data["can_manage"] is True
        # Hak ada di seluruh divisi, tapi sub-topik tidak bisa punya sub-topik lagi.
        assert _buat_folder(w.mgr_sales, w, w.topik_t2).status_code == status.HTTP_400_BAD_REQUEST
        for induk in (w.f_hrga, w.f_hr):
            assert _buat_folder(w.mgr_sales, w, induk).status_code == status.HTTP_403_FORBIDDEN

    def test_supervisor_hanya_folder_departemennya(self, w):
        assert _buat_folder(w.spv_t1, w, w.f_t1).status_code == status.HTTP_201_CREATED
        assert _buat_folder(w.spv_t1, w, w.topik_t1).status_code == status.HTTP_400_BAD_REQUEST
        for induk in (w.f_sales, w.f_t2, w.topik_t2, w.f_hr):
            assert _buat_folder(w.spv_t1, w, induk).status_code == status.HTTP_403_FORBIDDEN

    def test_peran_per_tempat_supervisor_di_t1_staf_di_t2(self, w):
        assert _buat_folder(w.campur, w, w.f_t1).status_code == status.HTTP_201_CREATED
        assert _buat_folder(w.campur, w, w.f_t2).status_code == status.HTTP_403_FORBIDDEN

    def test_staf_dan_anggota_biasa_tidak_mengelola(self, w):
        for u in (w.staf_t1, w.biasa):
            assert _buat_folder(u, w, w.f_t1).status_code == status.HTTP_403_FORBIDDEN

    def test_tingkat_atas_tetap_admin(self, w):
        for u in (w.mgr_sales, w.spv_t1):
            assert _buat_folder(u, w).status_code == status.HTTP_403_FORBIDDEN
            res = _klien(u).post(f"{w.base}folders/", {"nama": "Umum", "umum": True}, format="json")
            assert res.status_code == status.HTTP_403_FORBIDDEN
        assert _buat_folder(w.admin, w).status_code == status.HTTP_201_CREATED

    def test_ubah_folder_unit_tanpa_nama_dan_tanpa_urutan_teratas(self, w):
        k = _klien(w.mgr_sales)
        assert k.patch(f"{w.base}folders/{w.f_t1.id}/", {"keterangan": "k"}, format="json").status_code == 200
        assert k.patch(f"{w.base}folders/{w.f_sales.id}/", {"keterangan": "k"}, format="json").status_code == 200
        # nama unit mengikuti God Mode, urutan folder teratas milik admin
        assert k.patch(f"{w.base}folders/{w.f_t1.id}/", {"nama": "X"}, format="json").status_code == 400
        assert k.patch(f"{w.base}folders/{w.f_sales.id}/", {"urutan": 1}, format="json").status_code == 403
        # urutan di dalam wilayahnya boleh
        assert k.patch(f"{w.base}folders/{w.topik_t1.id}/", {"urutan": 3}, format="json").status_code == 200
        assert (
            _klien(w.spv_t1).patch(f"{w.base}folders/{w.f_sales.id}/", {"keterangan": "x"}, format="json").status_code
            == 403
        )

    def test_arsip_hapus_dan_pulihkan_di_wilayah(self, w):
        k = _klien(w.mgr_sales)
        url = f"{w.base}folders/{w.topik_t2.id}/"
        assert _klien(w.spv_t1).post(f"{url}archive/").status_code == 403
        assert k.post(f"{url}archive/").status_code == 200
        assert k.delete(url).status_code == status.HTTP_204_NO_CONTENT

        sampah = k.get(f"{w.base}trash/").data["folders"]
        assert [f["id"] for f in sampah] == [str(w.topik_t2.id)]
        assert _klien(w.spv_t1).get(f"{w.base}trash/").data["folders"] == []
        assert _klien(w.mgr_hrga).get(f"{w.base}trash/").data["folders"] == []
        restore = f"{w.base}trash/folders/{w.topik_t2.id}/restore/"
        assert _klien(w.spv_t1).post(restore).status_code == 403
        assert k.post(restore).status_code == 200

    def test_folder_unit_tetap_tidak_bisa_diarsip_pengelola(self, w):
        assert _klien(w.spv_t1).post(f"{w.base}folders/{w.f_t1.id}/archive/").status_code == 400

    def test_bendera_can_manage_di_pohon(self, w):
        res = _klien(w.spv_t1).get(w.base)
        assert res.data["is_admin"] is False and res.data["can_manage_any"] is True
        peta = {f["id"]: f for f in res.data["folders"]}
        assert peta[str(w.f_t1.id)]["can_manage"] is True
        assert peta[str(w.topik_t1.id)]["can_manage"] is True
        assert peta[str(w.f_t2.id)]["can_manage"] is False
        assert peta[str(w.f_sales.id)]["can_manage"] is False
        assert _klien(w.staf_t1).get(w.base).data["can_manage_any"] is False

    def test_baris_divisi_lama_di_bawah_manager_tidak_memberi_hak(self, w):
        lama = _user("lama", w.ws)
        JabatanOrganisasi.objects.create(workspace=w.ws, member=lama, tingkat=TINGKAT_MEMBER, divisi=w.sales)
        assert _buat_folder(lama, w, w.f_t1).status_code == status.HTTP_403_FORBIDDEN

    def test_departemen_pindah_divisi_pindah_pengelola(self, w):
        Departemen.objects.filter(id=w.t1.id).update(divisi=w.hrga)
        pastikan_folder_unit(w.ws.id)
        assert _buat_folder(w.mgr_sales, w, w.f_t1).status_code == status.HTTP_403_FORBIDDEN
        assert _buat_folder(w.mgr_hrga, w, w.f_t1).status_code == status.HTTP_201_CREATED
        # supervisor departemen ikut bersama departemennya
        assert _buat_folder(w.spv_t1, w, w.f_t1).status_code == status.HTTP_201_CREATED


@pytest.mark.contract
@pytest.mark.django_db
class TestDirekturMengelolaSemuaUnit:
    """KEP-95 diperluas: direktur = kuasa manager divisi di SEMUA divisi dan departemen."""

    def test_membuat_subfolder_di_semua_unit(self, w):
        for induk in (w.f_sales, w.f_hrga, w.f_t1, w.f_t2, w.f_hr):
            res = _buat_folder(w.direktur, w, induk)
            assert res.status_code == status.HTTP_201_CREATED, (induk.nama, res.data)
            assert res.data["can_manage"] is True
        assert _buat_folder(w.direktur, w, w.topik_t2).status_code == status.HTTP_400_BAD_REQUEST

    def test_tingkat_atas_dan_general_tetap_admin(self, w):
        assert _buat_folder(w.direktur, w).status_code == status.HTTP_403_FORBIDDEN
        res = _klien(w.direktur).post(f"{w.base}folders/", {"nama": "Umum", "umum": True}, format="json")
        assert res.status_code == status.HTTP_403_FORBIDDEN
        umum = _klien(w.admin).post(f"{w.base}folders/", {"nama": "Umum", "umum": True}, format="json")
        assert umum.status_code == status.HTTP_201_CREATED, umum.data
        res = _buat_folder(w.direktur, w, WikiFolder.objects.get(id=umum.data["id"]))
        assert res.status_code == status.HTTP_403_FORBIDDEN
        k = _klien(w.direktur)
        assert k.patch(f"{w.base}folders/{w.f_sales.id}/", {"urutan": 1}, format="json").status_code == 403

    def test_ubah_arsip_hapus_pulihkan_folder(self, w):
        k = _klien(w.direktur)
        assert k.patch(f"{w.base}folders/{w.f_hr.id}/", {"keterangan": "k"}, format="json").status_code == 200
        assert k.patch(f"{w.base}folders/{w.f_t1.id}/", {"nama": "X"}, format="json").status_code == 400
        assert k.post(f"{w.base}folders/{w.f_t1.id}/archive/").status_code == 400
        url = f"{w.base}folders/{w.topik_t2.id}/"
        assert k.post(f"{url}archive/").status_code == 200
        assert k.delete(url).status_code == status.HTTP_204_NO_CONTENT
        assert [f["id"] for f in k.get(f"{w.base}trash/").data["folders"]] == [str(w.topik_t2.id)]
        assert k.post(f"{w.base}trash/folders/{w.topik_t2.id}/restore/").status_code == 200

    def test_materi_siapa_pun_di_unit_mana_pun(self, w):
        m_t1 = _materi(w, w.topik_t1, w.staf_t1, "a.pdf")
        m_hr = _materi(w, w.f_hr, w.mgr_hrga, "b.pdf")
        k = _klien(w.direktur)
        for m in (m_t1, m_hr):
            url = f"{w.base}materials/{m.id}/"
            assert k.patch(url, {"judul": "Oleh direktur"}, format="json").status_code == 200
            assert k.delete(url).status_code == status.HTTP_204_NO_CONTENT
        assert {m["id"] for m in k.get(f"{w.base}trash/").data["materials"]} == {str(m_t1.id), str(m_hr.id)}
        assert k.post(f"{w.base}trash/materials/{m_hr.id}/restore/").status_code == 200

    def test_bendera_can_manage_di_pohon(self, w):
        res = _klien(w.direktur).get(w.base)
        assert res.data["is_admin"] is False and res.data["can_manage_any"] is True
        peta = {f["id"]: f for f in res.data["folders"]}
        for f in (w.f_sales, w.f_hrga, w.f_t1, w.f_t2, w.f_hr, w.topik_t1):
            assert peta[str(f.id)]["can_manage"] is True, f.nama

    def test_bendera_materi(self, w):
        _materi(w, w.f_hr, w.mgr_hrga)
        daftar = _klien(w.direktur).get(f"{w.base}folders/{w.f_hr.id}/materials/").data["materials"]
        assert daftar[0]["can_manage"] is True and daftar[0]["can_delete"] is True


@pytest.mark.contract
@pytest.mark.django_db
class TestKelolaMateri:
    def test_pengelola_mengubah_dan_menghapus_materi_orang(self, w):
        materi = _materi(w, w.topik_t1, w.staf_t1)
        url = f"{w.base}materials/{materi.id}/"
        for u in (w.staf_t2, w.mgr_hrga, w.biasa):
            assert _klien(u).patch(url, {"judul": "x"}, format="json").status_code == 403
        assert _klien(w.spv_t1).patch(url, {"judul": "Oleh spv"}, format="json").status_code == 200
        assert _klien(w.mgr_sales).patch(url, {"judul": "Oleh mgr"}, format="json").status_code == 200
        daftar = _klien(w.spv_t1).get(f"{w.base}folders/{w.topik_t1.id}/materials/").data
        assert daftar["materials"][0]["can_manage"] is True and daftar["materials"][0]["can_delete"] is True
        assert _klien(w.spv_t1).delete(url).status_code == status.HTTP_204_NO_CONTENT

    def test_sampah_materi_pengelola_dan_pulihkan(self, w):
        m1 = _materi(w, w.f_t1, w.staf_t1, "a.pdf")
        m2 = _materi(w, w.f_t2, w.staf_t2, "b.pdf")
        _klien(w.staf_t1).delete(f"{w.base}materials/{m1.id}/")
        _klien(w.staf_t2).delete(f"{w.base}materials/{m2.id}/")

        assert [m["id"] for m in _klien(w.spv_t1).get(f"{w.base}trash/").data["materials"]] == [str(m1.id)]
        assert {m["id"] for m in _klien(w.mgr_sales).get(f"{w.base}trash/").data["materials"]} == {
            str(m1.id),
            str(m2.id),
        }
        assert _klien(w.mgr_hrga).get(f"{w.base}trash/").data["materials"] == []
        assert _klien(w.spv_t1).post(f"{w.base}trash/materials/{m2.id}/restore/").status_code == 403
        assert _klien(w.spv_t1).post(f"{w.base}trash/materials/{m1.id}/restore/").status_code == 200

    def test_supervisor_mengunggah_ke_folder_departemennya(self, w):
        _materi(w, w.topik_t1, w.spv_t1)


@pytest.mark.contract
@pytest.mark.django_db
class TestFolderMenyusul:
    def test_pohon_membuat_folder_departemen_yang_tertinggal(self, w):
        baru = Departemen.objects.create(workspace=w.ws, divisi=w.hrga, kode="GA", nama="General Affairs")
        assert not WikiFolder.objects.filter(departemen=baru).exists()
        res = _klien(w.biasa).get(w.base)
        f = WikiFolder.objects.get(departemen=baru)
        assert f.parent_id == w.f_hrga.id
        assert str(f.id) in {x["id"] for x in res.data["folders"]}

    def test_pohon_mengikuti_ganti_nama(self, w):
        Departemen.objects.filter(id=w.t2.id).update(nama="Tim Dua")
        _klien(w.biasa).get(w.base)
        w.f_t2.refresh_from_db()
        assert w.f_t2.nama == "Tim Dua"

    def test_sinkron_tanpa_perubahan_tidak_menulis(self, w):
        assert pastikan_folder_unit(w.ws.id) == 0


# -- halaman project departemen -----------------------------------------------


def _halaman(w, project, pemilik, akses, nama, arsip=False):
    page = Page.objects.create(
        workspace=w.ws,
        owned_by=pemilik,
        access=akses,
        name=nama,
        description_html=f"<p>{nama}</p>",
        archived_at=datetime.date.today() if arsip else None,
    )
    ProjectPage.objects.create(workspace=w.ws, project=project, page=page)
    return page


@pytest.fixture
def hal(w):
    h = type("H", (), {})()
    h.p_t1 = Project.objects.create(name="T1 Board", identifier="WKT1", workspace=w.ws)
    h.p_lain = Project.objects.create(name="Lepas", identifier="WKLP", workspace=w.ws)
    DepartemenProject.objects.create(workspace=w.ws, departemen=w.t1, project=h.p_t1)
    h.publik = _halaman(w, h.p_t1, w.staf_t1, Page.PUBLIC_ACCESS, "Panduan publik")
    h.privat = _halaman(w, h.p_t1, w.staf_t1, Page.PRIVATE_ACCESS, "Rahasia tim")
    h.privat_biasa = _halaman(w, h.p_t1, w.biasa, Page.PRIVATE_ACCESS, "Catatan biasa")
    h.arsip = _halaman(w, h.p_t1, w.staf_t1, Page.PUBLIC_ACCESS, "Lama", arsip=True)
    h.lepas = _halaman(w, h.p_lain, w.staf_t1, Page.PUBLIC_ACCESS, "Bukan departemen")
    h.url = f"{w.base}folders/{w.f_t1.id}/pages/"
    return h


def _anggota(project, user, role):
    """Keanggotaan project aktif dengan role ini. Sinkron hierarki bisa sudah
    membuatnya (DepartemenProject baru), jadi jangan `create` buta."""
    ProjectMember.objects.update_or_create(
        workspace=project.workspace,
        project=project,
        member=user,
        defaults={"role": role, "is_active": True},
    )


def _nama(res):
    return {p["name"] for p in res.data["pages"]}


@pytest.mark.contract
@pytest.mark.django_db
class TestHalamanDepartemen:
    def test_yang_berhak_melihat_privat(self, w, hal):
        for u in (w.staf_t1, w.spv_t1, w.campur, w.mgr_sales, w.direktur, w.admin):
            res = _klien(u).get(hal.url)
            assert res.status_code == status.HTTP_200_OK
            assert {"Panduan publik", "Rahasia tim", "Catatan biasa"} == _nama(res), u.email

    def test_yang_lain_hanya_publik(self, w, hal):
        for u in (w.staf_t2, w.mgr_hrga):
            assert _nama(_klien(u).get(hal.url)) == {"Panduan publik"}, u.email

    def test_pemilik_selalu_melihat_privatnya(self, w, hal):
        assert _nama(_klien(w.biasa).get(hal.url)) == {"Panduan publik", "Catatan biasa"}

    def test_label_departemen_dan_bentuk(self, w, hal):
        res = _klien(w.staf_t2).get(hal.url)
        assert res.data["departemen"] == {"id": str(w.t1.id), "nama": "Team 1", "project_id": str(hal.p_t1.id)}
        page = res.data["pages"][0]
        assert page["access"] == "public" and page["departemen_nama"] == "Team 1"
        assert page["project_id"] == str(hal.p_t1.id)
        assert "description_html" not in page

    def test_arsip_dan_project_lain_tidak_tampil(self, w, hal):
        nama = _nama(_klien(w.admin).get(hal.url))
        assert "Lama" not in nama and "Bukan departemen" not in nama

    def test_folder_bukan_departemen_kosong(self, w, hal):
        for f in (w.f_sales, w.topik_t1):
            res = _klien(w.admin).get(f"{w.base}folders/{f.id}/pages/")
            assert res.status_code == 200 and res.data == {"departemen": None, "pages": []}

    def test_departemen_tanpa_project_kosong(self, w, hal):
        res = _klien(w.admin).get(f"{w.base}folders/{w.f_t2.id}/pages/")
        assert res.data["pages"] == []

    def test_bukan_anggota_workspace_ditolak(self, w, hal):
        assert _klien(w.asing).get(hal.url).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(w.asing).get(f"{w.base}pages/{hal.publik.id}/").status_code == status.HTTP_403_FORBIDDEN

    def test_detail_privat_404_bagi_yang_tidak_berhak(self, w, hal):
        url = f"{w.base}pages/{hal.privat.id}/"
        for u in (w.staf_t2, w.mgr_hrga, w.biasa):
            assert _klien(u).get(url).status_code == status.HTTP_404_NOT_FOUND
        res = _klien(w.mgr_sales).get(url)
        assert res.status_code == 200
        assert res.data["description_html"] == "<p>Rahasia tim</p>"
        assert _klien(w.staf_t1).get(url).data["can_open_in_project"] is True
        # Anggota project: manager divisinya dan direktur kini bisa membukanya
        # di project (KEP-95); anggota departemen selain pemilik tetap tidak.
        for u in (w.mgr_sales, w.direktur, w.spv_t1):
            _anggota(hal.p_t1, u, 20)
        assert _klien(w.mgr_sales).get(url).data["can_open_in_project"] is True
        assert _klien(w.direktur).get(url).data["can_open_in_project"] is True
        assert _klien(w.spv_t1).get(url).data["can_open_in_project"] is False
        # Bukan anggota project: halaman project tidak akan terbuka baginya.
        ProjectMember.objects.filter(project=hal.p_t1, member=w.direktur).update(is_active=False)
        assert _klien(w.direktur).get(url).data["can_open_in_project"] is False

    def test_detail_publik_dan_tombol_buka(self, w, hal):
        url = f"{w.base}pages/{hal.publik.id}/"
        assert _klien(w.staf_t2).get(url).data["can_open_in_project"] is False
        ProjectMember.objects.create(workspace=w.ws, project=hal.p_t1, member=w.staf_t2, role=15)
        assert _klien(w.staf_t2).get(url).data["can_open_in_project"] is True

    def test_detail_arsip_lepas_dan_acak_404(self, w, hal):
        for pid in (hal.arsip.id, hal.lepas.id, uuid.uuid4()):
            assert _klien(w.admin).get(f"{w.base}pages/{pid}/").status_code == status.HTTP_404_NOT_FOUND

    def test_tidak_bocor_lewat_pencarian_dan_pohon(self, w, hal):
        assert _klien(w.staf_t2).get(f"{w.base}search/", {"q": "Rahasia"}).data == {"materials": [], "pages": []}
        pohon = _klien(w.staf_t2).get(w.base).data
        assert "Rahasia" not in str(pohon)


# -- halaman privat di dalam project (KEP-95, 6 Nov 2026) ----------------------


@pytest.fixture
def proj(w, hal):
    """Semua penguji jadi anggota project T1; manager HRGA juga (role 20) supaya
    terbukti role admin project saja tidak membuka halaman privat orang."""
    for u, role in (
        (w.staf_t1, 15),
        (w.staf_t2, 15),
        (w.spv_t1, 20),
        (w.mgr_sales, 20),
        (w.mgr_hrga, 20),
        (w.direktur, 20),
    ):
        _anggota(hal.p_t1, u, role)
    for u in (w.mgr_sales, w.direktur):
        _anggota(hal.p_lain, u, 20)
    hal.privat_lepas = _halaman(w, hal.p_lain, w.staf_t1, Page.PRIVATE_ACCESS, "Privat lepas")
    return hal


def _url_project(w, project, akhir=""):
    return f"/api/workspaces/{w.ws.slug}/projects/{project.id}/{akhir}"


def _daftar(user, w, project):
    res = _klien(user).get(_url_project(w, project, "pages/"))
    assert res.status_code == status.HTTP_200_OK, res.data
    return {p["name"] for p in res.data}


@pytest.mark.contract
@pytest.mark.django_db
class TestHalamanPrivatDiProject:
    _SEMUA_T1 = {"Panduan publik", "Rahasia tim", "Catatan biasa"}

    def test_daftar_memuat_privat_untuk_manager_divisi_dan_direktur(self, w, proj):
        for u in (w.mgr_sales, w.direktur):
            assert self._SEMUA_T1 <= _daftar(u, w, proj.p_t1), u.email

    def test_daftar_tidak_bocor_ke_yang_lain(self, w, proj):
        # spv/staf departemen itu sendiri, staf departemen lain, manager divisi lain
        for u in (w.spv_t1, w.staf_t2, w.mgr_hrga):
            nama = _daftar(u, w, proj.p_t1)
            assert "Rahasia tim" not in nama and "Catatan biasa" not in nama, u.email
        assert _daftar(w.staf_t1, w, proj.p_t1) & self._SEMUA_T1 == {"Panduan publik", "Rahasia tim"}

    def test_project_tanpa_departemen_hanya_direktur(self, w, proj):
        assert "Privat lepas" in _daftar(w.direktur, w, proj.p_lain)
        assert "Privat lepas" not in _daftar(w.mgr_sales, w, proj.p_lain)

    def test_ringkasan_menghitung_privat_sesuai_hak(self, w, proj):
        url = _url_project(w, proj.p_t1, "pages-summary/")
        assert _klien(w.mgr_sales).get(url).data["private_pages"] == 2
        assert _klien(w.mgr_hrga).get(url).data["private_pages"] == 0

    def test_detail_dan_isi_terbuka(self, w, proj):
        for u in (w.mgr_sales, w.direktur):
            k = _klien(u)
            res = k.get(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/"))
            assert res.status_code == status.HTTP_200_OK, (u.email, res.data)
            assert res.data["name"] == "Rahasia tim"
            isi = k.get(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/description/"))
            assert isi.status_code == status.HTTP_200_OK

    def test_detail_dan_isi_tertutup_bagi_yang_lain(self, w, proj):
        for u in (w.spv_t1, w.staf_t2, w.mgr_hrga):
            k = _klien(u)
            res = k.get(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/"))
            assert res.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), u.email
            isi = k.get(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/description/"))
            assert isi.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), u.email

    def test_ubah_mengikuti_aturan_halaman_publik(self, w, proj):
        """Privat orang lain = diperlakukan seperti publik orang lain (PERM_PAGE_EDIT)."""
        for u in (w.mgr_sales, w.direktur):
            k = _klien(u)
            publik = k.patch(_url_project(w, proj.p_t1, f"pages/{proj.publik.id}/"), {"name": "P"}, format="json")
            privat = k.patch(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/"), {"name": "Q"}, format="json")
            assert publik.status_code == privat.status_code, (u.email, publik.data, privat.data)
            edit = k.get(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/can-edit/"))
            assert edit.data["can_edit"] is (privat.status_code == status.HTTP_200_OK)
        res = _klien(w.mgr_hrga).patch(
            _url_project(w, proj.p_t1, f"pages/{proj.privat.id}/"), {"name": "X"}, format="json"
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_ganti_akses_tetap_pemilik(self, w, proj):
        k = _klien(w.direktur)
        res = k.post(_url_project(w, proj.p_t1, f"pages/{proj.privat.id}/access/"), {"access": 0}, format="json")
        assert res.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN)
        proj.privat.refresh_from_db()
        assert proj.privat.access == Page.PRIVATE_ACCESS

    def test_salin_privat(self, w, proj):
        url = _url_project(w, proj.p_t1, f"pages/{proj.privat.id}/duplicate/")
        assert _klien(w.mgr_hrga).post(url).status_code == status.HTTP_403_FORBIDDEN
        res = _klien(w.mgr_sales).post(url)
        assert res.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED), res.data


# -- angka halaman di pohon, tautan ke project, sampah per folder (KEP-97) ------


def _pohon(user, w):
    res = _klien(user).get(w.base)
    assert res.status_code == status.HTTP_200_OK, res.data
    return {f["id"]: f for f in res.data["folders"]}


@pytest.mark.contract
@pytest.mark.django_db
class TestAngkaHalamanDiPohon:
    def test_angka_mengikuti_hak_lihat(self, w, hal):
        harapan = {
            w.admin: 3,
            w.direktur: 3,
            w.mgr_sales: 3,
            w.staf_t1: 3,
            w.spv_t1: 3,
            w.biasa: 2,  # publik + privat miliknya
            w.staf_t2: 1,
            w.mgr_hrga: 1,
        }
        for u, n in harapan.items():
            assert _pohon(u, w)[str(w.f_t1.id)]["jumlah_halaman"] == n, u.email

    def test_angka_sama_dengan_daftar_untuk_semua_orang(self, w, hal):
        """Angka dan daftar memakai saringan yang sama: tidak pernah selisih."""
        for u in (w.admin, w.direktur, w.mgr_sales, w.mgr_hrga, w.spv_t1, w.staf_t1, w.staf_t2, w.campur, w.biasa):
            angka = _pohon(u, w)[str(w.f_t1.id)]["jumlah_halaman"]
            assert angka == len(_klien(u).get(hal.url).data["pages"]), u.email

    def test_angka_langsung_per_folder_departemen(self, w, hal):
        pohon = _pohon(w.admin, w)
        # Klien menjumlahkan ke atas (cermin angka materi); server mengirim angka langsung.
        for f in (w.f_sales, w.f_hrga, w.f_t2, w.f_hr, w.topik_t1):
            assert pohon[str(f.id)]["jumlah_halaman"] == 0
        assert pohon[str(w.f_t1.id)]["project_id"] == str(hal.p_t1.id)
        assert pohon[str(w.f_t2.id)]["project_id"] is None
        assert pohon[str(w.f_sales.id)]["project_id"] is None

    def test_arsip_lepas_dan_terhapus_tidak_dihitung(self, w, hal):
        ProjectPage.objects.filter(page=hal.publik).update(deleted_at=datetime.datetime.now(datetime.timezone.utc))
        assert _pohon(w.staf_t2, w)[str(w.f_t1.id)]["jumlah_halaman"] == 0
        assert _pohon(w.admin, w)[str(w.f_t1.id)]["jumlah_halaman"] == 2

    def test_project_terhapus_tidak_dihitung(self, w, hal):
        Project.objects.filter(id=hal.p_t1.id).update(deleted_at=datetime.datetime.now(datetime.timezone.utc))
        pohon = _pohon(w.admin, w)
        assert pohon[str(w.f_t1.id)]["jumlah_halaman"] == 0
        assert pohon[str(w.f_t1.id)]["project_id"] is None

    def test_jumlah_query_tidak_tumbuh_per_departemen(self, w, hal):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as sebelum:
            _pohon(w.staf_t2, w)
        p_t2 = Project.objects.create(name="T2 Board", identifier="WKT2", workspace=w.ws)
        p_hr = Project.objects.create(name="HR Board", identifier="WKHR", workspace=w.ws)
        DepartemenProject.objects.create(workspace=w.ws, departemen=w.t2, project=p_t2)
        DepartemenProject.objects.create(workspace=w.ws, departemen=w.hr, project=p_hr)
        for p in (p_t2, p_hr):
            _halaman(w, p, w.staf_t2, Page.PUBLIC_ACCESS, f"Publik {p.identifier}")
            _halaman(w, p, w.staf_t2, Page.PRIVATE_ACCESS, f"Privat {p.identifier}")
        with CaptureQueriesContext(connection) as sesudah:
            pohon = _pohon(w.staf_t2, w)
        assert len(sesudah) == len(sebelum)
        assert pohon[str(w.f_t2.id)]["jumlah_halaman"] == 2  # anggota T2 melihat privatnya
        assert pohon[str(w.f_hr.id)]["jumlah_halaman"] == 2  # pemilik privatnya


@pytest.mark.contract
@pytest.mark.django_db
class TestTautanHalamanKeProject:
    def _buka(self, user, hal):
        return {p["name"]: p["can_open_in_project"] for p in _klien(user).get(hal.url).data["pages"]}

    def test_bukan_anggota_project_tidak_bisa_membuka(self, w, hal):
        ProjectMember.objects.filter(project=hal.p_t1, member=w.staf_t2).delete()
        assert self._buka(w.staf_t2, hal) == {"Panduan publik": False}

    def test_anggota_project_membuka_publik(self, w, hal):
        _anggota(hal.p_t1, w.staf_t2, 15)
        assert self._buka(w.staf_t2, hal) == {"Panduan publik": True}

    def test_privat_orang_lain_tidak_terbuka_bagi_anggota_departemen(self, w, hal):
        _anggota(hal.p_t1, w.staf_t1, 15)
        buka = self._buka(w.staf_t1, hal)
        assert buka == {"Panduan publik": True, "Rahasia tim": True, "Catatan biasa": False}

    def test_manager_divisi_dan_direktur_membuka_privat(self, w, hal):
        for u in (w.mgr_sales, w.direktur):
            _anggota(hal.p_t1, u, 20)
            assert set(self._buka(u, hal).values()) == {True}, u.email

    def test_daftar_sama_dengan_detail(self, w, hal):
        for u in (w.staf_t1, w.mgr_sales, w.biasa, w.staf_t2):
            for p in _klien(u).get(hal.url).data["pages"]:
                detail = _klien(u).get(f"{w.base}pages/{p['id']}/").data
                assert detail["can_open_in_project"] == p["can_open_in_project"], (u.email, p["name"])


@pytest.mark.contract
@pytest.mark.django_db
class TestSampahPerFolder:
    def test_saringan_folder_memotong_ke_subpohon(self, w):
        m1 = _materi(w, w.f_t1, w.staf_t1, "a.pdf")
        m2 = _materi(w, w.topik_t2, w.staf_t2, "b.pdf")
        for m, u in ((m1, w.staf_t1), (m2, w.staf_t2)):
            assert _klien(u).delete(f"{w.base}materials/{m.id}/").status_code == status.HTTP_204_NO_CONTENT
        k = _klien(w.mgr_sales)
        ambil = lambda f: {m["id"] for m in k.get(f"{w.base}trash/", {"folder": str(f.id)}).data["materials"]}  # noqa: E731
        assert ambil(w.f_t1) == {str(m1.id)}
        assert ambil(w.f_t2) == {str(m2.id)}  # sub-topik ikut
        assert ambil(w.f_sales) == {str(m1.id), str(m2.id)}
        assert ambil(w.f_hrga) == set()

    def test_saringan_tidak_menambah_hak(self, w):
        m2 = _materi(w, w.f_t2, w.staf_t2, "b.pdf")
        _klien(w.staf_t2).delete(f"{w.base}materials/{m2.id}/")
        res = _klien(w.staf_t1).get(f"{w.base}trash/", {"folder": str(w.f_t2.id)})
        assert res.status_code == 200 and res.data["materials"] == [] and res.data["folders"] == []

    def test_folder_sampah_ikut_tersaring(self, w):
        sub = _topik(w, w.f_t1, "Akan dihapus")
        k = _klien(w.spv_t1)
        assert k.post(f"{w.base}folders/{sub.id}/archive/").status_code == 200
        assert k.delete(f"{w.base}folders/{sub.id}/").status_code == status.HTTP_204_NO_CONTENT
        assert [f["id"] for f in k.get(f"{w.base}trash/", {"folder": str(w.f_t1.id)}).data["folders"]] == [str(sub.id)]
        assert _klien(w.mgr_sales).get(f"{w.base}trash/", {"folder": str(w.f_t2.id)}).data["folders"] == []

    def test_folder_salah_ditolak(self, w):
        k = _klien(w.admin)
        assert k.get(f"{w.base}trash/", {"folder": "bukan-id"}).status_code == status.HTTP_400_BAD_REQUEST
        assert k.get(f"{w.base}trash/", {"folder": str(uuid.uuid4())}).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.contract
@pytest.mark.django_db
class TestCariHalaman:
    """Pencarian Wiki ikut mencari halaman departemen, dengan izin yang sama."""

    def _cari(self, user, w, q):
        res = _klien(user).get(f"{w.base}search/", {"q": q})
        assert res.status_code == status.HTTP_200_OK, res.data
        return res.data["pages"]

    def test_halaman_ketemu_lewat_judul_dan_isi(self, w, hal):
        isi = Page.objects.get(id=hal.publik.id)
        isi.description_html = "<p>Langkah pemasangan mesin reflow di lini dua.</p>"
        isi.save()
        by_judul = self._cari(w.staf_t1, w, "panduan")
        assert [p["id"] for p in by_judul] == [str(hal.publik.id)]
        assert by_judul[0]["project_id"] == str(hal.p_t1.id)
        by_isi = self._cari(w.staf_t1, w, "reflow")
        assert [p["id"] for p in by_isi] == [str(hal.publik.id)]
        assert "reflow" in by_isi[0]["cuplikan"]
        # Salah ketik di isi juga ketemu.
        assert [p["id"] for p in self._cari(w.staf_t1, w, "pemasagan")] == [str(hal.publik.id)]

    def test_izin_sama_dengan_daftar_halaman(self, w, hal):
        """Halaman privat hanya muncul untuk yang berhak; arsip dan halaman lepas tidak pernah."""
        for u in (w.admin, w.direktur, w.mgr_sales, w.staf_t1, w.spv_t1, w.biasa, w.staf_t2, w.mgr_hrga):
            terlihat = {p["name"] for p in _klien(u).get(hal.url).data["pages"]}
            ditemukan = set()
            for kata in ("panduan", "rahasia", "catatan"):
                ditemukan |= {p["name"] for p in self._cari(u, w, kata)}
            assert ditemukan == terlihat, u.email
        assert self._cari(w.admin, w, "lama") == []
        assert self._cari(w.admin, w, "Bukan departemen") == []
