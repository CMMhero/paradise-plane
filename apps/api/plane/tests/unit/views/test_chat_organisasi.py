# Kustomisasi Paradise Task Tracker: kanal divisi/departemen dan sebutan di obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kanal divisi & departemen yang anggotanya mengikuti God Mode, dan sebutan @.

ORM langsung, tanpa factory_boy (tidak ada di image runtime).
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    Divisi,
    JabatanOrganisasi,
    JenisPesan,
    Langganan,
    PesanLangsung,
    Ruang,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.db.models.hierarki import TINGKAT_MANAGER, TINGKAT_MEMBER
from plane.utils.kanal_organisasi import kunci_departemen, kunci_divisi, sinkronkan_kanal_organisasi
from plane.utils.kanal_sistem import kunci_kabar


def _orang(nama):
    return User.objects.create(id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama)


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


@pytest.fixture
def org(db):
    """Divisi SALES (departemen SMT1, SMT2) + seorang manager, dua staf, satu orang luar."""
    manager = _orang("manager")
    ws = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kantor-org", owner=manager)
    ani, budi, luar = _orang("ani"), _orang("budi"), _orang("luar")
    for u in (manager, ani, budi, luar):
        WorkspaceMember.objects.create(workspace=ws, member=u, role=15)
    sales = Divisi.objects.create(workspace=ws, kode="SALES", nama="Sales")
    smt1 = Departemen.objects.create(workspace=ws, divisi=sales, kode="SMT1", nama="SMT 1")
    smt2 = Departemen.objects.create(workspace=ws, divisi=sales, kode="SMT2", nama="SMT 2")
    JabatanOrganisasi.objects.create(workspace=ws, member=manager, tingkat=TINGKAT_MANAGER, divisi=sales)
    JabatanOrganisasi.objects.create(workspace=ws, member=ani, tingkat=TINGKAT_MEMBER, departemen=smt1)
    JabatanOrganisasi.objects.create(workspace=ws, member=budi, tingkat=TINGKAT_MEMBER, departemen=smt2)
    return {
        "ws": ws,
        "sales": sales,
        "smt1": smt1,
        "smt2": smt2,
        "manager": manager,
        "ani": ani,
        "budi": budi,
        "luar": luar,
    }


def _anggota(ws, kunci):
    ruang = Ruang.objects.get(workspace=ws, kunci_sistem=kunci)
    return set(Langganan.objects.filter(ruang=ruang).values_list("user_id", flat=True))


@pytest.mark.unit
class TestKanalOrganisasi:
    @pytest.mark.django_db
    def test_kanal_lahir_privat_dan_anggota_ikut_penempatan(self, org):
        ws = org["ws"]
        divisi = Ruang.objects.get(workspace=ws, kunci_sistem=kunci_divisi(org["sales"].id))
        assert divisi.tipe == Ruang.Tipe.PRIVAT and divisi.sistem and divisi.nama == "Sales"
        assert _anggota(ws, kunci_divisi(org["sales"].id)) == {org["manager"].id, org["ani"].id, org["budi"].id}
        # Manager ikut ke setiap departemen divisinya; staf hanya departemennya.
        assert _anggota(ws, kunci_departemen(org["smt1"].id)) == {org["manager"].id, org["ani"].id}
        assert _anggota(ws, kunci_departemen(org["smt2"].id)) == {org["manager"].id, org["budi"].id}

    @pytest.mark.django_db
    def test_pindah_departemen_memindah_kanal(self, org):
        ws, ani = org["ws"], org["ani"]
        baris = JabatanOrganisasi.objects.get(member=ani)
        baris.departemen = org["smt2"]
        baris.save()
        assert ani.id not in _anggota(ws, kunci_departemen(org["smt1"].id))
        assert ani.id in _anggota(ws, kunci_departemen(org["smt2"].id))
        assert ani.id in _anggota(ws, kunci_divisi(org["sales"].id))

    @pytest.mark.django_db
    def test_penempatan_dicabut_dan_keluar_workspace(self, org):
        ws = org["ws"]
        JabatanOrganisasi.objects.get(member=org["ani"]).delete()
        sinkronkan_kanal_organisasi(ws.id)
        assert org["ani"].id not in _anggota(ws, kunci_divisi(org["sales"].id))

        WorkspaceMember.objects.filter(workspace=ws, member=org["budi"]).update(is_active=False)
        sinkronkan_kanal_organisasi(ws.id, org["budi"].id)
        assert org["budi"].id not in _anggota(ws, kunci_departemen(org["smt2"].id))

    @pytest.mark.django_db
    def test_ganti_nama_dan_hapus_unit(self, org):
        ws, smt1 = org["ws"], org["smt1"]
        smt1.nama = "SMT Satu"
        smt1.save()
        assert Ruang.objects.get(workspace=ws, kunci_sistem=kunci_departemen(smt1.id)).nama == "SMT Satu"

        smt1.delete()  # hapus lunak = save -> sinkron workspace
        assert _anggota(ws, kunci_departemen(smt1.id)) == set()
        # Riwayatnya tetap: ruangnya tidak dihapus.
        assert Ruang.objects.filter(workspace=ws, kunci_sistem=kunci_departemen(smt1.id)).exists()

    @pytest.mark.django_db
    def test_bisa_ditulis_tapi_anggota_tidak_bisa_diatur_tangan(self, org):
        ws, ani = org["ws"], org["ani"]
        ruang = Ruang.objects.get(workspace=ws, kunci_sistem=kunci_departemen(org["smt1"].id))
        dasar = f"/api/workspaces/{ws.slug}/chat/ruang/{ruang.id}"
        assert _klien(ani).post(f"{dasar}/", {"isi": "halo tim"}, format="json").status_code == 201
        assert _klien(ani).delete(f"{dasar}/gabung/").status_code == 400
        tambah = _klien(ani).post(f"{dasar}/anggota/", {"user": str(org["luar"].id)}, format="json")
        assert tambah.status_code == 400
        # Orang luar tidak melihat isinya.
        assert _klien(org["luar"]).get(f"{dasar}/").status_code == 404


@pytest.mark.unit
class TestSebutan:
    @pytest.mark.django_db
    def test_sebutan_disaring_ke_anggota_dan_mengirim_kartu(self, org):
        ws, ani, manager, luar = org["ws"], org["ani"], org["manager"], org["luar"]
        ruang = Ruang.objects.get(workspace=ws, kunci_sistem=kunci_departemen(org["smt1"].id))
        jawab = _klien(ani).post(
            f"/api/workspaces/{ws.slug}/chat/ruang/{ruang.id}/",
            {"isi": "@manager tolong cek", "sebut": [str(manager.id), str(luar.id), str(ani.id), "bukan-uuid"]},
            format="json",
        )
        assert jawab.status_code == 201
        # Orang luar ruang dan diri sendiri dibuang; sampah diabaikan.
        assert jawab.json()["muatan"] == {"sebut": [str(manager.id)]}

        kartu = PesanLangsung.objects.filter(ruang__kunci_sistem=kunci_kabar(manager.id), jenis=JenisPesan.MENTION)
        assert kartu.count() == 1
        muatan = kartu.first().muatan
        assert muatan["obrolan"]["ruang_id"] == str(ruang.id)
        assert muatan["aktor"] == str(ani.id)
        assert not PesanLangsung.objects.filter(ruang__kunci_sistem=kunci_kabar(luar.id)).exists()

    @pytest.mark.django_db
    def test_sebutan_di_dm_tanpa_kartu(self, org):
        ws, ani, budi = org["ws"], org["ani"], org["budi"]
        jawab = _klien(ani).post(
            f"/api/workspaces/{ws.slug}/chat/{budi.id}/", {"isi": "@budi hai", "sebut": [str(budi.id)]}, format="json"
        )
        assert jawab.status_code == 201
        assert jawab.json()["muatan"] == {"sebut": [str(budi.id)]}
        assert not PesanLangsung.objects.filter(jenis=JenisPesan.MENTION).exists()


@pytest.mark.unit
class TestKartuDariCelery:
    @pytest.mark.django_db
    def test_notifikasi_di_memori_dengan_id_string_tetap_jadi_kartu(self, org):
        """`notification_task` membangun Notification di memori dengan id STRING.

        Versi lama mencocokkan issue lewat kunci UUID, jadi semua kartu dari jalur
        Celery (komentar, sebutan, pembaruan) terlewat diam-diam. Uji lama lolos
        karena membaca baris dari database, yang membawa UUID.
        """
        from plane.db.models import Issue, Notification, Project, State  # noqa: PLC0415
        from plane.utils.kartu_obrolan import kirim_kartu_notifikasi  # noqa: PLC0415

        ws, manager, ani = org["ws"], org["manager"], org["ani"]
        project = Project.objects.create(name="Aplikasi", identifier="APP", workspace=ws)
        state = State.objects.create(name="Todo", project=project, workspace=ws, group="unstarted")
        issue = Issue.objects.create(name="Laporan sprint", project=project, workspace=ws, state=state)
        notif = Notification(
            workspace=ws,
            project=project,
            sender="in_app:issue_activities:assigned",
            triggered_by_id=str(manager.id),
            receiver_id=str(ani.id),
            entity_identifier=str(issue.id),
            entity_name="issue",
            data={"issue_activity": {"field": "comment", "new_value": "Tolong cek", "old_value": ""}},
        )
        assert kirim_kartu_notifikasi([notif]) == 1
        kartu = PesanLangsung.objects.get(ruang__kunci_sistem=kunci_kabar(ani.id))
        assert kartu.jenis == JenisPesan.KOMENTAR
        assert kartu.muatan["tugas"]["id"] == str(issue.id)
