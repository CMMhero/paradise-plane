# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tepat waktu / terlambat memakai tenggat efektif
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Tes aturan tepat waktu / terlambat (`plane/utils/ketepatan_waktu.py`).

    tenggat efektif = max(Due date, hari kantor tugas dicatat)
    terlambat      = hari kantor selesai > tenggat efektif

Kasus yang memicu aturan ini: staf lupa membuat work item, mengerjakannya tepat
waktu, lalu mencatatnya sepekan kemudian dengan Due date asli dan langsung
mengajukan selesai. Itu bukan terlambat.

Bagian B menjalankan alur nyata (buat lewat API, geser ke Done = pengajuan,
atasan menyetujui) lalu membaca hasilnya dari laporan selesai, yang menghitung
angka di SQL (`q_tepat_waktu`/`q_terlambat`) dan label per baris di Python
(`ketepatan`). Keduanya harus sepakat.
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    DEFAULT_STATES,
    Issue,
    JabatanOrganisasi,
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
from plane.utils.hierarki import FLAG_GERBANG
from plane.utils.ketepatan_waktu import (
    TANPA_TENGGAT,
    TEPAT_WAKTU,
    TERLAMBAT,
    ketepatan,
    tenggat_efektif,
)
from plane.utils.laporan_selesai import PERIODE_30_HARI, susun_laporan
from plane.utils.tanggal_otomatis import tanggal_lokal

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_PUTUSKAN = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/{pk}/"
ZONA = "Asia/Jakarta"

TENGGAT = date(2026, 11, 10)


# ---------------------------------------------------------------------------
# A. Aturan murni
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAturanMurni:
    def test_tugas_biasa_tepat_waktu(self):
        # Dicatat 1 Nov, tenggat 10 Nov, selesai 9 Nov.
        assert ketepatan(date(2026, 11, 9), TENGGAT, date(2026, 11, 1)) == TEPAT_WAKTU

    def test_selesai_di_hari_tenggat_masih_tepat_waktu(self):
        assert ketepatan(TENGGAT, TENGGAT, date(2026, 11, 1)) == TEPAT_WAKTU

    def test_tugas_biasa_terlambat(self):
        assert ketepatan(date(2026, 11, 12), TENGGAT, date(2026, 11, 1)) == TERLAMBAT

    def test_dicatat_sesudah_tenggat_dan_selesai_hari_itu_tepat_waktu(self):
        # Lupa dicatat: dibuat 17 Nov dengan tenggat asli 10 Nov, diajukan 17 Nov.
        assert tenggat_efektif(TENGGAT, date(2026, 11, 17)) == date(2026, 11, 17)
        assert ketepatan(date(2026, 11, 17), TENGGAT, date(2026, 11, 17)) == TEPAT_WAKTU

    def test_dicatat_sesudah_tenggat_tapi_diajukan_belakangan_terlambat(self):
        # Pengecualian hanya untuk jeda tenggat -> pencatatan, bukan sesudahnya.
        assert ketepatan(date(2026, 11, 19), TENGGAT, date(2026, 11, 17)) == TERLAMBAT

    def test_tanpa_tanggal_dibuat_sama_dengan_aturan_lama(self):
        assert ketepatan(date(2026, 11, 12), TENGGAT) == TERLAMBAT
        assert ketepatan(date(2026, 11, 10), TENGGAT) == TEPAT_WAKTU

    def test_tanpa_tenggat(self):
        assert tenggat_efektif(None, date(2026, 11, 17)) is None
        assert ketepatan(date(2026, 11, 17), None, date(2026, 11, 17)) == TANPA_TENGGAT


# ---------------------------------------------------------------------------
# B. Alur nyata: buat, ajukan, setujui, baca laporan
# ---------------------------------------------------------------------------


def _hari_ini():
    return tanggal_lokal(None, ZONA)


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


@pytest.fixture
def workspace(db, monkeypatch):
    monkeypatch.setenv(FLAG_GERBANG, "1")
    pemilik = User.objects.create(email="owner-ktw@plane.so", username="owner_ktw")
    return Workspace.objects.create(name="WS", slug="ws-ktw", owner=pemilik)


@pytest.fixture
def staf(workspace):
    return _user("stafktw", workspace)


@pytest.fixture
def bos(workspace):
    return _user("bosktw", workspace)


@pytest.fixture
def divisi(workspace, bos, staf):
    project = Project.objects.create(
        name="Divisi T", identifier="DIVT", workspace=workspace, created_by=bos, timezone=ZONA
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


def _buat(staf, workspace, divisi, tenggat, dibuat_hari_lalu=0):
    """Staf mencatat tugas lewat API. `dibuat_hari_lalu` > 0 = tugas dicatat dulu."""
    res = _klien(staf).post(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id),
        {"name": "Tugas KTW", "assignee_ids": [str(staf.id)], "target_date": str(tenggat)},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED, getattr(res, "data", None)
    issue_id = res.json()["id"]
    if dibuat_hari_lalu:
        Issue.objects.filter(pk=issue_id).update(created_at=timezone.now() - timedelta(days=dibuat_hari_lalu))
    return issue_id


def _ajukan(staf, workspace, divisi, issue_id, hari_lalu=0):
    """Geser ke Done = pengajuan selesai. `hari_lalu` > 0 = pengajuan dibuat sekian hari lalu."""
    selesai = State.objects.filter(project=divisi, group="completed").order_by("sequence").first()
    res = _klien(staf).patch(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id) + f"{issue_id}/",
        {"state": str(selesai.id)},
        format="json",
    )
    assert res.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(res, "data", None)
    baris = PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")
    if hari_lalu:
        PersetujuanPenugasan.objects.filter(pk=baris.pk).update(created_at=timezone.now() - timedelta(days=hari_lalu))
        baris.refresh_from_db()
    return baris


def _setujui(bos, workspace, divisi, baris):
    res = _klien(bos).post(
        URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
        {"aksi": "setujui"},
        format="json",
    )
    assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)
    return Issue.objects.get(pk=baris.issue_id)


def _ketepatan_di_laporan(bos, workspace, issue_id):
    """(label baris, angka on_time, angka late) dari laporan selesai 30 hari."""
    laporan = susun_laporan(bos, workspace.slug, PERIODE_30_HARI)
    baris = next(t for t in laporan["items"] if t["id"] == str(issue_id))
    return baris["timing"], laporan["totals"]["on_time"], laporan["totals"]["late"]


@pytest.mark.contract
class TestKetepatanAlurPersetujuan:
    @pytest.mark.django_db
    def test_tugas_biasa_tepat_waktu(self, workspace, staf, bos, divisi):
        issue_id = _buat(staf, workspace, divisi, _hari_ini() + timedelta(days=3), dibuat_hari_lalu=5)
        _setujui(bos, workspace, divisi, _ajukan(staf, workspace, divisi, issue_id))

        assert _ketepatan_di_laporan(bos, workspace, issue_id) == (TEPAT_WAKTU, 1, 0)

    @pytest.mark.django_db
    def test_tugas_biasa_terlambat(self, workspace, staf, bos, divisi):
        # Dicatat 10 hari lalu, tenggat 5 hari lalu, baru diajukan hari ini.
        issue_id = _buat(staf, workspace, divisi, _hari_ini() - timedelta(days=5), dibuat_hari_lalu=10)
        _setujui(bos, workspace, divisi, _ajukan(staf, workspace, divisi, issue_id))

        assert _ketepatan_di_laporan(bos, workspace, issue_id) == (TERLAMBAT, 0, 1)

    @pytest.mark.django_db
    def test_dicatat_hari_ini_dengan_tenggat_lampau_dan_diajukan_hari_ini_tepat_waktu(
        self, workspace, staf, bos, divisi
    ):
        # Kasus user: lupa mencatat, pekerjaan sudah beres. Dicatat hari ini dengan
        # tenggat asli pekan lalu, langsung diajukan, disetujui.
        tenggat = _hari_ini() - timedelta(days=7)
        issue_id = _buat(staf, workspace, divisi, tenggat)
        issue = _setujui(bos, workspace, divisi, _ajukan(staf, workspace, divisi, issue_id))

        # Due date asli tidak digeser (selesai sesudah tenggat tak pernah menggesernya).
        assert issue.target_date == tenggat
        assert issue.state.group == "completed"
        assert _ketepatan_di_laporan(bos, workspace, issue_id) == (TEPAT_WAKTU, 1, 0)

    @pytest.mark.django_db
    def test_diajukan_terlambat_lalu_disetujui_tetap_terlambat(self, workspace, staf, bos, divisi):
        # Dicatat tepat waktu (10 hari lalu), tenggat 6 hari lalu, baru diajukan 2 hari
        # lalu, disetujui hari ini: selesainya memang sesudah tenggat.
        issue_id = _buat(staf, workspace, divisi, _hari_ini() - timedelta(days=6), dibuat_hari_lalu=10)
        _setujui(bos, workspace, divisi, _ajukan(staf, workspace, divisi, issue_id, hari_lalu=2))

        assert _ketepatan_di_laporan(bos, workspace, issue_id) == (TERLAMBAT, 0, 1)

    @pytest.mark.django_db
    def test_dicatat_belakangan_tapi_diajukan_beberapa_hari_sesudahnya_terlambat(self, workspace, staf, bos, divisi):
        # Pengecualian hanya menutup jeda tenggat -> pencatatan. Dicatat 3 hari lalu
        # (tenggat 10 hari lalu), diajukan hari ini: terlambat 3 hari dari pencatatan.
        issue_id = _buat(staf, workspace, divisi, _hari_ini() - timedelta(days=10), dibuat_hari_lalu=3)
        _setujui(bos, workspace, divisi, _ajukan(staf, workspace, divisi, issue_id))

        assert _ketepatan_di_laporan(bos, workspace, issue_id) == (TERLAMBAT, 0, 1)

    @pytest.mark.django_db
    def test_disetujui_sesudah_tenggat_tapi_diajukan_sebelumnya_tepat_waktu(self, workspace, staf, bos, divisi):
        # Selesai (diajukan) 5 hari lalu, tenggat 3 hari lalu, atasan baru menyetujui
        # hari ini. Waktu selesai = saat diajukan (KEP-84), jadi tepat waktu.
        issue_id = _buat(staf, workspace, divisi, _hari_ini() - timedelta(days=3), dibuat_hari_lalu=10)
        baris = _ajukan(staf, workspace, divisi, issue_id, hari_lalu=5)
        issue = _setujui(bos, workspace, divisi, baris)

        assert issue.completed_at == baris.created_at
        assert _ketepatan_di_laporan(bos, workspace, issue_id) == (TEPAT_WAKTU, 1, 0)

    @pytest.mark.django_db
    def test_hitung_ulang_memberi_hasil_sama(self, workspace, staf, bos, divisi):
        # Tidak ada nilai "terlambat" yang disimpan: membaca dua kali = hasil sama.
        issue_id = _buat(staf, workspace, divisi, _hari_ini() - timedelta(days=7))
        _setujui(bos, workspace, divisi, _ajukan(staf, workspace, divisi, issue_id))

        pertama = _ketepatan_di_laporan(bos, workspace, issue_id)
        assert _ketepatan_di_laporan(bos, workspace, issue_id) == pertama == (TEPAT_WAKTU, 1, 0)
