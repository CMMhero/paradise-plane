# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: program 2.9, obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Ruang kabar "Paradise" dihapus, kartu berisi teks bukan HTML, dan penulis
serta email kanal Announcements."""

import importlib
from uuid import uuid4

import pytest
from django.apps import apps as django_apps
from django.core import mail
from rest_framework.test import APIClient

from plane.bgtasks.pengumuman_email_task import kirim_email_pengumuman
from plane.db.models import (
    KUNCI_PENGUMUMAN,
    Departemen,
    Divisi,
    FileAsset,
    Issue,
    JabatanOrganisasi,
    JenisPesan,
    Langganan,
    Notification,
    PesanLangsung,
    Project,
    ReaksiPesan,
    Ruang,
    State,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.db.models.hierarki import TINGKAT_MEMBER
from plane.utils.kanal_sistem import ikutkan_ke_kanal_sistem
from plane.utils.kartu_obrolan import kirim_kartu_notifikasi
from plane.utils.teks_html import teks_polos

hapus_ruang_kabar = importlib.import_module("plane.db.migrations.0181_hapus_ruang_kabar").hapus_ruang_kabar


def _orang(nama):
    return User.objects.create(id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama.capitalize())


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


def _sebut(user):
    return (
        f'<mention-component id="{uuid4()}" entity_name="user_mention" '
        f'entity_identifier="{user.id}"></mention-component>'
    )


@pytest.fixture
def kantor(db):
    admin = _orang("admin")
    ws = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kantor-p29", owner=admin)
    hr, staf, tolak = _orang("hrd"), _orang("staf"), _orang("tolak")
    WorkspaceMember.objects.create(workspace=ws, member=admin, role=20)
    for u in (hr, staf, tolak):
        WorkspaceMember.objects.create(workspace=ws, member=u, role=15)
    hrga = Divisi.objects.create(workspace=ws, kode="HRGA", nama="HRGA")
    dept_hr = Departemen.objects.create(workspace=ws, divisi=hrga, kode="HR", nama="Human Resources")
    dept_ga = Departemen.objects.create(workspace=ws, divisi=hrga, kode="GA", nama="General Affairs")
    JabatanOrganisasi.objects.create(workspace=ws, member=hr, tingkat=TINGKAT_MEMBER, departemen=dept_hr)
    JabatanOrganisasi.objects.create(workspace=ws, member=staf, tingkat=TINGKAT_MEMBER, departemen=dept_ga)
    # Mematikan sendiri email pengumumannya dari Profil > Notifikasi.
    assert (
        _klien(tolak)
        .patch("/api/users/me/notification-preferences/", {"pengumuman": False}, format="json")
        .data["pengumuman"]
        is False
    )
    ikutkan_ke_kanal_sistem(ws.id)
    pengumuman = Ruang.objects.get(workspace=ws, kunci_sistem=KUNCI_PENGUMUMAN)
    return {
        "ws": ws,
        "admin": admin,
        "hr": hr,
        "staf": staf,
        "tolak": tolak,
        "dept_hr": dept_hr,
        "pengumuman": pengumuman,
    }


@pytest.fixture
def antrean(monkeypatch):
    """Id pesan yang diantrekan ke tugas email, tanpa broker."""
    masuk = []
    monkeypatch.setattr("plane.app.views.chat.kirim_email_pengumuman.delay", masuk.append)
    monkeypatch.setattr("plane.bgtasks.pengumuman_email_task.email_aktif", lambda host: True)
    return masuk


def _url(k, akhir=""):
    return f"/api/workspaces/{k['ws'].slug}/chat/ruang/{k['pengumuman'].id}/{akhir}"


@pytest.mark.contract
class TestPenulisPengumuman:
    @pytest.mark.django_db
    def test_staf_tanpa_izin_ditolak(self, kantor, antrean):
        jawab = _klien(kantor["staf"]).post(_url(kantor), {"isi": "halo"}, format="json")
        assert jawab.status_code == 403
        assert antrean == []

    @pytest.mark.django_db
    def test_departemen_diizinkan_menulis_dan_email_ke_semua_kecuali_penulis(self, kantor, antrean):
        k = kantor
        jawab = _klien(k["admin"]).post(_url(k, "penulis/"), {"departemen_id": str(k["dept_hr"].id)}, format="json")
        assert jawab.status_code == 201
        assert jawab.json()["departemen"]["nama"] == "Human Resources"

        daftar = _klien(k["hr"]).get(f"/api/workspaces/{k['ws'].slug}/chat/").json()
        assert next(r for r in daftar if r["kunci_sistem"] == KUNCI_PENGUMUMAN)["boleh_kirim"] is True

        kirim = _klien(k["hr"]).post(
            _url(k), {"isi": "Besok libur.\nKantor tutup <jam 12> & buka lusa."}, format="json"
        )
        assert kirim.status_code == 201
        assert antrean == [kirim.json()["id"]]

        mail.outbox.clear()
        hasil = kirim_email_pengumuman(antrean[0])
        assert hasil == {"terkirim": 2, "gagal": 0}
        penerima = sorted(m.to[0] for m in mail.outbox)
        # Penulis tidak menerima salinan; yang mematikan saklar `pengumuman` dilewati.
        assert penerima == [k["admin"].email, k["staf"].email]
        surat = mail.outbox[0]
        assert "Hrd" in surat.subject
        assert "Kantor tutup <jam 12> & buka lusa." in surat.body
        html = surat.alternatives[0][0]
        assert "&lt;jam 12&gt; &amp; buka lusa." in html
        assert f"chat?ruang={k['pengumuman'].id}" in html

    @pytest.mark.django_db
    def test_suntingan_tidak_mengirim_ulang(self, kantor, antrean):
        k = kantor
        kirim = _klien(k["admin"]).post(_url(k), {"isi": "Rapat jam 9"}, format="json")
        assert kirim.status_code == 201
        sunting = _klien(k["admin"]).patch(
            f"/api/workspaces/{k['ws'].slug}/chat/pesan/{kirim.json()['id']}/", {"isi": "Rapat jam 10"}, format="json"
        )
        assert sunting.status_code == 200
        assert len(antrean) == 1

    @pytest.mark.django_db
    def test_izin_dicabut_menulis_ditolak_lagi(self, kantor, antrean):
        k = kantor
        izin = _klien(k["admin"]).post(_url(k, "penulis/"), {"departemen_id": str(k["dept_hr"].id)}, format="json")
        assert (
            _klien(k["admin"])
            .post(_url(k, "penulis/"), {"departemen_id": str(k["dept_hr"].id)}, format="json")
            .status_code
            == 200
        )
        assert _klien(k["admin"]).get(_url(k, "penulis/")).json()["penulis"] == [izin.json()]

        assert _klien(k["admin"]).delete(_url(k, f"penulis/{izin.json()['id']}/")).status_code == 204
        assert _klien(k["admin"]).get(_url(k, "penulis/")).json()["penulis"] == []
        assert _klien(k["hr"]).post(_url(k), {"isi": "halo"}, format="json").status_code == 403

    @pytest.mark.django_db
    def test_izin_per_orang(self, kantor, antrean):
        k = kantor
        jawab = _klien(k["admin"]).post(_url(k, "penulis/"), {"user_id": str(k["staf"].id)}, format="json")
        assert jawab.status_code == 201 and jawab.json()["user"] == str(k["staf"].id)
        assert _klien(k["staf"]).post(_url(k), {"isi": "halo"}, format="json").status_code == 201
        assert _klien(k["hr"]).post(_url(k), {"isi": "halo"}, format="json").status_code == 403

    @pytest.mark.django_db
    def test_hanya_admin_yang_mengatur_dan_hanya_di_announcements(self, kantor):
        k = kantor
        assert _klien(k["staf"]).get(_url(k, "penulis/")).status_code == 403
        assert (
            _klien(k["hr"])
            .post(_url(k, "penulis/"), {"departemen_id": str(k["dept_hr"].id)}, format="json")
            .status_code
            == 403
        )
        biasa = _klien(k["admin"]).post(
            f"/api/workspaces/{k['ws'].slug}/chat/ruang/", {"nama": "umum", "tipe": "kanal"}, format="json"
        )
        url_biasa = f"/api/workspaces/{k['ws'].slug}/chat/ruang/{biasa.json()['id']}/penulis/"
        assert _klien(k["admin"]).get(url_biasa).status_code == 404
        assert (
            _klien(k["admin"]).post(_url(k, "penulis/"), {"departemen_id": "rusak"}, format="json").status_code == 400
        )
        assert _klien(k["admin"]).get(_url(k, "penulis/")).json()["departemen"][0]["divisi"] == "HRGA"


@pytest.fixture
def tugas(kantor):
    k = kantor
    project = Project.objects.create(name="Gudang", identifier="GDG", workspace=k["ws"])
    state = State.objects.create(name="Todo", project=project, workspace=k["ws"], group="unstarted")
    issue = Issue.objects.create(name="Hitung stok", project=project, workspace=k["ws"], state=state)
    return {**k, "project": project, "issue": issue}


def _notif(t, pemicu, penerima, aktivitas, sender="in_app:issue_activities:subscribed"):
    return Notification.objects.create(
        workspace=t["ws"],
        project=t["project"],
        sender=sender,
        triggered_by=pemicu,
        receiver=penerima,
        entity_identifier=t["issue"].id,
        entity_name="issue",
        data={"issue_activity": aktivitas},
    )


@pytest.mark.contract
class TestKartuTanpaRuangKabar:
    @pytest.mark.django_db
    def test_komentar_html_jadi_teks_dengan_sebutan(self, tugas):
        t = tugas
        html = (
            f'<p class="editor-paragraph-block" data-id="b42b">Pagi mas {_sebut(t["staf"])}</p>'
            "<p>Cek &amp; balas ya&nbsp;&lt;segera&gt;</p>"
        )
        notif = _notif(t, t["admin"], t["staf"], {"field": "comment", "new_value": html, "old_value": ""})
        assert kirim_kartu_notifikasi([notif]) == 1
        kartu = PesanLangsung.objects.get(jenis=JenisPesan.KOMENTAR)
        assert kartu.muatan["detail"]["komentar"] == "Pagi mas @Staf\nCek & balas ya <segera>"
        assert kartu.ruang.tipe == Ruang.Tipe.DM
        assert not Ruang.objects.filter(kunci_sistem__startswith="kabar:").exists()

    @pytest.mark.django_db
    def test_deskripsi_jadi_teks(self, tugas):
        t = tugas
        notif = _notif(
            t,
            t["admin"],
            t["staf"],
            {"field": "description", "old_value": "<p>lama</p>", "new_value": "<ul><li>satu</li><li>dua</li></ul>"},
        )
        assert kirim_kartu_notifikasi([notif]) == 1
        detail = PesanLangsung.objects.get(jenis=JenisPesan.PEMBARUAN).muatan["detail"]
        assert (detail["lama"], detail["baru"]) == ("lama", "satu\ndua")

    @pytest.mark.django_db
    def test_aksi_sendiri_dan_tanpa_pelaku_tidak_jadi_kartu(self, tugas):
        t = tugas
        notifs = [
            _notif(t, t["staf"], t["staf"], {"field": "comment", "new_value": "<p>x</p>"}),
            _notif(t, None, t["staf"], {"field": "state", "new_value": "Done"}),
        ]
        assert kirim_kartu_notifikasi(notifs) == 0
        assert not PesanLangsung.objects.exists()
        assert not Ruang.objects.filter(kunci_sistem__startswith="kabar:").exists()

    def test_teks_polos_tanpa_tag(self):
        assert teks_polos("<p>a<br>b</p><p></p><h2>c &gt; d</h2>") == "a\nb\nc > d"
        assert teks_polos(None) == ""


@pytest.mark.contract
class TestMigrasiHapusRuangKabar:
    @pytest.mark.django_db
    def test_ruang_kabar_dan_isinya_terhapus_ruang_lain_tetap(self, kantor):
        k = kantor
        ws, staf, hr = k["ws"], k["staf"], k["hr"]
        kabar = [
            Ruang.objects.create(
                workspace=ws, tipe=Ruang.Tipe.PRIVAT, nama="Paradise", sistem=True, kunci_sistem=f"kabar:{u.id}"
            )
            for u in (staf, hr)
        ]
        Langganan.objects.create(ruang=kabar[0], user=staf)
        kartu = PesanLangsung.objects.create(workspace=ws, ruang=kabar[0], isi="kartu", jenis=JenisPesan.KOMENTAR)
        ReaksiPesan.objects.create(pesan=kartu, user=staf, emoji="👍")
        FileAsset.objects.create(
            workspace=ws,
            asset="x/lampiran.png",
            entity_type=FileAsset.EntityTypeContext.CHAT_ATTACHMENT,
            entity_identifier=str(kartu.id),
        )
        # Sisa yang sudah dihapus lunak ikut hilang.
        PesanLangsung.objects.create(workspace=ws, ruang=kabar[1], isi="lama").delete()

        umum = PesanLangsung.objects.create(workspace=ws, ruang=k["pengumuman"], pengirim=k["admin"], isi="halo")
        ReaksiPesan.objects.create(pesan=umum, user=staf, emoji="👍")

        hapus_ruang_kabar(django_apps, None)
        hapus_ruang_kabar(django_apps, None)

        assert not Ruang.all_objects.filter(kunci_sistem__startswith="kabar:").exists()
        assert not PesanLangsung.all_objects.filter(ruang_id__in=[r.id for r in kabar]).exists()
        assert not Langganan.all_objects.filter(ruang_id__in=[r.id for r in kabar]).exists()
        assert not ReaksiPesan.all_objects.filter(pesan_id=kartu.id).exists()
        assert not FileAsset.all_objects.filter(entity_identifier=str(kartu.id)).exists()
        assert PesanLangsung.objects.filter(id=umum.id).exists()
        assert ReaksiPesan.objects.filter(pesan=umum).count() == 1
        assert Langganan.objects.filter(ruang=k["pengumuman"]).count() == 4
