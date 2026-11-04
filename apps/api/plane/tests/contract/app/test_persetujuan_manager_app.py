# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: persetujuan oleh manager divisi + biaya kueri antrean
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Antrean persetujuan dengan struktur KEP-29 yang hidup.

Bentuk uji:

    SALES -> SMT1 (P1) · SMT2 (P2)

Manager ditempatkan di DIVISI Sales (bukan di departemen mana pun), staf di SMT1.
Dikunci di sini:

* manager divisi melihat `boleh_saya_putuskan` dan bisa menyetujui/menolak (BUG-11);
* balasan keputusan membawa `tugas.state_id` status SESUDAH keputusan;
* jumlah kueri GET antrean tidak tumbuh mengikuti jumlah baris.
"""

from uuid import uuid4

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    DEFAULT_STATES,
    Departemen,
    DepartemenProject,
    Divisi,
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
from plane.utils.hierarki import FLAG_GERBANG

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_ISSUE_DETAIL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"
URL_PERSETUJUAN = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/"


def _user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_name="Uji"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _states(workspace, project):
    siap = {}
    for s in DEFAULT_STATES:
        st, _ = State.objects.get_or_create(
            project=project,
            workspace=workspace,
            name=s["name"],
            defaults={
                "color": s["color"],
                "sequence": s["sequence"],
                "group": s["group"],
                "default": s.get("default", False),
            },
        )
        siap.setdefault(st.group, st)
    return siap


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.p1 = Project.objects.create(name="SMT1 Board", identifier="P1", workspace=workspace, created_by=create_user)
    o.p2 = Project.objects.create(name="SMT2 Board", identifier="P2", workspace=workspace, created_by=create_user)
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="Sales Team 1")
    o.smt2 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT2", nama="Sales Team 2")
    DepartemenProject.objects.create(workspace=workspace, departemen=o.smt1, project=o.p1)
    DepartemenProject.objects.create(workspace=workspace, departemen=o.smt2, project=o.p2)

    o.manager = _user("mgr", workspace)
    o.direktur = _user("dir", workspace)
    o.sup2 = _user("sup2", workspace)
    o.staf = _user("staf", workspace)
    # Manager di DIVISI, tidak di departemen mana pun. Sinyal sinkron jangkauan
    # yang memberinya keanggotaan P1/P2, bukan tangan.
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.manager, tingkat=TINGKAT_MANAGER, divisi=o.sales)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.direktur, tingkat=TINGKAT_DIREKTUR)
    # Supervisor departemen LAIN: calon yang sah di P2, bukan di P1.
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.sup2, tingkat=TINGKAT_SUPERVISOR, departemen=o.smt2)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.staf, tingkat=TINGKAT_MEMBER, departemen=o.smt1)
    o.states = _states(workspace, o.p1)
    return o


def _ajukan(org, nama="Tugas staf"):
    """Staf membuat tugas lalu menggesernya ke Done: ditahan jadi pengajuan (KEP-55)."""
    respon = _klien(org.staf).post(
        URL_ISSUES.format(slug=org.ws.slug, project_id=org.p1.id),
        {"name": nama, "assignee_ids": [str(org.staf.id)]},
        format="json",
    )
    assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
    issue_id = respon.json()["id"]
    respon = _klien(org.staf).patch(
        URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=issue_id),
        {"state": str(org.states["completed"].id)},
        format="json",
    )
    assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
    return issue_id, PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")


@pytest.mark.contract
class TestManagerDivisiMemutuskan:
    @pytest.mark.django_db
    def test_manager_divisi_anggota_project_lewat_hierarki(self, org):
        assert ProjectMember.objects.filter(member=org.manager, project=org.p1, is_active=True).exists()

    @pytest.mark.django_db
    def test_antrean_penyetuju_menandai_boleh_saya_putuskan(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, baris = _ajukan(org)
        respon = _klien(org.manager).get(
            URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id) + "?peran=penyetuju"
        )
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        hasil = {h["id"]: h for h in respon.json()["hasil"]}
        assert hasil[str(baris.id)]["boleh_saya_putuskan"] is True
        penyetuju = {p["id"] for p in hasil[str(baris.id)]["penyetuju_di_divisi"]}
        assert str(org.manager.id) in penyetuju
        assert str(org.sup2.id) not in penyetuju  # supervisor departemen lain

    @pytest.mark.django_db
    def test_supervisor_departemen_lain_tidak_boleh(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, baris = _ajukan(org)
        # sup2 bukan anggota P1 (jangkauannya hanya SMT2), jadi ditolak lebih awal.
        respon = _klien(org.sup2).post(
            URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_manager_divisi_menyetujui_dan_balasan_membawa_state_baru(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, baris = _ajukan(org)
        respon = _klien(org.manager).post(
            URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id) + f"{baris.id}/",
            {"aksi": "setujui"},
            format="json",
        )
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        issue = Issue.objects.get(pk=issue_id)
        assert issue.state.group == "completed"
        assert respon.json()["status"] == "disetujui"
        assert respon.json()["tugas"]["state_id"] == str(issue.state_id)

    @pytest.mark.django_db
    def test_manager_divisi_menolak_dan_balasan_membawa_in_progress(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, baris = _ajukan(org)
        respon = _klien(org.manager).post(
            URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id) + f"{baris.id}/",
            {"aksi": "tolak", "alasan": "belum lengkap"},
            format="json",
        )
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        issue = Issue.objects.get(pk=issue_id)
        assert issue.state.group == "started"
        assert respon.json()["tugas"]["state_id"] == str(org.states["started"].id)


@pytest.mark.contract
class TestBiayaKueriAntrean:
    def _hitung(self, org):
        url = URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id) + "?peran=penyetuju"
        klien = _klien(org.manager)
        with CaptureQueriesContext(connection) as ctx:
            respon = klien.get(url)
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        return len(ctx.captured_queries), respon.json()["jumlah"]

    @pytest.mark.django_db
    def test_jumlah_kueri_tidak_tumbuh_mengikuti_baris(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _ajukan(org, "Satu")
        sedikit, n1 = self._hitung(org)
        for i in range(4):
            _ajukan(org, f"Tambahan {i}")
        banyak, n5 = self._hitung(org)
        assert (n1, n5) == (1, 5)
        assert banyak == sedikit, f"{sedikit} kueri untuk 1 baris, {banyak} untuk 5"

    @pytest.mark.django_db
    def test_riwayat_dipotong_menunggu_tidak(self, org, monkeypatch):
        """`peran=pemohon`: riwayat keputusan dibatasi, yang menunggu selalu utuh, terbaru dulu."""
        import plane.app.views.issue.persetujuan as modul  # noqa: PLC0415

        monkeypatch.setenv(FLAG_GERBANG, "1")
        monkeypatch.setattr(modul, "BATAS_RIWAYAT", 2)
        url = URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id)
        for i in range(3):
            _, baris = _ajukan(org, f"Ditolak {i}")
            _klien(org.manager).post(url + f"{baris.id}/", {"aksi": "tolak", "alasan": "ulang"}, format="json")
        _, menunggu = _ajukan(org, "Masih menunggu")

        respon = _klien(org.staf).get(url + "?peran=pemohon")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        hasil = respon.json()["hasil"]
        assert [h["status"] for h in hasil].count("ditolak") == 2
        assert hasil[0]["id"] == str(menunggu.id)
        waktu = [h["created_at"] for h in hasil]
        assert waktu == sorted(waktu, reverse=True)


@pytest.mark.contract
class TestAntreanHanyaUntukPenyetuju:
    """Antrean dan aksi memakai predikat yang sama: tak ada baris yang berujung 403."""

    @pytest.mark.django_db
    def test_bukan_penyetuju_tidak_melihat_baris_di_perlu_keputusan(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _, baris = _ajukan(org)
        url = URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id)
        # Pemohon sendiri dan rekan stafnya (anggota project, bukan atasan) tidak boleh melihatnya.
        rekan = _user("rekan", org.ws)
        JabatanOrganisasi.objects.create(
            workspace=org.ws, member=rekan, tingkat=TINGKAT_MEMBER, departemen=org.smt1
        )
        assert ProjectMember.objects.filter(member=rekan, project=org.p1, is_active=True).exists()
        for user in (org.staf, rekan):
            respon = _klien(user).get(url + "?peran=penyetuju")
            assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
            assert respon.json()["hasil"] == []
        # Tanpa `peran`: orang lain juga tidak melihat pengajuan yang bukan wewenangnya.
        respon = _klien(rekan).get(url)
        assert respon.json()["hasil"] == []
        # Penyetuju sah tetap melihatnya, dan aksi yang sama tidak ditolak.
        respon = _klien(org.manager).get(url + "?peran=penyetuju")
        assert [h["id"] for h in respon.json()["hasil"]] == [str(baris.id)]
        ok = _klien(org.manager).post(url + f"{baris.id}/", {"aksi": "setujui"}, format="json")
        assert ok.status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_ditolak_lalu_diajukan_ulang_tampil_menunggu_sekali(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        issue_id, baris = _ajukan(org)
        url = URL_PERSETUJUAN.format(slug=org.ws.slug, project_id=org.p1.id)
        tolak = _klien(org.manager).post(url + f"{baris.id}/", {"aksi": "tolak", "alasan": "ulang"}, format="json")
        assert tolak.status_code == status.HTTP_200_OK
        # Staf menggeser ke Done lagi = pengajuan ulang.
        geser = _klien(org.staf).patch(
            URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p1.id, issue_id=issue_id),
            {"state": str(org.states["completed"].id)},
            format="json",
        )
        assert geser.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)

        antrean = _klien(org.manager).get(url + "?peran=penyetuju").json()["hasil"]
        assert len(antrean) == 1
        assert antrean[0]["status"] == "menunggu" and antrean[0]["tugas"]["id"] == issue_id
        assert antrean[0]["boleh_saya_putuskan"] is True

        # "Pengajuan saya": satu baris terbaru per tugas, penolakan lama jadi riwayat saja.
        milik_staf = _klien(org.staf).get(url + "?peran=pemohon").json()["hasil"]
        assert [(h["tugas"]["id"], h["status"]) for h in milik_staf] == [(issue_id, "menunggu")]

        # Riwayat lengkap tetap ada lewat ?tugas=.
        riwayat = _klien(org.staf).get(url + f"?tugas={issue_id}").json()["hasil"]
        assert sorted(h["status"] for h in riwayat) == ["ditolak", "menunggu"]
        assert riwayat[0]["status"] == "menunggu"
