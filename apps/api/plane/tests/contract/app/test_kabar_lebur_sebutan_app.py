# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kabar lebur dan sebutan lintas departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Dua keputusan user 2026-11-17, diuji lewat tugas `notifications` yang asli.

1. Kabar lebur (utils/gabung_kabar.py): rentetan komentar dan suntingan dari satu
   pelaku atas satu work item = SATU baris inbox, SATU kartu obrolan.
2. Sebutan (utils/jangkauan_sebutan.py): siapa pun boleh disebut, tapi orang di
   luar project/departemen work item tidak menerima apa pun: tidak ada baris
   inbox, tidak ada baris email, tidak jadi subscriber, tidak jadi IssueMention.
   Direktur/sekretaris (jangkauan seluruh organisasi) tetap dikabari.
"""

import json
from unittest import mock
from uuid import uuid4

import pytest
from django.db.models import Q
from django.utils import timezone
from rest_framework.test import APIClient

from plane.app.serializers import IssueActivitySerializer
from plane.bgtasks.notification_task import notifications
from plane.db.models import (
    EmailNotificationLog,
    Issue,
    IssueActivity,
    IssueComment,
    IssueMention,
    IssueSubscriber,
    JabatanOrganisasi,
    Notification,
    PesanLangsung,
    Project,
    ProjectMember,
    State,
    TINGKAT_SEKRETARIS,
    User,
    WorkspaceMember,
)
from plane.utils.jangkauan_sebutan import dalam_jangkauan, saring_sebutan
from plane.utils.preferensi_email import SAKLAR_NOTIFIKASI

SEBUT = "in_app:issue_activities:mentioned"


def _user(prefix, workspace):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, display_name=prefix
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


def _anggota(project, user):
    ProjectMember.objects.update_or_create(
        project=project, member=user, workspace=project.workspace, defaults={"role": 15, "is_active": True}
    )


def _mention(user):
    return (
        f'<mention-component id="{uuid4()}" entity_name="user_mention" '
        f'entity_identifier="{user.id}"></mention-component>'
    )


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.project = Project.objects.create(name="Gudang", identifier="GDG", workspace=workspace)
    o.state = State.objects.create(project=o.project, workspace=workspace, name="Todo", group="unstarted")
    o.alice = create_user  # subscriber
    o.bob = _user("bob", workspace)  # pelaku
    o.cici = _user("cici", workspace)  # anggota project, disebut
    o.luar = _user("luar", workspace)  # anggota workspace, BUKAN anggota project
    o.sekre = _user("sekre", workspace)  # sekretaris: jangkauan seluruh organisasi, bukan anggota project
    for u in (o.alice, o.bob, o.cici):
        _anggota(o.project, u)
    JabatanOrganisasi.objects.create(workspace=workspace, member=o.sekre, tingkat=TINGKAT_SEKRETARIS)
    o.issue = Issue.objects.create(name="Hitung stok", project=o.project, workspace=workspace, state=o.state)
    IssueSubscriber.objects.create(issue=o.issue, project=o.project, workspace=workspace, subscriber=o.alice)
    return o


@pytest.fixture(autouse=True)
def _saklar_hidup_semua():
    """Semua saklar hidup: yang diuji aturan penerima, bukan preferensi pribadi atau batas direktur."""
    semua = dict.fromkeys(SAKLAR_NOTIFIKASI, True)
    with (
        mock.patch("plane.bgtasks.notification_task.saklar_untuk", lambda _u: dict(semua)),
        mock.patch("plane.utils.gabung_kabar.lebur_penuh_aktif", lambda: True),
        mock.patch("plane.utils.sinyal_data.siarkan_notifikasi_baris"),
        mock.patch("plane.utils.kanal_sistem.siarkan"),
        mock.patch("plane.utils.kartu_obrolan.siarkan"),
    ):
        yield


def _kartu_untuk(user):
    """Kartu kabar untuk `user`: di DM (penerima) atau di ruang kabar pribadi (muatan.penerima)."""
    return PesanLangsung.objects.filter(Q(penerima=user) | Q(muatan__penerima=str(user.id)))


def _aktivitas(org, pelaku, field, **kolom):
    return IssueActivity.objects.create(
        issue=org.issue,
        project=org.project,
        workspace=org.ws,
        actor=pelaku,
        field=field,
        epoch=1,
        comment=kolom.pop("comment", f"updated {field}"),
        verb=kolom.pop("verb", "updated"),
        **kolom,
    )


def _jalankan(org, pelaku, aktivitas, tipe="issue.activity.updated", requested=None, current=None):
    muatan = IssueActivitySerializer(aktivitas, many=True).data
    notifications(
        type=tipe,
        issue_id=str(org.issue.id),
        project_id=str(org.project.id),
        actor_id=str(pelaku.id),
        subscriber=False,
        issue_activities_created=json.dumps(list(muatan), default=str),
        requested_data=json.dumps(requested or {}),
        current_instance=json.dumps(current) if current is not None else None,
    )


def _komentar(org, pelaku, html):
    komentar = IssueComment.objects.create(
        issue=org.issue, project=org.project, workspace=org.ws, actor=pelaku, comment_html=html
    )
    akt = _aktivitas(
        org,
        pelaku,
        "comment",
        verb="created",
        comment="created a comment",
        new_value=html,
        new_identifier=komentar.id,
        issue_comment=komentar,
    )
    _jalankan(org, pelaku, [akt], tipe="comment.activity.created", requested={"comment_html": html})
    return komentar


# ---------------------------------------------------------------- kabar lebur


@pytest.mark.contract
class TestKabarLebur:
    @pytest.mark.django_db
    def test_rentetan_komentar_satu_baris_satu_kartu(self, org):
        for n in range(3):
            _komentar(org, org.bob, f"<p>komentar {n}</p>")

        kabar = Notification.objects.filter(receiver=org.alice, entity_identifier=org.issue.id)
        assert kabar.count() == 1
        baris = kabar.get()
        assert baris.read_at is None
        assert baris.data["gabungan"]["komentar"] == 3
        # Satu kartu, disunting di tempat dan memuat hitungannya.
        kartu = _kartu_untuk(org.alice)
        assert kartu.count() == 1
        assert kartu.get().muatan["detail"]["jumlah_komentar"] == 3

    @pytest.mark.django_db
    def test_suntingan_beberapa_kolom_lalu_komentar_satu_baris(self, org):
        _jalankan(org, org.bob, [_aktivitas(org, org.bob, "priority", old_value="low", new_value="high")])
        _jalankan(org, org.bob, [_aktivitas(org, org.bob, "start_date", old_value="", new_value="2026-11-20")])
        _komentar(org, org.bob, "<p>sudah</p>")

        baris = Notification.objects.get(receiver=org.alice, entity_identifier=org.issue.id)
        gab = baris.data["gabungan"]
        assert [p["field"] for p in gab["perubahan"]] == ["priority", "start_date"]
        assert gab["komentar"] == 1
        assert EmailNotificationLog.objects.filter(receiver=org.alice).count() == 3  # satu email per jendela

    @pytest.mark.django_db
    def test_kabar_yang_sudah_dibaca_memulai_baris_baru(self, org):
        _komentar(org, org.bob, "<p>satu</p>")
        Notification.objects.filter(receiver=org.alice).update(read_at=timezone.now())
        _komentar(org, org.bob, "<p>dua</p>")
        assert Notification.objects.filter(receiver=org.alice).count() == 2
        assert Notification.objects.filter(receiver=org.alice, read_at__isnull=True).count() == 1


# ---------------------------------------------------------------- sebutan lintas departemen


@pytest.mark.contract
class TestSebutanLintasDepartemen:
    @pytest.mark.django_db
    def test_aturan_jangkauan(self, org):
        ids = [org.cici.id, org.luar.id, org.sekre.id, "all", "rusak"]
        assert dalam_jangkauan(org.project.id, ids) == {str(org.cici.id), str(org.sekre.id)}
        assert saring_sebutan(org.project.id, [str(org.luar.id), str(org.cici.id)]) == [str(org.cici.id)]
        ProjectMember.objects.filter(project=org.project, member=org.cici).update(is_active=False)
        assert str(org.cici.id) not in dalam_jangkauan(org.project.id, ids)

    @pytest.mark.django_db
    def test_sebutan_deskripsi_orang_luar_tidak_menerima_apa_pun(self, org):
        html = f"<p>{_mention(org.cici)} {_mention(org.luar)} {_mention(org.sekre)}</p>"
        akt = _aktivitas(org, org.bob, "description", old_value="", new_value=html)
        _jalankan(org, org.bob, [akt], requested={"description_html": html}, current={"description_html": "<p></p>"})

        disebut = set(Notification.objects.filter(sender=SEBUT).values_list("receiver_id", flat=True))
        assert disebut == {org.cici.id, org.sekre.id}
        assert not Notification.objects.filter(receiver=org.luar).exists()
        assert not EmailNotificationLog.objects.filter(receiver=org.luar).exists()
        assert not IssueSubscriber.objects.filter(issue=org.issue, subscriber=org.luar).exists()
        assert set(IssueMention.objects.filter(issue=org.issue).values_list("mention_id", flat=True)) == {
            org.cici.id,
            org.sekre.id,
        }
        assert not _kartu_untuk(org.luar).exists()

    @pytest.mark.django_db
    def test_sebutan_komentar_orang_luar_tidak_menerima_apa_pun(self, org):
        _komentar(org, org.bob, f"<p>{_mention(org.luar)} {_mention(org.cici)} tolong cek</p>")
        assert Notification.objects.filter(receiver=org.cici, sender=SEBUT).count() == 1
        assert not Notification.objects.filter(receiver=org.luar).exists()
        assert not EmailNotificationLog.objects.filter(receiver=org.luar).exists()
        assert not IssueSubscriber.objects.filter(issue=org.issue, subscriber=org.luar).exists()
        assert not _kartu_untuk(org.luar).exists()

    @pytest.mark.django_db
    def test_sebutan_tetap_kabar_tersendiri_dan_tidak_dilebur(self, org):
        """Sebutan ditujukan ke orangnya: tidak ikut dilebur ke kabar komentar biasa."""
        IssueSubscriber.objects.create(issue=org.issue, project=org.project, workspace=org.ws, subscriber=org.cici)
        _komentar(org, org.bob, "<p>biasa</p>")
        _komentar(org, org.bob, f"<p>{_mention(org.cici)}</p>")
        assert Notification.objects.filter(receiver=org.cici, sender=SEBUT).count() == 1
        assert Notification.objects.filter(receiver=org.cici).exclude(sender=SEBUT).count() == 1

    @pytest.mark.django_db
    def test_judul_teks_polos_tidak_pernah_mengabari(self, org):
        """Judul work item teks polos: '@nama' atau markup sebutan di judul tidak dibaca sebagai sebutan."""
        judul = f"Minta {_mention(org.cici)} @cici cek"
        akt = _aktivitas(org, org.bob, "name", old_value="Hitung stok", new_value=judul)
        _jalankan(org, org.bob, [akt], requested={"name": judul}, current={"name": "Hitung stok"})
        assert not Notification.objects.filter(sender=SEBUT).exists()
        assert not IssueMention.objects.filter(issue=org.issue).exists()

    @pytest.mark.django_db
    def test_pemilih_menawarkan_orang_luar_dengan_tanda_tidak_dikabari(self, org):
        klien = APIClient()
        klien.force_authenticate(user=org.bob)
        res = klien.get(
            f"/api/workspaces/{org.ws.slug}/entity-search/",
            {"query_type": "user_mention", "project_id": str(org.project.id), "query": "", "count": 50},
        )
        assert res.status_code == 200, res.data
        assert "user_mention_di_luar" not in res.data
        peta = {u["member__id"]: u["dikabari"] for u in res.data["user_mention"]}
        assert peta[org.cici.id] is True
        assert peta[org.luar.id] is False
        assert peta[org.sekre.id] is True


@pytest.mark.django_db
def test_sebutan_di_simpanan_lanjutan_deskripsi_tetap_dikabarkan(org):
    """Penyunting menyimpan otomatis. Simpanan lanjutan tidak membuat baris aktivitas baru
    (yang lama hanya diperbarui), jadi tugas notifikasi menerima daftar aktivitas kosong."""
    _aktivitas(org, org.bob, "description")
    _jalankan(
        org,
        org.bob,
        [],
        requested={"description_html": f"<p>{_mention(org.cici)}</p>"},
        current={"description_html": "<p></p>"},
    )
    assert Notification.objects.filter(receiver=org.cici, sender=SEBUT).count() == 1
    assert EmailNotificationLog.objects.filter(receiver=org.cici).count() == 1

