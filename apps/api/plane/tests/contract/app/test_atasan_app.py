# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tidak ada yang bisa menugaskan atasannya
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Keputusan user (P29 putaran 2): "we shouldn't be able to assign our atasan".

Bentuk uji, satu departemen DEP (project P) di divisi DIV, ditambah DEP2 (P2):

    staf, staf_b           Staf di DEP
    leader, leader_b       Leader di DEP
    sup, sup_b             Supervisor di DEP
    manager, manager_b     Manager divisi DIV
    sek, sek_b             Sekretaris (tanpa tempat)
    dir, dir_b             Direktur (tanpa tempat)
    admin_staf             admin workspace, Staf di DEP
    admin_bebas            admin workspace tanpa jenjang di mana pun
    sa                     Super Admin tanpa jenjang
    sa_it                  Super Admin tanpa jenjang yang "anggota asli" P

Yang dikunci: tiap jenjang tidak bisa menugaskan jenjang di atasnya, dengan katup
gerbang mati maupun menyala dan dengan ASSIGN_DOWN_ONLY mati; setingkat dan ke
bawah tidak berubah; hanya Super Admin dan admin tanpa jenjang yang bebas. Juga
lewat pintu samping: naik assignee dari sub-item, default assignee project, dan
dropdown `bisa-ditugaskan/`.
"""

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    APIToken,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueAssignee,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    SuperAdminTerlihatDiProject,
    TINGKAT_DIREKTUR,
    TINGKAT_LEADER,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SEKRETARIS,
    TINGKAT_SUPERVISOR,
    WorkspaceMember,
)
from plane.db.superadmin import sinkronkan_super_admin
from plane.license.models import Instance, InstanceAdmin
from plane.space.serializer.issue import IssueCreateSerializer as SpaceIssueCreateSerializer
from plane.tests.contract.app.test_persetujuan_manager_app import (
    URL_ISSUE_DETAIL,
    URL_ISSUES,
    _klien,
    _states,
    _user,
)
from plane.utils.atasan import PESAN_ATASAN
from plane.utils.hierarki import FLAG_GERBANG
from plane.utils.saklar_instance import ASSIGN_DOWN_ONLY

URL_SUB = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/sub-issues/"
URL_KUASA = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/bisa-ditugaskan/"
URL_PROJECT = "/api/workspaces/{slug}/projects/{project_id}/"
URL_V1_PROJECT = "/api/v1/workspaces/{slug}/projects/{project_id}/"

SETELAN = {
    "katup_mati": {FLAG_GERBANG: "0", ASSIGN_DOWN_ONLY: "1"},
    "katup_nyala": {FLAG_GERBANG: "1", ASSIGN_DOWN_ONLY: "1"},
    "ke_bawah_mati": {FLAG_GERBANG: "1", ASSIGN_DOWN_ONLY: "0"},
}

# pelaku -> (di atasnya, setingkat, di bawahnya). Staf-mode pelaku ikut jadi assignee
# sendiri, karena dengan katup menyala staf wajib tetap ada di tugasnya.
TANGGA = {
    "staf": ("leader", "staf_b", None),
    "leader": ("sup", "leader_b", "staf"),
    "sup": ("manager", "sup_b", "leader"),
    "manager": ("sek", "manager_b", "sup"),
    "sek": ("dir", "sek_b", "manager"),
    "dir": ("sa_it", "dir_b", "sek"),
    "admin_staf": ("sup", "staf", None),
}
MODE_STAF = {"staf", "admin_staf"}


def _super_admin(ws, prefix):
    instance = Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-atasan-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )
    orang = _user(prefix, ws)
    InstanceAdmin.objects.create(instance=instance, user=orang, role=20)
    sinkronkan_super_admin(orang.id)
    return orang


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.p = Project.objects.create(name="DEP Board", identifier="DEP", workspace=workspace, created_by=create_user)
    o.p2 = Project.objects.create(name="DEP2 Board", identifier="DEPB", workspace=workspace, created_by=create_user)
    o.div = Divisi.objects.create(workspace=workspace, kode="DIV", nama="Divisi")
    o.dep = Departemen.objects.create(workspace=workspace, divisi=o.div, kode="DEP", nama="Departemen")
    o.dep2 = Departemen.objects.create(workspace=workspace, divisi=o.div, kode="DEP2", nama="Departemen 2")
    DepartemenProject.objects.create(workspace=workspace, departemen=o.dep, project=o.p)
    DepartemenProject.objects.create(workspace=workspace, departemen=o.dep2, project=o.p2)

    def tempatkan(nama, tingkat, **tempat):
        orang = _user(nama, workspace)
        JabatanOrganisasi.objects.create(workspace=workspace, member=orang, tingkat=tingkat, **tempat)
        setattr(o, nama, orang)
        return orang

    for nama in ("staf", "staf_b"):
        tempatkan(nama, TINGKAT_MEMBER, departemen=o.dep)
    for nama in ("leader", "leader_b"):
        tempatkan(nama, TINGKAT_LEADER, departemen=o.dep)
    for nama in ("sup", "sup_b"):
        tempatkan(nama, TINGKAT_SUPERVISOR, departemen=o.dep)
    for nama in ("manager", "manager_b"):
        tempatkan(nama, TINGKAT_MANAGER, divisi=o.div)
    for nama in ("sek", "sek_b"):
        tempatkan(nama, TINGKAT_SEKRETARIS)
    for nama in ("dir", "dir_b"):
        tempatkan(nama, TINGKAT_DIREKTUR)
    tempatkan("staf2", TINGKAT_MEMBER, departemen=o.dep2)

    tempatkan("admin_staf", TINGKAT_MEMBER, departemen=o.dep)
    o.admin_bebas = _user("admin_bebas", workspace)
    WorkspaceMember.objects.filter(workspace=workspace, member__in=[o.admin_staf, o.admin_bebas]).update(role=20)
    ProjectMember.objects.update_or_create(
        project=o.p, member=o.admin_bebas, workspace=workspace, defaults={"role": 20, "is_active": True}
    )

    o.sa = _super_admin(workspace, "sa")
    o.sa_it = _super_admin(workspace, "sa_it")
    SuperAdminTerlihatDiProject.objects.create(project=o.p, member=o.sa_it, workspace=workspace)

    o.states = _states(workspace, o.p)
    return o


def _setel(monkeypatch, setelan):
    for kunci, nilai in SETELAN[setelan].items():
        monkeypatch.setenv(kunci, nilai)


def _assignee(issue_id):
    return set(IssueAssignee.objects.filter(issue_id=issue_id).values_list("assignee_id", flat=True))


def _buat(org, pelaku, assignee_ids, project=None):
    return _klien(pelaku).post(
        URL_ISSUES.format(slug=org.ws.slug, project_id=(project or org.p).id),
        {"name": "Tugas uji", "assignee_ids": [str(a) for a in assignee_ids]},
        format="json",
    )


def _tugas(org, pembuat, *assignee, parent=None):
    issue = Issue(name="Tugas", workspace=org.ws, project=org.p, parent=parent, state=org.states["started"])
    issue.save()
    Issue.objects.filter(pk=issue.pk).update(created_by=pembuat)
    issue.refresh_from_db()
    for orang in assignee:
        IssueAssignee.objects.create(issue=issue, assignee=orang, project=org.p, workspace=org.ws)
    return issue


def _tugaskan(org, nama_pelaku, nama_penerima):
    pelaku, penerima = getattr(org, nama_pelaku), getattr(org, nama_penerima)
    ids = [pelaku.id, penerima.id] if nama_pelaku in MODE_STAF else [penerima.id]
    return _buat(org, pelaku, ids)


def _galat(respon):
    return str((getattr(respon, "data", None) or {}).get("assignee_ids", ""))


# --------------------------------------------------------------------------
# 1. Penugasan langsung: atas ditolak, setingkat dan bawah seperti sebelumnya
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestTidakBisaMenugaskanAtasan:
    @pytest.mark.parametrize("setelan", list(SETELAN))
    @pytest.mark.parametrize("pelaku", list(TANGGA))
    def test_atasan_ditolak(self, org, pelaku, setelan, monkeypatch):
        _setel(monkeypatch, setelan)
        respon = _tugaskan(org, pelaku, TANGGA[pelaku][0])
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, getattr(respon, "data", None)
        assert PESAN_ATASAN in _galat(respon)

    @pytest.mark.parametrize("setelan", list(SETELAN))
    @pytest.mark.parametrize("pelaku", [p for p, (_, _, bawah) in TANGGA.items() if bawah])
    def test_bawahan_tetap_boleh(self, org, pelaku, setelan, monkeypatch):
        _setel(monkeypatch, setelan)
        bawah = TANGGA[pelaku][2]
        respon = _tugaskan(org, pelaku, bawah)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert getattr(org, bawah).id in _assignee(respon.json()["id"])

    @pytest.mark.parametrize("setelan", list(SETELAN))
    @pytest.mark.parametrize("pelaku", list(TANGGA))
    def test_setingkat_tidak_disentuh_aturan_atasan(self, org, pelaku, setelan, monkeypatch):
        """Aturan rekan yang lama tetap memutuskan; katup mati = rekan boleh, seperti dulu."""
        _setel(monkeypatch, setelan)
        respon = _tugaskan(org, pelaku, TANGGA[pelaku][1])
        assert PESAN_ATASAN not in _galat(respon)
        if setelan == "katup_mati":
            assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    @pytest.mark.parametrize("setelan", list(SETELAN))
    @pytest.mark.parametrize("pelaku", ["sa", "admin_bebas"])
    @pytest.mark.parametrize("penerima", ["dir", "sa_it"])
    def test_super_admin_dan_admin_tanpa_jenjang_bebas(self, org, pelaku, penerima, setelan, monkeypatch):
        _setel(monkeypatch, setelan)
        respon = _tugaskan(org, pelaku, penerima)
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    @pytest.mark.parametrize("setelan", list(SETELAN))
    def test_staf_tanpa_jenjang_dihitung_staf(self, org, setelan, monkeypatch):
        """Anggota eksplisit tanpa jenjang: hanya setingkat Staf, tidak bisa ke Supervisor."""
        _setel(monkeypatch, setelan)
        tanpa = _user("tanpa", org.ws)
        ProjectMember.objects.create(project=org.p, member=tanpa, workspace=org.ws, role=15)
        respon = _buat(org, tanpa, [org.sup.id])
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
        assert PESAN_ATASAN in _galat(respon)

    @pytest.mark.parametrize("pelaku", list(TANGGA))
    def test_assign_diri_sendiri_selalu_boleh(self, org, pelaku, monkeypatch):
        _setel(monkeypatch, "katup_nyala")
        orang = getattr(org, pelaku)
        respon = _buat(org, orang, [orang.id])
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)

    def test_admin_berjenjang_di_departemen_lain_memakai_jenjangnya(self, org, monkeypatch):
        """Admin yang Supervisor di DEP2 dan tidak ditempatkan di DEP: jenjangnya Supervisor di P."""
        _setel(monkeypatch, "katup_mati")
        admin = _user("admin_sup2", org.ws)
        WorkspaceMember.objects.filter(workspace=org.ws, member=admin).update(role=20)
        JabatanOrganisasi.objects.create(
            workspace=org.ws, member=admin, tingkat=TINGKAT_SUPERVISOR, departemen=org.dep2
        )
        ProjectMember.objects.update_or_create(
            project=org.p, member=admin, workspace=org.ws, defaults={"role": 20, "is_active": True}
        )
        assert _buat(org, admin, [org.manager.id]).status_code == status.HTTP_400_BAD_REQUEST
        assert _buat(org, admin, [org.sup.id]).status_code == status.HTTP_201_CREATED

    def test_assignee_lama_tidak_diperiksa_ulang(self, org, monkeypatch):
        """Tugas yang sudah dipegang manager tetap bisa diberi bawahan oleh supervisor."""
        _setel(monkeypatch, "katup_mati")
        tugas = _tugas(org, org.manager, org.manager)
        respon = _klien(org.sup).patch(
            URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p.id, issue_id=tugas.id),
            {"assignee_ids": [str(org.manager.id), str(org.staf.id)]},
            format="json",
        )
        assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
        assert _assignee(tugas.id) == {org.manager.id, org.staf.id}


# --------------------------------------------------------------------------
# 2. Naik assignee dari sub-item tidak menugaskan atasan ke induk
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestNaikAssignee:
    @pytest.mark.parametrize("katup", ["0", "1"])
    def test_staf_memasang_sub_item_atasannya_tidak_menaikkan_atasan(self, org, katup, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, katup)
        induk = _tugas(org, org.staf, org.staf)
        anak = _tugas(org, org.manager, org.staf, org.manager)
        respon = _klien(org.staf).post(
            URL_SUB.format(slug=org.ws.slug, project_id=org.p.id, issue_id=induk.id),
            {"sub_issue_ids": [str(anak.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        anak.refresh_from_db()
        assert anak.parent_id == induk.id
        assert _assignee(induk.id) == {org.staf.id}

    @pytest.mark.parametrize("katup", ["0", "1"])
    def test_atasan_yang_memasang_tetap_menaikkan(self, org, katup, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, katup)
        induk = _tugas(org, org.manager, org.manager)
        anak = _tugas(org, org.manager, org.staf, org.sup)
        respon = _klien(org.manager).post(
            URL_SUB.format(slug=org.ws.slug, project_id=org.p.id, issue_id=induk.id),
            {"sub_issue_ids": [str(anak.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
        assert _assignee(induk.id) == {org.manager.id, org.staf.id, org.sup.id}

    @pytest.mark.parametrize("katup", ["0", "1"])
    def test_ganti_induk_lewat_patch_tidak_menaikkan_atasan(self, org, katup, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, katup)
        induk = _tugas(org, org.staf, org.staf)
        anak = _tugas(org, org.staf, org.staf, org.sup)
        respon = _klien(org.staf).patch(
            URL_ISSUE_DETAIL.format(slug=org.ws.slug, project_id=org.p.id, issue_id=anak.id),
            {"parent_id": str(induk.id)},
            format="json",
        )
        assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
        anak.refresh_from_db()
        assert anak.parent_id == induk.id
        assert _assignee(induk.id) == {org.staf.id}

    def test_membuat_sub_item_untuk_bawahan_tetap_naik(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        induk = _tugas(org, org.sup, org.sup)
        respon = _klien(org.sup).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p.id),
            {"name": "Anak", "parent_id": str(induk.id), "assignee_ids": [str(org.staf.id)]},
            format="json",
        )
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(induk.id) == {org.sup.id, org.staf.id}


# --------------------------------------------------------------------------
# 3. Default assignee
# --------------------------------------------------------------------------


@pytest.mark.contract
@pytest.mark.django_db
class TestDefaultAssignee:
    @pytest.mark.parametrize("katup", ["0", "1"])
    def test_default_atasan_tidak_dipasang_untuk_pembuat_di_bawahnya(self, org, katup, monkeypatch):
        """staf2 (DEP2) anggota eksplisit P: tidak sah auto-assign, jadi default yang berlaku."""
        monkeypatch.setenv(FLAG_GERBANG, katup)
        Project.objects.filter(pk=org.p.pk).update(default_assignee=org.manager)
        ProjectMember.objects.update_or_create(
            project=org.p, member=org.staf2, workspace=org.ws, defaults={"role": 15, "is_active": True}
        )
        respon = _klien(org.staf2).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p.id), {"name": "Tanpa assignee"}, format="json"
        )
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == set()

    def test_default_dipasang_untuk_admin_tanpa_jenjang(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "0")
        Project.objects.filter(pk=org.p.pk).update(default_assignee=org.manager)
        respon = _klien(org.admin_bebas).post(
            URL_ISSUES.format(slug=org.ws.slug, project_id=org.p.id), {"name": "Tanpa assignee"}, format="json"
        )
        assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
        assert _assignee(respon.json()["id"]) == {org.manager.id}

    @pytest.mark.parametrize(
        ("penyetel", "default", "harapan"),
        [
            ("sup", "manager", status.HTTP_400_BAD_REQUEST),
            ("sup", "staf", status.HTTP_200_OK),
            ("manager", "dir", status.HTTP_400_BAD_REQUEST),
            ("admin_staf", "sup", status.HTTP_400_BAD_REQUEST),
            ("admin_bebas", "dir", status.HTTP_200_OK),
            ("sa", "dir", status.HTTP_200_OK),
        ],
    )
    def test_setelan_project_menolak_default_atasan(self, org, penyetel, default, harapan):
        respon = _klien(getattr(org, penyetel)).patch(
            URL_PROJECT.format(slug=org.ws.slug, project_id=org.p.id),
            {"default_assignee": str(getattr(org, default).id)},
            format="json",
        )
        assert respon.status_code == harapan, getattr(respon, "data", None)
        if harapan == status.HTTP_400_BAD_REQUEST:
            assert PESAN_ATASAN in str(respon.data["default_assignee"])

    def test_setelan_project_lewat_api_v1(self, org):
        token = APIToken.objects.create(user=org.admin_staf, label=f"uji-{uuid4().hex[:6]}", user_type=0)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=token.token)
        url = URL_V1_PROJECT.format(slug=org.ws.slug, project_id=org.p.id)
        respon = client.patch(url, {"default_assignee": str(org.sup.id)}, format="json")
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, getattr(respon, "data", None)
        respon = client.patch(url, {"default_assignee": str(org.staf.id)}, format="json")
        assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)

    def test_default_papan_publik_tanpa_pelaku_hanya_staf(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "0")

        def buat(default):
            ser = SpaceIssueCreateSerializer(
                data={"name": "Dari papan publik"},
                context={"project_id": org.p.id, "workspace_id": org.ws.id, "default_assignee_id": default.id},
            )
            assert ser.is_valid(), ser.errors
            return ser.save(state=org.states["backlog"])

        assert _assignee(buat(org.sup).id) == set()
        assert _assignee(buat(org.staf).id) == {org.staf.id}


# --------------------------------------------------------------------------
# 4. Dropdown `bisa-ditugaskan/` tidak pernah menawarkan atasan
# --------------------------------------------------------------------------


def _pilihan(org, pelaku):
    respon = _klien(pelaku).get(URL_KUASA.format(slug=org.ws.slug, project_id=org.p.id))
    assert respon.status_code == status.HTTP_200_OK, getattr(respon, "data", None)
    data = respon.json()
    return set(data.get("user_ids") or [u["id"] for u in data.get("users", [])])


@pytest.mark.contract
@pytest.mark.django_db
class TestDropdown:
    @pytest.mark.parametrize("setelan", list(SETELAN))
    @pytest.mark.parametrize("pelaku", list(TANGGA))
    def test_atasan_tidak_ditawarkan(self, org, pelaku, setelan, monkeypatch):
        _setel(monkeypatch, setelan)
        atas, setara, bawah = TANGGA[pelaku]
        ids = _pilihan(org, getattr(org, pelaku))
        assert str(getattr(org, atas).id) not in ids
        assert str(getattr(org, pelaku).id) in ids
        if bawah:
            assert str(getattr(org, bawah).id) in ids
        if setelan == "katup_mati":
            assert str(getattr(org, setara).id) in ids

    @pytest.mark.parametrize("setelan", list(SETELAN))
    def test_supervisor_tidak_melihat_jenjang_di_atasnya_sama_sekali(self, org, setelan, monkeypatch):
        _setel(monkeypatch, setelan)
        ids = _pilihan(org, org.sup)
        for atas in ("manager", "manager_b", "sek", "sek_b", "dir", "dir_b", "sa_it"):
            assert str(getattr(org, atas).id) not in ids, atas

    @pytest.mark.parametrize("setelan", list(SETELAN))
    @pytest.mark.parametrize("pelaku", ["sa", "admin_bebas"])
    def test_yang_bebas_melihat_semua_yang_ditempatkan(self, org, pelaku, setelan, monkeypatch):
        _setel(monkeypatch, setelan)
        ids = _pilihan(org, getattr(org, pelaku))
        assert {str(org.dir.id), str(org.sa_it.id), str(org.staf.id)} <= ids
