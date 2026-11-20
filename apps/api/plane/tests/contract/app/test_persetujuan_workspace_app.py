# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes halaman Persetujuan workspace dan angka direktur
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keputusan user 2026-11-20, tiga butir yang saling terkait:

1. Halaman Persetujuan workspace: semua yang menunggu keputusan saya, dari semua
   departemen yang saya awasi (`GET /workspaces/<slug>/persetujuan/`).
2. Permintaan lintas departemen tampil di sana untuk atasan departemen tujuan,
   diterima lewat Intake bawaan, dan peminta diberi tahu.
3. Angka direktur dan sekretaris hanya dari tugas buatan Supervisor ke atas.

Struktur: divisi OPS berisi departemen Gudang (WH) dan Kirim (KR); divisi FIN
berisi Kasir (KS). Manager OPS mengawasi WH dan KR, supervisor hanya WH.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks.direktur_digest_task import DataWorkspace, susun_laporan
from plane.db.models import (
    Departemen,
    DepartemenProject,
    Divisi,
    Intake,
    IntakeIssue,
    Issue,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    State,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
)
from plane.utils.setelan_instance import hari_ini_kantor

URL_ANTREAN = "/api/workspaces/{slug}/persetujuan/"
URL_PERMINTAAN = "/api/workspaces/{slug}/cross-division/permintaan/"
URL_TUJUAN = "/api/workspaces/{slug}/cross-division/tujuan/"
URL_INTAKE = "/api/workspaces/{slug}/projects/{project_id}/intake-issues/{issue_id}/"
URL_DASHBOARD = "/api/workspaces/{slug}/divisi-dashboard/"
URL_INBOX = "/api/workspaces/{slug}/users/notifications/"
URL_PERHATIAN = "/api/workspaces/{slug}/paradise/attention/"
URL_LAPORAN = "/api/workspaces/{slug}/divisi-dashboard/laporan/"


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _orang(ws, nama, tingkat, departemen=None, divisi=None):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{nama}-{unik}@plane.so", username=f"{nama}_{unik}", display_name=nama)
    WorkspaceMember.objects.create(workspace=ws, member=user, role=15)
    JabatanOrganisasi.objects.create(workspace=ws, member=user, tingkat=tingkat, departemen=departemen, divisi=divisi)
    return user


def _departemen(ws, divisi, kode):
    """Departemen + project-nya, dengan Intake menyala."""
    dep = Departemen.objects.create(workspace=ws, divisi=divisi, kode=kode, nama=f"Dept {kode}")
    project = Project.objects.create(name=f"Dept {kode}", identifier=kode, workspace=ws)
    DepartemenProject.objects.create(workspace=ws, departemen=dep, project=project)
    Intake.objects.create(name=f"{kode} Intake", project=project, is_default=True)
    for grup in ("unstarted", "completed"):
        State.objects.create(
            name=grup, group=grup, color="#000000", project=project, workspace=ws, default=grup == "unstarted"
        )
    return dep, project


def _tugas(project, pembuat, nama, tenggat=None):
    issue = Issue(
        name=nama,
        workspace=project.workspace,
        project=project,
        state=State.objects.get(project=project, group="unstarted"),
        target_date=tenggat,
    )
    issue.save(created_by_id=pembuat.id)
    return issue


def _ajukan_selesai(project, staf, nama):
    issue = _tugas(project, staf, nama)
    PersetujuanPenugasan.objects.create(
        workspace=project.workspace, project=project, issue=issue, pemohon=staf, penerima=staf, status="menunggu"
    )
    return issue


@pytest.fixture
def org(db, workspace):
    o = type("Org", (), {})()
    o.ws = workspace
    ops = Divisi.objects.create(workspace=workspace, kode="OPS", nama="Operasional")
    fin = Divisi.objects.create(workspace=workspace, kode="FIN", nama="Keuangan")
    o.manager = _orang(workspace, "manager", TINGKAT_MANAGER, divisi=ops)
    o.direktur = _orang(workspace, "direktur", TINGKAT_DIREKTUR)
    o.dep_wh, o.wh = _departemen(workspace, ops, "WH")
    o.dep_kr, o.kr = _departemen(workspace, ops, "KR")
    o.dep_ks, o.ks = _departemen(workspace, fin, "KS")
    o.spv = _orang(workspace, "spv", TINGKAT_SUPERVISOR, departemen=o.dep_wh)
    o.staf_wh = _orang(workspace, "stafwh", TINGKAT_MEMBER, departemen=o.dep_wh)
    o.staf_kr = _orang(workspace, "stafkr", TINGKAT_MEMBER, departemen=o.dep_kr)
    o.kasir = _orang(workspace, "kasir", TINGKAT_MEMBER, departemen=o.dep_ks)
    for project, anggota in (
        (o.wh, {o.manager: 20, o.direktur: 20, o.spv: 20, o.staf_wh: 15}),
        (o.kr, {o.manager: 20, o.direktur: 20, o.staf_kr: 15}),
        (o.ks, {o.direktur: 20, o.kasir: 15}),
    ):
        for user, role in anggota.items():
            # Penempatan bisa sudah membuat keanggotaannya (sinkron hierarki); perannya disamakan.
            ProjectMember.objects.update_or_create(
                project=project, member=user, workspace=workspace, defaults={"role": role, "is_active": True}
            )
    return o


def _minta(org, tujuan, judul):
    respon = _klien(org.kasir).post(
        URL_PERMINTAAN.format(slug=org.ws.slug),
        {"asal_project": str(org.ks.id), "tujuan_project": str(tujuan.id), "judul": judul},
        format="json",
    )
    assert respon.status_code == status.HTTP_201_CREATED, respon.data
    return IntakeIssue.objects.get(project=tujuan, issue__name=judul)


def _antrean(user, slug):
    respon = _klien(user).get(URL_ANTREAN.format(slug=slug))
    assert respon.status_code == status.HTTP_200_OK, respon.data
    return respon.json()


def _kabar_lintas_divisi(user, slug):
    """Baris inbox keputusan, dibaca lewat API inbox yang sama dengan aplikasi."""
    respon = _klien(user).get(URL_INBOX.format(slug=slug))
    assert respon.status_code == status.HTTP_200_OK, respon.data
    (kabar,) = [n for n in respon.data if (n["data"] or {}).get("issue_activity", {}).get("field") == "cross_division"]
    return kabar


def _ringkas(data):
    return sorted((i["jenis"], i["tugas"]["judul"]) for i in data["hasil"])


@pytest.mark.contract
class TestAntreanPersetujuanWorkspace:
    @pytest.mark.django_db
    def test_manager_melihat_pengajuan_dan_permintaan_dari_dua_departemen(self, org):
        _ajukan_selesai(org.wh, org.staf_wh, "Selesai gudang")
        _ajukan_selesai(org.kr, org.staf_kr, "Selesai kirim")
        _minta(org, org.wh, "Minta gudang")
        _minta(org, org.kr, "Minta kirim")

        data = _antrean(org.manager, org.ws.slug)

        assert data["boleh_memutuskan"] is True
        assert _ringkas(data) == [
            ("permintaan", "Minta gudang"),
            ("permintaan", "Minta kirim"),
            ("selesai", "Selesai gudang"),
            ("selesai", "Selesai kirim"),
        ]
        baris = next(i for i in data["hasil"] if i["tugas"]["judul"] == "Minta gudang")
        assert baris["departemen"]["kode"] == "WH"
        assert baris["divisi"]["kode"] == "OPS"
        assert baris["asal"]["identifier"] == "KS"
        assert baris["pemohon"]["id"] == str(org.kasir.id)
        assert baris["tugas"]["state"] is not None

    @pytest.mark.django_db
    def test_supervisor_hanya_departemennya(self, org):
        _ajukan_selesai(org.wh, org.staf_wh, "Selesai gudang")
        _ajukan_selesai(org.kr, org.staf_kr, "Selesai kirim")
        _minta(org, org.wh, "Minta gudang")
        _minta(org, org.kr, "Minta kirim")

        data = _antrean(org.spv, org.ws.slug)

        assert _ringkas(data) == [("permintaan", "Minta gudang"), ("selesai", "Selesai gudang")]

    @pytest.mark.django_db
    def test_staf_tidak_mendapat_apa_pun(self, org):
        _ajukan_selesai(org.wh, org.staf_wh, "Selesai gudang")
        _minta(org, org.wh, "Minta gudang")

        data = _antrean(org.staf_kr, org.ws.slug)

        assert data == {"boleh_memutuskan": False, "jumlah": 0, "hasil": []}

    @pytest.mark.django_db
    def test_keputusan_lewat_endpoint_project_mengosongkan_antrean(self, org):
        _ajukan_selesai(org.wh, org.staf_wh, "Selesai gudang")
        pk = _antrean(org.spv, org.ws.slug)["hasil"][0]["id"]

        respon = _klien(org.spv).post(
            f"/api/workspaces/{org.ws.slug}/projects/{org.wh.id}/persetujuan-penugasan/{pk}/",
            {"aksi": "setujui"},
            format="json",
        )

        assert respon.status_code == status.HTTP_200_OK, respon.data
        assert _antrean(org.spv, org.ws.slug)["hasil"] == []


@pytest.mark.contract
class TestPermintaanLintasDepartemen:
    @pytest.mark.django_db
    def test_tujuan_tidak_memuat_departemen_sendiri(self, org):
        respon = _klien(org.kasir).get(URL_TUJUAN.format(slug=org.ws.slug))

        ids = {d["id"] for d in respon.json()}
        assert str(org.wh.id) in ids
        assert str(org.ks.id) not in ids

    @pytest.mark.django_db
    def test_diterima_supervisor_jadi_work_item_dan_peminta_diberi_tahu(self, org):
        intake_issue = _minta(org, org.wh, "Cek stok palet")
        assert _ringkas(_antrean(org.spv, org.ws.slug)) == [("permintaan", "Cek stok palet")]

        respon = _klien(org.spv).patch(
            URL_INTAKE.format(slug=org.ws.slug, project_id=org.wh.id, issue_id=intake_issue.issue_id),
            {"status": 1},
            format="json",
        )

        assert respon.status_code == status.HTTP_200_OK, respon.data
        issue = Issue.objects.get(pk=intake_issue.issue_id)
        assert issue.state.group == "unstarted"
        assert _antrean(org.spv, org.ws.slug)["hasil"] == []
        kabar = _kabar_lintas_divisi(org.kasir, org.ws.slug)
        assert kabar["data"]["issue_activity"]["verb"] == "accepted"
        assert kabar["project"] == org.ks.id
        assert kabar["triggered_by"] == org.spv.id
        milik = _klien(org.kasir).get(URL_PERMINTAAN.format(slug=org.ws.slug)).json()
        assert milik[0]["status_permintaan"] == "diterima"
        assert milik[0]["nomor_tugas_tujuan"] == f"WH-{issue.sequence_id}"
        assert milik[0]["boleh_dibuka"] is False

    @pytest.mark.django_db
    def test_ditolak_dengan_alasan_sampai_ke_peminta(self, org):
        intake_issue = _minta(org, org.kr, "Kirim besok")

        respon = _klien(org.manager).patch(
            URL_INTAKE.format(slug=org.ws.slug, project_id=org.kr.id, issue_id=intake_issue.issue_id),
            {"status": -1, "alasan": "Armada penuh minggu ini"},
            format="json",
        )

        assert respon.status_code == status.HTTP_200_OK, respon.data
        kabar = _kabar_lintas_divisi(org.kasir, org.ws.slug)
        assert kabar["data"]["issue_activity"]["verb"] == "declined"
        assert kabar["data"]["issue_activity"]["issue_comment"] == "Armada penuh minggu ini"
        milik = _klien(org.kasir).get(URL_PERMINTAAN.format(slug=org.ws.slug)).json()
        assert milik[0]["status_permintaan"] == "ditolak"
        assert milik[0]["alasan_tolak"] == "Armada penuh minggu ini"


@pytest.mark.contract
class TestAngkaDirekturHanyaBuatanAtasan:
    @pytest.fixture
    def terlambat(self, org):
        kemarin = hari_ini_kantor() - timedelta(days=2)
        _tugas(org.wh, org.staf_wh, "Buatan staf", kemarin)
        _tugas(org.wh, org.spv, "Buatan supervisor", kemarin)
        # Permintaan lintas departemen dari staf: tanpa pembuat, dihitung jenjang peminta.
        diterima = _minta(org, org.wh, "Permintaan staf")
        diterima.status = 1
        diterima.save()
        Issue.objects.filter(pk=diterima.issue_id).update(
            state=State.objects.get(project=org.wh, group="unstarted"), target_date=kemarin
        )

    @pytest.mark.django_db
    def test_dashboard_direktur_tanpa_buatan_staf(self, org, terlambat):
        data = _klien(org.direktur).get(URL_DASHBOARD.format(slug=org.ws.slug)).json()

        wh = next(p for p in data["projects"] if p["identifier"] == "WH")
        assert wh["issues_overdue"] == 1
        assert data["leader_created_only"] is True

    @pytest.mark.django_db
    def test_dashboard_supervisor_angka_penuh(self, org, terlambat):
        data = _klien(org.spv).get(URL_DASHBOARD.format(slug=org.ws.slug)).json()

        wh = next(p for p in data["projects"] if p["identifier"] == "WH")
        assert wh["issues_overdue"] == 3
        assert data["leader_created_only"] is False

    @pytest.mark.django_db
    def test_laporan_harian_direktur_tanpa_buatan_staf(self, org, terlambat):
        hari_ini = hari_ini_kantor()
        data = DataWorkspace(org.ws.id, hari_ini, timezone.now() - timedelta(days=1))

        laporan = susun_laporan(data, [org.wh.id], "24 jam terakhir")

        assert laporan.divisi[0].unit[0].angka.lewat == 1

    @pytest.mark.django_db
    def test_perhatian_direktur_tanpa_buatan_staf(self, org, terlambat):
        data = _klien(org.direktur).get(URL_PERHATIAN.format(slug=org.ws.slug)).json()

        tim = next(g for g in data["groups"] if g["key"] == "team_overdue")
        assert [i["name"] for i in tim["items"]] == ["Buatan supervisor"]

    @pytest.mark.django_db
    def test_perhatian_supervisor_angka_penuh(self, org, terlambat):
        data = _klien(org.spv).get(URL_PERHATIAN.format(slug=org.ws.slug)).json()

        tim = next(g for g in data["groups"] if g["key"] == "team_overdue")
        assert sorted(i["name"] for i in tim["items"]) == ["Buatan staf", "Buatan supervisor", "Permintaan staf"]

    @pytest.mark.django_db
    def test_laporan_selesai_direktur_tanpa_buatan_staf(self, org):
        selesai = State.objects.get(project=org.wh, group="completed")
        for pembuat, nama in ((org.staf_wh, "Selesai staf"), (org.spv, "Selesai supervisor")):
            issue = _tugas(org.wh, pembuat, nama)
            Issue.objects.filter(pk=issue.pk).update(state=selesai, completed_at=timezone.now())

        direktur = _klien(org.direktur).get(URL_LAPORAN.format(slug=org.ws.slug)).json()
        spv = _klien(org.spv).get(URL_LAPORAN.format(slug=org.ws.slug)).json()

        assert [i["name"] for i in direktur["items"]] == ["Selesai supervisor"]
        assert sorted(i["name"] for i in spv["items"]) == ["Selesai staf", "Selesai supervisor"]
