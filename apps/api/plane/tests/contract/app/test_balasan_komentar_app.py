# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: uji balasan komentar (KEP-103)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Balasan pada komentar work item: utas satu tingkat (KEP-103).

Yang dijaga:

1. Pembuatan: `parent` dicek server (work item sama, komentar hidup), membalas
   sebuah balasan menempel ke AKAR utas, `parent` tidak bisa dipalsukan lewat PATCH.
2. Izin: bukan anggota project ditolak; tamu mengikuti aturan komentar yang ada.
3. Menghapus induk membawa balasannya (app view dan API v1); menghapus balasan
   tidak menyentuh induknya.
4. Notifikasi: penulis induk dikabari lewat saklar komentar, tanpa dobel dengan
   kabar sebutan, tanpa kabar untuk diri sendiri.
"""

import json
from unittest import mock
from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.app.serializers import IssueActivitySerializer
from plane.bgtasks.notification_task import notifications, penerima_balasan_komentar
from plane.db.models import (
    APIToken,
    Issue,
    IssueActivity,
    IssueComment,
    Notification,
    Project,
    ProjectMember,
    State,
    User,
    UserNotificationPreference,
    WorkspaceMember,
)
from plane.utils.balasan_komentar import induk_balasan

# ---------------------------------------------------------------------------
# Pembantu
# ---------------------------------------------------------------------------


def _user(prefix, workspace, role=15):
    unik = uuid4().hex[:8]
    user = User.objects.create(
        email=f"{prefix}-{unik}@plane.so", username=f"{prefix}_{unik}", first_name=prefix, last_name="Uji"
    )
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    return user


def _anggota(project, user, role=15):
    ProjectMember.objects.update_or_create(
        project=project, member=user, workspace=project.workspace, defaults={"role": role, "is_active": True}
    )


def _klien(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _klien_token(user):
    token = APIToken.objects.create(user=user, label=f"uji-{uuid4().hex[:6]}", user_type=0)
    client = APIClient()
    client.credentials(HTTP_X_API_KEY=token.token)
    return client


def _saklar(user, **nilai):
    """Baris preferensi global dengan saklar yang ditulis tegas (tanpa bawaan jabatan)."""
    UserNotificationPreference.objects.update_or_create(
        user=user,
        workspace=None,
        project=None,
        defaults={"ikut_bawaan_jabatan": False, **nilai},
    )


@pytest.fixture
def org(db, workspace, create_user):
    o = type("Org", (), {})()
    o.ws = workspace
    o.project = Project.objects.create(name="Balasan", identifier="BAL", workspace=workspace)
    o.state = State.objects.create(project=o.project, workspace=workspace, name="Todo", group="unstarted")
    o.alice = create_user
    o.bob = _user("bob", workspace)
    o.cici = _user("cici", workspace)
    o.luar = _user("luar", workspace)  # anggota workspace, BUKAN anggota project
    o.tamu = _user("tamu", workspace, role=5)
    for u in (o.alice, o.bob, o.cici):
        _anggota(o.project, u)
    _anggota(o.project, o.tamu, role=5)
    o.issue = Issue.objects.create(name="Tugas", project=o.project, workspace=workspace, state=o.state)
    return o


def _komentar(org, penulis, html="<p>induk</p>", issue=None, **ekstra):
    return IssueComment.objects.create(
        issue=issue or org.issue,
        project=org.project,
        workspace=org.ws,
        actor=penulis,
        comment_html=html,
        **ekstra,
    )


def _url(org, issue=None, komentar=None, prefix="api"):
    base = f"/{prefix}/workspaces/{org.ws.slug}/projects/{org.project.id}/issues/{(issue or org.issue).id}/comments/"
    return base + (f"{komentar.id}/" if komentar else "")


@pytest.fixture(autouse=True)
def _tanpa_broker():
    """`.delay` ke broker tak relevan di sini; yang diuji adalah isi baris dan respons."""
    with (
        mock.patch("plane.app.views.issue.comment.issue_activity.delay") as aktivitas,
        mock.patch("plane.app.views.issue.comment.model_activity.delay"),
    ):
        yield aktivitas


def _balas(org, penulis, induk, html="<p>balasan</p>", issue=None):
    return _klien(penulis).post(
        _url(org, issue=issue), {"comment_html": html, "parent": str(induk.id)}, format="json"
    )


# ---------------------------------------------------------------------------
# Pembuatan
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestBuatBalasan:
    @pytest.mark.django_db
    def test_balasan_menempel_ke_induk(self, org):
        induk = _komentar(org, org.alice)
        res = _balas(org, org.bob, induk)
        assert res.status_code == status.HTTP_201_CREATED
        assert str(res.data["parent"]) == str(induk.id)
        balasan = IssueComment.objects.get(pk=res.data["id"])
        assert balasan.parent_id == induk.id
        assert balasan.actor_id == org.bob.id

    @pytest.mark.django_db
    def test_komentar_biasa_tanpa_parent(self, org):
        res = _klien(org.bob).post(_url(org), {"comment_html": "<p>biasa</p>"}, format="json")
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["parent"] is None

    @pytest.mark.django_db
    def test_membalas_balasan_menempel_ke_akar_utas(self, org):
        akar = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>b1</p>", parent=akar)
        res = _balas(org, org.cici, balasan)
        assert res.status_code == status.HTTP_201_CREATED
        assert str(res.data["parent"]) == str(akar.id)

    @pytest.mark.django_db
    def test_parent_dari_work_item_lain_ditolak(self, org):
        lain = Issue.objects.create(name="Lain", project=org.project, workspace=org.ws, state=org.state)
        induk_lain = _komentar(org, org.alice, issue=lain)
        res = _balas(org, org.bob, induk_lain)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert not IssueComment.objects.filter(parent=induk_lain).exists()

    @pytest.mark.django_db
    def test_parent_dari_project_lain_ditolak(self, org):
        proyek2 = Project.objects.create(name="Dua", identifier="BA2", workspace=org.ws)
        _anggota(proyek2, org.alice)
        isu2 = Issue.objects.create(name="Dua", project=proyek2, workspace=org.ws)
        induk2 = IssueComment.objects.create(
            issue=isu2, project=proyek2, workspace=org.ws, actor=org.alice, comment_html="<p>x</p>"
        )
        assert _balas(org, org.bob, induk2).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    @pytest.mark.parametrize("nilai", ["bukan-uuid", "00000000-0000-0000-0000-000000000000", 12345])
    def test_parent_sampah_ditolak(self, org, nilai):
        res = _klien(org.bob).post(_url(org), {"comment_html": "<p>x</p>", "parent": nilai}, format="json")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert not IssueComment.objects.filter(comment_html="<p>x</p>").exists()

    @pytest.mark.django_db
    def test_induk_yang_sudah_dihapus_ditolak(self, org):
        induk = _komentar(org, org.alice)
        induk.delete()
        assert _balas(org, org.bob, induk).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_akar_yang_sudah_dihapus_menolak_balasan_ke_balasan(self, org):
        akar = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, parent=akar)
        IssueComment.objects.filter(pk=akar.pk).update(deleted_at="2026-01-01T00:00:00Z")
        assert _balas(org, org.cici, balasan).status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_parent_tidak_bisa_dipalsukan_lewat_patch(self, org):
        induk_a = _komentar(org, org.alice)
        induk_b = _komentar(org, org.alice, "<p>b</p>")
        balasan = _komentar(org, org.bob, "<p>r</p>", parent=induk_a)
        res = _klien(org.bob).patch(_url(org, komentar=balasan), {"parent": str(induk_b.id)}, format="json")
        assert res.status_code == status.HTTP_200_OK
        balasan.refresh_from_db()
        assert balasan.parent_id == induk_a.id

    @pytest.mark.django_db
    def test_komentar_biasa_tidak_bisa_dijadikan_balasan_lewat_patch(self, org):
        induk = _komentar(org, org.alice)
        biasa = _komentar(org, org.bob, "<p>biasa</p>")
        _klien(org.bob).patch(_url(org, komentar=biasa), {"parent": str(induk.id)}, format="json")
        biasa.refresh_from_db()
        assert biasa.parent_id is None

    @pytest.mark.django_db
    def test_menyunting_induk_tidak_menyentuh_balasan(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>r</p>", parent=induk)
        res = _klien(org.alice).patch(_url(org, komentar=induk), {"comment_html": "<p>baru</p>"}, format="json")
        assert res.status_code == status.HTTP_200_OK
        balasan.refresh_from_db()
        assert balasan.parent_id == induk.id
        assert balasan.deleted_at is None

    @pytest.mark.django_db
    def test_daftar_aktivitas_membawa_parent(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>r</p>", parent=induk)
        res = _klien(org.alice).get(
            f"/api/workspaces/{org.ws.slug}/projects/{org.project.id}/issues/{org.issue.id}/history/",
            {"activity_type": "issue-comment"},
        )
        assert res.status_code == status.HTTP_200_OK
        induk_per_id = {str(row["id"]): row["parent"] for row in res.data}
        assert induk_per_id[str(balasan.id)] == induk.id or str(induk_per_id[str(balasan.id)]) == str(induk.id)
        assert induk_per_id[str(induk.id)] is None


# ---------------------------------------------------------------------------
# Izin
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestIzinBalasan:
    @pytest.mark.django_db
    def test_bukan_anggota_project_ditolak(self, org):
        induk = _komentar(org, org.alice)
        res = _balas(org, org.luar, induk)
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert not IssueComment.objects.filter(parent=induk).exists()

    @pytest.mark.django_db
    def test_tamu_mengikuti_aturan_komentar_yang_ada(self, org):
        induk = _komentar(org, org.alice)
        # Tamu bukan pembuat work item dan project tidak membuka semua fitur untuk tamu.
        assert _balas(org, org.tamu, induk).status_code == status.HTTP_400_BAD_REQUEST
        Issue.objects.filter(pk=org.issue.pk).update(created_by=org.tamu)
        assert _balas(org, org.tamu, induk).status_code == status.HTTP_201_CREATED

    @pytest.mark.django_db
    def test_induk_tidak_bisa_dibaca_orang_luar_lewat_tebakan_id(self, org):
        """Orang luar yang menebak id induk tetap ditolak di gerbang peran, bukan bocor lewat 400 vs 201."""
        induk = _komentar(org, org.alice)
        res_luar = _balas(org, org.luar, induk)
        res_ngawur = _klien(org.luar).post(
            _url(org), {"comment_html": "<p>x</p>", "parent": str(uuid4())}, format="json"
        )
        assert res_luar.status_code == res_ngawur.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.django_db
    def test_hapus_balasan_orang_lain_tetap_ditolak(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>r</p>", parent=induk)
        # cici bukan penulis dan bukan atasan: aturan KEP-85 yang ada berlaku apa adanya.
        res = _klien(org.cici).delete(_url(org, komentar=balasan))
        assert res.status_code == status.HTTP_403_FORBIDDEN
        balasan.refresh_from_db()
        assert balasan.deleted_at is None


# ---------------------------------------------------------------------------
# Hapus
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestHapusInduk:
    @pytest.mark.django_db
    def test_hapus_induk_membawa_balasannya(self, org):
        induk = _komentar(org, org.alice)
        b1 = _komentar(org, org.bob, "<p>1</p>", parent=induk)
        b2 = _komentar(org, org.cici, "<p>2</p>", parent=induk)
        mandiri = _komentar(org, org.bob, "<p>mandiri</p>")
        res = _klien(org.alice).delete(_url(org, komentar=induk))
        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not IssueComment.objects.filter(pk__in=[induk.pk, b1.pk, b2.pk]).exists()
        assert IssueComment.objects.filter(pk=mandiri.pk).exists()
        # Hapus lunak: barisnya masih ada untuk Trash/pemulihan.
        assert IssueComment.all_objects.filter(pk__in=[b1.pk, b2.pk], deleted_at__isnull=False).count() == 2

    @pytest.mark.django_db
    def test_hapus_balasan_tidak_menyentuh_induk_dan_saudaranya(self, org):
        induk = _komentar(org, org.alice)
        b1 = _komentar(org, org.bob, "<p>1</p>", parent=induk)
        b2 = _komentar(org, org.cici, "<p>2</p>", parent=induk)
        assert _klien(org.bob).delete(_url(org, komentar=b1)).status_code == status.HTTP_204_NO_CONTENT
        assert IssueComment.objects.filter(pk__in=[induk.pk, b2.pk]).count() == 2
        assert not IssueComment.objects.filter(pk=b1.pk).exists()

    @pytest.mark.django_db
    def test_hapus_induk_lewat_api_v1_membawa_balasannya(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>r</p>", parent=induk)
        with mock.patch("plane.api.views.issue.issue_activity.delay"):
            res = _klien_token(org.alice).delete(_url(org, komentar=induk, prefix="api/v1"))
        assert res.status_code == status.HTTP_204_NO_CONTENT
        assert not IssueComment.objects.filter(pk__in=[induk.pk, balasan.pk]).exists()

    @pytest.mark.django_db
    def test_api_v1_buat_komentar_tidak_menerima_parent(self, org):
        induk = _komentar(org, org.alice)
        with (
            mock.patch("plane.api.views.issue.issue_activity.delay"),
            mock.patch("plane.api.views.issue.model_activity.delay"),
        ):
            res = _klien_token(org.bob).post(
                _url(org, prefix="api/v1"), {"comment_html": "<p>v1</p>", "parent": str(induk.id)}, format="json"
            )
        assert res.status_code == status.HTTP_201_CREATED
        assert IssueComment.objects.get(pk=res.data["id"]).parent_id is None

    @pytest.mark.django_db
    def test_induk_balasan_hanya_menerima_komentar_hidup_di_work_item_sama(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, parent=induk)
        slug, pid, iid = org.ws.slug, org.project.id, org.issue.id
        assert induk_balasan(slug, pid, iid, induk.id).pk == induk.pk
        assert induk_balasan(slug, pid, iid, balasan.id).pk == induk.pk
        assert induk_balasan(slug, pid, iid, None) is None
        assert induk_balasan(slug, pid, uuid4(), induk.id) is None
        assert induk_balasan("slug-lain", pid, iid, induk.id) is None


# ---------------------------------------------------------------------------
# Notifikasi
# ---------------------------------------------------------------------------


def _mention(user):
    return (
        f'<p><mention-component id="{uuid4()}" entity_name="user_mention" '
        f'entity_identifier="{user.id}"></mention-component> setuju</p>'
    )


def _kirim_notifikasi(org, penulis, balasan):
    """Jalankan tugas notifikasi persis seperti `issue_activity` memanggilnya untuk komentar baru."""
    aktivitas = IssueActivity.objects.create(
        issue=org.issue,
        project=org.project,
        workspace=org.ws,
        comment="created a comment",
        verb="created",
        actor=penulis,
        field="comment",
        new_value=balasan.comment_html,
        new_identifier=balasan.id,
        issue_comment=balasan,
        epoch=1,
    )
    muatan = IssueActivitySerializer([aktivitas], many=True).data
    with (
        mock.patch("plane.utils.kartu_obrolan.kirim_kartu_notifikasi"),
        mock.patch("plane.utils.sinyal_data.siarkan_notifikasi_baris"),
    ):
        notifications(
            type="comment.activity.created",
            issue_id=str(org.issue.id),
            project_id=str(org.project.id),
            actor_id=str(penulis.id),
            subscriber=True,
            issue_activities_created=json.dumps(list(muatan), default=str),
            requested_data=json.dumps({"id": str(balasan.id), "comment_html": balasan.comment_html}),
            current_instance=None,
        )


@pytest.mark.contract
class TestNotifikasiBalasan:
    @pytest.fixture(autouse=True)
    def _saklar_tegas(self, org):
        for u in (org.alice, org.bob, org.cici):
            _saklar(u, inbox_comment=True, inbox_mention=True, comment=False, mention=False)

    @pytest.mark.django_db
    def test_penulis_induk_dikabari_walau_bukan_subscriber(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>setuju</p>", parent=induk)
        _kirim_notifikasi(org, org.bob, balasan)
        kabar = Notification.objects.filter(receiver=org.alice)
        assert kabar.count() == 1
        assert kabar.first().triggered_by_id == org.bob.id
        assert kabar.first().data["issue_activity"]["field"] == "comment"
        assert Notification.objects.filter(receiver=org.bob).count() == 0
        assert Notification.objects.filter(receiver=org.cici).count() == 0

    @pytest.mark.django_db
    def test_balas_komentar_sendiri_tidak_dikabari(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.alice, "<p>tambahan</p>", parent=induk)
        _kirim_notifikasi(org, org.alice, balasan)
        assert Notification.objects.filter(receiver=org.alice).count() == 0

    @pytest.mark.django_db
    def test_yang_disebut_dan_dibalas_hanya_dapat_satu_kabar(self, org):
        from plane.db.models import IssueSubscriber

        IssueSubscriber.objects.create(issue=org.issue, project=org.project, workspace=org.ws, subscriber=org.alice)
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, _mention(org.alice), parent=induk)
        _kirim_notifikasi(org, org.bob, balasan)
        kabar = Notification.objects.filter(receiver=org.alice)
        assert kabar.count() == 1
        assert kabar.first().sender == "in_app:issue_activities:mentioned"

    @pytest.mark.django_db
    def test_subscriber_penulis_induk_tidak_dapat_dua_kabar(self, org):
        from plane.db.models import IssueSubscriber

        IssueSubscriber.objects.create(issue=org.issue, project=org.project, workspace=org.ws, subscriber=org.alice)
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>setuju</p>", parent=induk)
        _kirim_notifikasi(org, org.bob, balasan)
        assert Notification.objects.filter(receiver=org.alice).count() == 1

    @pytest.mark.django_db
    def test_sebutan_dimatikan_balasan_tetap_dikabari_sekali(self, org):
        _saklar(org.alice, inbox_comment=True, inbox_mention=False, comment=False, mention=False)
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, _mention(org.alice), parent=induk)
        _kirim_notifikasi(org, org.bob, balasan)
        kabar = Notification.objects.filter(receiver=org.alice)
        assert kabar.count() == 1
        assert kabar.first().sender == "in_app:issue_activities:subscribed"

    @pytest.mark.django_db
    def test_saklar_komentar_mati_tidak_ada_kabar_balasan(self, org):
        _saklar(org.alice, inbox_comment=False, inbox_mention=True, comment=False, mention=False)
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>setuju</p>", parent=induk)
        _kirim_notifikasi(org, org.bob, balasan)
        assert Notification.objects.filter(receiver=org.alice).count() == 0

    @pytest.mark.django_db
    def test_orang_ketiga_yang_disebut_dapat_kabar_sebutan_penulis_induk_kabar_balasan(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, _mention(org.cici), parent=induk)
        _kirim_notifikasi(org, org.bob, balasan)
        assert Notification.objects.filter(receiver=org.alice).count() == 1
        assert Notification.objects.filter(receiver=org.cici).count() == 1
        assert Notification.objects.get(receiver=org.cici).sender == "in_app:issue_activities:mentioned"

    @pytest.mark.django_db
    def test_komentar_tanpa_induk_tidak_membuat_kabar_balasan(self, org):
        biasa = _komentar(org, org.bob, "<p>biasa</p>")
        _kirim_notifikasi(org, org.bob, biasa)
        assert Notification.objects.count() == 0

    @pytest.mark.django_db
    def test_penerima_balasan_hanya_untuk_komentar_baru_dan_anggota_aktif(self, org):
        induk = _komentar(org, org.alice)
        balasan = _komentar(org, org.bob, "<p>r</p>", parent=induk)
        aktivitas = {"field": "comment", "verb": "created", "issue_comment": str(balasan.id), "id": "x"}
        anggota = {str(org.alice.id), str(org.bob.id)}
        assert list(penerima_balasan_komentar([aktivitas], org.issue.id, str(org.bob.id), anggota)) == [
            str(org.alice.id)
        ]
        # menyunting balasan tidak mengabari ulang
        assert penerima_balasan_komentar([{**aktivitas, "verb": "updated"}], org.issue.id, str(org.bob.id), anggota) == {}  # noqa: E501
        # penulis induk yang sudah keluar dari project tidak dikabari
        assert penerima_balasan_komentar([aktivitas], org.issue.id, str(org.bob.id), {str(org.bob.id)}) == {}
        # induk tanpa penulis (komentar sistem/impor)
        IssueComment.objects.filter(pk=induk.pk).update(actor=None, created_by=None)
        assert penerima_balasan_komentar([aktivitas], org.issue.id, str(org.bob.id), anggota) == {}
