# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Wiki divisi tanpa sub-topik
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Kontrak struktur Wiki yang disederhanakan (keputusan user 2026-10-24):

    - hanya folder divisi, tanpa sub-topik (buat halaman ber-parent -> 403),
    - materi ditaruh langsung di folder divisinya,
    - folder & sub-topik: HANYA admin workspace atau Super Admin,
    - unggah materi: admin, atau anggota departemen pemilik folder (KEP-51),
    - ubah/hapus materi: admin, pengunggahnya, atau atasannya (KEP-51, KEP-85),
    - folder non-divisi tanpa pemilik = General (semua anggota Wiki),
    - governance selalu aktif untuk project WIKI tanpa saklar,
    - folder divisi dibuat otomatis per Divisi (`pastikan_folder_divisi`).
"""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    FileAsset,
    JabatanOrganisasi,
    Page,
    Project,
    ProjectMember,
    ProjectPage,
    TINGKAT_SUPERVISOR,
    User,
    WikiFolderAccess,
    WikiGovernedProject,
    WorkspaceMember,
)
from plane.utils.wiki_access import pastikan_folder_divisi


def _user(prefix, workspace):
    user = User.objects.create(email=f"{prefix}-{uuid.uuid4().hex[:8]}@uji.id", username=f"{prefix}-wiki")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _anggota(workspace, project, user, role):
    # Sinyal bawaan bisa sudah memasukkan user ke project (mis. bawaan member
    # baru), jadi tetapkan peran yang diuji alih-alih membuat baris ganda.
    pm, _ = ProjectMember.objects.update_or_create(
        project=project, member=user, deleted_at__isnull=True,
        defaults={"workspace": workspace, "role": role, "is_active": True},
    )
    return pm


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def wiki(db, workspace):
    w = type("Wiki", (), {})()
    w.ws = workspace
    w.wiki = Project.objects.create(name="Wiki", identifier="WIKI", workspace=workspace)
    WikiGovernedProject.objects.create(workspace=workspace, project=w.wiki)
    w.div = Project.objects.create(name="Divisi IT", identifier="DIVT", workspace=workspace)
    return w


@pytest.mark.contract
class TestWikiTanpaSubTopik:
    @pytest.fixture
    def siap(self, db, workspace, wiki):
        admin = _user("admin", workspace)
        anggota = _user("anggota", workspace)
        pengunggah = _user("pengunggah", workspace)
        spv = _user("spv", workspace)
        for u, role in ((admin, 20), (anggota, 15), (pengunggah, 15), (spv, 15)):
            _anggota(workspace, wiki.wiki, u, role)
            _anggota(workspace, wiki.div, u, role)
        JabatanOrganisasi.objects.create(workspace=workspace, member=spv, tingkat=TINGKAT_SUPERVISOR)

        folder = Page.objects.create(
            workspace=workspace, owned_by=admin, name="Divisi IT", access=Page.PUBLIC_ACCESS
        )
        ProjectPage.objects.create(workspace=workspace, project=wiki.wiki, page=folder)
        WikiFolderAccess.objects.create(workspace=workspace, project=wiki.wiki, folder=folder, division=wiki.div)

        materi = FileAsset.objects.create(
            attributes={"name": "panduan.pdf", "title": "Panduan", "type": "application/pdf"},
            asset=f"{workspace.id}/panduan.pdf",
            size=1024,
            workspace=workspace,
            project=wiki.wiki,
            page=folder,
            created_by=pengunggah,
            entity_type=FileAsset.EntityTypeContext.WIKI_MATERIAL,
            is_uploaded=True,
        )
        # BaseModel.save() menimpa created_by dari request (kosong di tes), jadi
        # pengunggahnya ditetapkan lewat update() seperti jalur API yang asli.
        FileAsset.objects.filter(id=materi.id).update(created_by=pengunggah)
        materi.refresh_from_db()
        return admin, anggota, pengunggah, spv, wiki.wiki, wiki.div, folder, materi

    def _url_buat(self, workspace, project_id):
        return f"/api/workspaces/{workspace.slug}/projects/{project_id}/pages/"

    def _url_hapus_materi(self, workspace, project_id, asset_id):
        return f"/api/assets/v2/workspaces/{workspace.slug}/projects/{project_id}/{asset_id}/"

    @pytest.mark.django_db
    def test_anggota_biasa_tidak_boleh_buat_sub_topik(self, workspace, siap):
        _, anggota, _, _, wiki_p, _, folder, _ = siap
        res = _klien(anggota).post(
            self._url_buat(workspace, wiki_p.id), {"name": "Topik liar", "parent": str(folder.id)}, format="json"
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_workspace_boleh_buat_sub_topik_di_bawah_folder_wiki(self, workspace, siap):
        _, _, _, _, wiki_p, _, folder, _ = siap
        admin_ws = _user("adminsub", workspace)
        WorkspaceMember.objects.filter(workspace=workspace, member=admin_ws).update(role=20)
        _anggota(workspace, wiki_p, admin_ws, 15)
        res = _klien(admin_ws).post(
            self._url_buat(workspace, wiki_p.id), {"name": "Topik baru", "parent": str(folder.id)}, format="json"
        )
        assert res.status_code == status.HTTP_201_CREATED, getattr(res, "data", None)

    @pytest.mark.django_db
    def test_sub_topik_dengan_induk_halaman_project_lain_ditolak(self, workspace, siap):
        _, _, _, _, wiki_p, div, _, _ = siap
        admin_ws = _user("adminasing", workspace)
        WorkspaceMember.objects.filter(workspace=workspace, member=admin_ws).update(role=20)
        _anggota(workspace, wiki_p, admin_ws, 15)
        asing = Page.objects.create(workspace=workspace, owned_by=admin_ws, name="Asing", access=Page.PUBLIC_ACCESS)
        ProjectPage.objects.create(workspace=workspace, project=div, page=asing)
        res = _klien(admin_ws).post(
            self._url_buat(workspace, wiki_p.id), {"name": "X", "parent": str(asing.id)}, format="json"
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_pengunggah_boleh_hapus_materinya_sendiri(self, workspace, siap):
        _, _, pengunggah, _, wiki_p, _, _, materi = siap
        res = _klien(pengunggah).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_anggota_biasa_tidak_boleh_hapus_materi_orang(self, workspace, siap):
        _, anggota, _, _, wiki_p, _, _, materi = siap
        res = _klien(anggota).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    # KEP-85 (4 Nov 2026) membalik KEP-51 untuk atasan: bawaan PERM_WIKI_DELETE =
    # pengunggah + atasannya. "Pemilik saja" di God Mode mengembalikan aturan lama.
    @pytest.mark.django_db
    def test_spv_boleh_hapus_materi_bawahan_secara_bawaan(self, workspace, siap):
        _, _, _, spv, wiki_p, _, _, materi = siap
        res = _klien(spv).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_spv_TIDAK_boleh_hapus_materi_bawahan_kalau_pemilik_saja(self, workspace, siap):
        from plane.license.models import InstanceConfiguration  # noqa: PLC0415
        from plane.utils import saklar_instance as si  # noqa: PLC0415

        InstanceConfiguration.objects.update_or_create(
            key=si.PERM_WIKI_DELETE,
            defaults={"value": str(si.IZIN_PEMILIK_SAJA), "category": "PARADISE", "is_encrypted": False},
        )
        _, _, _, spv, wiki_p, _, _, materi = siap
        res = _klien(spv).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_admin_workspace_boleh_hapus_materi(self, workspace, siap):
        _, _, _, _, wiki_p, _, _, materi = siap
        admin_ws = _user("adminws", workspace)
        WorkspaceMember.objects.filter(workspace=workspace, member=admin_ws).update(role=20)
        _anggota(workspace, wiki_p, admin_ws, 15)
        res = _klien(admin_ws).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_anggota_departemen_boleh_unggah_ke_folder_divisinya(self, workspace, siap):
        from plane.utils.wiki_access import can_edit_wiki_page  # noqa: PLC0415

        _, anggota, _, _, _, _, folder, _ = siap
        assert can_edit_wiki_page(anggota, folder) is True

    @pytest.mark.django_db
    def test_bukan_anggota_departemen_tidak_boleh_unggah(self, workspace, siap):
        from plane.utils.wiki_access import can_edit_wiki_page  # noqa: PLC0415

        _, _, _, _, wiki_p, _, folder, _ = siap
        luar = _user("luar", workspace)
        _anggota(workspace, wiki_p, luar, 15)
        assert can_edit_wiki_page(luar, folder) is False

    @pytest.mark.django_db
    def test_guest_departemen_tidak_boleh_unggah(self, workspace, siap):
        from plane.utils.wiki_access import can_edit_wiki_page  # noqa: PLC0415

        _, _, _, _, wiki_p, div, folder, _ = siap
        tamu = _user("tamu", workspace)
        _anggota(workspace, wiki_p, tamu, 5)
        _anggota(workspace, div, tamu, 5)
        assert can_edit_wiki_page(tamu, folder) is False

    @pytest.mark.django_db
    def test_folder_non_divisi_tanpa_pemilik_jadi_general(self, workspace, siap):
        from plane.utils.wiki_access import can_edit_wiki_page  # noqa: PLC0415

        admin, _, _, _, wiki_p, _, _, _ = siap
        umum = Page.objects.create(workspace=workspace, owned_by=admin, name="General", access=Page.PUBLIC_ACCESS)
        ProjectPage.objects.create(workspace=workspace, project=wiki_p, page=umum)
        luar = _user("luar2", workspace)
        _anggota(workspace, wiki_p, luar, 15)
        assert can_edit_wiki_page(luar, umum) is True

    @pytest.mark.django_db
    def test_folder_divisi_tanpa_departemen_hanya_admin(self, workspace, siap):
        from plane.utils.wiki_access import can_edit_wiki_page  # noqa: PLC0415

        admin, anggota, _, _, wiki_p, _, _, _ = siap
        Divisi.objects.create(workspace=workspace, kode="FIN", nama="Keuangan")
        kosong = Page.objects.create(workspace=workspace, owned_by=admin, name="Keuangan", access=Page.PUBLIC_ACCESS)
        ProjectPage.objects.create(workspace=workspace, project=wiki_p, page=kosong)
        assert can_edit_wiki_page(anggota, kosong) is False

    @pytest.mark.django_db
    def test_izin_borongan_sama_dengan_resolver(self, workspace, siap):
        _, anggota, _, _, wiki_p, _, folder, _ = siap
        luar = _user("luar3", workspace)
        _anggota(workspace, wiki_p, luar, 15)
        url = f"/api/workspaces/{workspace.slug}/projects/{wiki_p.id}/wiki-permissions/"

        def bisa(user):
            data = _klien(user).get(url).data
            return next(f for f in data["folders"] if f["id"] == str(folder.id))["can_upload"]

        assert bisa(anggota) is True
        assert bisa(luar) is False

    @pytest.mark.django_db
    def test_anggota_tidak_boleh_ganti_nama_folder(self, workspace, siap):
        _, anggota, _, _, wiki_p, _, folder, _ = siap
        res = _klien(anggota).patch(
            f"/api/workspaces/{workspace.slug}/projects/{wiki_p.id}/wiki/folders/{folder.id}/",
            {"name": "Liar"},
            format="json",
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.contract
class TestGovernanceBawaan:
    @pytest.mark.django_db
    def test_project_wiki_selalu_ber_governance_tanpa_baris(self, db, workspace):
        from plane.utils.wiki_access import is_wiki_governed  # noqa: PLC0415

        wiki = Project.objects.create(name="Wiki", identifier="WIKI", workspace=workspace)
        lain = Project.objects.create(name="Lain", identifier="LAIN", workspace=workspace)
        assert is_wiki_governed(wiki.id) is True
        assert is_wiki_governed(lain.id) is False


@pytest.mark.contract
class TestFolderDivisiOtomatis:
    @pytest.mark.django_db
    def test_buat_folder_dan_pemilik_per_divisi(self, db, workspace):
        admin = _user("admin", workspace)
        wiki = Project.objects.create(name="Wiki", identifier="WIKI", workspace=workspace)
        divisi = Divisi.objects.create(workspace=workspace, kode="IT", nama="Teknologi Informasi")
        dep = Departemen.objects.create(workspace=workspace, divisi=divisi, kode="IT-SAP", nama="SAP")
        proj = Project.objects.create(name="SAP Board", identifier="SAPB", workspace=workspace)
        DepartemenProject.objects.create(workspace=workspace, departemen=dep, project=proj)

        hasil = pastikan_folder_divisi(workspace, actor=admin)

        assert hasil["dibuat"] == ["Teknologi Informasi"]
        folder = Page.objects.filter(
            workspace=workspace, parent__isnull=True, name="Teknologi Informasi", deleted_at__isnull=True
        ).first()
        assert folder is not None
        assert ProjectPage.objects.filter(project=wiki, page=folder, deleted_at__isnull=True).exists()
        pemilik = set(
            WikiFolderAccess.objects.filter(folder=folder, deleted_at__isnull=True).values_list(
                "division_id", flat=True
            )
        )
        assert pemilik == {proj.id}

    @pytest.mark.django_db
    def test_idempoten_tidak_ganda(self, db, workspace):
        admin = _user("admin", workspace)
        Project.objects.create(name="Wiki", identifier="WIKI", workspace=workspace)
        Divisi.objects.create(workspace=workspace, kode="IT", nama="Teknologi Informasi")

        pastikan_folder_divisi(workspace, actor=admin)
        hasil = pastikan_folder_divisi(workspace, actor=admin)

        assert hasil["dibuat"] == []
        assert (
            Page.objects.filter(workspace=workspace, parent__isnull=True, name="Teknologi Informasi").count() == 1
        )
