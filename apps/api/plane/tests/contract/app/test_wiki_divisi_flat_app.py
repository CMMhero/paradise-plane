# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Wiki divisi tanpa sub-topik
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""
Kontrak struktur Wiki yang disederhanakan (keputusan user 2026-10-24):

    - hanya folder divisi, tanpa sub-topik (buat halaman ber-parent -> 403),
    - materi ditaruh langsung di folder divisinya,
    - hapus materi: pengunggah, admin/kepala divisi, SPV divisi, atau Super Admin,
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
    return ProjectMember.objects.create(workspace=workspace, project=project, member=user, role=role)


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
        return admin, anggota, pengunggah, spv, wiki.wiki, wiki.div, folder, materi

    def _url_buat(self, workspace, project_id):
        return f"/api/workspaces/{workspace.slug}/projects/{project_id}/pages/"

    def _url_hapus_materi(self, workspace, project_id, asset_id):
        return f"/api/assets/v2/workspaces/{workspace.slug}/projects/{project_id}/{asset_id}/"

    @pytest.mark.django_db
    def test_buat_sub_topik_ditolak(self, workspace, siap):
        _, anggota, _, _, wiki_p, _, folder, _ = siap
        res = _klien(anggota).post(
            self._url_buat(workspace, wiki_p.id), {"name": "Topik liar", "parent": str(folder.id)}, format="json"
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_pengunggah_boleh_hapus_materinya(self, workspace, siap):
        _, _, pengunggah, _, wiki_p, _, _, materi = siap
        res = _klien(pengunggah).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_anggota_biasa_tidak_boleh_hapus_materi_orang(self, workspace, siap):
        _, anggota, _, _, wiki_p, _, _, materi = siap
        res = _klien(anggota).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_spv_divisi_boleh_hapus_materi_anggota(self, workspace, siap):
        _, _, _, spv, wiki_p, _, _, materi = siap
        res = _klien(spv).delete(self._url_hapus_materi(workspace, wiki_p.id, materi.id))
        assert res.status_code == status.HTTP_204_NO_CONTENT


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
