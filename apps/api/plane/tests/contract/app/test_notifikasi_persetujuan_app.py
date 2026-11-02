# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pemberitahuan persetujuan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Tes kontrak: pengajuan & keputusan persetujuan menulis inbox + antrean email.

Yang dijaga: atasan diping saat ada yang menunggu (sebelumnya diam), pemohon
diping saat diputuskan, saklar `approval` hanya mematikan EMAIL (inbox tetap
ditulis, konsisten dengan preferensi issue lain), dan penolakan membawa alasan.
"""

from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    EmailNotificationLog,
    Issue,
    JabatanOrganisasi,
    Notification,
    PersetujuanPenugasan,
    Profile,
    Project,
    ProjectMember,
    TINGKAT_MEMBER,
    TINGKAT_SUPERVISOR,
    User,
    UserNotificationPreference,
    Workspace,
    WorkspaceMember,
)
from plane.license.models import Instance, InstanceAdmin
from plane.utils.hierarki import FLAG_GERBANG

URL_ISSUES = "/api/workspaces/{slug}/projects/{project_id}/issues/"
URL_PUTUSKAN = "/api/workspaces/{slug}/projects/{project_id}/persetujuan-penugasan/{pk}/"


def _buat_user(prefix, workspace=None, peran_workspace=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so",
        username=f"{prefix}_{unik}",
        first_name=prefix.capitalize(),
        last_name="Uji",
    )
    user.set_password("test-password")
    user.save()
    if workspace is not None:
        WorkspaceMember.objects.create(workspace=workspace, member=user, role=peran_workspace)
    return user


@pytest.fixture
def workspace(db):
    pemilik = User.objects.create(email="owner@plane.so", username="owner_notif")
    return Workspace.objects.create(name="WS", slug="ws-notif", owner=pemilik)


@pytest.fixture
def staf(db, workspace):
    return _buat_user("stafn", workspace)


@pytest.fixture
def bos(db, workspace):
    return _buat_user("bosn", workspace)


@pytest.fixture
def divisi(db, workspace, bos, staf):
    project = Project.objects.create(name="Divisi N", identifier="DIVN", workspace=workspace, created_by=bos)
    ProjectMember.objects.create(project=project, member=bos, workspace=workspace, role=20)
    ProjectMember.objects.create(project=project, member=staf, workspace=workspace, role=15)
    JabatanOrganisasi.objects.create(workspace=workspace, member=bos, tingkat=TINGKAT_SUPERVISOR)
    JabatanOrganisasi.objects.create(workspace=workspace, member=staf, tingkat=TINGKAT_MEMBER)
    return project


@pytest.fixture
def instance_god_mode(db):
    return Instance.objects.create(
        instance_name="uji",
        instance_id=f"uji-notif-{uuid4().hex[:8]}",
        current_version="uji",
        last_checked_at=timezone.now(),
    )


@pytest.fixture
def super_admin(db, instance_god_mode, workspace):
    user = _buat_user("notifsuper", workspace, peran_workspace=20)
    InstanceAdmin.objects.create(instance=instance_god_mode, user=user, role=20)
    return user


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _ajukan(staf, workspace, divisi, monkeypatch):
    """Staf membuat tugas untuk dirinya lalu menggesernya ke selesai → baris menunggu lahir."""
    from plane.db.models import DEFAULT_STATES, State

    monkeypatch.setenv(FLAG_GERBANG, "1")
    res = _klien(staf).post(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id),
        {"name": "Tugas butuh restu", "assignee_ids": [str(staf.id)]},
        format="json",
    )
    assert res.status_code == status.HTTP_201_CREATED, getattr(res, "data", None)
    selesai = None
    for d in DEFAULT_STATES:
        st, _ = State.objects.get_or_create(
            project=divisi,
            workspace=workspace,
            name=d["name"],
            defaults={"color": d["color"], "sequence": d["sequence"], "group": d["group"], "default": d.get("default", False)},
        )
        if st.group == "completed" and selesai is None:
            selesai = st
    _klien(staf).patch(
        URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id) + res.json()["id"] + "/",
        {"state": str(selesai.id)},
        format="json",
    )
    return Issue.objects.get(pk=res.json()["id"])


@pytest.mark.contract
class TestNotifikasiDiajukan:
    @pytest.mark.django_db
    def test_pengajuan_menulis_inbox_untuk_atasan_bukan_pemohon(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()
        assert baris is not None

        untuk_bos = Notification.objects.filter(
            receiver=bos, entity_identifier=issue.id, sender="in_app:approval:submitted"
        )
        assert untuk_bos.count() == 1
        assert Notification.objects.filter(
            receiver=staf, entity_identifier=issue.id, sender="in_app:approval:submitted"
        ).count() == 0

    @pytest.mark.django_db
    def test_atasan_yang_menyalakan_sendiri_dapat_antrean_email(self, workspace, staf, bos, divisi, monkeypatch):
        UserNotificationPreference.objects.filter(user=bos).update(approval=True, ikut_bawaan_jabatan=False)
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        log = EmailNotificationLog.objects.filter(receiver=bos, entity_identifier=issue.id).first()
        assert log is not None
        assert log.entity == "approval"
        assert log.processed_at is None

    @pytest.mark.django_db
    def test_bawaan_pimpinan_tidak_menulis_email_tapi_inbox_tetap(self, workspace, staf, bos, divisi, monkeypatch):
        # Supervisor ke atas: email mati secara bawaan (keputusan user 2026-10-30).
        issue = _ajukan(staf, workspace, divisi, monkeypatch)

        assert Notification.objects.filter(receiver=bos, entity_identifier=issue.id).exists()
        assert not EmailNotificationLog.objects.filter(receiver=bos, entity_identifier=issue.id).exists()


@pytest.mark.contract
class TestNotifikasiDiputuskan:
    @pytest.mark.django_db
    def test_setujui_memberitahu_pemohon(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()

        res = _klien(bos).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "setujui"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)

        assert Notification.objects.filter(
            receiver=staf, entity_identifier=issue.id, sender="in_app:approval:decided"
        ).exists()
        log = EmailNotificationLog.objects.filter(receiver=staf, entity_identifier=issue.id).first()
        assert log is not None
        assert log.new_value == "disetujui"

    @pytest.mark.django_db
    def test_tolak_membawa_alasan_ke_pemohon(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()

        res = _klien(bos).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "tolak", "alasan": "Kurang rincian estimasi"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)

        log = EmailNotificationLog.objects.filter(receiver=staf, entity_identifier=issue.id).first()
        assert log is not None
        assert log.new_value == "ditolak"
        assert log.data["issue_activity"]["issue_comment"] == "Kurang rincian estimasi"

    @pytest.mark.django_db
    def test_ajukan_ulang_membunyikan_atasan_lagi(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()
        _klien(bos).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "tolak", "alasan": "Perbaiki dulu"},
            format="json",
        )
        awal = Notification.objects.filter(receiver=bos, entity_identifier=issue.id).count()

        res = _klien(staf).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "ajukan-ulang"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)
        assert Notification.objects.filter(receiver=bos, entity_identifier=issue.id).count() == awal + 1


@pytest.mark.contract
class TestKirimEmailPersetujuan:
    @pytest.mark.django_db
    def test_kirim_mengikuti_bahasa_penerima_dan_menandai_terkirim(self, workspace, staf, bos, divisi, monkeypatch):
        from plane.bgtasks import email_notification_task as tugas

        # Pimpinan tidak diemail secara bawaan (KEP-42): atasan ini menyalakannya sendiri.
        UserNotificationPreference.objects.filter(user=bos).update(approval=True, ikut_bawaan_jabatan=False)
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        log = EmailNotificationLog.objects.filter(receiver=bos, entity_identifier=issue.id).first()
        assert log is not None
        Profile.objects.update_or_create(user=bos, defaults={"language": "id"})

        terkirim = []

        class KoneksiPalsu:
            def send_messages(self, pesan):
                terkirim.extend(pesan)
                return len(pesan)

        with (
            mock.patch.object(
                tugas,
                "get_email_configuration",
                return_value=("smtp.test", "u", "p", 587, "1", "0", "noreply@test"),
            ),
            mock.patch.object(tugas, "get_connection", return_value=KoneksiPalsu()),
        ):
            tugas.send_approval_email_notification(str(log.pk))

        assert len(terkirim) == 1
        assert "Perlu persetujuan" in terkirim[0].subject
        log.refresh_from_db()
        assert log.processed_at is not None
        assert log.sent_at is not None

    @pytest.mark.django_db
    def test_tanpa_smtp_baris_ditandai_selesai_bukan_macat(self, workspace, staf, bos, divisi, monkeypatch):
        from plane.bgtasks import email_notification_task as tugas

        # Pimpinan tidak diemail secara bawaan (KEP-42): atasan ini menyalakannya sendiri.
        UserNotificationPreference.objects.filter(user=bos).update(approval=True, ikut_bawaan_jabatan=False)
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        log = EmailNotificationLog.objects.filter(receiver=bos, entity_identifier=issue.id).first()

        with mock.patch.object(tugas, "get_email_configuration", return_value=(None, "", "", 587, "1", "0", "")):
            tugas.send_approval_email_notification(str(log.pk))

        log.refresh_from_db()
        assert log.processed_at is not None
        assert log.sent_at is None


@pytest.mark.contract
class TestSelesaiDitahanJadiPengajuan:
    """KEP-55 (keputusan user 2 Nov 2026): staf yang menggeser ke Done hanya MENGAJUKAN.

    Statusnya tidak berpindah sampai atasan menyetujui; ditolak = kembali ke In
    Progress; tiap pengajuan dan keputusan tercatat di log aktivitas tugas.
    """

    @staticmethod
    def _aktivitas(issue, verb):
        from plane.db.models import IssueActivity

        return IssueActivity.objects.filter(issue=issue, field="approval", verb=verb)

    @staticmethod
    def _putuskan(bos, workspace, divisi, baris, **data):
        return _klien(bos).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id), data, format="json"
        )

    @pytest.mark.django_db
    def test_geser_ke_selesai_tidak_memindahkan_status(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        issue.refresh_from_db()
        assert issue.state is None or issue.state.group != "completed"
        assert issue.completed_at is None
        assert PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").count() == 1

    @pytest.mark.django_db
    def test_pengajuan_tercatat_di_log_aktivitas(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        log = self._aktivitas(issue, "requested")
        assert log.count() == 1
        assert log.first().actor_id == staf.id

    @pytest.mark.django_db
    def test_patch_membalas_status_asli_dan_tanda_pengajuan(self, workspace, staf, bos, divisi, monkeypatch):
        from plane.db.models import DEFAULT_STATES, State

        monkeypatch.setenv(FLAG_GERBANG, "1")
        # Status bawaan Plane (Backlog = default) seperti project sungguhan. Tanpa ini
        # satu-satunya status adalah Done, dan Issue.save() memilihnya sebagai bawaan.
        for d in DEFAULT_STATES:
            State.objects.get_or_create(
                project=divisi,
                workspace=workspace,
                name=d["name"],
                defaults={
                    "color": d["color"],
                    "sequence": d["sequence"],
                    "group": d["group"],
                    "default": d.get("default", False),
                },
            )
        res = _klien(staf).post(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id),
            {"name": "Tugas indikator", "assignee_ids": [str(staf.id)]},
            format="json",
        )
        selesai = State.objects.filter(project=divisi, group="completed").first()
        patch = _klien(staf).patch(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id) + res.json()["id"] + "/",
            {"state": str(selesai.id)},
            format="json",
        )
        assert patch.status_code == status.HTTP_200_OK, getattr(patch, "data", None)
        body = patch.json()
        assert body["approval_status"] == "menunggu"
        assert body["approval_requested"] is True
        # Klien mengembalikan status optimisnya ke nilai ini: status yang benar-benar tersimpan, bukan Done.
        tersimpan = Issue.objects.get(pk=res.json()["id"]).state_id
        assert body["state_id"] == (str(tersimpan) if tersimpan else None)
        assert body["state_id"] != str(selesai.id)

    @pytest.mark.django_db
    def test_geser_ke_selesai_lagi_selagi_menunggu_tidak_menggandakan(self, workspace, staf, bos, divisi, monkeypatch):
        from plane.db.models import State

        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        selesai = State.objects.filter(project=divisi, group="completed").first()
        _klien(staf).patch(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id) + f"{issue.id}/",
            {"state": str(selesai.id)},
            format="json",
        )
        assert PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").count() == 1
        assert self._aktivitas(issue, "requested").count() == 1

    @pytest.mark.django_db
    def test_setujui_memindahkan_ke_selesai_dan_mencatat(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()
        res = self._putuskan(bos, workspace, divisi, baris, aksi="setujui")
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)
        issue.refresh_from_db()
        assert issue.state.group == "completed"
        assert self._aktivitas(issue, "approved").filter(actor=bos).count() == 1

    @pytest.mark.django_db
    def test_tolak_kembali_ke_in_progress_dengan_alasan_di_log(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()
        res = self._putuskan(bos, workspace, divisi, baris, aksi="tolak", alasan="Belum lengkap")
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)
        issue.refresh_from_db()
        assert issue.state.group == "started"
        log = self._aktivitas(issue, "rejected").get()
        assert log.actor_id == bos.id
        assert log.new_value == "Belum lengkap"

    @pytest.mark.django_db
    def test_ditolak_lalu_geser_ke_selesai_lagi_jadi_pengajuan_baru(self, workspace, staf, bos, divisi, monkeypatch):
        from plane.db.models import State

        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()
        self._putuskan(bos, workspace, divisi, baris, aksi="tolak", alasan="Ulangi")
        selesai = State.objects.filter(project=divisi, group="completed").first()
        _klien(staf).patch(
            URL_ISSUES.format(slug=workspace.slug, project_id=divisi.id) + f"{issue.id}/",
            {"state": str(selesai.id)},
            format="json",
        )
        issue.refresh_from_db()
        assert issue.state.group == "started"
        assert PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").count() == 1
        assert PersetujuanPenugasan.objects.filter(issue=issue, status="ditolak").count() == 1
        assert self._aktivitas(issue, "requested").count() == 2

    @pytest.mark.django_db
    def test_ajukan_ulang_tidak_memindahkan_status(self, workspace, staf, bos, divisi, monkeypatch):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()
        self._putuskan(bos, workspace, divisi, baris, aksi="tolak", alasan="Ulangi")
        res = _klien(staf).post(
            URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk=baris.id),
            {"aksi": "ajukan-ulang"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)
        assert res.json()["status"] == "menunggu"
        issue.refresh_from_db()
        assert issue.state.group == "started"

    @pytest.mark.django_db
    def test_riwayat_per_tugas_terlihat_oleh_atasan_termasuk_yang_sudah_diputuskan(
        self, workspace, staf, bos, divisi, monkeypatch
    ):
        issue = _ajukan(staf, workspace, divisi, monkeypatch)
        baris = PersetujuanPenugasan.objects.filter(issue=issue, status="menunggu").first()
        self._putuskan(bos, workspace, divisi, baris, aksi="tolak", alasan="Ulangi")
        dasar = URL_PUTUSKAN.format(slug=workspace.slug, project_id=divisi.id, pk="x").removesuffix("x/")
        res = _klien(bos).get(f"{dasar}?tugas={issue.id}")
        assert res.status_code == status.HTTP_200_OK, getattr(res, "data", None)
        assert [b["status"] for b in res.json()["hasil"]] == ["ditolak"]
