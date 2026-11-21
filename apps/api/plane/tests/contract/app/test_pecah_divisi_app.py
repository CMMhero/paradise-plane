# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pecah satu divisi jadi beberapa divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes perintah `pecah_divisi` (Plant Cilegon dipecah mengikuti bagan organisasi).

Bentuk uji:

    Kantor pusat  FIN -> FIN-FIN (P_FIN)             manager mgr_fin
    Cabang CLG    PC  -> LOG, PPC, ENG-ENG, QQ        Direktur Cabang bd
                  yosafat: Supervisor LOG + Staf FIN-FIN
                  staf_log, staf_ppc, spv_eng, staf_qq; tamu = anggota eksplisit PPC

Rencana: LOG {LOG, PPC} manager yosafat, ENG {ENG-ENG} kosong, QAQC {QQ} manager staf_qq.
"""

import json
from io import StringIO
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from plane.db.models import (
    Cabang,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    JabatanOrganisasi,
    Langganan,
    Project,
    ProjectMember,
    QuickLinkBersama,
    Ruang,
    State,
    TINGKAT_CABANG,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WikiFolder,
    Workspace,
    WorkspaceMember,
)
from plane.utils.hierarki import tingkat_anggota
from plane.utils.kanal_organisasi import kunci_divisi
from plane.utils.wiki_mandiri import pastikan_folder_unit

RENCANA = {
    "sumber": "PC",
    "divisi": [
        {"kode": "LOG", "nama": "Logistics", "departemen": ["LOG", "PPC"], "manager": True},
        {"kode": "ENG", "nama": "Engineering", "departemen": ["ENG-ENG"], "manager": False},
        {"kode": "QAQC", "nama": "QA QC", "departemen": ["QQ"], "manager": True},
    ],
}


def _user(ws, nama, **kolom):
    unik = uuid4().hex[:8]
    data = {"email": f"{nama}-{unik}@plane.so", "username": f"{nama}_{unik}", "display_name": nama, **kolom}
    user = User.objects.create(**data)
    WorkspaceMember.objects.create(workspace=ws, member=user, role=15)
    return user


def _orang(ws, nama, *baris):
    """`baris` = (tingkat, departemen, divisi, cabang) per penempatan."""
    user = _user(ws, nama)
    for tingkat, departemen, divisi, cabang in baris:
        JabatanOrganisasi.objects.create(
            workspace=ws, member=user, tingkat=tingkat, departemen=departemen, divisi=divisi, cabang=cabang
        )
    return user


def _departemen(ws, divisi, kode):
    dep = Departemen.objects.create(workspace=ws, divisi=divisi, kode=kode, nama=f"Dept {kode}")
    project = Project.objects.create(name=f"Dept {kode}", identifier=kode.replace("-", ""), workspace=ws)
    DepartemenProject.objects.create(workspace=ws, departemen=dep, project=project)
    State.objects.create(name="Todo", group="unstarted", color="#000000", project=project, workspace=ws, default=True)
    return dep, project


def _aktif(user, project):
    return ProjectMember.objects.filter(member=user, project=project, is_active=True).exists()


@pytest.fixture
def pc(db, workspace):
    o = type("PC", (), {})()
    o.ws = workspace
    o.clg = Cabang.objects.create(workspace=workspace, kode="CLG", nama="Plant Cilegon")
    o.fin = Divisi.objects.create(workspace=workspace, kode="FIN", nama="Finance")
    o.pc = Divisi.objects.create(workspace=workspace, kode="PC", nama="Plant Cilegon", cabang=o.clg)
    o.d_fin, o.p_fin = _departemen(workspace, o.fin, "FIN-FIN")
    o.d_log, o.p_log = _departemen(workspace, o.pc, "LOG")
    o.d_ppc, o.p_ppc = _departemen(workspace, o.pc, "PPC")
    o.d_eng, o.p_eng = _departemen(workspace, o.pc, "ENG-ENG")
    o.d_qq, o.p_qq = _departemen(workspace, o.pc, "QQ")
    o.mgr_fin = _orang(workspace, "mgrfin", (TINGKAT_MANAGER, None, o.fin, None))
    o.yosafat = _orang(
        workspace, "yosafat", (TINGKAT_SUPERVISOR, o.d_log, None, None), (TINGKAT_MEMBER, o.d_fin, None, None)
    )
    o.staf_log = _orang(workspace, "staflog", (TINGKAT_MEMBER, o.d_log, None, None))
    o.staf_ppc = _orang(workspace, "stafppc", (TINGKAT_MEMBER, o.d_ppc, None, None))
    o.spv_eng = _orang(workspace, "spveng", (TINGKAT_SUPERVISOR, o.d_eng, None, None))
    o.staf_qq = _orang(workspace, "stafqq", (TINGKAT_MEMBER, o.d_qq, None, None))
    o.bd = _orang(workspace, "bd", (TINGKAT_CABANG, None, None, o.clg))
    o.tamu = _user(workspace, "tamu")
    ProjectMember.objects.create(project=o.p_ppc, member=o.tamu, workspace=workspace, role=15)
    issue = Issue(name="Stok opname", workspace=workspace, project=o.p_log, state=State.objects.get(project=o.p_log))
    issue.save(created_by_id=o.staf_log.id)
    pastikan_folder_unit(workspace.id)
    o.folder_pc = WikiFolder.objects.get(divisi=o.pc)
    o.link_pc = QuickLinkBersama.objects.create(
        workspace=workspace, url="https://contoh.test/sop", title="SOP Plant", cakupan="organisasi"
    )
    o.link_pc.divisi.add(o.pc)
    o.link_fin = QuickLinkBersama.objects.create(
        workspace=workspace, url="https://contoh.test/fin", title="Kas", cakupan="organisasi"
    )
    o.link_fin.divisi.add(o.fin)
    return o


@pytest.fixture
def berkas(tmp_path):
    def tulis(isi=RENCANA):
        path = tmp_path / f"rencana-{uuid4().hex[:6]}.json"
        path.write_text(json.dumps(isi))
        return str(path)

    return tulis


def _jalankan(path, *args):
    keluar = StringIO()
    call_command("pecah_divisi", "--sumber", "PC", "--rencana", path, *args, stdout=keluar)
    return keluar.getvalue()


def _manager(o):
    return ("--manager", f"LOG={o.yosafat.username}", "--manager", f"QAQC={o.staf_qq.email}")


def _potret():
    """Semua yang bisa ditulis perintah ini."""
    return (
        set(Divisi.all_objects.values_list("id", "kode", "cabang_id", "deleted_at")),
        set(Departemen.all_objects.values_list("id", "divisi_id", "deleted_at")),
        set(DepartemenProject.all_objects.values_list("id", "departemen_id", "project_id", "deleted_at")),
        set(
            JabatanOrganisasi.all_objects.values_list(
                "id", "tingkat", "departemen_id", "divisi_id", "cabang_id", "deleted_at"
            )
        ),  # noqa: E501
        set(WikiFolder.all_objects.values_list("id", "divisi_id", "departemen_id", "parent_id")),
        set(QuickLinkBersama.divisi.through.objects.values_list("quicklinkbersama_id", "divisi_id")),
        set(ProjectMember.objects.filter(is_active=True).values_list("project_id", "member_id", "role")),
        set(Langganan.objects.values_list("ruang_id", "user_id")),
    )


@pytest.mark.contract
class TestPecahDivisi:
    @pytest.mark.django_db
    def test_dry_run_tidak_menulis(self, pc, berkas):
        sebelum = _potret()
        keluar = _jalankan(berkas(), *_manager(pc))
        assert "Create division LOG Logistics in branch CLG." in keluar
        assert "Move department LOG Dept LOG from PC to LOG." in keluar
        assert "Place yosafat (now Supervisor) as Manager of LOG Logistics." in keluar
        assert "yosafat leaves their seat in department LOG Dept LOG" in keluar
        assert "SOP Plant" in keluar
        assert "Dry run: nothing was written." in keluar
        assert _potret() == sebelum

    @pytest.mark.django_db
    def test_apply_memecah_tanpa_kehilangan(self, pc, berkas):
        dep_project = set(DepartemenProject.objects.values_list("id", "departemen_id", "project_id"))
        fin = set(Divisi.objects.filter(pk=pc.fin.pk).values_list("kode", "nama", "cabang_id", "updated_at"))
        jabatan_ho = set(
            JabatanOrganisasi.objects.filter(member__in=[pc.mgr_fin, pc.bd]).values_list(
                "id", "tingkat", "departemen_id", "divisi_id", "cabang_id"
            )
        )
        tugas = set(Issue.issue_objects.values_list("id", "project_id"))

        keluar = _jalankan(berkas(), *_manager(pc), "--apply")
        assert "Done." in keluar

        log, eng, qaqc = (Divisi.objects.get(kode=k) for k in ("LOG", "ENG", "QAQC"))
        assert {log.cabang_id, eng.cabang_id, qaqc.cabang_id} == {pc.clg.id}
        assert (log.nama, eng.nama, qaqc.nama) == ("Logistics", "Engineering", "QA QC")
        # Departemen tetap barisnya sendiri, hanya divisinya yang berubah.
        assert set(Departemen.objects.values_list("id", "divisi_id")) == {
            (pc.d_fin.id, pc.fin.id),
            (pc.d_log.id, log.id),
            (pc.d_ppc.id, log.id),
            (pc.d_eng.id, eng.id),
            (pc.d_qq.id, qaqc.id),
        }
        assert set(DepartemenProject.objects.values_list("id", "departemen_id", "project_id")) == dep_project
        assert set(Issue.issue_objects.values_list("id", "project_id")) == tugas

        # Sumber terhapus lunak.
        assert not Divisi.objects.filter(kode="PC").exists()
        assert Divisi.all_objects.get(pk=pc.pc.pk).deleted_at is not None

        # Folder Wiki PC tetap ada, hanya lepas dari divisinya; folder departemen pindah induk.
        folder = WikiFolder.objects.get(pk=pc.folder_pc.pk)
        assert folder.divisi_id is None
        folder_log = WikiFolder.objects.get(divisi=log)
        assert WikiFolder.objects.get(departemen=pc.d_ppc).parent_id == folder_log.id

        # Quick link kehilangan sasaran PC dan judulnya dicetak; link FIN tidak tersentuh.
        assert not pc.link_pc.divisi.exists()
        assert "Shared quick link no longer aimed at PC: 'SOP Plant'." in keluar
        assert list(pc.link_fin.divisi.all()) == [pc.fin]

        # Kantor pusat dan Direktur Cabang tidak tersentuh.
        assert set(Divisi.objects.filter(pk=pc.fin.pk).values_list("kode", "nama", "cabang_id", "updated_at")) == fin
        assert Departemen.objects.get(pk=pc.d_fin.pk).divisi_id == pc.fin.id
        assert (
            set(
                JabatanOrganisasi.objects.filter(member__in=[pc.mgr_fin, pc.bd]).values_list(
                    "id", "tingkat", "departemen_id", "divisi_id", "cabang_id"
                )
            )
            == jabatan_ho
        )
        for p in (pc.p_log, pc.p_ppc, pc.p_eng, pc.p_qq):
            assert _aktif(pc.bd, p)
        assert not _aktif(pc.bd, pc.p_fin)

        # Manager: kursi supervisor LOG dilepas (divisinya menjangkau), kursi FIN-FIN tetap.
        assert set(
            JabatanOrganisasi.objects.filter(member=pc.yosafat).values_list("tingkat", "departemen_id", "divisi_id")
        ) == {(TINGKAT_MANAGER, None, log.id), (TINGKAT_MEMBER, pc.d_fin.id, None)}
        assert JabatanOrganisasi.objects.get(member=pc.yosafat, divisi=log).sumber == "pecah-divisi"
        assert tingkat_anggota(pc.yosafat.id, pc.ws.id) == TINGKAT_MANAGER
        assert ProjectMember.objects.get(member=pc.yosafat, project=pc.p_ppc, is_active=True).role == 20
        assert ProjectMember.objects.get(member=pc.yosafat, project=pc.p_log, is_active=True).role == 20
        assert _aktif(pc.yosafat, pc.p_fin)
        assert set(
            JabatanOrganisasi.objects.filter(member=pc.staf_qq).values_list("tingkat", "departemen_id", "divisi_id")
        ) == {(TINGKAT_MANAGER, None, qaqc.id)}
        assert not JabatanOrganisasi.objects.filter(divisi=eng).exists()

        # Akses: anggota departemen yang dipindah tetap di papannya.
        assert _aktif(pc.staf_log, pc.p_log)
        assert _aktif(pc.staf_ppc, pc.p_ppc)
        assert _aktif(pc.spv_eng, pc.p_eng)
        assert _aktif(pc.staf_qq, pc.p_qq)
        assert _aktif(pc.tamu, pc.p_ppc)

        # Kanal obrolan: divisi baru punya kanalnya, kanal PC dikosongkan (riwayat tetap).
        kanal_log = Ruang.objects.get(kunci_sistem=kunci_divisi(log.id))
        assert set(Langganan.objects.filter(ruang=kanal_log).values_list("user_id", flat=True)) == {
            pc.yosafat.id,
            pc.staf_log.id,
            pc.staf_ppc.id,
        }
        kanal_pc = Ruang.objects.get(kunci_sistem=kunci_divisi(pc.pc.id))
        assert not Langganan.objects.filter(ruang=kanal_pc).exists()

    @pytest.mark.django_db
    def test_jalan_ulang_tidak_mengubah_apa_pun(self, pc, berkas):
        path = berkas()
        _jalankan(path, *_manager(pc), "--apply")
        sesudah = _potret()

        keluar = _jalankan(path, *_manager(pc), "--apply")
        assert "Nothing to change. Division PC is deleted and LOG, ENG, QAQC are in place." in keluar
        # Tanpa --manager pun tidak ada yang ditulis: kursinya sudah terisi.
        assert "Nothing to change." in _jalankan(path, "--apply")
        assert _potret() == sesudah
        assert Divisi.objects.filter(kode="LOG").count() == 1

    @pytest.mark.django_db
    def test_keadaan_setengah_jadi_diselesaikan(self, pc, berkas):
        # LOG sudah dibuat dan LOG dipindah lewat God Mode sebelumnya.
        log = Divisi.objects.create(workspace=pc.ws, kode="LOG", nama="Logistics", cabang=pc.clg)
        pc.d_log.divisi = log
        pc.d_log.save()

        keluar = _jalankan(berkas(), *_manager(pc), "--apply")

        assert "Create division LOG" not in keluar
        assert Divisi.objects.filter(kode="LOG").count() == 1
        assert set(Departemen.objects.filter(divisi=log).values_list("kode", flat=True)) == {"LOG", "PPC"}
        assert not Divisi.objects.filter(kode="PC").exists()

    @pytest.mark.django_db
    def test_tanpa_hapus_sumber(self, pc, berkas):
        _jalankan(berkas(), *_manager(pc), "--apply", "--no-hapus-sumber")
        pc.pc.refresh_from_db()
        assert pc.pc.deleted_at is None
        assert not Departemen.objects.filter(divisi=pc.pc).exists()


def _ubah(**ganti):
    isi = json.loads(json.dumps(RENCANA))
    for i, baris in ganti.items():
        isi["divisi"][int(i[1:])].update(baris)
    return isi


@pytest.mark.contract
class TestPecahDivisiDitolak:
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        ("isi", "pesan"),
        [
            (_ubah(d1={"departemen": ["ENG-ENG", "XYZ"]}), "Department XYZ in the plan does not exist."),
            (_ubah(d2={"departemen": ["ENG-ENG"]}), "appears in more than one division"),
            (
                {**RENCANA, "divisi": RENCANA["divisi"][:2]},
                "Department QQ Dept QQ is in PC but not in the plan.",
            ),
            (_ubah(d1={"kode": "FIN"}), "Division code FIN is already used by FIN Finance (head office)."),
            (_ubah(d1={"kode": "PC"}), "Division code PC is the division being split."),
            (_ubah(d1={"departemen": ["ENG-ENG", "FIN-FIN"]}), "Department FIN-FIN is in division FIN, not in PC."),
            (_ubah(d1={"kode": "ENGINEERING-PLANT"}), "at most 12 characters"),
        ],
    )
    def test_rencana_salah(self, pc, berkas, isi, pesan):
        sebelum = _potret()
        with pytest.raises(CommandError, match=pesan.replace("(", r"\(").replace(")", r"\)")):
            _jalankan(berkas(isi), *_manager(pc), "--apply")
        assert _potret() == sebelum

    @pytest.mark.django_db
    def test_manager_tidak_ditemukan(self, pc, berkas):
        with pytest.raises(CommandError, match="'nobody' is not an active member"):
            _jalankan(berkas(), "--manager", "LOG=nobody", "--manager", f"QAQC={pc.staf_qq.email}", "--apply")
        assert not Divisi.objects.filter(kode="LOG").exists()

    @pytest.mark.django_db
    def test_manager_ganda(self, pc, berkas):
        _user(pc.ws, "a", username="ganda@plane.so")
        _user(pc.ws, "b", email="ganda@plane.so")
        with pytest.raises(CommandError, match="matches more than one member"):
            _jalankan(berkas(), "--manager", "LOG=ganda@plane.so", "--manager", f"QAQC={pc.staf_qq.email}", "--apply")
        assert not Divisi.objects.filter(kode="LOG").exists()

    @pytest.mark.django_db
    def test_manager_bukan_anggota_aktif(self, pc, berkas):
        WorkspaceMember.objects.filter(member=pc.yosafat).update(is_active=False)
        with pytest.raises(CommandError, match="is not an active member"):
            _jalankan(berkas(), *_manager(pc), "--apply")

    @pytest.mark.django_db
    def test_manager_wajib_dan_kursi_kosong(self, pc, berkas):
        with pytest.raises(CommandError, match="Division QAQC needs a manager"):
            _jalankan(berkas(), "--manager", f"LOG={pc.yosafat.id}", "--apply")
        with pytest.raises(CommandError, match="the plan keeps ENG vacant"):
            _jalankan(berkas(), *_manager(pc), "--manager", f"ENG={pc.spv_eng.username}", "--apply")
        assert not Divisi.objects.filter(kode="LOG").exists()

    @pytest.mark.django_db
    def test_manager_di_sumber_menahan_hapus(self, pc, berkas):
        orang = _orang(pc.ws, "mgrpc", (TINGKAT_MANAGER, None, pc.pc, None))
        with pytest.raises(CommandError, match="Managers are still placed in PC: mgrpc"):
            _jalankan(berkas(), *_manager(pc), "--apply")
        assert JabatanOrganisasi.objects.get(member=orang).divisi_id == pc.pc.id

    @pytest.mark.django_db
    def test_kode_sama_di_cabang_lain(self, pc, berkas):
        Divisi.objects.create(workspace=pc.ws, kode="LOG", nama="Logistics")
        with pytest.raises(CommandError, match="Division code LOG is already used by LOG Logistics"):
            _jalankan(berkas(), *_manager(pc), "--apply")

    @pytest.mark.django_db
    def test_workspace_wajib_kalau_lebih_dari_satu(self, pc, berkas):
        Workspace.objects.create(name="Lain", owner=pc.yosafat, slug="lain")
        with pytest.raises(CommandError, match="Pass --workspace"):
            _jalankan(berkas(), *_manager(pc))
        assert "Dry run" in _jalankan(berkas(), *_manager(pc), "--workspace", pc.ws.slug)
