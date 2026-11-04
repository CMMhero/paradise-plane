# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: waktu selesai = saat mengajukan (KEP-84)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Tes kontrak KEP-84.

* APPROVAL_FINISH_TIME: 0 (bawaan) = `completed_at` dan Due date otomatis memakai
  waktu PENGAJUAN; 1 = waktu disetujui (perilaku lama). Ajukan ulang memakai
  pengajuan terbaru; ditolak tetap NULL.
* APPROVAL_PENDING_NOT_LATE: 1 (bawaan) = tugas yang menunggu persetujuan tidak
  terlambat di Dashboard Divisi, Needs attention, dasbor Home, pengingat staf,
  ringkasan harian dan direktur; penyetujunya yang diingatkan. 0 = perilaku lama.
* Ringkasan sore dan laporan direktur menghitung tugas yang DISETUJUI di jendelanya
  walau `completed_at`-nya (waktu pengajuan) lebih awal.
"""

from datetime import timedelta
from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks import deadline_reminder_task as pengingat
from plane.db.models import (
    DEFAULT_STATES,
    Issue,
    IssueAssignee,
    JabatanOrganisasi,
    Notification,
    PengingatTenggat,
    PersetujuanPenugasan,
    Project,
    ProjectMember,
    State,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.license.models import InstanceConfiguration
from plane.utils import saklar_instance as si
from plane.utils.hierarki import FLAG_GERBANG
from plane.utils.tanggal_otomatis import tanggal_lokal

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_PUTUSKAN = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/{pk}/"
URL_DASBOR = "/api/users/me/workspaces/{slug}/dashboard/"
ZONA = "Asia/Jakarta"


def _setel(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": str(nilai), "category": "PARADISE", "is_encrypted": False}
    )


def _user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _hari_ini():
    return tanggal_lokal(None, ZONA)


@pytest.fixture
def workspace(db, monkeypatch):
    monkeypatch.setenv(FLAG_GERBANG, "1")
    pemilik = User.objects.create(email="owner-k84@plane.so", username="owner_k84")
    return Workspace.objects.create(name="WS", slug="ws-k84", owner=pemilik)


@pytest.fixture
def staf(workspace):
    return _user("stafk84", workspace)


@pytest.fixture
def bos(workspace):
    return _user("bosk84", workspace)


@pytest.fixture
def divisi(workspace, bos, staf):
    project = Project.objects.create(
        name="Divisi K", identifier="DIVK", workspace=workspace, created_by=bos, timezone=ZONA
    )
    ProjectMember.objects.create(project=project, member=bos, workspace=workspace, role=20)
    ProjectMember.objects.create(project=project, member=staf, workspace=workspace, role=15)
    JabatanOrganisasi.objects.create(workspace=workspace, member=bos, tingkat=TINGKAT_SUPERVISOR)
    JabatanOrganisasi.objects.create(workspace=workspace, member=staf, tingkat=TINGKAT_MEMBER)
    for d in DEFAULT_STATES:
        State.objects.get_or_create(
            project=project,
            workspace=workspace,
            name=d["name"],
            defaults={
                "color": d["color"],
                "sequence": d["sequence"],
                "group": d["group"],
                "default": d.get("default", False),
            },
        )
    return project


def _state(divisi, group):
    return State.objects.filter(project=divisi, group=group).order_by("sequence").first()


def _buat(user, workspace, divisi, **extra):
    res = _klien(user).post(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id),
        {"name": "Tugas K84", "assignee_ids": [str(user.id)], **extra},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED, getattr(res, "data", None)
    return res.json()["id"]


def _ajukan(staf, workspace, divisi, issue_id, mundur_hari=0):
    """Staf menggeser ke Done (= pengajuan). `mundur_hari`: pengajuan dibuat sekian hari lalu."""
    res = _klien(staf).patch(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id) + f"{issue_id}/",
        {"state": str(_state(divisi, "completed").id)},
        format="json",
    )
    assert res.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(res, "data", None)
    baris = PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")
    if mundur_hari:
        PersetujuanPenugasan.objects.filter(pk=baris.pk).update(
            created_at=timezone.now() - timedelta(days=mundur_hari)
        )
        baris.refresh_from_db()
    return baris


def _putuskan(bos, workspace, divisi, baris, aksi="setujui"):
    data = {"aksi": aksi}
    if aksi == "tolak":
        data["alasan"] = "Belum lengkap"
    res = _klien(bos).post(
        URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id), data, format="json"
    )
    assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)
    return Issue.objects.get(pk=baris.issue_id)


def _tugas_lewat(workspace, divisi, staf, menunggu, hari_lewat=2):
    """Tugas aktif (In Progress) milik staf, tenggat `hari_lewat` hari lalu."""
    issue = Issue.objects.create(
        name=f"Lewat {uuid4().hex[:4]}",
        workspace=workspace,
        project=divisi,
        state=_state(divisi, "started"),
        target_date=_hari_ini() - timedelta(days=hari_lewat),
        created_by=staf,
    )
    IssueAssignee.objects.create(issue=issue, assignee=staf, project=divisi, workspace=workspace)
    if menunggu:
        PersetujuanPenugasan.objects.create(
            workspace=workspace, project=divisi, issue=issue, pemohon=staf, penerima=staf
        )
    return issue


# ---------------------------------------------------------------------------
# A. APPROVAL_FINISH_TIME
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestWaktuSelesai:
    @pytest.mark.django_db
    def test_bawaan_saat_diajukan(self, workspace, staf, bos, divisi):
        issue_id = _buat(staf, workspace, divisi)
        baris = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=3)
        assert Issue.objects.get(pk=issue_id).completed_at is None, "menunggu: belum selesai"

        issue = _putuskan(bos, workspace, divisi, baris)

        assert issue.state.group == "completed"
        assert issue.completed_at == baris.created_at
        # Due date kosong diisi hari PENGAJUAN, bukan hari disetujui.
        assert issue.target_date == tanggal_lokal(baris.created_at, ZONA)
        assert issue.target_date == _hari_ini() - timedelta(days=3)

    @pytest.mark.django_db
    def test_saat_disetujui(self, workspace, staf, bos, divisi):
        _setel(si.APPROVAL_FINISH_TIME, si.SELESAI_SAAT_DISETUJUI)
        issue_id = _buat(staf, workspace, divisi)
        baris = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=3)
        sebelum = timezone.now()

        issue = _putuskan(bos, workspace, divisi, baris)

        assert issue.completed_at >= sebelum
        assert issue.target_date == _hari_ini()

    @pytest.mark.django_db
    def test_majukan_rencana_memakai_hari_pengajuan(self, workspace, staf, bos, divisi):
        # Diajukan 2 hari lalu, rencana 3 hari lagi, disetujui hari ini: selesai lebih
        # awal, jadi DUE_DATE_ON_EARLY_DONE=1 memajukan ke hari pengajuan.
        _setel(si.DUE_DATE_ON_EARLY_DONE, si.DUE_DATE_MAJU_KE_SELESAI)
        rencana = _hari_ini() + timedelta(days=3)
        issue_id = _buat(staf, workspace, divisi, target_date=str(rencana))
        baris = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=2)

        issue = _putuskan(bos, workspace, divisi, baris)

        assert issue.target_date == _hari_ini() - timedelta(days=2)

    @pytest.mark.django_db
    def test_diajukan_tepat_waktu_disetujui_terlambat_TIDAK_terlambat(self, workspace, staf, bos, divisi):
        # Rencana kemarin, diajukan 3 hari lalu (tepat waktu), disetujui hari ini.
        rencana = _hari_ini() - timedelta(days=1)
        issue_id = _buat(staf, workspace, divisi, target_date=str(rencana))
        baris = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=3)

        issue = _putuskan(bos, workspace, divisi, baris)

        assert issue.target_date == rencana
        assert tanggal_lokal(issue.completed_at, ZONA) <= issue.target_date

    @pytest.mark.django_db
    def test_ditolak_completed_at_tetap_kosong(self, workspace, staf, bos, divisi):
        issue_id = _buat(staf, workspace, divisi)
        baris = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=2)

        issue = _putuskan(bos, workspace, divisi, baris, "tolak")

        assert issue.completed_at is None
        assert issue.target_date is None

    @pytest.mark.django_db
    def test_ajukan_ulang_memakai_pengajuan_terbaru(self, workspace, staf, bos, divisi):
        issue_id = _buat(staf, workspace, divisi)
        lama = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=5)
        _putuskan(bos, workspace, divisi, lama, "tolak")

        # Diajukan ulang SESUDAH ditolak (urutan nyata), jadi bukan pengajuan lama.
        baru = _ajukan(staf, workspace, divisi, issue_id)
        issue = _putuskan(bos, workspace, divisi, baru)

        assert baru.id != lama.id
        assert issue.completed_at == baru.created_at
        assert issue.completed_at > lama.created_at
        assert issue.target_date == tanggal_lokal(baru.created_at, ZONA)


# ---------------------------------------------------------------------------
# B. APPROVAL_PENDING_NOT_LATE: penghitung terlambat
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestMenungguTidakTerlambat:
    @pytest.mark.django_db
    def test_dashboard_divisi(self, workspace, staf, bos, divisi):
        from plane.utils.ringkasan_divisi import hitung_ringkasan

        _tugas_lewat(workspace, divisi, staf, menunggu=True)
        _tugas_lewat(workspace, divisi, staf, menunggu=False)

        totals = hitung_ringkasan(bos, workspace.slug)["totals"]
        assert totals["issues_overdue"] == 1
        # Tetap aktif: belum disetujui selesai.
        assert totals["issues_active"] == 2

        _setel(si.APPROVAL_PENDING_NOT_LATE, "0")
        assert hitung_ringkasan(bos, workspace.slug)["totals"]["issues_overdue"] == 2

    @pytest.mark.django_db
    def test_needs_attention(self, workspace, staf, bos, divisi):
        from plane.utils.perhatian import susun_perhatian

        menunggu = _tugas_lewat(workspace, divisi, staf, menunggu=True)
        jalan = _tugas_lewat(workspace, divisi, staf, menunggu=False)
        segera = _tugas_lewat(workspace, divisi, staf, menunggu=True, hari_lewat=-2)

        def grup(user):
            return {g["key"]: g for g in susun_perhatian(user, workspace.slug)["groups"]}

        def ids(g):
            return {str(i["id"]) for i in g["items"]}

        milik = grup(staf)
        assert ids(milik["overdue_mine"]) == {str(jalan.id)}
        assert str(segera.id) not in ids(milik.get("due_soon", {"items": []}))
        # Tetap terlihat sebagai menunggu persetujuan.
        assert {str(menunggu.id), str(segera.id)} <= ids(milik["waiting_mine"])

        atasan = grup(bos)
        assert ids(atasan["team_overdue"]) == {str(jalan.id)}
        assert str(menunggu.id) in ids(atasan["decide"])

        _setel(si.APPROVAL_PENDING_NOT_LATE, "0")
        assert ids(grup(staf)["overdue_mine"]) == {str(jalan.id), str(menunggu.id)}

    @pytest.mark.django_db
    def test_dasbor_home(self, workspace, staf, divisi):
        _tugas_lewat(workspace, divisi, staf, menunggu=True)
        jalan = _tugas_lewat(workspace, divisi, staf, menunggu=False)

        res = _klien(staf).get(URL_DASBOR.format(slug=workspace.slug))
        assert res.status_code == status.HTTP_200_OK
        assert {str(i["id"]) for i in res.data["overdue_issues"]} == {str(jalan.id)}

        _setel(si.APPROVAL_PENDING_NOT_LATE, "0")
        res = _klien(staf).get(URL_DASBOR.format(slug=workspace.slug))
        assert len(res.data["overdue_issues"]) == 2

    @pytest.mark.django_db
    def test_ringkasan_harian_tanpa_tugas_menunggu(self, workspace, staf, divisi):
        from plane.bgtasks.daily_digest_task import TugasWorkspace

        menunggu = _tugas_lewat(workspace, divisi, staf, menunggu=True)
        jalan = _tugas_lewat(workspace, divisi, staf, menunggu=False)

        ids = {i.id for i in TugasWorkspace(workspace.id, _hari_ini()).tugas}
        assert jalan.id in ids and menunggu.id not in ids

        _setel(si.APPROVAL_PENDING_NOT_LATE, "0")
        assert menunggu.id in {i.id for i in TugasWorkspace(workspace.id, _hari_ini()).tugas}

    @pytest.mark.django_db
    def test_laporan_direktur_tanpa_tugas_menunggu(self, workspace, staf, divisi):
        from plane.bgtasks.direktur_digest_task import DataWorkspace

        _tugas_lewat(workspace, divisi, staf, menunggu=True, hari_lewat=10)
        _tugas_lewat(workspace, divisi, staf, menunggu=False, hari_lewat=10)
        sejak = timezone.now() - timedelta(days=1)

        angka = DataWorkspace(workspace.id, _hari_ini(), sejak, hari_macet=7, hari_ke_depan=7).angka[divisi.id]
        assert (angka.lewat, angka.macet) == (1, 1)

        _setel(si.APPROVAL_PENDING_NOT_LATE, "0")
        angka = DataWorkspace(workspace.id, _hari_ini(), sejak, hari_macet=7, hari_ke_depan=7).angka[divisi.id]
        assert (angka.lewat, angka.macet) == (2, 2)


# ---------------------------------------------------------------------------
# B. Pengingat: staf berhenti, penyetuju diingatkan
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestPengingatPenyetuju:
    @pytest.mark.django_db
    def test_inbox_pindah_ke_penyetuju(self, workspace, staf, bos, divisi):
        # Tenggat kemarin = titik inbox +1.
        menunggu = _tugas_lewat(workspace, divisi, staf, menunggu=True, hari_lewat=1)
        jalan = _tugas_lewat(workspace, divisi, staf, menunggu=False, hari_lewat=1)
        hari_ini = _hari_ini()

        pengingat.tulis_inbox_tenggat(hari_ini)
        pengingat.tulis_inbox_penyetuju(hari_ini)
        pengingat.tulis_inbox_penyetuju(hari_ini)  # idempoten

        staf_rows = Notification.objects.filter(receiver=staf, sender__startswith=pengingat.SENDER_TENGGAT + ":")
        assert set(staf_rows.values_list("entity_identifier", flat=True)) == {jalan.id}
        bos_rows = Notification.objects.filter(receiver=bos, sender__startswith=pengingat.SENDER_TENGGAT_PENYETUJU)
        assert list(bos_rows.values_list("entity_identifier", flat=True)) == [menunggu.id]
        assert bos_rows.get().data["issue_activity"]["verb"] == pengingat.VERB_PENYETUJU

    @pytest.mark.django_db
    def test_penyetuju_tidak_diingatkan_sebelum_tenggat(self, workspace, staf, bos, divisi):
        # Jatuh tempo besok (titik inbox -1): staf tidak, penyetuju juga belum.
        _tugas_lewat(workspace, divisi, staf, menunggu=True, hari_lewat=-1)

        assert pengingat.tulis_inbox_penyetuju(_hari_ini()) == 0
        assert pengingat.tulis_inbox_tenggat(_hari_ini()) == 0

    @pytest.mark.django_db
    def test_saklar_mati_perilaku_lama(self, workspace, staf, bos, divisi):
        _setel(si.APPROVAL_PENDING_NOT_LATE, "0")
        menunggu = _tugas_lewat(workspace, divisi, staf, menunggu=True, hari_lewat=1)

        pengingat.tulis_inbox_tenggat(_hari_ini())
        assert pengingat.tulis_inbox_penyetuju(_hari_ini()) == 0

        assert Notification.objects.filter(receiver=staf, entity_identifier=menunggu.id).exists()
        assert not Notification.objects.filter(receiver=bos, entity_identifier=menunggu.id).exists()

    @pytest.mark.django_db
    def test_email_ke_penyetuju_sekali(self, workspace, staf, bos, divisi):
        menunggu = _tugas_lewat(workspace, divisi, staf, menunggu=True, hari_lewat=3)
        panggilan = []

        def palsu(issue, penerima, titik, label="", penyetuju=False):
            panggilan.append((issue.id, {o.id for o in penerima}, titik, penyetuju))
            return [(list(penerima), None)]

        with (
            mock.patch.object(pengingat, "_aktif", return_value=True),
            mock.patch.object(pengingat, "aktif_sejak", return_value=True),
            mock.patch.object(pengingat, "boleh_email", return_value=True),
            mock.patch.object(pengingat, "kirim_email_pengingat_bersama", palsu),
        ):
            pertama = pengingat.kirim_pengingat_tenggat(tanggal=_hari_ini().isoformat())
            kedua = pengingat.kirim_pengingat_tenggat(tanggal=_hari_ini().isoformat())

        assert panggilan == [(menunggu.id, {bos.id}, 3, True)], "staf tidak, penyetuju sekali"
        assert pertama["terkirim"] == 1 and kedua["terkirim"] == 0 and kedua["dilewati"] == 1
        assert PengingatTenggat.objects.filter(issue=menunggu, penerima=bos, titik=3).count() == 1

    @pytest.mark.django_db
    def test_email_penyetuju_teksnya_untuk_penyetuju(self, workspace, staf, bos, divisi):
        from plane.bgtasks.deadline_reminder_email import susun_email_pengingat

        issue = _tugas_lewat(workspace, divisi, staf, menunggu=True, hari_lewat=3)
        subjek, teks, _ = susun_email_pengingat(issue, [bos], 3, bahasa="en", penyetuju=True)
        assert subjek.startswith("[Waiting for approval]")
        assert "waiting for your approval" in teks
        subjek_staf, _, _ = susun_email_pengingat(issue, [staf], 3, bahasa="en")
        assert subjek_staf.startswith("[OVERDUE]")


# ---------------------------------------------------------------------------
# Ringkasan: "selesai" ikut tanggal keputusan
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestSelesaiMenurutKeputusan:
    @pytest.mark.django_db
    def test_ringkasan_sore_memuat_yang_disetujui_hari_ini(self, workspace, staf, bos, divisi):
        from plane.bgtasks.daily_digest_task import TugasWorkspace

        issue_id = _buat(staf, workspace, divisi)
        baris = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=2)
        issue = _putuskan(bos, workspace, divisi, baris)
        assert tanggal_lokal(issue.completed_at, ZONA) < _hari_ini()

        data = TugasWorkspace(workspace.id, _hari_ini(), dengan_selesai=True)
        assert issue.id in data.selesai_ids

    @pytest.mark.django_db
    def test_laporan_direktur_menghitung_yang_disetujui_sejak(self, workspace, staf, bos, divisi):
        from plane.bgtasks.direktur_digest_task import DataWorkspace

        issue_id = _buat(staf, workspace, divisi)
        baris = _ajukan(staf, workspace, divisi, issue_id, mundur_hari=3)
        _putuskan(bos, workspace, divisi, baris)

        sejak = timezone.now() - timedelta(days=1)
        angka = DataWorkspace(workspace.id, _hari_ini(), sejak, hari_macet=7, hari_ke_depan=7).angka[divisi.id]
        assert angka.selesai == 1


# ---------------------------------------------------------------------------
# Registri & payload publik
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestRegistri:
    def test_kunci_sensitif_dan_bawaan(self):
        from plane.utils import setelan_instance as st

        assert {si.APPROVAL_FINISH_TIME, si.APPROVAL_PENDING_NOT_LATE} <= st.SENSITIF
        assert st.bawaan(si.APPROVAL_FINISH_TIME) == "0"
        assert st.bawaan(si.APPROVAL_PENDING_NOT_LATE) == "1"
        assert si.SETELAN_PILIHAN[si.APPROVAL_FINISH_TIME] == (0, 1)
        with pytest.raises(st.NilaiTidakSah):
            st.normalkan(si.APPROVAL_FINISH_TIME, "2")

    @pytest.mark.django_db
    def test_payload_instance(self):
        from django.core.cache import cache
        from rest_framework.test import APIRequestFactory

        from plane.license.api.views.instance import InstanceEndpoint
        from plane.license.models import Instance

        Instance.objects.create(
            instance_name="uji",
            instance_id=f"uji-k84-{uuid4().hex[:8]}",
            current_version="uji",
            last_checked_at=timezone.now(),
        )

        def nilai():
            cache.clear()
            res = InstanceEndpoint.as_view()(APIRequestFactory().get("/api/instances/"))
            return res.data["config"]["paradise_approval_pending_not_late"]

        try:
            assert nilai() is True
            _setel(si.APPROVAL_PENDING_NOT_LATE, "0")
            assert nilai() is False
        finally:
            cache.clear()
