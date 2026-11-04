# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji quick link bersama & metadata otomatis (KEP-82)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Dikunci:

1. Hanya Super Admin / admin workspace yang boleh membuat, mengubah, menghapus link bersama.
2. Sasaran: semua orang, departemen (+ manager divisinya), divisi (+ semua departemennya).
3. Departemen sasaran yang terhapus TIDAK membuat link jadi untuk semua orang.
4. Judul & favicon diambil otomatis; judul/ikon manual menimpa tanpa menghapus yang otomatis,
   dan "pakai bawaan" mengembalikannya.
5. Quick link pribadi ikut mendapat judul & favicon otomatis; metadata tidak bisa ditulis klien.
"""

from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    Divisi,
    JabatanOrganisasi,
    QuickLinkBersama,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    User,
    WorkspaceMember,
    WorkspaceUserLink,
)
from plane.license.models import Instance, InstanceAdmin

URL = "/api/workspaces/{slug}/quick-links/shared/"
URL_DETAIL = "/api/workspaces/{slug}/quick-links/shared/{pk}/"
URL_PRIBADI = "/api/workspaces/{slug}/quick-links/"
FAVICON = "data:image/png;base64,iVBORw0KGgo="
IKON = {"in_use": "icon", "icon": {"name": "star", "color": "#ff0000", "background_color": "#fff"}}


def _situs(url):
    return {"title": f"  Situs\n {url.split('//')[1]}  ", "favicon": FAVICON, "favicon_url": url + "/favicon.ico"}


@pytest.fixture(autouse=True)
def tanpa_internet():
    with (
        mock.patch("plane.utils.quick_link.crawl_work_item_link_title_and_favicon", side_effect=_situs) as crawl,
        mock.patch("plane.bgtasks.quick_link_task.isi_metadata_quick_link.delay") as delay,
    ):
        yield type("Palsu", (), {"crawl": crawl, "delay": delay})


def _user(prefix, workspace, role=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.admin = create_user  # role 20 dari fixture workspace
    o.sales = Divisi.objects.create(workspace=workspace, kode="SLS", nama="Sales")
    o.hrga = Divisi.objects.create(workspace=workspace, kode="HR", nama="HRGA")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="SMT 1")
    o.smt2 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT2", nama="SMT 2")
    o.ga = Departemen.objects.create(workspace=workspace, divisi=o.hrga, kode="GA", nama="General Affairs")
    o.staf_smt1 = _user("smt1", workspace)
    o.staf_ga = _user("ga", workspace)
    o.manager_sales = _user("mgr", workspace)
    o.tanpa_tempat = _user("bebas", workspace)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.staf_smt1, tingkat=TINGKAT_MEMBER, departemen=o.smt1)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.staf_ga, tingkat=TINGKAT_MEMBER, departemen=o.ga)
    JabatanOrganisasi.objects.create(
        workspace=workspace, member=o.manager_sales, tingkat=TINGKAT_MANAGER, divisi=o.sales
    )
    return o


def _buat(org, **data):
    resp = _klien(org.admin).post(URL.format(slug=org.ws.slug), data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED, resp.data
    return resp.data


def _terlihat(org, user):
    resp = _klien(user).get(URL.format(slug=org.ws.slug))
    assert resp.status_code == status.HTTP_200_OK
    return {link["url"] for link in resp.data["links"]}


@pytest.mark.contract
@pytest.mark.django_db
class TestIzin:
    def test_member_biasa_tidak_boleh_menambah(self, org):
        resp = _klien(org.staf_smt1).post(URL.format(slug=org.ws.slug), {"url": "erp.example.com"}, format="json")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert not QuickLinkBersama.objects.exists()

    def test_member_biasa_tidak_boleh_mengubah_atau_menghapus(self, org):
        link = _buat(org, url="erp.example.com")
        klien = _klien(org.staf_smt1)
        detail = URL_DETAIL.format(slug=org.ws.slug, pk=link["id"])
        assert klien.patch(detail, {"title": "x"}, format="json").status_code == status.HTTP_403_FORBIDDEN
        assert klien.delete(detail).status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_bukan_admin_workspace_boleh(self, org):
        instance = Instance.objects.create(
            instance_name="uji",
            instance_id=f"uji-{uuid4().hex[:8]}",
            current_version="uji",
            last_checked_at=timezone.now(),
        )
        super_admin = _user("super", org.ws, role=15)
        InstanceAdmin.objects.create(instance=instance, user=super_admin, role=20)
        resp = _klien(super_admin).post(URL.format(slug=org.ws.slug), {"url": "erp.example.com"}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED

    def test_hanya_admin_menerima_daftar_semua_dan_organisasi(self, org):
        _buat(org, url="erp.example.com")
        biasa = _klien(org.staf_smt1).get(URL.format(slug=org.ws.slug)).data
        assert biasa["boleh_kelola"] is False and "semua" not in biasa and "organisasi" not in biasa
        admin = _klien(org.admin).get(URL.format(slug=org.ws.slug)).data
        assert admin["boleh_kelola"] is True
        assert {v["kode"] for v in admin["organisasi"]} == {"SLS", "HR"}


@pytest.mark.contract
@pytest.mark.django_db
class TestSasaran:
    def test_untuk_semua_terlihat_semua_orang(self, org):
        _buat(org, url="erp.example.com")
        for user in (org.staf_smt1, org.staf_ga, org.manager_sales, org.tanpa_tempat):
            assert _terlihat(org, user) == {"https://erp.example.com"}

    def test_departemen_terlihat_anggotanya_dan_manager_divisinya(self, org):
        _buat(org, url="smt1.example.com", cakupan="organisasi", departemen_ids=[str(org.smt1.id)])
        assert _terlihat(org, org.staf_smt1) == {"https://smt1.example.com"}
        assert _terlihat(org, org.manager_sales) == {"https://smt1.example.com"}
        assert _terlihat(org, org.staf_ga) == set()
        assert _terlihat(org, org.tanpa_tempat) == set()

    def test_divisi_terlihat_semua_departemennya(self, org):
        _buat(org, url="sales.example.com", cakupan="organisasi", divisi_ids=[str(org.sales.id)])
        assert _terlihat(org, org.staf_smt1) == {"https://sales.example.com"}
        assert _terlihat(org, org.manager_sales) == {"https://sales.example.com"}
        assert _terlihat(org, org.staf_ga) == set()

    def test_admin_melihat_semua_di_daftar_kelola_tapi_links_hanya_sasarannya(self, org):
        _buat(org, url="ga.example.com", cakupan="organisasi", departemen_ids=[str(org.ga.id)])
        data = _klien(org.admin).get(URL.format(slug=org.ws.slug)).data
        assert data["links"] == []
        assert [link["url"] for link in data["semua"]] == ["https://ga.example.com"]

    def test_departemen_terhapus_tidak_menjadikan_link_untuk_semua(self, org):
        _buat(org, url="ga.example.com", cakupan="organisasi", departemen_ids=[str(org.ga.id)])
        org.ga.delete()
        assert _terlihat(org, org.tanpa_tempat) == set()
        assert _terlihat(org, org.staf_smt1) == set()

    def test_organisasi_tanpa_sasaran_ditolak(self, org):
        resp = _klien(org.admin).post(
            URL.format(slug=org.ws.slug), {"url": "x.example.com", "cakupan": "organisasi"}, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_sasaran_workspace_lain_ditolak(self, org, create_user):
        from plane.db.models import Workspace  # noqa: PLC0415

        lain = Workspace.objects.create(name="Lain", owner=create_user, slug=f"lain-{uuid4().hex[:6]}")
        asing = Divisi.objects.create(workspace=lain, kode="X", nama="Asing")
        resp = _klien(org.admin).post(
            URL.format(slug=org.ws.slug),
            {"url": "x.example.com", "cakupan": "organisasi", "divisi_ids": [str(asing.id)]},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_ganti_ke_semua_mengosongkan_sasaran(self, org):
        link = _buat(org, url="ga.example.com", cakupan="organisasi", departemen_ids=[str(org.ga.id)])
        resp = _klien(org.admin).patch(
            URL_DETAIL.format(slug=org.ws.slug, pk=link["id"]), {"cakupan": "semua"}, format="json"
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["departemen_ids"] == [] and resp.data["cakupan"] == "semua"
        assert _terlihat(org, org.tanpa_tempat) == {"https://ga.example.com"}

    def test_hapus(self, org):
        link = _buat(org, url="erp.example.com")
        resp = _klien(org.admin).delete(URL_DETAIL.format(slug=org.ws.slug, pk=link["id"]))
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert _terlihat(org, org.staf_smt1) == set()


@pytest.mark.contract
@pytest.mark.django_db
class TestJudulDanIkon:
    def test_judul_dan_favicon_diambil_otomatis(self, org):
        link = _buat(org, url="erp.example.com")
        assert link["title"] is None
        assert link["metadata"]["title"] == "Situs erp.example.com"
        assert link["metadata"]["favicon"] == FAVICON

    def test_judul_manual_lalu_kembali_ke_bawaan(self, org):
        link = _buat(org, url="erp.example.com", title="ERP Kantor")
        assert link["title"] == "ERP Kantor"
        assert link["metadata"]["title"] == "Situs erp.example.com"
        resp = _klien(org.admin).patch(URL_DETAIL.format(slug=org.ws.slug, pk=link["id"]), {"title": ""}, format="json")
        assert resp.data["title"] is None
        assert resp.data["metadata"]["title"] == "Situs erp.example.com"

    def test_url_berubah_mengambil_ulang(self, org, tanpa_internet):
        link = _buat(org, url="erp.example.com")
        detail = URL_DETAIL.format(slug=org.ws.slug, pk=link["id"])
        _klien(org.admin).patch(detail, {"title": "Baru"}, format="json")
        assert tanpa_internet.crawl.call_count == 1
        resp = _klien(org.admin).patch(detail, {"url": "crm.example.com"}, format="json")
        assert tanpa_internet.crawl.call_count == 2
        assert resp.data["metadata"]["title"] == "Situs crm.example.com"

    def test_ikon_dipilih_lalu_dihapus_dengan_null(self, org):
        link = _buat(org, url="erp.example.com", logo_props=IKON)
        assert link["metadata"]["logo_props"] == IKON
        assert link["metadata"]["favicon"] == FAVICON
        detail = URL_DETAIL.format(slug=org.ws.slug, pk=link["id"])
        resp = _klien(org.admin).patch(detail, {"logo_props": None}, format="json")
        assert "logo_props" not in resp.data["metadata"]
        assert resp.data["metadata"]["favicon"] == FAVICON

    def test_emoji_dipilih_dan_kunci_asing_dibuang(self, org):
        link = _buat(
            org,
            url="erp.example.com",
            logo_props={"in_use": "emoji", "emoji": {"value": "128512", "x": 1}, "icon": {"name": "star"}, "z": 2},
        )
        assert link["metadata"]["logo_props"] == {"in_use": "emoji", "emoji": {"value": "128512"}}

    def test_logo_kosong_dihapus(self, org):
        link = _buat(org, url="erp.example.com", logo_props=IKON)
        resp = _klien(org.admin).patch(
            URL_DETAIL.format(slug=org.ws.slug, pk=link["id"]), {"logo_props": {}}, format="json"
        )
        assert "logo_props" not in resp.data["metadata"]

    @pytest.mark.parametrize(
        "logo",
        [
            {"in_use": "image", "emoji": {"value": "1"}},
            {"in_use": "emoji", "emoji": {}},
            {"in_use": "icon", "icon": {"name": "Bad Name"}},
            {"in_use": "icon", "icon": {"name": "star", "color": "red"}},
            "star",
        ],
    )
    def test_logo_tidak_valid_ditolak(self, org, logo):
        resp = _klien(org.admin).post(URL.format(slug=org.ws.slug), {"url": "erp.example.com", "logo_props": logo}, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["error"] == "Pick an icon from the list."
        assert not QuickLinkBersama.objects.exists()

    def test_patch_tanpa_logo_props_tidak_menyentuhnya(self, org):
        link = _buat(org, url="erp.example.com", logo_props=IKON)
        resp = _klien(org.admin).patch(
            URL_DETAIL.format(slug=org.ws.slug, pk=link["id"]), {"title": "ERP"}, format="json"
        )
        assert resp.data["metadata"]["logo_props"] == IKON

    def test_sisa_ikon_kustom_lama_dibuang_saat_menulis(self, org):
        link = _buat(org, url="erp.example.com")
        QuickLinkBersama.objects.filter(pk=link["id"]).update(
            metadata={**link["metadata"], "ikon_kustom": "data:image/png;base64,AA", "ikon_kustom_url": "x"}
        )
        resp = _klien(org.admin).patch(
            URL_DETAIL.format(slug=org.ws.slug, pk=link["id"]), {"title": "ERP"}, format="json"
        )
        assert "ikon_kustom" not in resp.data["metadata"]
        assert "ikon_kustom_url" not in resp.data["metadata"]

    def test_situs_tanpa_favicon_tidak_menyimpan_svg_bawaan(self, org, tanpa_internet):
        tanpa_internet.crawl.side_effect = lambda url: {
            "title": None,
            "favicon": "data:image/svg+xml;base64,AAAA",
            "favicon_url": None,
        }
        link = _buat(org, url="erp.example.com")
        assert link["metadata"]["favicon"] is None
        assert link["metadata"]["title"] is None

    def test_link_lama_diantrekan_untuk_diisi(self, org, tanpa_internet):
        lama = QuickLinkBersama.objects.create(workspace=org.ws, url="https://lama.example.com")
        _klien(org.staf_smt1).get(URL.format(slug=org.ws.slug))
        tanpa_internet.delay.assert_called_once_with("bersama", [str(lama.id)])


@pytest.mark.contract
@pytest.mark.django_db
class TestQuickLinkPribadi:
    def test_dibuat_dengan_judul_dan_favicon_otomatis(self, org):
        resp = _klien(org.staf_smt1).post(
            URL_PRIBADI.format(slug=org.ws.slug), {"url": "mail.example.com"}, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["metadata"]["title"] == "Situs mail.example.com"
        assert resp.data["metadata"]["favicon"] == FAVICON

    def test_ikon_pilihan_dibuat_diubah_dan_dihapus(self, org):
        klien = _klien(org.staf_smt1)
        resp = klien.post(URL_PRIBADI.format(slug=org.ws.slug), {"url": "mail.example.com", "logo_props": IKON}, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["metadata"]["logo_props"] == IKON
        detail = URL_PRIBADI.format(slug=org.ws.slug) + f"{resp.data['id']}/"
        # Tanpa logo_props = tidak disentuh.
        resp = klien.patch(detail, {"title": "Mail"}, format="json")
        assert resp.data["metadata"]["logo_props"] == IKON
        emoji = {"in_use": "emoji", "emoji": {"value": "1f600"}}
        resp = klien.patch(detail, {"logo_props": emoji}, format="json")
        assert resp.data["metadata"]["logo_props"] == emoji
        resp = klien.patch(detail, {"logo_props": None}, format="json")
        assert "logo_props" not in resp.data["metadata"]

    def test_ikon_pribadi_tidak_valid_ditolak(self, org):
        klien = _klien(org.staf_smt1)
        resp = klien.post(
            URL_PRIBADI.format(slug=org.ws.slug),
            {"url": "mail.example.com", "logo_props": {"in_use": "icon", "icon": {"name": "../x"}}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert resp.data["error"] == "Pick an icon from the list."
        assert not WorkspaceUserLink.objects.exists()

    def test_metadata_tidak_bisa_ditulis_klien(self, org):
        resp = _klien(org.staf_smt1).post(
            URL_PRIBADI.format(slug=org.ws.slug),
            {"url": "mail.example.com", "metadata": {"favicon": "data:text/html,<script>"}},
            format="json",
        )
        assert resp.data["metadata"]["favicon"] == FAVICON

    def test_link_lama_diantrekan_untuk_diisi(self, org, tanpa_internet):
        lama = WorkspaceUserLink.objects.create(workspace=org.ws, owner=org.staf_smt1, url="https://lama.example.com")
        _klien(org.staf_smt1).get(URL_PRIBADI.format(slug=org.ws.slug))
        tanpa_internet.delay.assert_called_once_with("pribadi", [str(lama.id)])

    def test_tugas_latar_mengisi_link_lama(self, org):
        from plane.bgtasks.quick_link_task import isi_metadata_quick_link  # noqa: PLC0415

        lama = WorkspaceUserLink.objects.create(workspace=org.ws, owner=org.staf_smt1, url="https://lama.example.com")
        isi_metadata_quick_link("pribadi", [str(lama.id)])
        lama.refresh_from_db()
        assert lama.metadata["title"] == "Situs lama.example.com"
        assert lama.metadata["diambil_pada"]
