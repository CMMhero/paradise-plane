# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jenjang Sekretaris (KEP-101)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# ruff: noqa: F811 -- pytest fixtures imported from conftest are used as arguments

"""Tes kontrak: jenjang Sekretaris (tingkat 35, KEP-101).

Sekretaris menjangkau seluruh organisasi seperti direktur, tapi kedudukannya satu
anak tangga di bawahnya. Yang dikunci di sini:

* JANGKAUAN sama dengan direktur: mengawasi semua project, otomatis anggota semua
  project (juga yang dibuat belakangan), bucket notifikasi `direktur`, ikut laporan
  direktur, tidak ditempatkan di satu departemen/divisi, folder Wiki semua unit.
* KEDUDUKAN di bawah direktur: direktur boleh menugaskan sekretaris, sekretaris
  boleh menugaskan manager ke bawah, tapi TIDAK direktur (apa pun nilai saklar
  ASSIGN_DOWN_ONLY), dan bukan penyetuju bagi tugas direktur.
* Jenjang 10/20/30/40 tidak berubah arti.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks.daily_digest_task import NAMA_PERAN, _cakupan
from plane.bgtasks.direktur_digest_task import direktur_workspace
from plane.db.models import (
    JabatanOrganisasi,
    Project,
    ProjectMember,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_NAMA,
    TINGKAT_SEKRETARIS,
    menjangkau_seluruh_organisasi,
)
from plane.db.penempatan import setel_penempatan, tingkat_sesudah_cabut
from plane.license.api.views.organisasi import pohon_organisasi
from plane.tests.contract.app.test_organisasi_app import (  # noqa: F401 (fixture)
    _setel_hierarki,
    _tempat,
    _user,
    org,
    super_admin,
)
from plane.license.models import InstanceConfiguration
from plane.utils import saklar_instance as si
from plane.utils.hierarki import (
    FLAG_GERBANG,
    calon_penyetuju,
    divisi_diawasi,
    galat_penugasan,
    jangkauan_hierarki,
    tingkat_anggota,
)
from plane.utils.preferensi_email import BAWAAN_DIREKTUR, kelompok_jabatan, saklar_untuk
from plane.utils.wiki_mandiri import PenilaiWiki, pastikan_folder_unit, pengawas_halaman_privat


def _setel(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": str(nilai), "category": "PARADISE", "is_encrypted": False}
    )


def _pimpinan_puncak(org, prefix, tingkat):
    """Orang tanpa tempat (seperti direktur) dengan jenjang `tingkat`."""
    orang = _user(prefix, org.ws)
    JabatanOrganisasi.objects.create(workspace=org.ws, member=orang, tingkat=tingkat)
    return orang


@pytest.fixture
def puncak(org):
    """Satu sekretaris, satu sekretaris lain, satu direktur. Semua tanpa tempat."""
    o = type("Puncak", (), {})()
    o.sek = _pimpinan_puncak(org, "sek", TINGKAT_SEKRETARIS)
    o.sek_b = _pimpinan_puncak(org, "sekb", TINGKAT_SEKRETARIS)
    o.dir = _pimpinan_puncak(org, "dir", TINGKAT_DIREKTUR)
    return o


# --------------------------------------------------------------------------
# Aturan murni
# --------------------------------------------------------------------------


@pytest.mark.unit
class TestTangga:
    def test_sekretaris_di_antara_manager_dan_direktur(self):
        assert TINGKAT_MANAGER < TINGKAT_SEKRETARIS < TINGKAT_DIREKTUR
        assert TINGKAT_SEKRETARIS == 35

    def test_nama_jenjang_lama_tidak_berubah(self):
        assert TINGKAT_NAMA == {
            10: "Member",
            20: "Supervisor",
            30: "Manager",
            35: "Sekretaris",
            40: "Direktur",
        }

    @pytest.mark.parametrize(
        ("tingkat", "harapan"),
        [(None, False), (0, False), (10, False), (20, False), (30, False), (35, True), (40, True)],
    )
    def test_menjangkau_seluruh_organisasi(self, tingkat, harapan):
        assert menjangkau_seluruh_organisasi(tingkat) is harapan

    def test_sekretaris_tidak_jatuh_ke_staf_saat_dicabut(self):
        assert tingkat_sesudah_cabut(TINGKAT_SEKRETARIS, {"d"}, set(), set(), set()) == TINGKAT_SEKRETARIS
        assert tingkat_sesudah_cabut(TINGKAT_MANAGER, set(), {"v"}, set(), set()) == TINGKAT_MEMBER

    def test_nama_peran_ringkasan_harian(self):
        assert NAMA_PERAN[TINGKAT_SEKRETARIS] == "Sekretaris"
        assert NAMA_PERAN[TINGKAT_DIREKTUR] == "Direktur"

    @pytest.mark.django_db
    def test_cakupan_ringkasan_harian_sekretaris_seperti_direktur(self, org, puncak):
        for tingkat in (TINGKAT_SEKRETARIS, TINGKAT_DIREKTUR):
            assert _cakupan(puncak.sek.id, org.ws.id, tingkat, 0) == ("Seluruh divisi", "Seluruh divisi")
        assert _cakupan(org.manager.id, org.ws.id, TINGKAT_MANAGER, 0)[0] != "Seluruh divisi"


# --------------------------------------------------------------------------
# Jangkauan seluruh organisasi
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestJangkauan:
    @pytest.mark.django_db
    def test_mengawasi_semua_project(self, org, puncak):
        semua = set(Project.objects.filter(workspace=org.ws).values_list("id", flat=True))
        assert divisi_diawasi(puncak.sek.id, org.ws.id) == semua
        assert divisi_diawasi(puncak.dir.id, org.ws.id) == semua

    @pytest.mark.django_db
    def test_manager_tetap_hanya_divisinya(self, org, puncak):
        semua = set(Project.objects.filter(workspace=org.ws).values_list("id", flat=True))
        assert divisi_diawasi(org.manager.id, org.ws.id) < semua

    @pytest.mark.django_db
    def test_jangkauan_lihat_semua_project_role_admin(self, org, puncak):
        hasil = jangkauan_hierarki(puncak.sek.id, org.ws.id)
        semua = set(Project.objects.filter(workspace=org.ws).values_list("id", flat=True))
        assert set(hasil) == semua
        assert set(hasil.values()) == {20}

    @pytest.mark.django_db
    def test_otomatis_anggota_semua_project_yang_ada(self, org, puncak):
        for project in (org.p1, org.p2, org.p3):
            anggota = ProjectMember.objects.get(project=project, member=puncak.sek, is_active=True)
            assert anggota.role == 20

    @pytest.mark.django_db
    def test_project_baru_langsung_punya_sekretaris(self, org, puncak, create_user):
        baru = Project.objects.create(name="Baru", identifier="BARU", workspace=org.ws, created_by=create_user)
        assert ProjectMember.objects.filter(project=baru, member=puncak.sek, is_active=True).exists()

    @pytest.mark.django_db
    def test_naik_dari_manager_ke_sekretaris_disusulkan(self, org):
        orang = _user("naik", org.ws)
        JabatanOrganisasi.objects.create(workspace=org.ws, member=orang, tingkat=TINGKAT_MEMBER)
        assert not ProjectMember.objects.filter(project=org.p2, member=orang).exists()
        baris = JabatanOrganisasi.objects.get(workspace=org.ws, member=orang)
        baris.tingkat = TINGKAT_SEKRETARIS
        baris.save()
        assert ProjectMember.objects.filter(project=org.p2, member=orang, is_active=True).exists()

    @pytest.mark.django_db
    def test_staf_dan_manager_tidak_otomatis_masuk(self, org, create_user):
        baru = Project.objects.create(name="Baru2", identifier="BARU2", workspace=org.ws, created_by=create_user)
        assert not ProjectMember.objects.filter(project=baru, member=org.manager).exists()
        assert not ProjectMember.objects.filter(project=baru, member=org.staf1).exists()


# --------------------------------------------------------------------------
# Kedudukan: di bawah direktur
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestPenugasan:
    @pytest.mark.django_db
    @pytest.mark.parametrize("penerima", ["staf1", "sup1", "manager"])
    def test_sekretaris_boleh_menugaskan_manager_ke_bawah(self, org, puncak, penerima):
        orang = getattr(org, penerima)
        assert galat_penugasan(org.p1.id, [orang.id], actor=puncak.sek, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_sekretaris_tidak_boleh_menugaskan_direktur(self, org, puncak):
        galat = galat_penugasan(org.p1.id, [puncak.dir.id], actor=puncak.sek, abaikan_katup=True)
        assert galat and "jenjang yang sama" in galat

    @pytest.mark.django_db
    def test_sekretaris_tidak_boleh_menugaskan_direktur_walau_saklar_mati(self, org, puncak):
        _setel(si.ASSIGN_DOWN_ONLY, "0")
        assert galat_penugasan(org.p1.id, [puncak.dir.id], actor=puncak.sek, abaikan_katup=True)
        # Saklar mati hanya melonggarkan sesama jenjang, bukan menembus direktur.
        assert galat_penugasan(org.p1.id, [puncak.sek_b.id], actor=puncak.sek, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_sesama_sekretaris_ditolak_selama_hanya_ke_bawah(self, org, puncak):
        assert galat_penugasan(org.p1.id, [puncak.sek_b.id], actor=puncak.sek, abaikan_katup=True)

    @pytest.mark.django_db
    def test_direktur_boleh_menugaskan_sekretaris(self, org, puncak):
        assert galat_penugasan(org.p1.id, [puncak.sek.id], actor=puncak.dir, abaikan_katup=True) is None

    @pytest.mark.django_db
    def test_manager_tidak_boleh_menugaskan_sekretaris(self, org, puncak):
        assert galat_penugasan(org.p1.id, [puncak.sek.id], actor=org.manager, abaikan_katup=True)

    @pytest.mark.django_db
    def test_sekretaris_menugaskan_campuran_ditolak_kalau_ada_direktur(self, org, puncak):
        assert galat_penugasan(org.p1.id, [org.staf1.id, puncak.dir.id], actor=puncak.sek, abaikan_katup=True)

    @pytest.mark.django_db
    def test_direktur_tetap_boleh_menugaskan_siapa_pun(self, org, puncak):
        semua = [org.staf1.id, org.manager.id, puncak.sek.id, puncak.sek_b.id]
        assert galat_penugasan(org.p1.id, semua, actor=puncak.dir, abaikan_katup=True) is None


@pytest.mark.contract
class TestPenyetuju:
    @pytest.mark.django_db
    def test_sekretaris_dan_direktur_calon_penyetuju_tugas_staf(self, org, puncak):
        calon = calon_penyetuju(org.ws.id, org.p1.id, tingkat_pembuat=TINGKAT_MEMBER)
        assert puncak.sek.id in calon and puncak.dir.id in calon

    @pytest.mark.django_db
    def test_tugas_manager_disetujui_sekretaris_atau_direktur(self, org, puncak):
        calon = calon_penyetuju(org.ws.id, org.p1.id, tingkat_pembuat=TINGKAT_MANAGER)
        assert puncak.sek.id in calon and puncak.dir.id in calon

    @pytest.mark.django_db
    def test_tugas_sekretaris_hanya_disetujui_direktur(self, org, puncak):
        calon = calon_penyetuju(org.ws.id, org.p1.id, tingkat_pembuat=TINGKAT_SEKRETARIS)
        assert puncak.dir.id in calon
        assert puncak.sek.id not in calon and puncak.sek_b.id not in calon

    @pytest.mark.django_db
    def test_tugas_direktur_tidak_punya_penyetuju(self, org, puncak):
        assert calon_penyetuju(org.ws.id, org.p1.id, tingkat_pembuat=TINGKAT_DIREKTUR) == []

    @pytest.mark.django_db
    def test_ambang_direktur_menahan_sekretaris_juga(self, org, puncak):
        """APPROVAL_DI_BAWAH_DIREKTUR = "semua kecuali direktur": sekretaris termasuk yang menunggu."""
        from plane.utils.hierarki import butuh_persetujuan

        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_DIREKTUR)
        assert butuh_persetujuan(puncak.sek, org.p1.id, [puncak.sek.id]) is True
        assert butuh_persetujuan(puncak.dir, org.p1.id, [puncak.dir.id]) is False

    @pytest.mark.django_db
    def test_sekretaris_tidak_menunggu_persetujuan_bawaan(self, org, puncak):
        from plane.utils.hierarki import butuh_persetujuan

        assert butuh_persetujuan(puncak.sek, org.p1.id, [puncak.sek.id]) is False


@pytest.mark.contract
class TestDaftarBisaDitugaskan:
    URL = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/bisa-ditugaskan/"

    def _ambil(self, org, user):
        klien = APIClient()
        klien.force_authenticate(user=user)
        return klien.get(self.URL.format(slug=org.ws.slug, project_id=org.p1.id))

    @pytest.mark.django_db
    def test_direktur_melihat_semua_anggota(self, org, puncak, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respon = self._ambil(org, puncak.dir)
        assert respon.status_code == status.HTTP_200_OK, respon.content
        assert respon.json()["mode"] == "semua"

    @pytest.mark.django_db
    def test_sekretaris_melihat_bawahan_tanpa_direktur(self, org, puncak, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        respon = self._ambil(org, puncak.sek)
        assert respon.status_code == status.HTTP_200_OK, respon.content
        data = respon.json()
        assert data["mode"] == "bawahan"
        assert data["tingkat_saya"] == TINGKAT_SEKRETARIS
        ids = {u["id"] for u in data["users"]}
        assert {str(org.staf1.id), str(org.sup1.id), str(org.manager.id), str(puncak.sek.id)} <= ids
        assert str(puncak.dir.id) not in ids
        assert str(puncak.sek_b.id) not in ids

    @pytest.mark.django_db
    def test_saklar_ke_bawah_mati_tetap_tanpa_direktur(self, org, puncak, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _setel(si.ASSIGN_DOWN_ONLY, "0")
        ids = {u["id"] for u in self._ambil(org, puncak.sek).json()["users"]}
        assert str(puncak.dir.id) not in ids
        assert str(puncak.sek_b.id) in ids
        assert str(org.staf1.id) in ids


# --------------------------------------------------------------------------
# Notifikasi dan laporan
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestNotifikasiDanLaporan:
    @pytest.mark.django_db
    def test_kelompok_notifikasi_sekretaris_adalah_direktur(self, org, puncak):
        assert kelompok_jabatan(puncak.sek.id) == "direktur"
        assert kelompok_jabatan(puncak.dir.id) == "direktur"
        assert kelompok_jabatan(org.manager.id) == "pimpinan"

    @pytest.mark.django_db
    def test_sekretaris_ikut_bawaan_direktur(self, org, puncak):
        assert saklar_untuk(puncak.sek.id) == BAWAAN_DIREKTUR

    @pytest.mark.django_db
    def test_sekretaris_menerima_laporan_direktur(self, org, puncak):
        penerima = {u.id for u in direktur_workspace()[org.ws.id]}
        assert {puncak.sek.id, puncak.sek_b.id, puncak.dir.id} <= penerima
        assert org.manager.id not in penerima


# --------------------------------------------------------------------------
# God Mode: menyetel jenjang dan pohon organisasi
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestGodMode:
    @pytest.mark.django_db
    def test_jenjang_35_diterima(self, org, super_admin):
        respon = _setel_hierarki(super_admin, {"member_id": str(org.staf1.id), "tingkat": TINGKAT_SEKRETARIS})
        assert respon.status_code == status.HTTP_200_OK, respon.data
        assert respon.data["member"]["tingkat"] == TINGKAT_SEKRETARIS
        assert respon.data["member"]["tingkat_nama"] == "Sekretaris"

    @pytest.mark.django_db
    def test_jenjang_di_antara_ditolak(self, org, super_admin):
        respon = _setel_hierarki(super_admin, {"member_id": str(org.staf1.id), "tingkat": 36})
        assert respon.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_naik_ke_sekretaris_masuk_semua_project(self, org, super_admin):
        _setel_hierarki(super_admin, {"member_id": str(org.staf2.id), "tingkat": TINGKAT_SEKRETARIS})
        assert tingkat_anggota(org.staf2.id, org.ws.id) == TINGKAT_SEKRETARIS
        for project in (org.p1, org.p2, org.p3):
            assert ProjectMember.objects.filter(project=project, member=org.staf2, is_active=True).exists()

    @pytest.mark.django_db
    def test_cabut_sekretaris_kembali_staf_tanpa_tempat(self, org, super_admin):
        _setel_hierarki(super_admin, {"member_id": str(org.staf2.id), "tingkat": TINGKAT_SEKRETARIS})
        respon = _setel_hierarki(super_admin, {"member_id": str(org.staf2.id), "tingkat": None})
        assert respon.status_code == status.HTTP_200_OK, respon.data
        assert respon.data["member"]["tingkat"] == TINGKAT_MEMBER
        assert _tempat(org.staf2, org.ws) == {(None, None)}

    @pytest.mark.django_db
    def test_tidak_didaftar_di_tempat_mana_pun_pada_pohon(self, org, puncak):
        # Baris divisi bertingkat 35 (God Mode membolehkannya, seperti direktur) tidak dihitung manager.
        setel_penempatan(org.ws, puncak.sek, TINGKAT_SEKRETARIS, [], [org.sales.id])
        pohon = pohon_organisasi(org.ws)
        semua = [a["id"] for v in pohon["divisi"] for d in v["departemen"] for a in d["anggota"]]
        semua += [m["id"] for v in pohon["divisi"] for m in v["manager"]]
        assert str(puncak.sek.id) not in semua
        assert str(org.manager.id) in semua


# --------------------------------------------------------------------------
# Wiki
# --------------------------------------------------------------------------


@pytest.mark.contract
class TestWiki:
    @pytest.mark.django_db
    def test_sekretaris_mengelola_folder_semua_unit_seperti_direktur(self, org, puncak):
        from plane.db.models import WikiFolder

        pastikan_folder_unit(org.ws.id)
        folder = WikiFolder.objects.get(divisi=org.sales)
        for orang in (puncak.sek, puncak.dir):
            penilai = PenilaiWiki(orang, org.ws.id)
            assert penilai.direktur is True
            assert penilai.mengelola(folder.id) is True
        assert PenilaiWiki(org.staf1, org.ws.id).mengelola(folder.id) is False

    @pytest.mark.django_db
    def test_sekretaris_mengawasi_halaman_privat(self, org, puncak):
        assert pengawas_halaman_privat(puncak.sek, org.p1.id) is True
        assert pengawas_halaman_privat(org.staf1, org.p1.id) is False
