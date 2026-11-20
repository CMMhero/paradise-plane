# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: Leader, admin berjenjang staf, tugas selesai terkunci (P29)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
# ruff: noqa: F811  (fixture `org` diimpor lalu dipakai sebagai parameter, pola pytest)

"""Tiga keputusan P29 (6, 7, 11).

Bentuk uji (fixture `org` dari test_persetujuan_manager_app) ditambah:

    SMT1 (P1): leader (Leader), sup1 (Supervisor), staf + staf2 (Staf)
    SMT2 (P2): sup2 (Supervisor), staf_lain (Staf, juga anggota eksplisit P1)
    admin_ws   admin workspace tanpa penempatan, anggota eksplisit P1
    admin_staf admin workspace yang ditempatkan sebagai Staf di SMT1
    sa         Super Admin tanpa penempatan
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from plane.db.models import (
    APIToken,
    FileAsset,
    Issue,
    IssueAssignee,
    IssueComment,
    IssueLink,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    ProjectMember,
    TINGKAT_LEADER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    WorkspaceMember,
)
from plane.db.superadmin import sinkronkan_super_admin
from plane.license.api.views.hierarki import InstanceHierarkiEndpoint
from plane.license.models import Instance, InstanceAdmin
from plane.tests.contract.app.test_persetujuan_manager_app import (  # noqa: F401
    URL_ISSUE_DETAIL,
    URL_ISSUES,
    URL_PERSETUJUAN,
    _klien,
    _user,
    org,
)
from plane.utils.hierarki import FLAG_GERBANG, tingkat_anggota

URL_KUASA = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/bisa-ditugaskan/"
URL_KOMENTAR = URL_ISSUE_DETAIL + "comments/"
URL_TAUTAN = URL_ISSUE_DETAIL + "issue-links/"
URL_LAMPIRAN = URL_ISSUE_DETAIL + "issue-attachments/{pk}/"
URL_SUB = URL_ISSUE_DETAIL + "sub-issues/"
URL_ARSIP = URL_ISSUE_DETAIL + "archive/"
URL_TANGGAL = "/api/workspaces/{slug}/projects/{project_id}/issue-dates/"
URL_V1_DETAIL = "/api/v1/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/"


def _tempatkan(org, user, tingkat, departemen):
    JabatanOrganisasi.objects.create(workspace=org.ws, member=user, tingkat=tingkat, departemen=departemen)


def _admin_ws(org, user):
    WorkspaceMember.objects.filter(workspace=org.ws, member=user).update(role=20)


@pytest.fixture
def p29(org, monkeypatch):
    monkeypatch.setenv(FLAG_GERBANG, "1")
    o = org
    o.leader = _user("leader", o.ws)
    o.sup1 = _user("sup1", o.ws)
    o.staf2 = _user("staf2", o.ws)
    o.staf_lain = _user("staflain", o.ws)
    _tempatkan(o, o.leader, TINGKAT_LEADER, o.smt1)
    _tempatkan(o, o.sup1, TINGKAT_SUPERVISOR, o.smt1)
    _tempatkan(o, o.staf2, TINGKAT_MEMBER, o.smt1)
    _tempatkan(o, o.staf_lain, TINGKAT_MEMBER, o.smt2)
    # Anggota eksplisit P1, supaya penolakannya datang dari aturan, bukan dari saringan anggota serializer.
    ProjectMember.objects.update_or_create(
        project=o.p1, member=o.staf_lain, workspace=o.ws, defaults={"role": 15, "is_active": True}
    )

    o.admin_ws = _user("adminws", o.ws)
    _admin_ws(o, o.admin_ws)
    ProjectMember.objects.update_or_create(
        project=o.p1, member=o.admin_ws, workspace=o.ws, defaults={"role": 20, "is_active": True}
    )

    o.admin_staf = _user("adminstaf", o.ws)
    _admin_ws(o, o.admin_staf)
    _tempatkan(o, o.admin_staf, TINGKAT_MEMBER, o.smt1)
    ProjectMember.objects.update_or_create(
        project=o.p2, member=o.admin_staf, workspace=o.ws, defaults={"role": 20, "is_active": True}
    )

    o.instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-p29-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    o.sa = _user("sa", o.ws)
    InstanceAdmin.objects.create(instance=o.instance, user=o.sa, role=20)
    sinkronkan_super_admin(o.sa.id)
    return o


def _url(pola, org, issue=None, project=None, **lain):
    return pola.format(slug=org.ws.slug, project_id=(project or org.p1).id, issue_id=getattr(issue, "id", None), **lain)


def _tugas(org, pembuat, assignees, grup="started", nama="Tugas"):
    issue = Issue(name=nama, workspace=org.ws, project=org.p1, state=org.states[grup])
    issue.save(created_by_id=pembuat.id)
    for a in assignees:
        IssueAssignee.objects.create(issue=issue, assignee=a, project=org.p1, workspace=org.ws)
    return issue


def _buat(client, org, assignees, project=None):
    return client.post(
        _url(URL_ISSUES, org, project=project),
        {"name": "Tugas baru", "assignee_ids": [str(a.id) for a in assignees]},
        format="json",
    )


def _patch(client, org, issue, data):
    return client.patch(_url(URL_ISSUE_DETAIL, org, issue), data, format="json")


def _kuasa(user, org, project=None):
    respon = _klien(user).get(_url(URL_KUASA, org, project=project))
    assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
    return respon.json()


# --------------------------------------------------------------------------
# A. Leader (keputusan 11)
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestLeader:
    def test_dropdown_leader_berisi_staf_departemennya(self, p29):
        data = _kuasa(p29.leader, p29)
        assert data["mode"] == "bawahan"
        assert data["tingkat_saya"] == TINGKAT_LEADER
        ids = {u["id"] for u in data["users"]}
        staf_smt1 = {str(p29.staf.id), str(p29.staf2.id), str(p29.admin_staf.id)}
        assert ids == {str(p29.leader.id)} | staf_smt1
        assert set(data["bawahan_ids"]) == staf_smt1

    def test_leader_menugaskan_staf_departemennya(self, p29):
        respon = _buat(_klien(p29.leader), p29, [p29.staf, p29.staf2])
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert set(
            IssueAssignee.objects.filter(issue_id=respon.json()["id"]).values_list("assignee_id", flat=True)
        ) == {
            p29.staf.id,
            p29.staf2.id,
        }

    @pytest.mark.parametrize("sasaran", ["sup1", "manager", "staf_lain"])
    def test_leader_DITOLAK_menugaskan_atasan_atau_departemen_lain(self, p29, sasaran):
        respon = _buat(_klien(p29.leader), p29, [getattr(p29, sasaran)])
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, getattr(respon, "data", None)

    def test_leader_mengubah_dan_berkomentar_di_tugas_staf(self, p29):
        tugas = _tugas(p29, p29.sup1, [p29.staf])
        assert _patch(_klien(p29.leader), p29, tugas, {"name": "Diubah leader"}).status_code == status.HTTP_200_OK
        respon = _klien(p29.leader).post(_url(URL_KOMENTAR, p29, tugas), {"comment_html": "<p>cek</p>"}, format="json")
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        respon = _patch(_klien(p29.leader), p29, tugas, {"assignee_ids": [str(p29.staf2.id)]})
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    def test_leader_DITOLAK_mengubah_tugas_supervisor(self, p29):
        tugas = _tugas(p29, p29.sup1, [p29.sup1])
        assert _patch(_klien(p29.leader), p29, tugas, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN

    def test_staf_bukan_leader_bagi_rekannya(self, p29):
        """Kontrol: Staf tetap tidak bisa menyentuh tugas rekannya."""
        tugas = _tugas(p29, p29.sup1, [p29.staf2])
        assert _patch(_klien(p29.staf), p29, tugas, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN

    def test_penyelesaian_leader_sendiri_menunggu_persetujuan(self, p29):
        tugas = _tugas(p29, p29.leader, [p29.leader])
        respon = _patch(_klien(p29.leader), p29, tugas, {"state_id": str(p29.states["completed"].id)})
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert respon.json()["approval_requested"] is True
        tugas.refresh_from_db()
        assert tugas.state.group == "started"
        assert PersetujuanPenugasan.objects.filter(issue=tugas, status="menunggu", pemohon=p29.leader).exists()

    def test_leader_menyelesaikan_tugas_staf_tetap_lewat_atasan(self, p29):
        tugas = _tugas(p29, p29.sup1, [p29.staf])
        respon = _patch(_klien(p29.leader), p29, tugas, {"state_id": str(p29.states["completed"].id)})
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        tugas.refresh_from_db()
        assert tugas.state.group == "started"
        assert PersetujuanPenugasan.objects.filter(issue=tugas, status="menunggu").exists()

    def test_leader_tidak_menyetujui(self, p29):
        tugas = _tugas(p29, p29.staf, [p29.staf])
        _patch(_klien(p29.staf), p29, tugas, {"state_id": str(p29.states["completed"].id)})
        baris = PersetujuanPenugasan.objects.get(issue=tugas, status="menunggu")
        antrean = _klien(p29.leader).get(_url(URL_PERSETUJUAN, p29) + "?peran=penyetuju")
        assert antrean.status_code == status.HTTP_200_OK
        assert all(not h["boleh_saya_putuskan"] for h in antrean.json()["hasil"])
        respon = _klien(p29.leader).post(
            _url(URL_PERSETUJUAN, p29) + f"{baris.id}/", {"aksi": "setujui"}, format="json"
        )
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        respon = _klien(p29.sup1).post(_url(URL_PERSETUJUAN, p29) + f"{baris.id}/", {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    def test_god_mode_menjadikan_leader_departemen(self, p29):
        request = APIRequestFactory().post(
            "/api/instances/hierarki/",
            {"member_id": str(p29.staf2.id), "peran_departemen": {str(p29.smt1.id): TINGKAT_LEADER}},
            format="json",
        )
        force_authenticate(request, user=p29.sa)
        respon = InstanceHierarkiEndpoint.as_view()(request)
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert respon.data["member"]["tingkat_nama"] == "Leader"
        assert tingkat_anggota(p29.staf2.id, p29.ws.id, p29.p1.id) == TINGKAT_LEADER


# --------------------------------------------------------------------------
# B. Admin berjenjang Staf di departemennya sendiri (keputusan 7)
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestAdminBerjenjangStaf:
    def test_dropdown_admin_staf_di_departemennya_mode_staf(self, p29):
        data = _kuasa(p29.admin_staf, p29)
        assert data["mode"] in ("rekan", "diri-sendiri")
        assert data["admin_penuh"] is True
        assert str(p29.admin_staf.id) in {u["id"] for u in data["users"]}

    def test_dropdown_admin_staf_di_departemen_lain_tetap_semua(self, p29):
        assert _kuasa(p29.admin_staf, p29, project=p29.p2)["mode"] == "semua"

    def test_admin_tanpa_penempatan_tetap_semua(self, p29):
        assert _kuasa(p29.admin_ws, p29)["mode"] == "semua"

    def test_tanpa_assignee_terisi_dirinya(self, p29):
        respon = _buat(_klien(p29.admin_staf), p29, [])
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert set(
            IssueAssignee.objects.filter(issue_id=respon.json()["id"]).values_list("assignee_id", flat=True)
        ) == {p29.admin_staf.id}

    def test_wajib_tetap_ada_dan_rekan_setingkat(self, p29):
        klien = _klien(p29.admin_staf)
        assert _buat(klien, p29, [p29.staf]).status_code == status.HTTP_400_BAD_REQUEST
        assert _buat(klien, p29, [p29.admin_staf, p29.sup1]).status_code == status.HTTP_400_BAD_REQUEST
        assert _buat(klien, p29, [p29.admin_staf, p29.staf]).status_code == status.HTTP_201_CREATED

    def test_di_luar_departemennya_tetap_admin(self, p29):
        respon = _buat(_klien(p29.admin_staf), p29, [p29.sup2], project=p29.p2)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    def test_super_admin_staf_juga_terikat(self, p29):
        _tempatkan(p29, p29.sa, TINGKAT_MEMBER, p29.smt1)
        assert _kuasa(p29.sa, p29)["mode"] in ("rekan", "diri-sendiri")
        assert _buat(_klien(p29.sa), p29, [p29.manager]).status_code == status.HTTP_400_BAD_REQUEST


# --------------------------------------------------------------------------
# C. Tugas selesai terkunci (keputusan 6)
# --------------------------------------------------------------------------

PERAN_SEMUA = ("staf", "leader", "sup1", "admin_ws", "sa")


def _selesai(p29):
    tugas = _tugas(p29, p29.sup1, [p29.staf], grup="completed")
    lampiran = FileAsset.objects.create(
        attributes={"name": "a.png", "type": "image/png", "size": 10},
        asset=f"{p29.ws.id}/a.png",
        size=10,
        workspace=p29.ws,
        project=p29.p1,
        issue=tugas,
        entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
        is_uploaded=True,
    )
    return tugas, lampiran


@pytest.mark.contract
@pytest.mark.django_db
class TestSelesaiTerkunci:
    @pytest.mark.parametrize("peran", PERAN_SEMUA)
    def test_tidak_ada_yang_bisa_mengubah(self, p29, peran):
        tugas, lampiran = _selesai(p29)
        klien = _klien(getattr(p29, peran))
        assert _patch(klien, p29, tugas, {"name": "Baru"}).status_code == status.HTTP_403_FORBIDDEN
        assert _patch(klien, p29, tugas, {"assignee_ids": [str(p29.staf2.id)]}).status_code == status.HTTP_403_FORBIDDEN
        komentar = klien.post(_url(URL_KOMENTAR, p29, tugas), {"comment_html": "<p>x</p>"}, format="json")
        assert komentar.status_code == status.HTTP_403_FORBIDDEN
        tautan = klien.post(_url(URL_TAUTAN, p29, tugas), {"url": "https://contoh.test/a"}, format="json")
        assert tautan.status_code == status.HTTP_403_FORBIDDEN
        hapus = klien.delete(_url(URL_LAMPIRAN, p29, tugas, pk=lampiran.id))
        assert hapus.status_code == status.HTTP_403_FORBIDDEN
        tugas.refresh_from_db()
        assert tugas.name == "Tugas"
        assert not IssueComment.objects.filter(issue=tugas).exists()
        assert not IssueLink.objects.filter(issue=tugas).exists()
        assert FileAsset.objects.filter(pk=lampiran.pk).exists()
        assert set(IssueAssignee.objects.filter(issue=tugas).values_list("assignee_id", flat=True)) == {p29.staf.id}

    @pytest.mark.parametrize("peran", ("sup1", "admin_ws", "sa"))
    def test_atasan_dan_admin_bisa_membuka_kembali_lalu_mengubah(self, p29, peran):
        tugas, _ = _selesai(p29)
        klien = _klien(getattr(p29, peran))
        respon = _patch(klien, p29, tugas, {"state_id": str(p29.states["started"].id)})
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        tugas.refresh_from_db()
        assert tugas.state.group == "started"
        assert _patch(klien, p29, tugas, {"name": "Sesudah dibuka"}).status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("peran", ("staf", "leader"))
    def test_assignee_dan_leader_tidak_bisa_membuka_kembali(self, p29, peran):
        tugas, _ = _selesai(p29)
        respon = _patch(_klien(getattr(p29, peran)), p29, tugas, {"state_id": str(p29.states["started"].id)})
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        tugas.refresh_from_db()
        assert tugas.state.group == "completed"

    def test_buka_kembali_sambil_mengubah_ditolak(self, p29):
        tugas, _ = _selesai(p29)
        respon = _patch(_klien(p29.sup1), p29, tugas, {"state_id": str(p29.states["started"].id), "name": "Diam-diam"})
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        tugas.refresh_from_db()
        assert (tugas.state.group, tugas.name) == ("completed", "Tugas")

    def test_terkunci_walau_katup_gerbang_mati(self, p29, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "0")
        tugas, _ = _selesai(p29)
        assert _patch(_klien(p29.admin_ws), p29, tugas, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN
        komentar = _klien(p29.staf).post(_url(URL_KOMENTAR, p29, tugas), {"comment_html": "<p>x</p>"}, format="json")
        assert komentar.status_code == status.HTTP_403_FORBIDDEN

    def test_pintu_samping_tanggal_dan_sub_item(self, p29):
        tugas, _ = _selesai(p29)
        klien = _klien(p29.sa)
        tanggal = klien.post(
            _url(URL_TANGGAL, p29), {"updates": [{"id": str(tugas.id), "start_date": "2026-11-03"}]}, format="json"
        )
        assert tanggal.status_code == status.HTTP_403_FORBIDDEN
        anak = _tugas(p29, p29.sup1, [p29.staf], nama="Anak")
        sub = klien.post(_url(URL_SUB, p29, tugas), {"sub_issue_ids": [str(anak.id)]}, format="json")
        assert sub.status_code == status.HTTP_403_FORBIDDEN
        baru = klien.post(_url(URL_ISSUES, p29), {"name": "Anak baru", "parent_id": str(tugas.id)}, format="json")
        assert baru.status_code == status.HTTP_403_FORBIDDEN
        Issue.objects.filter(pk=anak.pk).update(parent=tugas)
        lepas = _patch(klien, p29, anak, {"parent_id": None})
        assert lepas.status_code == status.HTTP_403_FORBIDDEN

    def test_api_token_ikut_terkunci(self, p29):
        tugas, _ = _selesai(p29)
        token = APIToken.objects.create(user=p29.sa, label=f"uji-{uuid4().hex[:6]}", user_type=0)
        from rest_framework.test import APIClient  # noqa: PLC0415

        klien = APIClient()
        klien.credentials(HTTP_X_API_KEY=token.token)
        respon = klien.patch(_url(URL_V1_DETAIL, p29, tugas), {"name": "Lewat token"}, format="json")
        assert respon.status_code == status.HTTP_403_FORBIDDEN, getattr(respon, "data", None)

    def test_arsip_tugas_selesai_tetap_bisa(self, p29):
        tugas, _ = _selesai(p29)
        respon = _klien(p29.sup1).post(_url(URL_ARSIP, p29, tugas))
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    def test_alur_persetujuan_setujui_dan_tolak_tetap_jalan(self, p29):
        disetujui = _tugas(p29, p29.staf, [p29.staf])
        ditolak = _tugas(p29, p29.staf, [p29.staf], nama="Ditolak")
        for tugas in (disetujui, ditolak):
            _patch(_klien(p29.staf), p29, tugas, {"state_id": str(p29.states["completed"].id)})
        for tugas, aksi in ((disetujui, "setujui"), (ditolak, "tolak")):
            baris = PersetujuanPenugasan.objects.get(issue=tugas, status="menunggu")
            respon = _klien(p29.sup1).post(
                _url(URL_PERSETUJUAN, p29) + f"{baris.id}/", {"aksi": aksi, "alasan": "uji"}, format="json"
            )
            assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        disetujui.refresh_from_db()
        ditolak.refresh_from_db()
        assert disetujui.state.group == "completed"
        assert ditolak.state.group == "started"
        # Sesudah disetujui, tugasnya terkunci seperti tugas selesai lain.
        assert _patch(_klien(p29.staf), p29, disetujui, {"name": "x"}).status_code == status.HTTP_403_FORBIDDEN
