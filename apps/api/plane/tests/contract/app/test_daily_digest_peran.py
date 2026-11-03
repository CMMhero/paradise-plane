# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: ringkasan harian sesuai jabatan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""KEP-43: satu ringkasan harian, isinya mengikuti jabatan & penempatan.

Struktur uji:

    Divisi OPS ── Departemen GDG (project GDG) ── staf, supervisor
               └─ Departemen KRM (project KRM) ── staf2
    Divisi HR  ── Departemen REK (project REK)
    manager -> divisi OPS, direktur -> tanpa tempat
"""

from datetime import datetime, time, timedelta
from unittest import mock
from uuid import uuid4

import pytest
from django.core import mail

from plane.bgtasks import daily_digest_task
from plane.bgtasks.daily_digest_task import (
    TugasWorkspace,
    penerima_dan_saklar,
    penerima_workspace,
    susun_ringkasan,
)
from plane.celery import app as celery_app
from plane.db.models import (
    TINGKAT_DIREKTUR,
    TINGKAT_MANAGER,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    Departemen,
    DepartemenProject,
    Divisi,
    Issue,
    IssueAssignee,
    JabatanOrganisasi,
    Project,
    State,
    User,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)

# Hari kantor (WIB), sama dengan yang dipakai pengirimnya. Hari UTC beda tanggal
# antara 17.00 dan 24.00 UTC.
HARI_INI = daily_digest_task.hari_ini_kantor()


def _orang(workspace, prefix):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@uji.id", username=f"{prefix}_{unik}", display_name=prefix.capitalize()
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    # Email ikut `Profile.language` penerima (3 Nov 2026); tes di sini memeriksa teks Indonesia.
    from plane.db.models import Profile

    Profile.objects.update_or_create(user=user, defaults={"language": "id"})
    return user


class Dunia:
    """Satu workspace lengkap dengan struktur, orang, dan tugas."""

    def __init__(self):
        pemilik = User.objects.create(email=f"own-{uuid4().hex[:8]}@uji.id", username=f"own_{uuid4().hex[:8]}")
        self.ws = Workspace.objects.create(name="WS", slug=f"ws-dg-{uuid4().hex[:6]}", owner=pemilik)
        ops = Divisi.objects.create(workspace=self.ws, kode="OPS", nama="Operasional")
        hr = Divisi.objects.create(workspace=self.ws, kode="HR", nama="HRGA")
        self.dept, self.project, self.selesai, self.buka = {}, {}, {}, {}
        for kode, div in (("GDG", ops), ("KRM", ops), ("REK", hr)):
            dept = Departemen.objects.create(workspace=self.ws, divisi=div, kode=kode, nama=f"Dept {kode}")
            project = Project.objects.create(name=f"Proj {kode}", identifier=kode, workspace=self.ws)
            DepartemenProject.objects.create(workspace=self.ws, departemen=dept, project=project)
            self.dept[kode], self.project[kode] = dept, project
            state = State.objects.create
            self.buka[kode] = state(project=project, workspace=self.ws, name="Todo", group="unstarted")
            self.selesai[kode] = state(project=project, workspace=self.ws, name="Done", group="completed")

        self.staf = _orang(self.ws, "staf")
        self.staf2 = _orang(self.ws, "staf2")
        self.sup = _orang(self.ws, "sup")
        self.mgr = _orang(self.ws, "mgr")
        self.dir = _orang(self.ws, "dir")
        J = JabatanOrganisasi.objects.create
        J(workspace=self.ws, member=self.staf, tingkat=TINGKAT_MEMBER, departemen=self.dept["GDG"])
        J(workspace=self.ws, member=self.staf2, tingkat=TINGKAT_MEMBER, departemen=self.dept["KRM"])
        J(workspace=self.ws, member=self.sup, tingkat=TINGKAT_SUPERVISOR, departemen=self.dept["GDG"])
        J(workspace=self.ws, member=self.mgr, tingkat=TINGKAT_MANAGER, divisi=ops)
        J(workspace=self.ws, member=self.dir, tingkat=TINGKAT_DIREKTUR)

        # Milik staf, diberikan supervisor, terlambat 2 hari.
        self.t_staf = self.tugas("GDG", -2, [self.staf], pembuat=self.sup)
        # Rekan staf di departemen yang sama, 3 hari lagi.
        self.t_gdg = self.tugas("GDG", 3, [self.staf2])
        # Departemen lain di divisi yang sama, hari ini.
        self.t_krm = self.tugas("KRM", 0, [self.staf2])
        # Divisi lain, tanpa penanggung jawab, terlambat.
        self.t_rek = self.tugas("REK", -1, [])
        # Di luar jendela & sudah selesai: tidak boleh muncul di mana pun.
        self.t_jauh = self.tugas("GDG", 20, [self.staf])
        self.t_beres = self.tugas("GDG", -5, [self.staf], selesai=True)

    def tugas(self, kode, selisih, assignee, pembuat=None, selesai=False):
        state = self.selesai[kode] if selesai else self.buka[kode]
        issue = Issue.objects.create(
            workspace=self.ws,
            project=self.project[kode],
            name=f"Tugas {kode} {selisih}",
            state=state,
            target_date=HARI_INI + timedelta(days=selisih),
        )
        if pembuat:
            # Lewat update(): BaseModel.save() menolkan created_by di luar request.
            Issue.objects.filter(pk=issue.pk).update(created_by=pembuat)
        for orang in assignee:
            IssueAssignee.objects.create(issue=issue, assignee=orang, project=self.project[kode], workspace=self.ws)
        return issue

    def ringkasan(self, user):
        return susun_ringkasan(user, self.ws.id, TugasWorkspace(self.ws.id, HARI_INI), HARI_INI)


def _ids(kelompok):
    return {i.id for i in kelompok.hari + kelompok.depan + kelompok.lewat}


def _tim(ringkasan):
    return {g.nama: _ids(g.tugas) for g in ringkasan.tim}


@pytest.fixture
def dunia(db):
    return Dunia()


@pytest.mark.contract
class TestIsiPerJabatan:
    @pytest.mark.django_db
    def test_staf_hanya_tugasnya_sendiri(self, dunia):
        r = dunia.ringkasan(dunia.staf)
        assert r.peran == "Staf" and r.cakupan == "Dept GDG"
        assert _ids(r.sendiri) == {dunia.t_staf.id}
        assert [i.id for i in r.sendiri.lewat] == [dunia.t_staf.id]
        assert not r.diberikan and r.tim == []

    @pytest.mark.django_db
    def test_supervisor_melihat_yang_ia_berikan_dan_departemennya(self, dunia):
        r = dunia.ringkasan(dunia.sup)
        assert r.peran == "Supervisor" and r.judul_tim == "Departemen Anda"
        assert not r.sendiri
        assert _ids(r.diberikan) == {dunia.t_staf.id}
        # t_staf sudah di "diberikan", tidak diulang di tim.
        assert _tim(r) == {"Proj GDG": {dunia.t_gdg.id}}
        assert r.penanggung[dunia.t_staf.id] == ["Staf"]

    @pytest.mark.django_db
    def test_manager_melihat_seluruh_divisinya_saja(self, dunia):
        r = dunia.ringkasan(dunia.mgr)
        assert r.peran == "Manager" and r.cakupan == "Operasional"
        assert _tim(r) == {
            "Proj GDG": {dunia.t_staf.id, dunia.t_gdg.id},
            "Proj KRM": {dunia.t_krm.id},
        }

    @pytest.mark.django_db
    def test_direktur_tanpa_bagian_tim(self, dunia):
        # 2026-11-02: ikhtisar divisi datang lewat laporan direktur, bukan rincian staf di sini.
        r = dunia.ringkasan(dunia.dir)
        assert r.peran == "Direktur"
        assert r.tim == []
        # Tanpa tugas pribadi = ringkasan kosong = tidak dikirim.
        assert not r


@pytest.mark.contract
class TestPenerima:
    @pytest.mark.django_db
    def test_bawaan_semua_jabatan_menerima(self, dunia):
        penerima = set(penerima_workspace(dunia.ws.id))
        assert {dunia.staf, dunia.staf2, dunia.sup, dunia.mgr, dunia.dir} <= penerima

    @pytest.mark.django_db
    def test_yang_mematikan_tidak_dikirimi(self, dunia):
        UserNotificationPreference.objects.filter(user=dunia.sup).update(daily_digest=False, ikut_bawaan_jabatan=False)
        assert dunia.sup not in set(penerima_workspace(dunia.ws.id))


@pytest.mark.contract
class TestKirim:
    @pytest.mark.django_db
    def test_satu_email_per_orang_yang_punya_isi(self, dunia, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        nganggur = _orang(dunia.ws, "nganggur")
        with mock.patch.object(daily_digest_task, "_koneksi", return_value=(None, "noreply@uji.id")):
            hasil = daily_digest_task.kirim_ringkasan_harian()

        ke = {m.to[0]: m for m in mail.outbox if m.to[0].endswith("@uji.id")}
        for orang in (dunia.staf, dunia.staf2, dunia.sup, dunia.mgr):
            assert orang.email in ke, orang.username
        # Direktur tanpa tugas pribadi tidak menerima ringkasan harian.
        assert dunia.dir.email not in ke
        assert hasil["gagal"] == 0
        assert "== DEPARTEMEN ANDA ==" in ke[dunia.sup.email].body
        assert "== TUGAS YANG ANDA BERIKAN ==" in ke[dunia.sup.email].body
        # Staf tanpa tugas apa pun: tidak dikirimi email kosong.
        assert nganggur.email not in ke
        assert hasil["kosong"] >= 1

    def test_jadwal_senin_jumat_0830_jakarta(self):
        jadwal = celery_app.conf.beat_schedule["ringkasan-harian"]["schedule"]
        # Celery berjalan di UTC: 08.30 WIB = 01.30 UTC.
        assert jadwal.hour == {1} and jadwal.minute == {30}
        assert jadwal.day_of_week == {1, 2, 3, 4, 5}


@pytest.mark.contract
class TestEdisiSore:
    """Keputusan user 2026-11-02: ringkasan akhir hari 17.30 WIB, saklarnya sendiri."""

    def _sore(self, dunia, user, hari_ke_depan=1):
        data = TugasWorkspace(dunia.ws.id, HARI_INI, hari_ke_depan, dengan_selesai=True)
        return susun_ringkasan(user, dunia.ws.id, data, HARI_INI, sore=True)

    @pytest.mark.django_db
    def test_memuat_yang_selesai_hari_ini(self, dunia):
        r = self._sore(dunia, dunia.staf)
        assert r.sore
        assert [i.id for i in r.sendiri.selesai] == [dunia.t_beres.id]
        assert [i.id for i in r.sendiri.lewat] == [dunia.t_staf.id]
        # Edisi pagi tidak pernah memuat yang selesai.
        assert not dunia.ringkasan(dunia.staf).sendiri.selesai

    @pytest.mark.django_db
    def test_selesai_kemarin_tidak_ikut(self, dunia):
        kemarin = _kemarin_siang()
        Issue.objects.filter(pk=dunia.t_beres.pk).update(completed_at=kemarin)
        assert not self._sore(dunia, dunia.staf).sendiri.selesai

    @pytest.mark.django_db
    def test_jendela_depan_hanya_hari_kerja_berikutnya(self, dunia):
        besok = dunia.tugas("GDG", 1, [dunia.staf])
        lusa = dunia.tugas("GDG", 2, [dunia.staf])
        ids = {i.id for i in self._sore(dunia, dunia.staf).sendiri.depan}
        assert besok.id in ids and lusa.id not in ids

    @pytest.mark.django_db
    def test_saklar_hari_ini_mati_menyembunyikan_selesai(self, dunia):
        data = TugasWorkspace(dunia.ws.id, HARI_INI, 1, dengan_selesai=True)
        r = susun_ringkasan(dunia.staf, dunia.ws.id, data, HARI_INI, {"digest_hari_ini": False}, sore=True)
        assert not r.sendiri.selesai

    @pytest.mark.django_db
    def test_penerima_mengikuti_saklar_sore(self, dunia):
        assert dunia.sup in {o for o, _ in penerima_dan_saklar(dunia.ws.id, "daily_digest_sore")}
        UserNotificationPreference.objects.filter(user=dunia.sup).update(
            daily_digest=True, daily_digest_sore=False, ikut_bawaan_jabatan=False
        )
        assert dunia.sup not in {o for o, _ in penerima_dan_saklar(dunia.ws.id, "daily_digest_sore")}
        # Saklar pagi tidak ikut mati.
        assert dunia.sup in set(penerima_workspace(dunia.ws.id))

    @pytest.mark.django_db
    def test_kirim_sore_bersubjek_sore(self, dunia, settings):
        settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
        with mock.patch.object(daily_digest_task, "_koneksi", return_value=(None, "noreply@uji.id")):
            hasil = daily_digest_task.kirim_ringkasan_sore()
        ke = {m.to[0]: m for m in mail.outbox if m.to[0].endswith("@uji.id")}
        assert hasil["gagal"] == 0
        assert ke[dunia.staf.email].subject.startswith("[Ringkasan sore]")
        assert "SELESAI HARI INI (1)" in ke[dunia.staf.email].body

    def test_jadwal_senin_jumat_1730_jakarta(self):
        jadwal = celery_app.conf.beat_schedule["ringkasan-sore"]["schedule"]
        # 17.30 WIB = 10.30 UTC.
        assert jadwal.hour == {10} and jadwal.minute == {30}
        assert jadwal.day_of_week == {1, 2, 3, 4, 5}


def _kemarin_siang():
    """12.00 WIB kemarin, untuk completed_at yang jelas di luar "hari ini"."""
    return datetime.combine(HARI_INI, time(12), tzinfo=daily_digest_task.ZONA_KANTOR) - timedelta(days=1)
