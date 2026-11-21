# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi assignee tugas buatan staf: pembuatnya jadi assignee (migrasi 0186 + perintah)."""

import importlib
import uuid
from io import StringIO

import pytest
from django.apps import apps
from django.core.management import call_command
from django.utils import timezone

from plane.db.models import (
    Departemen,
    Divisi,
    Issue,
    IssueAssignee,
    JabatanOrganisasi,
    Project,
    ProjectMember,
    State,
    User,
)
from plane.db.models.hierarki import TINGKAT_LEADER, TINGKAT_MEMBER, TINGKAT_SUPERVISOR
from plane.utils.isi_assignee_staf import isi_assignee_staf


@pytest.fixture
def project(workspace):
    p = Project.objects.create(name="Proyek Staf", identifier="STF", workspace=workspace)
    State.objects.create(name="Todo", color="#000", project=p, workspace=workspace, sequence=1, group="backlog")
    return p


def _user(nama):
    return User.objects.create(email=f"{nama}-{uuid.uuid4().hex[:6]}@example.com", username=uuid.uuid4().hex[:20])


def _tugas(project, pembuat, **kw):
    t = Issue.objects.create(name="t", project=project, workspace=project.workspace, **kw)
    Issue.all_objects.filter(pk=t.pk).update(created_by=pembuat)
    return t


def _anggota(project, user):
    ProjectMember.objects.create(project=project, member=user, role=15)


def _hidup(tugas):
    return list(IssueAssignee.objects.filter(issue=tugas).values_list("assignee_id", flat=True))


def _jalan(apply=True):
    return isi_assignee_staf(apps.get_model, apply=apply)


@pytest.mark.django_db
def test_staf_tanpa_baris_hierarki_diisi(project):
    u = _user("a")
    _anggota(project, u)
    t = _tugas(project, u)
    hasil = _jalan()
    assert _hidup(t) == [u.id]
    assert hasil["diisi"] == 1


@pytest.mark.django_db
def test_member_diisi_leader_dan_supervisor_tidak(project, workspace):
    member, leader, spv = _user("m"), _user("l"), _user("s")
    for u, tingkat in ((member, TINGKAT_MEMBER), (leader, TINGKAT_LEADER), (spv, TINGKAT_SUPERVISOR)):
        _anggota(project, u)
        JabatanOrganisasi.objects.create(workspace=workspace, member=u, tingkat=tingkat)
    tm, tl, ts = _tugas(project, member), _tugas(project, leader), _tugas(project, spv)
    hasil = _jalan()
    assert _hidup(tm) == [member.id]
    assert _hidup(tl) == [] and _hidup(ts) == []
    assert hasil["dilewati"]["bukan_staf"] == 2


@pytest.mark.django_db
def test_jenjang_tertinggi_dari_semua_baris_yang_dipakai(project, workspace):
    u = _user("dua")
    _anggota(project, u)
    divisi = Divisi.objects.create(workspace=workspace, kode="D1", nama="Divisi 1")
    d1 = Departemen.objects.create(workspace=workspace, divisi=divisi, kode="A", nama="A")
    d2 = Departemen.objects.create(workspace=workspace, divisi=divisi, kode="B", nama="B")
    JabatanOrganisasi.objects.create(workspace=workspace, member=u, tingkat=TINGKAT_MEMBER, departemen=d1)
    JabatanOrganisasi.objects.create(workspace=workspace, member=u, tingkat=TINGKAT_SUPERVISOR, departemen=d2)
    t = _tugas(project, u)
    _jalan()
    assert _hidup(t) == []


@pytest.mark.django_db
def test_baris_hierarki_terhapus_dianggap_tidak_ada(project, workspace):
    u = _user("del")
    _anggota(project, u)
    j = JabatanOrganisasi.objects.create(workspace=workspace, member=u, tingkat=TINGKAT_SUPERVISOR)
    JabatanOrganisasi.all_objects.filter(pk=j.pk).update(deleted_at=timezone.now())
    t = _tugas(project, u)
    _jalan()
    assert _hidup(t) == [u.id]


@pytest.mark.django_db
def test_tugas_yang_sudah_punya_assignee_tidak_disentuh(project):
    u, lain = _user("a"), _user("b")
    _anggota(project, u)
    _anggota(project, lain)
    t = _tugas(project, u)
    IssueAssignee.objects.create(issue=t, assignee=lain, project=project)
    _jalan()
    assert _hidup(t) == [lain.id]


@pytest.mark.django_db
def test_assignee_terhapus_dianggap_kosong(project):
    u, lain = _user("a"), _user("b")
    _anggota(project, u)
    t = _tugas(project, u)
    baris = IssueAssignee.objects.create(issue=t, assignee=lain, project=project)
    IssueAssignee.all_objects.filter(pk=baris.pk).update(deleted_at=timezone.now())
    _jalan()
    assert _hidup(t) == [u.id]


@pytest.mark.django_db
def test_pembuat_bukan_anggota_project_dilewati(project):
    u = _user("a")
    t = _tugas(project, u)
    hasil = _jalan()
    assert _hidup(t) == []
    assert hasil["dilewati"]["bukan_anggota_project"] == 1


@pytest.mark.django_db
def test_anggota_nonaktif_dan_user_nonaktif_dilewati(project):
    a, b = _user("a"), _user("b")
    _anggota(project, a)
    ProjectMember.objects.filter(project=project, member=a).update(is_active=False)
    _anggota(project, b)
    User.objects.filter(pk=b.pk).update(is_active=False)
    ta, tb = _tugas(project, a), _tugas(project, b)
    hasil = _jalan()
    assert _hidup(ta) == [] and _hidup(tb) == []
    assert hasil["dilewati"]["bukan_anggota_project"] == 1
    assert hasil["dilewati"]["pembuat_nonaktif"] == 1


@pytest.mark.django_db
def test_bot_dilewati(project):
    u = _user("bot")
    User.objects.filter(pk=u.pk).update(is_bot=True)
    _anggota(project, u)
    t = _tugas(project, u)
    _jalan()
    assert _hidup(t) == []


@pytest.mark.django_db
def test_tugas_arsip_terhapus_draf_dilewati(project):
    u = _user("a")
    _anggota(project, u)
    arsip, hapus, draf = _tugas(project, u), _tugas(project, u), _tugas(project, u)
    Issue.all_objects.filter(pk=arsip.pk).update(archived_at=timezone.now().date())
    Issue.all_objects.filter(pk=hapus.pk).update(deleted_at=timezone.now())
    Issue.all_objects.filter(pk=draf.pk).update(is_draft=True)
    hasil = _jalan()
    assert hasil["diisi"] == 0
    assert IssueAssignee.objects.filter(issue__in=[arsip, hapus, draf]).count() == 0


@pytest.mark.django_db
def test_idempoten(project):
    u = _user("a")
    _anggota(project, u)
    t = _tugas(project, u)
    assert _jalan()["diisi"] == 1
    assert _jalan()["diisi"] == 0
    assert IssueAssignee.all_objects.filter(issue=t).count() == 1


@pytest.mark.django_db
def test_banyak_batch(project):
    u = _user("a")
    _anggota(project, u)
    tugas = [_tugas(project, u) for _ in range(5)]
    hasil = isi_assignee_staf(apps.get_model, apply=True, batch=2)
    assert hasil["diisi"] == 5
    assert all(_hidup(t) == [u.id] for t in tugas)


@pytest.mark.django_db
def test_dry_run_tidak_menulis(project):
    u = _user("a")
    _anggota(project, u)
    t = _tugas(project, u)
    assert _jalan(apply=False)["diisi"] == 1
    assert _hidup(t) == []
    out = StringIO()
    call_command("isi_assignee_staf", stdout=out)
    assert _hidup(t) == []
    assert "Dry run" in out.getvalue()
    call_command("isi_assignee_staf", "--apply", stdout=out)
    assert _hidup(t) == [u.id]


@pytest.mark.django_db
def test_fungsi_migrasi_mengisi(project):
    u = _user("a")
    _anggota(project, u)
    t = _tugas(project, u)
    migrasi = importlib.import_module("plane.db.migrations.0186_isi_assignee_staf")
    migrasi._isi(apps, None)
    assert _hidup(t) == [u.id]
