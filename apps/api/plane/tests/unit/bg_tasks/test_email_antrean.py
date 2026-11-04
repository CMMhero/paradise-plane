# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: rem spam email
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Kumpul email per penerima, utas per work item, dan saringan member aktif.

Yang dijaga:
- satu penerima = satu email per jendela; menyapu ulang tidak mengirim lagi;
- jendela belum habis = belum dikirim; saklar mati = jalur lama per kejadian;
- pengajuan yang menunggu keputusan penerima tampil paling atas;
- SMTP putus melepas klaim (dicoba lagi), tidak menelan kabar;
- email pertama tentang satu work item memakai id akar, berikutnya membalasnya;
- orang yang lama tak aktif tidak diemail, barisnya tetap diproses.
"""

import smtplib
from datetime import timedelta
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest
from django.core import mail
from django.utils import timezone

from plane.bgtasks import email_antrean
from plane.bgtasks.email_antrean import kelompokkan, kirim_kabar_penerima, sapu_antrean
from plane.db.models import EmailNotificationLog, Issue, Project, State, User
from plane.utils.email_utas import ENTITY_UTAS, domain_pesan, header_utas, id_akar, klaim_akar, subjek_utas
from plane.utils.penerima_aktif import aktif_sejak, batas_aktif
from plane.utils.saklar_instance import (
    EMAIL_ACTIVE_DAYS,
    EMAIL_BATCH_DELAY_MINUTES,
    ENABLE_EMAIL_ACTIVE_ONLY,
    ENABLE_EMAIL_BATCH,
    ENABLE_EMAIL_THREADING,
)

SMTP_UJI = ("smtp.uji", "", "", "587", "1", "0", "Paradise <noreply@paradise.test>")


@pytest.fixture
def saklar(monkeypatch):
    """Saklar lewat env (benih), karena barisnya belum ada di database uji."""
    monkeypatch.setenv(ENABLE_EMAIL_BATCH, "1")
    monkeypatch.setenv(ENABLE_EMAIL_THREADING, "0")
    monkeypatch.setenv(ENABLE_EMAIL_ACTIVE_ONLY, "0")
    monkeypatch.setenv(EMAIL_BATCH_DELAY_MINUTES, "15")
    monkeypatch.setenv(EMAIL_ACTIVE_DAYS, "30")
    return monkeypatch


@pytest.fixture
def smtp():
    with mock.patch("plane.license.utils.instance_value.get_email_configuration", return_value=SMTP_UJI):
        yield


def _user(prefix):
    unik = uuid4().hex[:8]
    return User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_active=timezone.now()
    )


@pytest.fixture
def penerima(db):
    return _user("penerima")


@pytest.fixture
def aktor(db):
    return _user("aktor")


@pytest.fixture
def project(workspace, create_user):
    return Project.objects.create(name="Uji", identifier="UJI", workspace=workspace, created_by=create_user)


def _issue(project, nama):
    state = State.objects.filter(project=project).first() or State.objects.create(
        name="Todo", project=project, group="unstarted", default=True
    )
    return Issue.objects.create(name=nama, workspace=project.workspace, project=project, state=state)


def _baris(issue, penerima, aktor, *, entity="", verb="updated", field="priority", lama="low", baru="high", umur=20):
    waktu = timezone.now() - timedelta(minutes=umur)
    baris = EmailNotificationLog.objects.create(
        receiver=penerima,
        triggered_by=aktor,
        entity_identifier=issue.id,
        entity_name="issue",
        entity=entity,
        data={
            "issue": {"id": str(issue.id), "name": issue.name},
            "issue_activity": {
                "verb": verb,
                "field": "approval" if entity == "approval" else field,
                "old_value": lama,
                "new_value": baru,
                "issue_comment": "",
                "activity_time": waktu.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        },
    )
    # created_at diisi otomatis; mundurkan supaya jendela kumpulnya bisa diuji.
    EmailNotificationLog.objects.filter(pk=baris.pk).update(created_at=waktu)
    return baris


# ---------------------------------------------------------------- murni


def test_kelompokkan_memisah_pengajuan_dan_menjaga_urutan():
    t0 = timezone.now()

    def b(i, entity, verb, issue):
        return SimpleNamespace(
            id=i,
            entity=entity,
            entity_identifier=issue,
            created_at=t0 + timedelta(minutes=i),
            data={"issue_activity": {"verb": verb}},
        )

    daftar = [
        b(3, "", "updated", "A"),
        b(1, "", "updated", "B"),
        b(2, "approval", "submitted", "A"),
        b(4, "", "x", "B"),
    ]
    aksi, per_issue = kelompokkan(daftar)
    assert [x.id for x in aksi] == [2]
    assert list(per_issue) == ["B", "A"]  # urut kabar pertama tiap work item
    assert [x.id for x in per_issue["B"]] == [1, 4]


def test_header_utas_pertama_dan_balasan():
    akar = id_akar("abc", "paradise.test")
    assert akar == "<issue-abc@paradise.test>"
    assert header_utas("abc", "paradise.test", pertama=True) == {"Message-ID": akar}
    balas = header_utas("abc", "paradise.test", pertama=False)
    assert balas["In-Reply-To"] == akar and balas["References"] == akar
    assert balas["Message-ID"] != akar
    assert subjek_utas("UJI-1", "Judul", balasan=False) == "[UJI-1] Judul"
    assert subjek_utas("UJI-1", "Judul", balasan=True) == "Re: [UJI-1] Judul"


def test_domain_pesan_dari_pengirim_lalu_host():
    assert domain_pesan("Paradise <noreply@Paradise.Test>") == "paradise.test"
    assert domain_pesan("", "https://space.contoh.id/") == "space.contoh.id"
    assert domain_pesan("", "") == "paradise.local"


def test_aktif_sejak_murni():
    sekarang = timezone.now()
    batas = sekarang - timedelta(days=30)
    lama = SimpleNamespace(last_active=sekarang - timedelta(days=40), last_login_time=None)
    baru_login = SimpleNamespace(last_active=sekarang - timedelta(days=40), last_login_time=sekarang)
    kosong = SimpleNamespace(last_active=None, last_login_time=None)
    assert aktif_sejak(lama, None) is True  # saklar mati: semua lolos
    assert aktif_sejak(lama, batas) is False
    assert aktif_sejak(baru_login, batas) is True
    assert aktif_sejak(kosong, batas) is False


# ---------------------------------------------------------------- kumpul


@pytest.mark.django_db
def test_satu_email_untuk_semua_kabar_dan_tanpa_duplikat(saklar, smtp, project, penerima, aktor):
    a = _issue(project, "Laporan bulanan")
    b = _issue(project, "Rapat vendor")
    _baris(a, penerima, aktor, umur=25)
    _baris(b, penerima, aktor, field="state", lama="Todo", baru="In Progress", umur=22)
    _baris(b, penerima, aktor, entity="approval", verb="submitted", lama="", baru="", umur=21)

    hasil = sapu_antrean()

    assert hasil == {"terkirim": 1}
    assert len(mail.outbox) == 1
    pesan = mail.outbox[0]
    assert pesan.to == [penerima.email]
    # Pengajuan yang menunggu keputusan di atas, sebelum bagian pembaruan.
    badan = pesan.body
    assert badan.index("Rapat vendor") < badan.index("Laporan bulanan")
    assert (
        EmailNotificationLog.objects.filter(receiver=penerima, sent_at__isnull=True).exclude(entity=ENTITY_UTAS).count()
        == 0
    )

    # Menyapu lagi (penyapu kedua, task terulang) tidak mengirim apa pun.
    assert sapu_antrean() == {}
    assert kirim_kabar_penerima(penerima.id, smtp_siap=True) == "kosong"
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_jendela_belum_habis_belum_dikirim(saklar, smtp, project, penerima, aktor):
    baris = _baris(_issue(project, "Baru saja"), penerima, aktor, umur=5)
    assert sapu_antrean() == {}
    assert len(mail.outbox) == 0
    baris.refresh_from_db()
    assert baris.processed_at is None


@pytest.mark.django_db
def test_kabar_baru_ikut_email_kabar_lama(saklar, smtp, project, penerima, aktor):
    issue = _issue(project, "Satu tugas")
    _baris(issue, penerima, aktor, umur=20)
    _baris(issue, penerima, aktor, field="state", lama="Todo", baru="Done", umur=1)
    assert sapu_antrean() == {"terkirim": 1}
    assert len(mail.outbox) == 1
    assert EmailNotificationLog.objects.filter(receiver=penerima, processed_at__isnull=True).count() == 0


@pytest.mark.django_db
def test_smtp_putus_melepas_klaim(saklar, smtp, project, penerima, aktor):
    baris = _baris(_issue(project, "Gagal kirim"), penerima, aktor)
    with mock.patch.object(email_antrean, "buat_pesan", side_effect=smtplib.SMTPServerDisconnected("putus")):
        assert kirim_kabar_penerima(penerima.id, smtp_siap=True) == "diulang"
    baris.refresh_from_db()
    assert baris.processed_at is None and baris.sent_at is None
    # Putaran berikutnya mengirimnya.
    assert kirim_kabar_penerima(penerima.id, smtp_siap=True) == "terkirim"
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_saklar_mati_jalur_lama_per_kejadian(saklar, project, penerima, aktor):
    saklar.setenv(ENABLE_EMAIL_BATCH, "0")
    issue = _issue(project, "Lama")
    p1 = _baris(issue, penerima, aktor, entity="approval", verb="submitted", umur=0)
    p2 = _baris(issue, penerima, aktor, entity="approval", verb="approved", umur=0)
    from plane.bgtasks import email_notification_task as tugas

    with (
        mock.patch.object(tugas.send_approval_email_notification, "delay") as kirim,
        mock.patch.object(tugas.send_email_notification, "delay"),
    ):
        tugas.stack_email_notification()
    assert sorted(c.kwargs["email_log_id"] for c in kirim.call_args_list) == sorted([str(p1.id), str(p2.id)])


# ---------------------------------------------------------------- utas


@pytest.mark.django_db
def test_klaim_akar_hanya_sekali_per_penerima(project, penerima, aktor):
    issue = _issue(project, "Utas")
    assert klaim_akar(penerima.id, issue.id, "paradise.test") is True
    assert klaim_akar(penerima.id, issue.id, "paradise.test") is False
    # Penerima lain punya email pertamanya sendiri.
    assert klaim_akar(aktor.id, issue.id, "paradise.test") is True


@pytest.mark.django_db
def test_email_satu_work_item_masuk_utas(saklar, smtp, project, penerima, aktor):
    saklar.setenv(ENABLE_EMAIL_THREADING, "1")
    issue = _issue(project, "Utas tetap")
    akar = id_akar(issue.id, "paradise.test")

    _baris(issue, penerima, aktor, umur=20)
    assert sapu_antrean() == {"terkirim": 1}
    _baris(issue, penerima, aktor, field="state", lama="Todo", baru="Done", umur=20)
    assert sapu_antrean() == {"terkirim": 1}

    pertama, kedua = (m.message() for m in mail.outbox)
    assert pertama["Message-ID"] == akar
    assert pertama["Subject"] == f"[UJI-{issue.sequence_id}] Utas tetap"
    assert kedua["Message-ID"] != akar
    assert kedua["In-Reply-To"] == akar and kedua["References"] == akar
    assert kedua["Subject"] == f"Re: [UJI-{issue.sequence_id}] Utas tetap"
    # Penanda utas tidak pernah ikut disapu sebagai kabar.
    assert sapu_antrean() == {}


@pytest.mark.django_db
def test_email_persetujuan_tunggal_ikut_utas_work_itemnya(saklar, smtp, project, penerima, aktor):
    saklar.setenv(ENABLE_EMAIL_THREADING, "1")
    issue = _issue(project, "Butuh restu")
    _baris(issue, penerima, aktor, entity="approval", verb="submitted", lama="", baru="")
    assert sapu_antrean() == {"terkirim": 1}
    pesan = mail.outbox[0].message()
    assert pesan["Subject"] == f"[UJI-{issue.sequence_id}] Butuh restu"
    assert pesan["Message-ID"] == id_akar(issue.id, "paradise.test")


@pytest.mark.django_db
def test_ringkasan_banyak_work_item_tidak_masuk_utas(saklar, smtp, project, penerima, aktor):
    saklar.setenv(ENABLE_EMAIL_THREADING, "1")
    a, b = _issue(project, "Satu"), _issue(project, "Dua")
    _baris(a, penerima, aktor)
    _baris(b, penerima, aktor)
    assert sapu_antrean() == {"terkirim": 1}
    pesan = mail.outbox[0].message()
    assert pesan["In-Reply-To"] is None
    assert not EmailNotificationLog.objects.filter(entity=ENTITY_UTAS).exists()


# ---------------------------------------------------------------- member aktif


@pytest.mark.django_db
def test_member_lama_tak_aktif_tidak_diemail(saklar, smtp, project, penerima, aktor):
    saklar.setenv(ENABLE_EMAIL_ACTIVE_ONLY, "1")
    User.objects.filter(pk=penerima.pk).update(
        last_active=timezone.now() - timedelta(days=45), last_login_time=timezone.now() - timedelta(days=45)
    )
    baris = _baris(_issue(project, "Sepi"), penerima, aktor)
    assert batas_aktif() is not None
    assert sapu_antrean() == {"dilewati": 1}
    assert len(mail.outbox) == 0
    baris.refresh_from_db()
    assert baris.processed_at is not None and baris.sent_at is None


@pytest.mark.django_db
def test_member_aktif_tetap_diemail_saat_saringan_menyala(saklar, smtp, project, penerima, aktor):
    saklar.setenv(ENABLE_EMAIL_ACTIVE_ONLY, "1")
    _baris(_issue(project, "Ramai"), penerima, aktor)
    assert sapu_antrean() == {"terkirim": 1}


@pytest.mark.django_db
def test_saringan_tidak_menyentuh_email_sistem(saklar, penerima):
    """Reset sandi dan kode masuk tidak lewat `penerima_aktif` sama sekali."""
    saklar.setenv(ENABLE_EMAIL_ACTIVE_ONLY, "1")
    import inspect

    from plane.bgtasks import forgot_password_task, magic_link_code_task, workspace_invitation_task

    for modul in (forgot_password_task, magic_link_code_task, workspace_invitation_task):
        assert "penerima_aktif" not in inspect.getsource(modul)
