# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji dashboard KPI
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tes kontrak halaman KPI (`/kinerja`).

Yang dijaga:

1. Angka satu orang persis: selesai tepat waktu, terlambat, tanpa tenggat,
   terlambat sekarang (yang menunggu persetujuan tidak dihitung), terbuka, waktu
   siklus, persetujuan, jam kerja, tren, dan pembanding periode sebelumnya.
2. Tiap penanggung jawab mendapat kredit penuh; angka kelompok menghitung satu
   tugas sekali.
3. Lingkup: staf hanya dirinya, supervisor departemennya dan stafnya, manager
   divisinya, direktur dan admin workspace semuanya. Di luar itu 403.
4. Batas periode memakai hari kantor (WIB), bukan hari UTC.
5. Judul tugas hanya keluar untuk project yang pemanggil anggotai.
"""

from datetime import date, datetime
from unittest.mock import patch
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Departemen,
    Divisi,
    Issue,
    IssueAssignee,
    IssueWorkLog,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    State,
    StateGroup,
    STATUS_PERSETUJUAN_DISETUJUI,
    STATUS_PERSETUJUAN_DITOLAK,
    STATUS_PERSETUJUAN_MENUNGGU,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)

URL = "/api/workspaces/{slug}/kinerja/"
URL_LINGKUP = "/api/workspaces/{slug}/kinerja/lingkup/"
WIB = ZoneInfo("Asia/Jakarta")
# Rabu 18 Nov 2026, 10.00 WIB. Bulan ini = 1-18 Nov, pembanding = 14-31 Okt.
SEKARANG = datetime(2026, 11, 18, 10, tzinfo=WIB)

SELESAI = StateGroup.COMPLETED.value
BELUM = StateGroup.UNSTARTED.value
JALAN = StateGroup.STARTED.value
BATAL = StateGroup.CANCELLED.value


def _wib(bulan, hari, jam=0, menit=0):
    return datetime(2026, bulan, hari, jam, menit, tzinfo=WIB)


def _orang(workspace, nama, tingkat=None, departemen=None, divisi=None):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{nama}-{unik}@plane.so", username=f"{nama}_{unik}", display_name=nama)
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    if tingkat is not None:
        JabatanOrganisasi.objects.create(
            workspace=workspace, member=user, tingkat=tingkat, departemen=departemen, divisi=divisi
        )
    return user


def _tugas(project, states, grup, orang, nama, tenggat=None, selesai=None, mulai=None, dibuat=None, prioritas="none"):
    issue = Issue(name=nama, workspace=project.workspace, project=project, state=states[grup], priority=prioritas)
    issue.save()
    # update(), bukan save(): save() mengisi tanggal otomatis dan completed_at = sekarang.
    Issue.objects.filter(pk=issue.pk).update(
        completed_at=selesai, target_date=tenggat, start_date=mulai, created_at=dibuat or _wib(10, 1)
    )
    for user in orang:
        IssueAssignee.objects.create(issue=issue, assignee=user, project=project, workspace=project.workspace)
    return issue


def _persetujuan(issue, pemohon, penerima, status_, diputuskan=None):
    return PersetujuanPenugasan.objects.create(
        workspace=issue.workspace,
        project=issue.project,
        issue=issue,
        pemohon=pemohon,
        penerima=penerima,
        status=status_,
        diputuskan_pada=diputuskan,
    )


def _ambil(user, slug, **params):
    klien = APIClient()
    klien.force_authenticate(user=user)
    # Jam dibekukan di tempat modul KPI membacanya; freezegun mematahkan impor
    # malas pydantic di dalam permintaan.
    with patch("plane.utils.kinerja.timezone.now", return_value=SEKARANG):
        return klien.get(URL.format(slug=slug), params)


@pytest.fixture
def org(db, workspace):
    ops = Divisi.objects.create(workspace=workspace, kode="OPS", nama="Operasional")
    fin = Divisi.objects.create(workspace=workspace, kode="FIN", nama="Keuangan")
    gudang = Departemen.objects.create(workspace=workspace, divisi=ops, kode="GUD", nama="Gudang")
    kirim = Departemen.objects.create(workspace=workspace, divisi=ops, kode="KRM", nama="Kirim")
    akun = Departemen.objects.create(workspace=workspace, divisi=fin, kode="AKT", nama="Akuntansi")

    o = {
        "staf_a": _orang(workspace, "staf-a", TINGKAT_MEMBER, gudang),
        "staf_b": _orang(workspace, "staf-b", TINGKAT_MEMBER, gudang),
        "spv": _orang(workspace, "spv-gudang", TINGKAT_SUPERVISOR, gudang),
        "staf_k": _orang(workspace, "staf-kirim", TINGKAT_MEMBER, kirim),
        "manager": _orang(workspace, "manager-ops", TINGKAT_MANAGER, divisi=ops),
        "staf_f": _orang(workspace, "staf-fin", TINGKAT_MEMBER, akun),
        "direktur": _orang(workspace, "direktur", TINGKAT_DIREKTUR),
    }

    project = Project.objects.create(name="Gudang", identifier="GUD", workspace=workspace)
    for kunci in ("staf_a", "staf_b", "spv"):
        ProjectMember.objects.create(project=project, member=o[kunci], workspace=workspace, role=15)
    s = {
        grup: State.objects.create(
            name=grup, group=grup, color="#000000", project=project, workspace=workspace, default=grup == BELUM
        )
        for grup in (BELUM, JALAN, SELESAI, BATAL)
    }

    a, b = o["staf_a"], o["staf_b"]
    # Siklus 2,0 hari (Start date 8 Nov 00.00 WIB).
    tepat = _tugas(project, s, SELESAI, [a], "Tepat", date(2026, 11, 10), _wib(11, 10), mulai=date(2026, 11, 8))
    # Siklus 4,0 hari (dibuat 3 Nov 12.00).
    _tugas(project, s, SELESAI, [a], "Telat", date(2026, 11, 5), _wib(11, 7, 12), dibuat=_wib(11, 3, 12))
    # Siklus 3,0 hari.
    _tugas(project, s, SELESAI, [a], "Tanpa tenggat", None, _wib(11, 12), dibuat=_wib(11, 9))
    # Dua penanggung jawab, siklus 1,5 hari.
    _tugas(project, s, SELESAI, [a, b], "Berdua", date(2026, 11, 14), _wib(11, 13, 12), dibuat=_wib(11, 12))
    lewat = _tugas(project, s, BELUM, [a], "Lewat tenggat", date(2026, 11, 10), prioritas="high")
    _tugas(project, s, JALAN, [a], "Masih jalan", date(2026, 11, 30))
    menunggu = _tugas(project, s, JALAN, [a], "Menunggu persetujuan", date(2026, 11, 9))
    _tugas(project, s, BATAL, [a], "Batal", date(2026, 11, 1))
    _tugas(project, s, SELESAI, [a], "Bulan lalu", date(2026, 10, 25), _wib(10, 20, 9), dibuat=_wib(10, 19, 9))
    # Batas hari kantor: 00.30 WIB 1 Nov masih 31 Okt di UTC.
    _tugas(project, s, SELESAI, [b], "Awal November", None, _wib(11, 1, 0, 30), dibuat=_wib(10, 30))
    _tugas(project, s, SELESAI, [b], "Akhir Oktober", None, _wib(10, 31, 23, 30), dibuat=_wib(10, 30))

    _persetujuan(tepat, a, o["spv"], STATUS_PERSETUJUAN_DISETUJUI, _wib(11, 10))
    _persetujuan(lewat, a, o["spv"], STATUS_PERSETUJUAN_DITOLAK, _wib(11, 13))
    _persetujuan(menunggu, a, o["spv"], STATUS_PERSETUJUAN_MENUNGGU)
    IssueWorkLog.objects.create(
        issue=tepat, project=project, workspace=workspace, logged_by=a, duration=90, logged_at=_wib(11, 10, 9)
    )

    return {**o, "ops": ops, "fin": fin, "gudang": gudang, "kirim": kirim, "akun": akun, "project": project}


@pytest.mark.contract
class TestAngkaSatuOrang:
    def test_nilai_persis_untuk_diri_sendiri(self, org, workspace):
        response = _ambil(org["staf_a"], workspace.slug, periode="this_month")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["scope"]["kind"] == "orang"
        assert response.data["period"]["start"] == date(2026, 11, 1)
        assert response.data["period"]["end"] == date(2026, 11, 18)
        assert response.data["period"]["previous_start"] == date(2026, 10, 14)
        assert response.data["values"] == {
            "completed": 4,
            "on_time_rate": 67,
            "completed_late": 1,
            "completed_no_due_date": 1,
            "overdue": 1,
            "open": 3,
            "cycle_avg_days": 2.6,
            "cycle_median_days": 2.5,
            "approvals_approved": 1,
            "approvals_rejected": 1,
            "worklog_hours": 1.5,
        }

    def test_pembanding_periode_sebelumnya(self, org, workspace):
        sebelumnya = _ambil(org["staf_a"], workspace.slug, periode="this_month").data["previous"]
        assert sebelumnya["completed"] == 1
        assert sebelumnya["on_time_rate"] == 100
        assert sebelumnya["cycle_avg_days"] == 1.0
        assert sebelumnya["overdue"] == 0
        assert sebelumnya["open"] is None

    def test_daftar_metrik_dikirim_bersama_nilainya(self, org, workspace):
        data = _ambil(org["staf_a"], workspace.slug).data
        assert [m["key"] for m in data["metrics"]] == list(data["values"])
        terlambat = next(m for m in data["metrics"] if m["key"] == "overdue")
        assert terlambat == {
            "key": "overdue",
            "label_key": "kinerja.metric.overdue",
            "unit": "count",
            "direction": "down",
            "snapshot": True,
        }

    def test_beban_terbuka_per_status_dan_prioritas(self, org, workspace):
        beban = _ambil(org["staf_a"], workspace.slug).data["workload"]
        assert beban["by_state_group"] == {"backlog": 0, "unstarted": 1, "started": 2}
        assert beban["by_priority"] == {"urgent": 0, "high": 1, "medium": 0, "low": 0, "none": 2}

    def test_tren_harian(self, org, workspace):
        tren = _ambil(org["staf_a"], workspace.slug, periode="this_month").data["trend"]
        assert tren["bucket"] == "day"
        assert len(tren["points"]) == 18
        isi = {t["start"]: t for t in tren["points"] if t["completed"] or t["became_overdue"]}
        assert {k: (v["completed"], v["on_time"], v["became_overdue"]) for k, v in isi.items()} == {
            date(2026, 11, 6): (0, 0, 1),
            date(2026, 11, 7): (1, 0, 0),
            date(2026, 11, 10): (1, 1, 0),
            date(2026, 11, 11): (0, 0, 1),
            date(2026, 11, 12): (1, 0, 0),
            date(2026, 11, 13): (1, 1, 0),
        }

    def test_tren_mingguan_untuk_rentang_panjang(self, org, workspace):
        tren = _ambil(org["staf_a"], workspace.slug, periode="this_quarter").data["trend"]
        assert tren["bucket"] == "week"
        assert tren["points"][0]["start"] == date(2026, 10, 1)
        assert tren["points"][1]["start"] == date(2026, 10, 5)
        assert sum(t["completed"] for t in tren["points"]) == 5

    def test_daftar_tugas_orang(self, org, workspace):
        daftar = _ambil(org["staf_a"], workspace.slug).data["items"]
        assert [t["name"] for t in daftar["overdue"]] == ["Lewat tenggat"]
        assert [t["name"] for t in daftar["completed"]] == ["Berdua", "Tanpa tenggat", "Tepat", "Telat"]
        assert [t["timing"] for t in daftar["completed"]] == ["on_time", "no_due_date", "on_time", "late"]


@pytest.mark.contract
class TestLingkup:
    def test_staf_hanya_dirinya(self, org, workspace):
        staf = org["staf_a"]
        assert _ambil(staf, workspace.slug, lingkup="saya").status_code == status.HTTP_200_OK
        assert _ambil(staf, workspace.slug, lingkup="orang", id=str(staf.id)).status_code == status.HTTP_200_OK
        ditolak = (
            {"lingkup": "orang", "id": str(org["staf_b"].id)},
            {"lingkup": "departemen", "id": str(org["gudang"].id)},
            {"lingkup": "divisi", "id": str(org["ops"].id)},
            {"lingkup": "organisasi"},
        )
        for params in ditolak:
            assert _ambil(staf, workspace.slug, **params).status_code == status.HTTP_403_FORBIDDEN, params

    def test_supervisor_departemennya_dan_stafnya(self, org, workspace):
        spv = org["spv"]
        departemen = _ambil(spv, workspace.slug, lingkup="departemen", id=str(org["gudang"].id))
        assert departemen.status_code == status.HTTP_200_OK
        # "Berdua" dihitung sekali untuk departemen, sekali per orang di tabel.
        assert departemen.data["values"]["completed"] == 5
        per_orang = {o["display_name"]: o["values"]["completed"] for o in departemen.data["people"]}
        assert per_orang == {"staf-a": 4, "staf-b": 2, "spv-gudang": 0}
        assert departemen.data["items"] is None

        assert _ambil(spv, workspace.slug, lingkup="orang", id=str(org["staf_a"].id)).data["values"]["completed"] == 4
        ditolak = (
            {"lingkup": "departemen", "id": str(org["kirim"].id)},
            {"lingkup": "orang", "id": str(org["staf_k"].id)},
            {"lingkup": "orang", "id": str(org["manager"].id)},
            {"lingkup": "divisi", "id": str(org["ops"].id)},
            {"lingkup": "organisasi"},
        )
        for params in ditolak:
            assert _ambil(spv, workspace.slug, **params).status_code == status.HTTP_403_FORBIDDEN, params

    def test_manager_divisinya(self, org, workspace):
        manager = org["manager"]
        divisi = _ambil(manager, workspace.slug, lingkup="divisi", id=str(org["ops"].id))
        assert divisi.status_code == status.HTTP_200_OK
        assert divisi.data["values"]["completed"] == 5
        assert divisi.data["breakdown"]["kind"] == "departemen"
        rincian = {b["code"]: (b["people"], b["values"]["completed"]) for b in divisi.data["breakdown"]["rows"]}
        assert rincian == {"GUD": (3, 5), "KRM": (1, 0)}
        assert {o["display_name"] for o in divisi.data["people"]} == {
            "staf-a",
            "staf-b",
            "spv-gudang",
            "staf-kirim",
            "manager-ops",
        }

        for params in (
            {"lingkup": "departemen", "id": str(org["kirim"].id)},
            {"lingkup": "orang", "id": str(org["spv"].id)},
            {"lingkup": "orang", "id": str(org["staf_k"].id)},
        ):
            assert _ambil(manager, workspace.slug, **params).status_code == status.HTTP_200_OK, params
        for params in (
            {"lingkup": "divisi", "id": str(org["fin"].id)},
            {"lingkup": "departemen", "id": str(org["akun"].id)},
            {"lingkup": "orang", "id": str(org["staf_f"].id)},
            {"lingkup": "organisasi"},
        ):
            assert _ambil(manager, workspace.slug, **params).status_code == status.HTTP_403_FORBIDDEN, params

    def test_direktur_seluruh_organisasi(self, org, workspace):
        direktur = org["direktur"]
        organisasi = _ambil(direktur, workspace.slug, lingkup="organisasi")
        assert organisasi.status_code == status.HTTP_200_OK
        assert organisasi.data["values"]["completed"] == 5
        assert organisasi.data["breakdown"]["kind"] == "divisi"
        rincian = {b["code"]: b["values"]["completed"] for b in organisasi.data["breakdown"]["rows"]}
        assert rincian == {"OPS": 5, "FIN": 0}
        for params in (
            {"lingkup": "divisi", "id": str(org["fin"].id)},
            {"lingkup": "departemen", "id": str(org["akun"].id)},
            {"lingkup": "orang", "id": str(org["staf_f"].id)},
        ):
            assert _ambil(direktur, workspace.slug, **params).status_code == status.HTTP_200_OK, params

    def test_admin_workspace_seluruh_organisasi(self, org, workspace, create_user):
        assert _ambil(create_user, workspace.slug, lingkup="organisasi").status_code == status.HTTP_200_OK

    def test_judul_hanya_dari_project_yang_dianggotai(self, org, workspace, create_user):
        # Admin workspace bukan anggota project Gudang: angkanya tetap, judulnya tidak.
        data = _ambil(create_user, workspace.slug, lingkup="orang", id=str(org["staf_a"].id)).data
        assert data["values"]["completed"] == 4
        assert data["values"]["overdue"] == 1
        assert data["items"] == {"overdue": [], "completed": []}

    def test_pilihan_lingkup_per_jenjang(self, org, workspace):
        def pilihan(user):
            klien = APIClient()
            klien.force_authenticate(user=user)
            data = klien.get(URL_LINGKUP.format(slug=workspace.slug)).data
            return (
                data["organisation"],
                [d["code"] for d in data["divisions"]],
                [d["code"] for d in data["departments"]],
                {o["display_name"] for o in data["people"]},
            )

        assert pilihan(org["staf_a"]) == (False, [], [], set())
        assert pilihan(org["spv"]) == (False, [], ["GUD"], {"staf-a", "staf-b"})
        assert pilihan(org["manager"]) == (
            False,
            ["OPS"],
            ["GUD", "KRM"],
            {"staf-a", "staf-b", "spv-gudang", "staf-kirim"},
        )
        seluruh, divisi, departemen, orang = pilihan(org["direktur"])
        assert (seluruh, divisi, departemen) == (True, ["FIN", "OPS"], ["AKT", "GUD", "KRM"])
        assert {"staf-a", "staf-fin", "manager-ops"} <= orang


@pytest.mark.contract
class TestPeriode:
    def test_batas_bulan_memakai_hari_kantor(self, org, workspace):
        data = _ambil(org["staf_b"], workspace.slug, periode="this_month").data
        # "Awal November" (00.30 WIB) masuk November; "Akhir Oktober" masuk pembanding.
        assert data["values"]["completed"] == 2
        assert data["previous"]["completed"] == 1

    def test_pekan_ini_mulai_senin(self, org, workspace):
        data = _ambil(org["staf_a"], workspace.slug, periode="this_week").data
        assert data["period"]["start"] == date(2026, 11, 16)
        assert data["values"]["completed"] == 0
        # Terlambat sekarang tidak mengikuti periode.
        assert data["values"]["overdue"] == 1

    def test_rentang_khusus_inklusif(self, org, workspace):
        data = _ambil(org["staf_b"], workspace.slug, periode="custom", mulai="2026-10-31", sampai="2026-10-31").data
        assert data["values"]["completed"] == 1
        assert data["period"]["previous_start"] == date(2026, 10, 30)

    @pytest.mark.parametrize(
        "params",
        [
            {"periode": "selamanya"},
            {"periode": "custom"},
            {"periode": "custom", "mulai": "2026-11-10", "sampai": "2026-11-01"},
            {"periode": "custom", "mulai": "kemarin", "sampai": "2026-11-01"},
            {"lingkup": "planet"},
            {"lingkup": "departemen"},
        ],
    )
    def test_parameter_tidak_sah_400(self, org, workspace, params):
        assert _ambil(org["staf_a"], workspace.slug, **params).status_code == status.HTTP_400_BAD_REQUEST
