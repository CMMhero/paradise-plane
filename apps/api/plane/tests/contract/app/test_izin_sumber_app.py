# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji izin per sumber (KEP-85)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kepemilikan + hierarki untuk sumber SELAIN work item (KEP-85).

Dua lapis yang diuji:

1. `PenilaiIzin` langsung: admin selalu lolos, pemilik lolos, staf tidak bisa
   menyentuh milik orang lain, supervisor atas bawahannya lolos tapi tidak atas
   rekan setingkat, pilihan God Mode (pemilik saja / setiap anggota) benar-benar
   mengubah hasil, dan ambang struktur (20/30/90) dibatasi project yang diawasi.
2. Endpoint: aturan itu benar-benar ditegakkan di module, view, komentar
   (termasuk API v1 yang dulu tanpa cek penulis sama sekali), state, dan arsip
   project.

Semua anggota project di sini sengaja ber-role 20 (admin project): itulah keadaan
kantor ini, dan role itu tidak boleh lagi memberi wewenang atas barang orang lain.
Setelan diubah lewat baris `InstanceConfiguration`, persis yang ditulis God Mode.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueComment,
    IssueView,
    JabatanOrganisasi,
    Module,
    ModuleMember,
    Page,
    Project,
    ProjectMember,
    ProjectPage,
    State,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)
from plane.license.models import InstanceConfiguration
from plane.utils import saklar_instance as si
from plane.utils.izin_sumber import PenilaiIzin

# ---------------------------------------------------------------------------
# Pembantu
# ---------------------------------------------------------------------------


def _setel(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": str(nilai), "category": "PARADISE", "is_encrypted": False}
    )


def _user(prefix, workspace, role=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_name="Uji"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _anggota(project, user, role=20):
    ProjectMember.objects.update_or_create(
        project=project, member=user, workspace=project.workspace, defaults={"role": role, "is_active": True}
    )


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _klien_token(user):
    token = APIToken.objects.create(user=user, label=f"uji-{uuid4().hex[:6]}", user_type=0)
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token.token)
    return client


def _pemilik(obj, user, kolom="created_by"):
    """BaseModel.save() mengisi created_by dari crum (kosong di tes), jadi ditimpa."""
    type(obj).objects.filter(pk=obj.pk).update(**{kolom: user})
    obj.refresh_from_db()
    return obj


@pytest.fixture
def org(db, workspace, create_user):
    """SALES -> SMT1 (P1) dan SMT2 (P2).

    P1: staf, staf2, sup, sup_b (rekan setingkat sup), tamu. P2: sup2 (supervisor
    departemen lain). Manager divisi SALES, direktur. Admin workspace = create_user.
    """
    o = type("Org", (), {})()
    o.ws = workspace
    o.admin = create_user
    o.p1 = Project.objects.create(name="SMT1 Board", identifier="IZP1", workspace=workspace)
    o.p2 = Project.objects.create(name="SMT2 Board", identifier="IZP2", workspace=workspace)
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="Sales Team 1")
    o.smt2 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT2", nama="Sales Team 2")
    DepartemenProject.objects.create(workspace=workspace, departemen=o.smt1, project=o.p1)
    DepartemenProject.objects.create(workspace=workspace, departemen=o.smt2, project=o.p2)

    o.staf = _user("staf", workspace)
    o.staf2 = _user("staf2", workspace)
    o.sup = _user("sup", workspace)
    o.sup_b = _user("supb", workspace)
    o.sup2 = _user("sup2", workspace)
    o.manager = _user("mgr", workspace)
    o.direktur = _user("dir", workspace)
    o.tamu = _user("tamu", workspace, role=5)
    for u, tingkat, dept in (
        (o.staf, TINGKAT_MEMBER, o.smt1),
        (o.staf2, TINGKAT_MEMBER, o.smt1),
        (o.sup, TINGKAT_SUPERVISOR, o.smt1),
        (o.sup_b, TINGKAT_SUPERVISOR, o.smt1),
        (o.sup2, TINGKAT_SUPERVISOR, o.smt2),
    ):
        JabatanOrganisasi.objects.create(workspace=workspace, member=u, tingkat=tingkat, departemen=dept)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.manager, tingkat=TINGKAT_MANAGER, divisi=o.sales)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.direktur, tingkat=TINGKAT_DIREKTUR)

    for u in (o.admin, o.staf, o.staf2, o.sup, o.sup_b, o.manager, o.direktur):
        _anggota(o.p1, u)
    _anggota(o.p1, o.tamu, role=5)
    for u in (o.admin, o.sup2, o.manager, o.direktur):
        _anggota(o.p2, u)
    return o


def _boleh(user, org, kunci, **kw):
    return PenilaiIzin(user, org.ws.id).boleh(kunci, **kw)


# ---------------------------------------------------------------------------
# 1. PenilaiIzin
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestPenilaiIsi:
    K = si.PERM_MODULE_DELETE

    @pytest.mark.django_db
    def test_admin_workspace_selalu_lolos(self, org):
        assert _boleh(org.admin, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_pemilik_lolos(self, org):
        assert _boleh(org.staf, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_yang_terlibat_lolos(self, org):
        assert _boleh(org.staf2, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id, terlibat_ids=[org.staf2.id])

    @pytest.mark.django_db
    def test_staf_bukan_pemilik_ditolak_walau_admin_project(self, org):
        assert not _boleh(org.staf2, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_supervisor_atas_bawahan_lolos(self, org):
        assert _boleh(org.sup, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_manager_dan_direktur_atas_staf_lolos(self, org):
        assert _boleh(org.manager, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)
        assert _boleh(org.direktur, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_supervisor_rekan_setingkat_ditolak(self, org):
        assert not _boleh(org.sup, org, self.K, project_id=org.p1.id, pemilik_id=org.sup_b.id)

    @pytest.mark.django_db
    def test_supervisor_departemen_lain_ditolak(self, org):
        assert not _boleh(org.sup2, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_pemilik_saja_menolak_atasan(self, org):
        _setel(self.K, si.IZIN_PEMILIK_SAJA)
        assert not _boleh(org.sup, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)
        assert _boleh(org.staf, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)
        assert _boleh(org.admin, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_semua_anggota_meloloskan_anggota_bukan_tamu(self, org):
        _setel(self.K, si.IZIN_SEMUA_ANGGOTA)
        assert _boleh(org.staf2, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)
        assert not _boleh(org.tamu, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)
        # Anggota project LAIN tidak ikut lolos.
        assert not _boleh(org.sup2, org, self.K, project_id=org.p1.id, pemilik_id=org.staf.id)

    @pytest.mark.django_db
    def test_sumber_workspace_atasan_di_salah_satu_project(self, org):
        # View workspace: tanpa project, atasan dinilai lewat project yang ia awasi.
        assert _boleh(org.sup, org, si.PERM_VIEW_DELETE, pemilik_id=org.staf.id)
        assert not _boleh(org.staf2, org, si.PERM_VIEW_DELETE, pemilik_id=org.staf.id)
        assert not _boleh(org.sup, org, si.PERM_VIEW_DELETE, pemilik_id=org.sup_b.id)


@pytest.mark.contract
class TestPenilaiStruktur:
    K = si.PERM_PROJECT_WORKFLOW

    @pytest.mark.django_db
    def test_bawaan_supervisor_di_project_yang_diawasi(self, org):
        assert _boleh(org.sup, org, self.K, project_id=org.p1.id)
        assert not _boleh(org.staf, org, self.K, project_id=org.p1.id)
        assert not _boleh(org.sup, org, self.K, project_id=org.p2.id)
        assert _boleh(org.admin, org, self.K, project_id=org.p1.id)

    @pytest.mark.django_db
    def test_ambang_manager(self, org):
        _setel(self.K, si.STRUKTUR_MANAGER)
        assert not _boleh(org.sup, org, self.K, project_id=org.p1.id)
        assert _boleh(org.manager, org, self.K, project_id=org.p1.id)
        assert _boleh(org.direktur, org, self.K, project_id=org.p1.id)

    @pytest.mark.django_db
    def test_admin_saja(self, org):
        _setel(self.K, si.STRUKTUR_ADMIN_SAJA)
        assert not _boleh(org.manager, org, self.K, project_id=org.p1.id)
        assert not _boleh(org.direktur, org, self.K, project_id=org.p1.id)
        assert _boleh(org.admin, org, self.K, project_id=org.p1.id)

    @pytest.mark.django_db
    def test_tanpa_project_ditolak_kecuali_admin(self, org):
        assert not _boleh(org.direktur, org, self.K)
        assert _boleh(org.admin, org, self.K)


# ---------------------------------------------------------------------------
# 2. Endpoint
# ---------------------------------------------------------------------------


def _module(org, pembuat, **kw):
    module = Module.objects.create(name=f"Module {uuid4().hex[:6]}", project=org.p1, workspace=org.ws, **kw)
    return _pemilik(module, pembuat)


def _url_p1(org, akhir):
    return f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/{akhir}"


@pytest.mark.contract
class TestModuleEndpoint:
    @pytest.mark.django_db
    def test_staf_bukan_pemilik_tidak_bisa_ubah_atau_hapus(self, org):
        module = _module(org, org.staf)
        url = _url_p1(org, f"modules/{module.id}/")
        ubah = _klien(org.staf2).patch(url, {"name": "Dibajak"}, format="json")
        assert ubah.status_code == status.HTTP_403_FORBIDDEN, ubah.data
        hapus = _klien(org.staf2).delete(url)
        assert hapus.status_code == status.HTTP_403_FORBIDDEN
        assert Module.objects.filter(pk=module.pk).exists()

    @pytest.mark.django_db
    def test_pemilik_bisa_ubah_dan_hapus(self, org):
        module = _module(org, org.staf)
        url = _url_p1(org, f"modules/{module.id}/")
        assert _klien(org.staf).patch(url, {"name": "Milikku"}, format="json").status_code == status.HTTP_200_OK
        assert _klien(org.staf).delete(url).status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_atasan_bisa_hapus_module_bawahan(self, org):
        module = _module(org, org.staf)
        hapus = _klien(org.sup).delete(_url_p1(org, f"modules/{module.id}/"))
        assert hapus.status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_anggota_module_bisa_ubah(self, org):
        module = _module(org, org.staf)
        ModuleMember.objects.create(module=module, member=org.staf2, project=org.p1, workspace=org.ws)
        ubah = _klien(org.staf2).patch(_url_p1(org, f"modules/{module.id}/"), {"name": "Bersama"}, format="json")
        assert ubah.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestViewEndpoint:
    def _view(self, org, pemilik, akses=1):
        return IssueView.objects.create(
            name="View uji", project=org.p1, workspace=org.ws, owned_by=pemilik, access=akses
        )

    @pytest.mark.django_db
    def test_hapus_view_orang_lain_ditolak(self, org):
        view = self._view(org, org.staf)
        hapus = _klien(org.staf2).delete(_url_p1(org, f"views/{view.id}/"))
        assert hapus.status_code == status.HTTP_403_FORBIDDEN
        assert IssueView.objects.filter(pk=view.pk).exists()

    @pytest.mark.django_db
    def test_pemilik_dan_atasan_bisa_hapus(self, org):
        milik = self._view(org, org.staf)
        assert _klien(org.staf).delete(_url_p1(org, f"views/{milik.id}/")).status_code == status.HTTP_204_NO_CONTENT
        bawahan = self._view(org, org.staf)
        assert _klien(org.sup).delete(_url_p1(org, f"views/{bawahan.id}/")).status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_atasan_tidak_bisa_ganti_akses_view_bawahan(self, org):
        view = self._view(org, org.staf)
        res = _klien(org.sup).patch(_url_p1(org, f"views/{view.id}/"), {"access": 0}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestKomentarApiV1:
    def _komentar(self, org, penulis):
        issue = Issue.objects.create(name="Tugas", project=org.p1, workspace=org.ws)
        komentar = IssueComment.objects.create(
            issue=issue, project=org.p1, workspace=org.ws, actor=penulis, comment_html="<p>asli</p>"
        )
        return issue, komentar

    def _url(self, org, issue, komentar):
        return f"/api/v1/workspaces/{org.ws.slug}/projects/{org.p1.id}/issues/{issue.id}/comments/{komentar.id}/"

    @pytest.mark.django_db
    def test_bukan_penulis_tidak_bisa_ubah_atau_hapus(self, org):
        issue, komentar = self._komentar(org, org.staf)
        klien = _klien_token(org.staf2)
        ubah = klien.patch(self._url(org, issue, komentar), {"comment_html": "<p>dibajak</p>"}, format="json")
        assert ubah.status_code == status.HTTP_403_FORBIDDEN
        assert klien.delete(self._url(org, issue, komentar)).status_code == status.HTTP_403_FORBIDDEN
        komentar.refresh_from_db()
        assert komentar.comment_html == "<p>asli</p>"

    @pytest.mark.django_db
    def test_penulis_bisa_ubah(self, org):
        issue, komentar = self._komentar(org, org.staf)
        ubah = _klien_token(org.staf).patch(
            self._url(org, issue, komentar), {"comment_html": "<p>diubah</p>"}, format="json"
        )
        assert ubah.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestKomentarApp:
    @pytest.mark.django_db
    def test_admin_project_bukan_penulis_tidak_bisa_hapus(self, org):
        issue = Issue.objects.create(name="Tugas", project=org.p1, workspace=org.ws)
        komentar = IssueComment.objects.create(
            issue=issue, project=org.p1, workspace=org.ws, actor=org.staf, comment_html="<p>x</p>"
        )
        url = _url_p1(org, f"issues/{issue.id}/comments/{komentar.id}/")
        assert _klien(org.staf2).delete(url).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(org.sup).delete(url).status_code == status.HTTP_204_NO_CONTENT


@pytest.mark.contract
class TestStrukturEndpoint:
    @pytest.mark.django_db
    def test_staf_tidak_bisa_ubah_state(self, org):
        state = State.objects.create(name="Uji", project=org.p1, workspace=org.ws, group="started", color="#000")
        url = _url_p1(org, f"states/{state.id}/")
        assert _klien(org.staf).patch(url, {"name": "Diubah staf"}, format="json").status_code == 403
        assert _klien(org.sup).patch(url, {"name": "Diubah sup"}, format="json").status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_staf_tidak_bisa_arsip_project(self, org):
        url = _url_p1(org, "archive/")
        assert _klien(org.staf).post(url).status_code == status.HTTP_403_FORBIDDEN
        org.p1.refresh_from_db()
        assert org.p1.archived_at is None
        assert _klien(org.sup).post(url).status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_staf_admin_project_tidak_bisa_ubah_setelan_project(self, org):
        url = f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/"
        assert _klien(org.staf).patch(url, {"name": "Dibajak"}, format="json").status_code == 403


@pytest.mark.contract
class TestHalamanDanTrash:
    def _halaman(self, org, pemilik, arsip=False):
        halaman = Page.objects.create(
            workspace=org.ws,
            owned_by=pemilik,
            access=Page.PUBLIC_ACCESS,
            name="Halaman uji",
            archived_at=timezone.now() if arsip else None,
        )
        ProjectPage.objects.create(workspace=org.ws, project=org.p1, page=halaman)
        return halaman

    @pytest.mark.django_db
    def test_hapus_halaman_orang_lain_ditolak_atasan_boleh(self, org):
        halaman = self._halaman(org, org.staf, arsip=True)
        url = _url_p1(org, f"pages/{halaman.id}/")
        assert _klien(org.staf2).delete(url).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(org.sup).delete(url).status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_atasan_bisa_ubah_halaman_bawahan(self, org):
        halaman = self._halaman(org, org.staf)
        url = _url_p1(org, f"pages/{halaman.id}/")
        assert _klien(org.staf2).patch(url, {"name": "X"}, format="json").status_code == 403
        assert _klien(org.sup).patch(url, {"name": "Y"}, format="json").status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_trash_pulihkan_milik_sendiri_tapi_bukan_milik_orang_lain(self, org):
        milik = self._halaman(org, org.staf)
        orang_lain = self._halaman(org, org.staf2)
        milik.delete()
        orang_lain.delete()
        url = _url_p1(org, "trash/page/{}/")
        assert _klien(org.staf).post(url.format(milik.id)).status_code == status.HTTP_200_OK
        assert _klien(org.staf).post(url.format(orang_lain.id)).status_code == status.HTTP_403_FORBIDDEN
        # Buang permanen = wewenang struktur: staf tidak, supervisor project ini ya.
        assert _klien(org.staf).delete(url.format(orang_lain.id)).status_code == status.HTTP_403_FORBIDDEN
        assert _klien(org.sup).delete(url.format(orang_lain.id)).status_code == status.HTTP_204_NO_CONTENT
