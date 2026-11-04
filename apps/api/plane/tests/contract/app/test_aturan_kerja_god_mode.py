# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji aturan kerja & batas dari God Mode (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Setiap aturan KEP-83 diuji dua kali: bawaannya SAMA dengan perilaku sebelum
setelannya ada (deploy tidak mengubah apa pun), lalu nilai lainnya benar-benar
mengubah perilaku.

Setelan diubah lewat baris `InstanceConfiguration`, persis yang ditulis God Mode;
kunci KEP-83 tidak membaca env dengan namanya sendiri (KEP-48).
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.backends.db import SessionStore
from django.test import RequestFactory
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    DEFAULT_STATES,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueAssignee,
    IssueMention,
    JabatanOrganisasi,
    PersetujuanPenugasan,
    PesanLangsung,
    Project,
    ProjectMember,
    ProjectMemberInvite,
    State,
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    WorkspaceMember,
    WorkspaceMemberInvite,
    WorkspacePlan,
)
from plane.license.models import InstanceConfiguration
from plane.utils import saklar_instance as si
from plane.utils.hierarki import (
    FLAG_GERBANG,
    butuh_persetujuan,
    galat_penugasan,
    peta_tingkat,
    periksa_tingkat_penerima,
    saring_penyetuju,
)


# ---------------------------------------------------------------------------
# Pembantu
# ---------------------------------------------------------------------------


def _setel(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": str(nilai), "category": "PARADISE", "is_encrypted": False}
    )


def _user(prefix, workspace=None, role=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_name="Uji"
    )
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
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


def _tugas(project, pembuat, assignee=None, tenggat=None):
    issue = Issue(name="Tugas uji", workspace=project.workspace, project=project, target_date=tenggat)
    issue.save()
    # BaseModel.save() mengisi created_by dari crum (kosong di tes), jadi ditimpa.
    Issue.objects.filter(pk=issue.pk).update(created_by=pembuat)
    issue.refresh_from_db()
    if assignee:
        IssueAssignee.objects.create(issue=issue, assignee=assignee, project=project, workspace=project.workspace)
    return issue


def _anggota(project, user, role=15):
    ProjectMember.objects.update_or_create(
        project=project, member=user, workspace=project.workspace, defaults={"role": role, "is_active": True}
    )


@pytest.fixture
def org(db, workspace, create_user):
    """SALES -> SMT1 (P1). Staf & dua supervisor di SMT1, manager di divisi, direktur."""
    o = type("Org", (), {})()
    o.ws = workspace
    o.p1 = Project.objects.create(name="SMT1 Board", identifier="P1", workspace=workspace, created_by=create_user)
    o.sales = Divisi.objects.create(workspace=workspace, kode="SALES", nama="Sales")
    o.smt1 = Departemen.objects.create(workspace=workspace, divisi=o.sales, kode="SMT1", nama="Sales Team 1")
    DepartemenProject.objects.create(workspace=workspace, departemen=o.smt1, project=o.p1)
    o.staf = _user("staf", workspace)
    o.sup = _user("sup", workspace)
    o.sup_b = _user("supb", workspace)
    o.manager = _user("mgr", workspace)
    o.direktur = _user("dir", workspace)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.staf, tingkat=TINGKAT_MEMBER, departemen=o.smt1)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.sup, tingkat=TINGKAT_SUPERVISOR, departemen=o.smt1)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.sup_b, tingkat=TINGKAT_SUPERVISOR, departemen=o.smt1)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.manager, tingkat=TINGKAT_MANAGER, divisi=o.sales)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.direktur, tingkat=TINGKAT_DIREKTUR)
    for u in (o.staf, o.sup, o.sup_b, o.manager, o.direktur):
        _anggota(o.p1, u)
    o.states = _states(workspace, o.p1)
    return o


# ---------------------------------------------------------------------------
# 1. Persetujuan
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestAmbangPersetujuan:
    @pytest.mark.django_db
    def test_bawaan_hanya_staf_yang_butuh_persetujuan(self, org):
        assert si.setelan_angka(si.APPROVAL_REQUIRED_BELOW_LEVEL) == si.APPROVAL_DI_BAWAH_SUPERVISOR
        assert butuh_persetujuan(org.staf, org.p1.id, [org.staf.id]) is True
        assert butuh_persetujuan(org.sup, org.p1.id, [org.sup.id]) is False
        assert butuh_persetujuan(org.manager, org.p1.id, [org.manager.id]) is False

    @pytest.mark.django_db
    def test_jenjang_kosong_tetap_staf(self, org):
        tanpa_jenjang = _user("kosong", org.ws)
        assert butuh_persetujuan(tanpa_jenjang, org.p1.id, [tanpa_jenjang.id]) is True

    @pytest.mark.django_db
    def test_ambang_manager_menahan_supervisor_juga(self, org):
        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_MANAGER)
        assert butuh_persetujuan(org.sup, org.p1.id, [org.sup.id]) is True
        assert butuh_persetujuan(org.manager, org.p1.id, [org.manager.id]) is False

    @pytest.mark.django_db
    def test_ambang_direktur_menahan_semua_kecuali_direktur(self, org):
        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_DIREKTUR)
        assert butuh_persetujuan(org.manager, org.p1.id, [org.manager.id]) is True
        assert butuh_persetujuan(org.direktur, org.p1.id, [org.direktur.id]) is False

    @pytest.mark.django_db
    def test_penyetuju_pengajuan_staf_tidak_disaring(self, org):
        peta = peta_tingkat(org.ws.id)
        calon = [org.sup.id, org.sup_b.id, org.manager.id]
        assert saring_penyetuju(calon, peta, org.staf.id) == calon

    @pytest.mark.django_db
    def test_penyetuju_pengajuan_supervisor_hanya_yang_lebih_tinggi(self, org):
        peta = peta_tingkat(org.ws.id)
        calon = [org.sup.id, org.sup_b.id, org.manager.id]
        assert saring_penyetuju(calon, peta, org.sup.id) == [org.manager.id]


def _ajukan(org):
    """Staf membuat tugas lalu menggesernya ke Done: ditahan jadi pengajuan (KEP-55)."""
    url = f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/issues/"
    respon = _klien(org.staf).post(url, {"name": "Tugas staf", "assignee_ids": [str(org.staf.id)]}, format="json")
    assert respon.status_code == status.HTTP_201_CREATED, getattr(respon, "data", None)
    issue_id = respon.json()["id"]
    respon = _klien(org.staf).patch(f"{url}{issue_id}/", {"state": str(org.states["completed"].id)}, format="json")
    assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), getattr(respon, "data", None)
    return PersetujuanPenugasan.objects.get(issue_id=issue_id, status="menunggu")


def _tolak(org, baris, alasan=""):
    url = f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/persetujuan-penugasan/{baris.id}/"
    return _klien(org.manager).post(url, {"aksi": "tolak", "alasan": alasan}, format="json")


@pytest.mark.contract
class TestAlasanPenolakan:
    @pytest.mark.django_db
    def test_bawaan_menolak_tanpa_alasan(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        baris = _ajukan(org)
        respon = _tolak(org, baris)
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, respon.data
        baris.refresh_from_db()
        assert baris.status == "menunggu"

    @pytest.mark.django_db
    def test_saklar_mati_boleh_tanpa_alasan(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _setel(si.APPROVAL_REJECT_REASON_REQUIRED, "0")
        baris = _ajukan(org)
        respon = _tolak(org, baris)
        assert respon.status_code == status.HTTP_200_OK, respon.data
        baris.refresh_from_db()
        assert baris.status == "ditolak"

    @pytest.mark.django_db
    def test_pengajuan_supervisor_tidak_bisa_diputuskan_rekan_setingkat(self, org, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_MANAGER)
        issue = _tugas(org.p1, org.sup, assignee=org.sup)
        baris = PersetujuanPenugasan.objects.create(
            workspace=org.ws, project=org.p1, issue=issue, pemohon=org.sup, penerima=org.sup, status="menunggu"
        )
        url = f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/persetujuan-penugasan/{baris.id}/"
        respon = _klien(org.sup_b).post(url, {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        respon = _klien(org.manager).post(url, {"aksi": "setujui"}, format="json")
        assert respon.status_code == status.HTTP_200_OK, respon.data

    @pytest.mark.django_db
    def test_aturan_dikirim_ke_klien(self, org):
        url = f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/persetujuan-penugasan/bisa-ditugaskan/"
        respon = _klien(org.staf).get(url)
        assert respon.status_code == status.HTTP_200_OK
        assert respon.json()["aturan"] == {
            "hapus_tugas": 0,
            "ganti_tenggat": 0,
            "persetujuan_di_bawah": 20,
            "alasan_tolak_wajib": True,
            "tugaskan_ke_bawah_saja": True,
        }


# ---------------------------------------------------------------------------
# 2. Kepemilikan: hapus/arsip dan Due date
# ---------------------------------------------------------------------------


@pytest.fixture
def papan(db, workspace, create_user):
    o = type("Papan", (), {})()
    o.ws = workspace
    o.p = Project.objects.create(name="Papan", identifier="PB", workspace=workspace, created_by=create_user)
    o.pembuat = _user("pembuat", workspace)
    o.assignee = _user("assignee", workspace)
    o.admin = _user("admin", workspace)
    o.anggota = _user("anggota", workspace)
    _anggota(o.p, o.pembuat)
    _anggota(o.p, o.assignee)
    _anggota(o.p, o.admin, role=20)
    _anggota(o.p, o.anggota)
    o.issue = _tugas(o.p, o.pembuat, assignee=o.assignee)
    return o


def _hapus(papan, user):
    from plane.utils.task_access import bisa_hapus_tugas

    return bisa_hapus_tugas(user, papan.issue, papan.ws.slug, papan.p.id)


def _tenggat(papan, user):
    from plane.utils.task_access import bisa_ganti_tenggat

    return bisa_ganti_tenggat(user, papan.issue)


@pytest.mark.contract
class TestAturanHapus:
    @pytest.mark.django_db
    def test_bawaan_pembuat_dan_admin_project(self, papan):
        assert [_hapus(papan, u) for u in (papan.pembuat, papan.admin, papan.assignee, papan.anggota)] == [
            True,
            True,
            False,
            False,
        ]

    @pytest.mark.django_db
    def test_pembuat_saja(self, papan):
        _setel(si.TASK_DELETE_RULE, si.HAPUS_PEMBUAT_SAJA)
        assert [_hapus(papan, u) for u in (papan.pembuat, papan.admin, papan.assignee)] == [True, False, False]

    @pytest.mark.django_db
    def test_yang_boleh_ubah_gerbang_mati_semua_anggota(self, papan):
        _setel(si.TASK_DELETE_RULE, si.HAPUS_YANG_BOLEH_UBAH)
        assert all(_hapus(papan, u) for u in (papan.pembuat, papan.admin, papan.assignee, papan.anggota))

    @pytest.mark.django_db
    def test_yang_boleh_ubah_gerbang_nyala_ikut_hierarki(self, papan, monkeypatch):
        monkeypatch.setenv(FLAG_GERBANG, "1")
        _setel(si.TASK_DELETE_RULE, si.HAPUS_YANG_BOLEH_UBAH)
        assert _hapus(papan, papan.assignee) is True
        assert _hapus(papan, papan.anggota) is False

    @pytest.mark.django_db
    def test_endpoint_hapus_mengikuti_aturan(self, papan):
        url = f"/api/workspaces/{papan.ws.slug}/projects/{papan.p.id}/issues/{papan.issue.id}/"
        _setel(si.TASK_DELETE_RULE, si.HAPUS_PEMBUAT_SAJA)
        assert _klien(papan.admin).delete(url).status_code == status.HTTP_403_FORBIDDEN
        assert Issue.objects.filter(pk=papan.issue.pk).exists()
        # Kembali ke bawaan: admin project boleh lagi, seperti sebelum KEP-83.
        _setel(si.TASK_DELETE_RULE, si.HAPUS_ATURAN_HARI_INI)
        assert _klien(papan.admin).delete(url).status_code == status.HTTP_204_NO_CONTENT

    @pytest.mark.django_db
    def test_aturan_massal_dibaca_sekali(self, papan, django_assert_max_num_queries):
        # Endpoint massal: setelan, gerbang, Super Admin, dan peran admin dibaca
        # sekali untuk semua tugas, bukan per tugas. Jawabannya sama dengan satuan.
        from plane.utils.task_access import AturanTugas, bisa_ganti_tenggat, bisa_hapus_tugas

        _setel(si.DUE_DATE_CHANGE_RULE, si.TENGGAT_PLUS_ADMIN_PROJECT)
        tugas = [_tugas(papan.p, papan.pembuat) for _ in range(10)]
        aturan = AturanTugas(papan.admin)
        bisa_hapus_tugas(papan.admin, tugas[0], papan.ws.slug, papan.p.id, aturan)
        bisa_ganti_tenggat(papan.admin, tugas[0], aturan)
        with django_assert_max_num_queries(0):
            hapus = [bisa_hapus_tugas(papan.admin, t, papan.ws.slug, papan.p.id, aturan) for t in tugas]
            tenggat = [bisa_ganti_tenggat(papan.admin, t, aturan) for t in tugas]
        assert all(hapus) and all(tenggat)
        assert hapus == [_hapus(papan, papan.admin)] * 10
        # Slug workspace lain: admin project tidak berlaku, sama dengan saringan lama.
        assert bisa_hapus_tugas(papan.admin, tugas[0], "workspace-lain", papan.p.id, aturan) is False


@pytest.mark.contract
class TestAturanTenggat:
    @pytest.mark.django_db
    def test_bawaan_pembuat_saja(self, papan):
        assert [_tenggat(papan, u) for u in (papan.pembuat, papan.admin, papan.assignee)] == [True, False, False]

    @pytest.mark.django_db
    def test_plus_admin_project(self, papan):
        _setel(si.DUE_DATE_CHANGE_RULE, si.TENGGAT_PLUS_ADMIN_PROJECT)
        assert [_tenggat(papan, u) for u in (papan.pembuat, papan.admin, papan.assignee)] == [True, True, False]

    @pytest.mark.django_db
    def test_yang_boleh_ubah(self, papan, monkeypatch):
        _setel(si.DUE_DATE_CHANGE_RULE, si.TENGGAT_YANG_BOLEH_UBAH)
        assert _tenggat(papan, papan.anggota) is True
        monkeypatch.setenv(FLAG_GERBANG, "1")
        assert _tenggat(papan, papan.assignee) is True
        assert _tenggat(papan, papan.anggota) is False

    @pytest.mark.django_db
    def test_endpoint_patch_mengikuti_aturan(self, papan):
        url = f"/api/workspaces/{papan.ws.slug}/projects/{papan.p.id}/issues/{papan.issue.id}/"
        badan = {"target_date": "2026-12-01"}
        respon = _klien(papan.admin).patch(url, badan, format="json")
        assert respon.status_code == status.HTTP_403_FORBIDDEN
        assert "pembuat" in respon.json()["error"] or "membuat" in respon.json()["error"]
        _setel(si.DUE_DATE_CHANGE_RULE, si.TENGGAT_PLUS_ADMIN_PROJECT)
        respon = _klien(papan.admin).patch(url, badan, format="json")
        assert respon.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), respon.data
        papan.issue.refresh_from_db()
        assert str(papan.issue.target_date) == "2026-12-01"


# ---------------------------------------------------------------------------
# 3. Penugasan hanya ke bawah
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestTugaskanKeBawah:
    @pytest.mark.django_db
    def test_dibaca_saat_dipanggil(self, db):
        assert periksa_tingkat_penerima() is True
        _setel(si.ASSIGN_DOWN_ONLY, "0")
        assert periksa_tingkat_penerima() is False

    @pytest.mark.django_db
    def test_bawaan_menolak_rekan_setingkat(self, org):
        galat = galat_penugasan(org.p1.id, [org.sup_b.id], actor=org.sup, abaikan_katup=True)
        assert galat and "jenjang yang sama" in galat

    @pytest.mark.django_db
    def test_saklar_mati_membolehkan_rekan_setingkat(self, org):
        _setel(si.ASSIGN_DOWN_ONLY, "0")
        assert galat_penugasan(org.p1.id, [org.sup_b.id], actor=org.sup, abaikan_katup=True) is None


# ---------------------------------------------------------------------------
# 4. Batas unggahan
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestBatasUnggah:
    @pytest.mark.django_db
    def test_bawaan_sama_dengan_file_size_limit(self, db):
        from plane.utils.plan_limits import batas_ukuran_unggahan, batas_unggah_byte

        assert batas_unggah_byte() == settings.FILE_SIZE_LIMIT
        assert batas_ukuran_unggahan(None, 10**12) == settings.FILE_SIZE_LIMIT

    @pytest.mark.django_db
    def test_god_mode_menurunkan_batas(self, db):
        from plane.utils.plan_limits import batas_ukuran_unggahan, batas_unggah_byte

        if si.batas_proxy_mb() < 2:
            pytest.skip("Batas proxy terlalu kecil untuk diturunkan.")
        _setel(si.UPLOAD_MAX_MB, 1)
        assert batas_unggah_byte() == 1024 * 1024
        assert batas_ukuran_unggahan(None, 10**12) == 1024 * 1024
        assert batas_ukuran_unggahan(None, 10) == 10

    @pytest.mark.django_db
    def test_tidak_bisa_melewati_proxy(self, db):
        from plane.utils.plan_limits import batas_unggah_byte

        _setel(si.UPLOAD_MAX_MB, si.batas_proxy_mb() + 50)
        assert batas_unggah_byte() == settings.FILE_SIZE_LIMIT


# ---------------------------------------------------------------------------
# 5. Umur sesi
# ---------------------------------------------------------------------------


def _masuk(user, **kwargs):
    from plane.authentication.utils.login import user_login

    request = RequestFactory().post("/auth/sign-in/", HTTP_USER_AGENT="pytest")
    request.session = SessionStore()
    request.user = AnonymousUser()
    user_login(request=request, user=user, **kwargs)
    return request.session


@pytest.mark.contract
class TestUmurSesi:
    @pytest.mark.django_db
    def test_bawaan_sama_dengan_session_cookie_age(self, db):
        from plane.authentication.utils.login import umur_sesi_detik

        assert umur_sesi_detik() == settings.SESSION_COOKIE_AGE
        sesi = _masuk(_user("sesi"), is_app=True)
        assert sesi.get_expiry_age() == settings.SESSION_COOKIE_AGE

    @pytest.mark.django_db
    @pytest.mark.parametrize("detik_env,hari_bawaan", [(1800, 1), (200 * 86400, 90), (3 * 86400 + 600, 3)])
    def test_env_di_luar_rentang_tetap_detik_env(self, db, settings, monkeypatch, detik_env, hari_bawaan):
        # Env lama di bawah sehari / di atas 90 hari / bukan kelipatan sehari:
        # bawaan SESSION_DAYS (hasil jepit) tetap memberi detik env apa adanya.
        settings.SESSION_COOKIE_AGE = detik_env
        monkeypatch.setitem(si.SETELAN_ANGKA, si.SESSION_DAYS, (hari_bawaan, 1, 90))
        assert _masuk(_user("sesi"), is_app=True).get_expiry_age() == detik_env
        # Angka lain yang dipilih di God Mode berlaku dalam hari.
        _setel(si.SESSION_DAYS, 5)
        assert _masuk(_user("sesi"), is_app=True).get_expiry_age() == 5 * 86400

    @pytest.mark.django_db
    def test_god_mode_mengubah_umur_sesi_baru(self, db):
        _setel(si.SESSION_DAYS, 3)
        assert _masuk(_user("sesi"), is_app=True).get_expiry_age() == 3 * 86400
        assert _masuk(_user("sesi"), is_space=True).get_expiry_age() == 3 * 86400

    @pytest.mark.django_db
    def test_sesi_god_mode_tetap_dari_env(self, db):
        _setel(si.SESSION_DAYS, 3)
        assert _masuk(_user("admin"), is_admin=True).get_expiry_age() == settings.ADMIN_SESSION_COOKIE_AGE


# ---------------------------------------------------------------------------
# 6. Masa berlaku undangan
# ---------------------------------------------------------------------------


def _undangan_ws(workspace, user, hari_lalu):
    undangan = WorkspaceMemberInvite.objects.create(workspace=workspace, email=user.email, token="tok-ws", role=15)
    WorkspaceMemberInvite.objects.filter(pk=undangan.pk).update(created_at=timezone.now() - timedelta(days=hari_lalu))
    return undangan


def _undangan_project(project, user, hari_lalu):
    undangan = ProjectMemberInvite.objects.create(
        project=project, workspace=project.workspace, email=user.email, token="tok-pr", role=15
    )
    ProjectMemberInvite.objects.filter(pk=undangan.pk).update(created_at=timezone.now() - timedelta(days=hari_lalu))
    return undangan


def _terima_ws(workspace, user, undangan):
    # Tingkatan gratis = 1 kursi (plan_limits); tes ini menguji masa berlaku, bukan kuota.
    WorkspacePlan.objects.get_or_create(workspace=workspace, defaults={"tier": "EXPERT"})
    url = f"/api/workspaces/{workspace.slug}/invitations/{undangan.id}/join/"
    return _klien(user).post(url, {"token": "tok-ws", "accepted": True}, format="json")


@pytest.mark.contract
class TestMasaUndangan:
    @pytest.mark.django_db
    def test_nol_hari_undangan_lama_tetap_bisa_diterima(self, workspace):
        _setel(si.INVITE_EXPIRY_DAYS, 0)  # 0 = never expires; the default is 7 since KEP-84
        tamu = _user("tamu")
        undangan = _undangan_ws(workspace, tamu, hari_lalu=400)
        respon = _terima_ws(workspace, tamu, undangan)
        assert respon.status_code == status.HTTP_200_OK, respon.data
        assert WorkspaceMember.objects.filter(workspace=workspace, member=tamu).exists()

    @pytest.mark.django_db
    def test_undangan_kedaluwarsa_ditolak_dan_tetap_tersimpan(self, workspace):
        _setel(si.INVITE_EXPIRY_DAYS, 7)
        tamu = _user("tamu")
        undangan = _undangan_ws(workspace, tamu, hari_lalu=8)
        respon = _terima_ws(workspace, tamu, undangan)
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
        assert respon.json()["error_code"] == "INVITE_EXPIRED"
        assert not WorkspaceMember.objects.filter(workspace=workspace, member=tamu).exists()
        undangan.refresh_from_db()
        assert undangan.responded_at is None

    @pytest.mark.django_db
    def test_undangan_kedaluwarsa_tidak_memakan_kursi(self, workspace):
        from plane.utils.plan_limits import kursi_terpakai

        _undangan_ws(workspace, _user("lama"), hari_lalu=8)
        _setel(si.INVITE_EXPIRY_DAYS, 0)  # 0 hari (tidak pernah kedaluwarsa): undangan lama tetap dihitung
        dasar = kursi_terpakai(workspace.id)
        _setel(si.INVITE_EXPIRY_DAYS, 7)
        assert kursi_terpakai(workspace.id) == dasar - 1

    @pytest.mark.django_db
    def test_undangan_baru_masih_berlaku(self, workspace):
        _setel(si.INVITE_EXPIRY_DAYS, 7)
        tamu = _user("tamu")
        undangan = _undangan_ws(workspace, tamu, hari_lalu=2)
        assert _terima_ws(workspace, tamu, undangan).status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_daftar_undangan_menandai_kedaluwarsa(self, workspace, create_user):
        _setel(si.INVITE_EXPIRY_DAYS, 7)
        _undangan_ws(workspace, _user("lama"), hari_lalu=30)
        respon = _klien(create_user).get(f"/api/workspaces/{workspace.slug}/invitations/")
        assert respon.status_code == status.HTTP_200_OK
        assert [u["is_expired"] for u in respon.json()] == [True]

    @pytest.mark.django_db
    def test_terima_massal_menolak_yang_kedaluwarsa(self, workspace):
        _setel(si.INVITE_EXPIRY_DAYS, 7)
        tamu = _user("tamu")
        undangan = _undangan_ws(workspace, tamu, hari_lalu=30)
        respon = _klien(tamu).post(
            "/api/users/me/workspaces/invitations/", {"invitations": [str(undangan.id)]}, format="json"
        )
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
        assert respon.json()["error_code"] == "INVITE_EXPIRED"

    @pytest.mark.django_db
    def test_undangan_project_kedaluwarsa_ditolak(self, workspace, create_user):
        project = Project.objects.create(name="Undang", identifier="UND", workspace=workspace, created_by=create_user)
        tamu = _user("tamu")
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/join/{{pk}}/"

        lama = _undangan_project(project, tamu, hari_lalu=400)
        _setel(si.INVITE_EXPIRY_DAYS, 30)
        respon = _klien(tamu).post(url.format(pk=lama.id), {"token": "tok-pr", "accepted": True}, format="json")
        assert respon.status_code == status.HTTP_400_BAD_REQUEST
        assert respon.json()["error_code"] == "INVITE_EXPIRED"

        _setel(si.INVITE_EXPIRY_DAYS, 0)
        respon = _klien(tamu).post(url.format(pk=lama.id), {"token": "tok-pr", "accepted": True}, format="json")
        assert respon.status_code == status.HTTP_200_OK, respon.data


# ---------------------------------------------------------------------------
# 7. Obrolan
# ---------------------------------------------------------------------------


def _kirim(workspace, user, isi, lampiran=None):
    badan = {"isi": isi}
    if lampiran is not None:
        badan["lampiran"] = lampiran
    return _klien(user).post(f"/api/workspaces/{workspace.slug}/chat/{user.id}/", badan, format="json")


def _sunting(workspace, user, pesan_id, isi):
    return _klien(user).patch(f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan_id}/", {"isi": isi}, format="json")


@pytest.mark.contract
class TestBatasObrolan:
    @pytest.mark.django_db
    def test_bawaan_panjang_5000(self, workspace, create_user):
        assert _kirim(workspace, create_user, "a" * 5000).status_code == status.HTTP_201_CREATED
        assert _kirim(workspace, create_user, "a" * 5001).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_panjang_dari_god_mode_juga_di_sunting(self, workspace, create_user):
        _setel(si.CHAT_MESSAGE_MAX_LENGTH, 100)
        assert _kirim(workspace, create_user, "a" * 101).status_code == status.HTTP_400_BAD_REQUEST
        respon = _kirim(workspace, create_user, "a" * 100)
        assert respon.status_code == status.HTTP_201_CREATED
        assert _sunting(workspace, create_user, respon.data["id"], "b" * 101).status_code == 400

    @pytest.mark.django_db
    def test_bawaan_lima_lampiran(self, workspace, create_user):
        enam = [str(uuid4()) for _ in range(6)]
        assert _kirim(workspace, create_user, "x", enam).status_code == status.HTTP_400_BAD_REQUEST
        # Lima id asing: lolos batas jumlah (berkas asing sendiri dibuang diam-diam).
        assert _kirim(workspace, create_user, "x", enam[:5]).status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_jumlah_lampiran_dari_god_mode(self, workspace, create_user):
        _setel(si.CHAT_ATTACHMENTS_MAX, 2)
        tiga = [str(uuid4()) for _ in range(3)]
        assert _kirim(workspace, create_user, "x", tiga).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_nol_jam_sunting_tanpa_batas_waktu(self, workspace, create_user):
        _setel(si.CHAT_EDIT_WINDOW_HOURS, 0)  # 0 = no limit; the default is 24 since KEP-84
        respon = _kirim(workspace, create_user, "lama")
        PesanLangsung.objects.filter(pk=respon.data["id"]).update(created_at=timezone.now() - timedelta(days=400))
        assert _sunting(workspace, create_user, respon.data["id"], "baru").status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_jendela_sunting_dari_god_mode(self, workspace, create_user):
        _setel(si.CHAT_EDIT_WINDOW_HOURS, 2)
        respon = _kirim(workspace, create_user, "lama")
        PesanLangsung.objects.filter(pk=respon.data["id"]).update(created_at=timezone.now() - timedelta(hours=3))
        assert _sunting(workspace, create_user, respon.data["id"], "baru").status_code == status.HTTP_403_FORBIDDEN
        segar = _kirim(workspace, create_user, "segar")
        assert _sunting(workspace, create_user, segar.data["id"], "baru").status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# 8. Needs attention
# ---------------------------------------------------------------------------


def _perhatian(org):
    respon = _klien(org.staf).get(f"/api/workspaces/{org.ws.slug}/paradise/attention/")
    assert respon.status_code == status.HTTP_200_OK, respon.data
    return {g["key"]: g for g in respon.json()["groups"]}


def _ditolak_lalu(org, hari):
    issue = _tugas(org.p1, org.staf, assignee=org.staf)
    Issue.objects.filter(pk=issue.pk).update(state=org.states["started"])
    PersetujuanPenugasan.objects.create(
        workspace=org.ws,
        project=org.p1,
        issue=issue,
        pemohon=org.staf,
        penerima=org.staf,
        status="ditolak",
        alasan="Belum",
        diputuskan_oleh=org.manager,
        diputuskan_pada=timezone.now() - timedelta(days=hari),
    )


def _disebut_lalu(org, hari):
    issue = _tugas(org.p1, org.manager, assignee=org.manager)
    Issue.objects.filter(pk=issue.pk).update(state=org.states["started"])
    sebut = IssueMention.objects.create(issue=issue, mention=org.staf, project=org.p1, workspace=org.ws)
    IssueMention.objects.filter(pk=sebut.pk).update(created_at=timezone.now() - timedelta(days=hari))


@pytest.mark.contract
class TestJendelaPerhatian:
    @pytest.mark.django_db
    def test_bawaan_14_dan_7_hari(self, org):
        _ditolak_lalu(org, 10)
        _disebut_lalu(org, 5)
        g = _perhatian(org)
        assert g["rejected"]["count"] == 1
        assert g["mentioned"]["count"] == 1

    @pytest.mark.django_db
    def test_jendela_dari_god_mode(self, org):
        _setel(si.ATTENTION_REJECTED_DAYS, 3)
        _setel(si.ATTENTION_MENTION_DAYS, 2)
        _ditolak_lalu(org, 10)
        _disebut_lalu(org, 5)
        g = _perhatian(org)
        assert g["rejected"]["count"] == 0
        assert g["mentioned"]["count"] == 0

    @pytest.mark.django_db
    def test_jendela_due_soon_dikirim_ke_web(self, org):
        url = f"/api/workspaces/{org.ws.slug}/paradise/attention/"
        assert _klien(org.staf).get(url).json()["lookahead_days"] == 7
        _setel(si.DIGEST_LOOKAHEAD_DAYS, 10)
        assert _klien(org.staf).get(url).json()["lookahead_days"] == 10


def _menunggu(org, pemohon):
    issue = _tugas(org.p1, pemohon, assignee=pemohon)
    return PersetujuanPenugasan.objects.create(
        workspace=org.ws, project=org.p1, issue=issue, pemohon=pemohon, penerima=pemohon, status="menunggu"
    )


def _decide(org, user):
    respon = _klien(user).get(f"/api/workspaces/{org.ws.slug}/paradise/attention/")
    assert respon.status_code == status.HTTP_200_OK, respon.data
    grup = {g["key"]: g for g in respon.json()["groups"]}.get("decide")
    return grup["count"] if grup else 0


@pytest.mark.contract
class TestDaftarPutuskanSamaDenganPost:
    """Widget "decide" dan angka Dashboard Divisi = baris yang lolos POST setuju/tolak."""

    @pytest.mark.django_db
    def test_bawaan_pengajuan_staf_untuk_semua_atasan(self, org):
        from plane.utils.ringkasan_divisi import _persetujuan_untuk_saya

        _menunggu(org, org.staf)
        for atasan in (org.sup_b, org.manager):
            assert _decide(org, atasan) == 1
            assert _persetujuan_untuk_saya(atasan, [org.p1]) == {org.p1.id: 1}
        # Pemohonnya sendiri tidak memutuskan.
        assert _decide(org, org.staf) == 0

    @pytest.mark.django_db
    def test_ambang_30_pengajuan_supervisor_hanya_untuk_yang_lebih_tinggi(self, org, monkeypatch):
        from plane.utils.ringkasan_divisi import _persetujuan_untuk_saya

        monkeypatch.setenv(FLAG_GERBANG, "1")
        _setel(si.APPROVAL_REQUIRED_BELOW_LEVEL, si.APPROVAL_DI_BAWAH_MANAGER)
        _menunggu(org, org.staf)
        baris_sup = _menunggu(org, org.sup)

        # Supervisor setingkat: hanya pengajuan staf. Manager: keduanya.
        assert _decide(org, org.sup_b) == 1
        assert _persetujuan_untuk_saya(org.sup_b, [org.p1]) == {org.p1.id: 1}
        assert _decide(org, org.manager) == 2
        assert _persetujuan_untuk_saya(org.manager, [org.p1]) == {org.p1.id: 2}

        # Sama dengan POST: sup_b ditolak untuk baris supervisor, manager boleh.
        url = f"/api/workspaces/{org.ws.slug}/projects/{org.p1.id}/persetujuan-penugasan/{baris_sup.id}/"
        assert _klien(org.sup_b).post(url, {"aksi": "setujui"}, format="json").status_code == 403
        assert _klien(org.manager).post(url, {"aksi": "setujui"}, format="json").status_code == 200


# ---------------------------------------------------------------------------
# 9. Plafon arsip otomatis
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestPlafonArsip:
    @pytest.mark.django_db
    def test_galat_mengikuti_plafon(self, db):
        from plane.utils.bawaan_project import galat_archive_in

        # Bawaan instance 90 hari = paling lambat 3 bulan.
        assert galat_archive_in(0) is None
        assert galat_archive_in(3) is None
        assert "90 days" in galat_archive_in(4)
        _setel(si.AUTO_ARCHIVE_DONE_DAYS, 0)
        assert galat_archive_in(12) is None

    @pytest.mark.django_db
    def test_project_baru_dan_ubah_ditolak_di_atas_plafon(self, workspace, create_user):
        project = Project.objects.create(name="Arsip", identifier="ARS", workspace=workspace, created_by=create_user)
        _anggota(project, create_user, role=20)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/"
        respon = _klien(create_user).patch(url, {"archive_in": 6}, format="json")
        assert respon.status_code == status.HTTP_400_BAD_REQUEST, respon.data
        respon = _klien(create_user).patch(url, {"archive_in": 2}, format="json")
        assert respon.status_code == status.HTTP_200_OK, respon.data

    @pytest.mark.django_db
    def test_project_lama_di_atas_plafon_tidak_rusak(self, workspace, create_user):
        project = Project.objects.create(name="Lama", identifier="LMA", workspace=workspace, created_by=create_user)
        Project.objects.filter(pk=project.pk).update(archive_in=12)
        _anggota(project, create_user, role=20)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/"
        respon = _klien(create_user).patch(url, {"archive_in": 12, "name": "Lama Baru"}, format="json")
        assert respon.status_code == status.HTTP_200_OK, respon.data
        project.refresh_from_db()
        assert project.archive_in == 12

    @pytest.mark.django_db
    def test_bawaan_project_baru_ikut_plafon(self, db):
        from plane.utils import bawaan_project

        _, galat = bawaan_project.periksa_perubahan({"archive_in": 6})
        assert galat and "90 days" in galat
        bawaan_project.simpan_bawaan({**bawaan_project.PABRIK, "archive_in": 6})
        assert bawaan_project.baca_bawaan()["archive_in"] == 3
        _setel(si.AUTO_ARCHIVE_DONE_DAYS, 365)
        assert bawaan_project.baca_bawaan()["archive_in"] == 6
