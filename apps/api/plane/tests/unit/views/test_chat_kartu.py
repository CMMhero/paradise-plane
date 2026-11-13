# Kustomisasi Paradise Task Tracker: kanal sistem, changelog, dan kartu obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Kanal sistem (Announcements, Changelog), catatan rilis, log panggilan, kartu kabar.

ORM langsung, tanpa factory_boy (tidak ada di image runtime).
"""

import json
from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.db.models import (
    KUNCI_CHANGELOG,
    KUNCI_PENGUMUMAN,
    Issue,
    JenisPesan,
    Langganan,
    Notification,
    PesanLangsung,
    Project,
    Ruang,
    State,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils import catatan_rilis
from plane.utils.kanal_sistem import ikutkan_ke_kanal_sistem, kirim_pesan_sistem, pastikan_kanal_sistem
from plane.utils.kartu_obrolan import kirim_kartu_notifikasi, tandai_persetujuan_diputuskan


def _orang(nama, is_active=True):
    return User.objects.create(
        id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama, is_active=is_active
    )


@pytest.fixture
def kantor(db):
    admin = _orang("admin")
    workspace = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kantor-kartu", owner=admin)
    staf = _orang("staf")
    nonaktif = _orang("pergi", is_active=False)
    terhapus = User.objects.create(
        id=uuid4(), username="hapus", email="terhapus-x@deleted.local", display_name="x", is_active=True
    )
    WorkspaceMember.objects.create(workspace=workspace, member=admin, role=20)
    WorkspaceMember.objects.create(workspace=workspace, member=staf, role=15)
    WorkspaceMember.objects.create(workspace=workspace, member=nonaktif, role=15)
    WorkspaceMember.objects.create(workspace=workspace, member=terhapus, role=15)
    return workspace, admin, staf, nonaktif, terhapus


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


def _kanal(workspace, kunci):
    return Ruang.objects.get(workspace=workspace, kunci_sistem=kunci)


@pytest.mark.unit
class TestKanalSistem:
    @pytest.mark.django_db
    def test_anggota_layak_ikut_dan_idempoten(self, kantor):
        workspace, admin, staf, nonaktif, terhapus = kantor
        assert ikutkan_ke_kanal_sistem(workspace.id) == 4  # 2 orang x 2 kanal
        assert ikutkan_ke_kanal_sistem(workspace.id) == 0
        for kunci in (KUNCI_PENGUMUMAN, KUNCI_CHANGELOG):
            ruang = _kanal(workspace, kunci)
            assert ruang.sistem
            anggota = set(Langganan.objects.filter(ruang=ruang).values_list("user_id", flat=True))
            # Akun nonaktif dan akun terhapus (KEP-50) tidak ikut.
            assert anggota == {admin.id, staf.id}
        assert Ruang.objects.filter(workspace=workspace, sistem=True).count() == 2

    @pytest.mark.django_db
    def test_daftar_percakapan_mengikutkan_secara_malas(self, kantor):
        workspace, _admin, staf, *_ = kantor
        hasil = _klien(staf).get(f"/api/workspaces/{workspace.slug}/chat/").json()
        sistem = {r["kunci_sistem"] for r in hasil if r["sistem"]}
        assert sistem == {KUNCI_PENGUMUMAN, KUNCI_CHANGELOG}
        # Langganan baru lahir terbaca.
        assert all(r["belum_dibaca"] == 0 for r in hasil)

    @pytest.mark.django_db
    def test_kanal_sistem_tidak_bisa_ditinggalkan(self, kantor):
        workspace, _admin, staf, *_ = kantor
        ikutkan_ke_kanal_sistem(workspace.id)
        ruang = _kanal(workspace, KUNCI_PENGUMUMAN)
        jawab = _klien(staf).delete(f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang.id}/gabung/")
        assert jawab.status_code == 400
        assert Langganan.objects.filter(ruang=ruang, user=staf).exists()

    @pytest.mark.django_db
    def test_pengumuman_hanya_admin_changelog_tidak_siapa_pun(self, kantor):
        workspace, admin, staf, *_ = kantor
        ikutkan_ke_kanal_sistem(workspace.id)
        pengumuman = _kanal(workspace, KUNCI_PENGUMUMAN)
        changelog = _kanal(workspace, KUNCI_CHANGELOG)
        url = f"/api/workspaces/{workspace.slug}/chat/ruang/%s/"

        assert _klien(staf).post(url % pengumuman.id, {"isi": "halo"}, format="json").status_code == 403
        assert _klien(admin).post(url % pengumuman.id, {"isi": "Libur besok"}, format="json").status_code == 201
        assert _klien(admin).post(url % changelog.id, {"isi": "x"}, format="json").status_code == 403

        # Semua orang boleh bereaksi pada pengumuman (kanal tanpa penerima).
        pesan = PesanLangsung.objects.get(ruang=pengumuman)
        reaksi = _klien(staf).post(
            f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/reaksi/", {"emoji": "👍"}, format="json"
        )
        assert reaksi.status_code == 201

        daftar = _klien(staf).get(f"/api/workspaces/{workspace.slug}/chat/").json()
        hak = {r["kunci_sistem"]: r["boleh_kirim"] for r in daftar if r["sistem"]}
        assert hak == {KUNCI_PENGUMUMAN: False, KUNCI_CHANGELOG: False}
        daftar_admin = _klien(admin).get(f"/api/workspaces/{workspace.slug}/chat/").json()
        assert {r["kunci_sistem"]: r["boleh_kirim"] for r in daftar_admin if r["sistem"]}[KUNCI_PENGUMUMAN]


@pytest.mark.unit
class TestChangelog:
    def _tulis(self, folder, versi, entri):
        (folder / f"{versi}.json").write_text(
            json.dumps({"version": versi, "date": "2026-11-03", "entries": entri}), encoding="utf-8"
        )

    @pytest.mark.django_db
    def test_terbit_sekali_dan_tidak_mendahului_versi(self, kantor, tmp_path):
        workspace, *_ = kantor
        self._tulis(tmp_path, "2.2.0", [{"type": "Added", "text": "A"}, {"type": "Fixed", "text": "B"}])
        self._tulis(tmp_path, "2.3.0", [{"type": "Added", "text": "masa depan"}])
        self._tulis(tmp_path, "2.1.0", [{"type": "Bogus", "text": "dibuang"}])
        (tmp_path / "rusak.json").write_text("{bukan json", encoding="utf-8")

        assert catatan_rilis.terbitkan("2.2.0", folder=tmp_path) == 1
        assert catatan_rilis.terbitkan("2.2.0", folder=tmp_path) == 0

        pesan = PesanLangsung.objects.get(ruang=_kanal(workspace, KUNCI_CHANGELOG))
        assert pesan.jenis == JenisPesan.CHANGELOG
        assert pesan.pengirim_id is None
        assert pesan.muatan["versi"] == "2.2.0"
        assert [e["type"] for e in pesan.muatan["entri"]] == ["Added", "Fixed"]

        # Versi berjalan naik: hanya 2.3.0 yang menyusul.
        assert catatan_rilis.terbitkan("2.3.0", folder=tmp_path) == 1

    @pytest.mark.django_db
    def test_rilis_lama_yang_menyusul_diberi_tanggal_rilisnya(self, kantor, tmp_path):
        workspace, *_ = kantor
        self._tulis(tmp_path, "2.2.0", [{"type": "Added", "text": "kini"}])
        assert catatan_rilis.terbitkan("2.2.0", folder=tmp_path) == 1

        (tmp_path / "2.0.0.json").write_text(
            json.dumps({"version": "2.0.0", "date": "2026-10-30", "entries": [{"type": "Added", "text": "lama"}]}),
            encoding="utf-8",
        )
        assert catatan_rilis.terbitkan("2.2.0", folder=tmp_path) == 1

        urut = list(
            PesanLangsung.objects.filter(ruang=_kanal(workspace, KUNCI_CHANGELOG))
            .order_by("created_at")
            .values_list("muatan__versi", flat=True)
        )
        assert urut == ["2.0.0", "2.2.0"]

    @pytest.mark.django_db
    def test_catatan_yang_dikoreksi_menyusul_ke_kartu_yang_sudah_terbit(self, kantor, tmp_path):
        workspace, *_ = kantor
        tulis = lambda versi, tanggal, teks: (tmp_path / f"{versi}.json").write_text(  # noqa: E731
            json.dumps({"version": versi, "date": tanggal, "entries": [{"type": "Added", "text": teks}]}),
            encoding="utf-8",
        )
        tulis("5.0.0", "2026-11-05", "salah tanggal")
        tulis("5.1.0", "2026-11-05", "kini")
        assert catatan_rilis.terbitkan("5.1.0", folder=tmp_path) == 2

        tulis("5.0.0", "2026-11-04", "tanggal benar")
        assert catatan_rilis.terbitkan("5.1.0", folder=tmp_path) == 0  # tidak ada kartu baru

        kanal = _kanal(workspace, KUNCI_CHANGELOG)
        pesan = PesanLangsung.objects.get(ruang=kanal, muatan__versi="5.0.0")
        assert pesan.muatan["tanggal"] == "2026-11-04"
        assert pesan.muatan["entri"] == [{"type": "Added", "text": "tanggal benar"}]
        assert "2026-11-04" in pesan.isi
        assert timezone.localtime(pesan.created_at).date().isoformat() == "2026-11-04"
        assert PesanLangsung.objects.filter(ruang=kanal).count() == 2

    @pytest.mark.django_db
    def test_kartu_bernomor_lama_dinomori_ulang_tanpa_kartu_ganda(self, kantor, tmp_path):
        workspace, *_ = kantor
        kanal = _kanal(workspace, KUNCI_CHANGELOG)
        # Keadaan produksi sebelum skema versi dibenahi: kartu terbit dengan nomor lama.
        kirim_pesan_sistem(
            kanal,
            JenisPesan.CHANGELOG,
            {"versi": "4.2.0", "tanggal": "2026-11-12", "entri": [{"type": "Added", "text": "lama"}]},
            "Paradise 4.2.0",
        )
        (tmp_path / "2.6.0.json").write_text(
            json.dumps({"version": "2.6.0", "date": "2026-11-12", "entries": [{"type": "Added", "text": "kini"}]}),
            encoding="utf-8",
        )

        assert catatan_rilis.terbitkan("2.6.0", folder=tmp_path) == 0  # dinomori ulang, bukan kartu baru
        assert catatan_rilis.terbitkan("2.6.0", folder=tmp_path) == 0

        pesan = PesanLangsung.objects.get(ruang=kanal)
        assert pesan.muatan["versi"] == "2.6.0"
        assert pesan.muatan["entri"] == [{"type": "Added", "text": "kini"}]
        assert "2.6.0" in pesan.isi and "4.2.0" not in pesan.isi

    def test_tanggal_catatan_sama_dengan_changelog(self):
        """Tanggal JSON = tanggal rilis di CHANGELOG.md, bukan tanggal ditulis."""
        from pathlib import Path

        changelog = Path(catatan_rilis.FOLDER_CATATAN).parents[3] / "CHANGELOG.md"
        if not changelog.exists():
            pytest.skip("CHANGELOG.md tidak ada (image API)")
        tanggal_rilis, tanggal = {}, None
        for baris in changelog.read_text(encoding="utf-8").splitlines():
            if baris.startswith("## 20"):
                tanggal = baris[3:].strip()
            elif baris.startswith("### Versi ") and tanggal:
                tanggal_rilis.setdefault(baris[len("### Versi ") :].strip(), tanggal)
        salah = {
            c["versi"]: (c["tanggal"], tanggal_rilis[c["versi"]])
            for c in catatan_rilis.baca_catatan()
            if c["versi"] in tanggal_rilis and c["tanggal"] != tanggal_rilis[c["versi"]]
        }
        assert salah == {}

    def test_berkas_bawaan_sah(self):
        catatan = catatan_rilis.baca_catatan()
        assert {"1.5.0", "1.6.0", "2.0.0", "2.1.0", "2.2.0"} <= {c["versi"] for c in catatan}
        assert catatan_rilis.versi_berjalan()


@pytest.fixture
def tugas(kantor):
    workspace, admin, staf, *_ = kantor
    project = Project.objects.create(name="Gudang", identifier="GDG", workspace=workspace)
    state = State.objects.create(name="Todo", project=project, workspace=workspace, group="unstarted")
    issue = Issue.objects.create(name="Hitung stok", project=project, workspace=workspace, state=state)
    return workspace, admin, staf, project, issue


def _notif(workspace, project, issue, pemicu, penerima, field, sender="in_app:issue_activities:subscribed", **akt):
    return Notification.objects.create(
        workspace=workspace,
        project=project,
        sender=sender,
        triggered_by=pemicu,
        receiver=penerima,
        entity_identifier=issue.id,
        entity_name="issue",
        data={"issue_activity": {"field": field, "new_value": "Beres", "old_value": "", **akt}},
    )


@pytest.mark.unit
class TestKartuKabar:
    @pytest.mark.django_db
    def test_kartu_dengan_pelaku_masuk_dm_pelaku_dan_penerima(self, tugas):
        # KEP-90: pelaku = pengirim, orang yang terdampak = penerima, satu DM per orang.
        workspace, admin, staf, project, issue = tugas
        kedua = _orang("kedua")
        WorkspaceMember.objects.create(workspace=workspace, member=kedua, role=15)
        notifs = [
            _notif(workspace, project, issue, admin, staf, "comment"),
            _notif(workspace, project, issue, admin, kedua, "comment"),
            _notif(workspace, project, issue, staf, admin, "approval", verb="submitted"),
        ]
        assert kirim_kartu_notifikasi(notifs) == 3

        assert not Ruang.objects.filter(kunci_sistem__startswith="kabar:").exists()
        for pelaku, penerima, jenis in (
            (admin, staf, JenisPesan.KOMENTAR),
            (admin, kedua, JenisPesan.KOMENTAR),
            (staf, admin, JenisPesan.PERSETUJUAN),
        ):
            ruang = Ruang.objects.get(kunci_dm=Ruang.buat_kunci_dm(pelaku.id, penerima.id))
            kartu = PesanLangsung.objects.filter(ruang=ruang, jenis=jenis).get()
            assert (kartu.pengirim_id, kartu.penerima_id) == (pelaku.id, penerima.id)
        # Kedua arah berbagi satu DM: komentar admin keluar, pengajuan staf masuk.
        dm = Ruang.objects.get(kunci_dm=Ruang.buat_kunci_dm(admin.id, staf.id))
        dibaca = _klien(admin).get(f"/api/workspaces/{workspace.slug}/chat/ruang/{dm.id}/").json()
        assert {(p["jenis"], p["pengirim"]) for p in dibaca} == {
            (JenisPesan.KOMENTAR, str(admin.id)),
            (JenisPesan.PERSETUJUAN, str(staf.id)),
        }

    @pytest.mark.django_db
    def test_saklar_mati_semua_kartu_kembali_ke_ruang_kabar(self, tugas, monkeypatch):
        workspace, admin, staf, project, issue = tugas
        monkeypatch.setattr("plane.utils.kartu_obrolan._tugas_ke_dm_aktif", lambda: False)
        assert kirim_kartu_notifikasi([_notif(workspace, project, issue, admin, staf, "comment")]) == 1
        assert Ruang.objects.filter(kunci_sistem=f"kabar:{staf.id}").exists()
        assert not Ruang.objects.filter(tipe=Ruang.Tipe.DM).exists()

    @pytest.mark.django_db
    def test_kartu_tanpa_pelaku_manusia_masuk_ruang_kabar_pribadi(self, tugas):
        workspace, admin, staf, project, issue = tugas
        bot = User.objects.create(
            id=uuid4(), username="bot-impor", email="bot-impor@x.test", display_name="Bot", is_bot=True
        )
        notifs = [
            _notif(workspace, project, issue, None, staf, "comment"),
            _notif(workspace, project, issue, bot, staf, "state"),
            _notif(workspace, project, issue, None, staf, "description", sender="in_app:issue_activities:mentioned"),
        ]
        assert kirim_kartu_notifikasi(notifs) == 3
        assert not Ruang.objects.filter(tipe=Ruang.Tipe.DM).exists()

        ruang = Ruang.objects.get(workspace=workspace, kunci_sistem=f"kabar:{staf.id}")
        assert ruang.tipe == Ruang.Tipe.PRIVAT and ruang.sistem
        assert list(Langganan.objects.filter(ruang=ruang).values_list("user_id", flat=True)) == [staf.id]
        jenis = sorted(PesanLangsung.objects.filter(ruang=ruang).values_list("jenis", flat=True))
        assert jenis == sorted([JenisPesan.KOMENTAR, JenisPesan.PEMBARUAN, JenisPesan.MENTION])
        kartu = PesanLangsung.objects.filter(ruang=ruang).first()
        assert kartu.pengirim_id is None
        assert kartu.muatan["tugas"]["nomor"] == f"GDG-{issue.sequence_id}"
        assert kartu.muatan["workspace_slug"] == workspace.slug
        assert kartu.muatan["penerima"] == str(staf.id)

        # Orang lain tidak bisa membaca ruang kabar staf.
        jawab = _klien(admin).get(f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang.id}/")
        assert jawab.status_code == 404
        dibaca = _klien(staf).get(f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang.id}/").json()
        assert {p["jenis"] for p in dibaca} == set(jenis)
        assert all(p["pengirim"] is None for p in dibaca)

    @pytest.mark.django_db
    def test_kartu_persetujuan_kehilangan_tombol_sesudah_diputuskan(self, tugas):
        workspace, admin, staf, project, issue = tugas
        pid = uuid4()
        notif = _notif(workspace, project, issue, staf, admin, "approval", verb="submitted")
        kirim_kartu_notifikasi([notif], persetujuan={"id": pid, "project_id": project.id, "status": "menunggu"})
        kartu = PesanLangsung.objects.get(jenis=JenisPesan.PERSETUJUAN)
        assert kartu.muatan["persetujuan"]["status"] == "menunggu"
        assert tandai_persetujuan_diputuskan(pid, "disetujui") == 1
        kartu.refresh_from_db()
        assert kartu.muatan["persetujuan"]["status"] == "disetujui"

    @pytest.mark.django_db
    def test_kartu_tidak_bisa_disunting(self, tugas):
        workspace, admin, staf, project, issue = tugas
        ikutkan_ke_kanal_sistem(workspace.id)
        pastikan_kanal_sistem(workspace.id)
        kirim_kartu_notifikasi([_notif(workspace, project, issue, admin, staf, "comment")])
        kartu = PesanLangsung.objects.get(jenis=JenisPesan.KOMENTAR)
        # Kartu di DM berpengirim pelaku (KEP-90), tapi pelakunya pun tidak bisa menyuntingnya.
        for orang in (staf, admin):
            jawab = _klien(orang).patch(
                f"/api/workspaces/{workspace.slug}/chat/pesan/{kartu.id}/", {"isi": "x"}, format="json"
            )
            assert jawab.status_code == 404


@pytest.mark.unit
class TestLogPanggilan:
    @pytest.mark.django_db
    def test_tak_terjawab_lalu_selesai_dengan_durasi(self, kantor):
        workspace, admin, staf, *_ = kantor
        url = f"/api/workspaces/{workspace.slug}/chat/{staf.id}/"
        _klien(admin).post(url, {"isi": "halo"}, format="json")
        ruang = Ruang.objects.get(kunci_dm=Ruang.buat_kunci_dm(admin.id, staf.id))
        log = f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang.id}/panggilan-log/"

        # Tidak diangkat.
        assert _klien(admin).post(log, {"peristiwa": "mulai", "video": True}, format="json").status_code == 201
        assert _klien(admin).post(log, {"peristiwa": "selesai"}, format="json").status_code == 200
        pertama = PesanLangsung.objects.filter(jenis=JenisPesan.PANGGILAN).order_by("created_at").first()
        assert pertama.muatan["status"] == "tak_terjawab"
        assert pertama.penerima_id == staf.id

        # Diangkat: tersambung dilaporkan pihak penerima, selesai pihak penelepon.
        _klien(admin).post(log, {"peristiwa": "mulai"}, format="json")
        _klien(staf).post(log, {"peristiwa": "tersambung"}, format="json")
        kedua = PesanLangsung.objects.filter(jenis=JenisPesan.PANGGILAN).order_by("-created_at").first()
        mundur = (timezone.now() - timedelta(seconds=75)).isoformat()
        kedua.muatan = {**kedua.muatan, "tersambung_pada": mundur}
        kedua.save()
        _klien(admin).post(log, {"peristiwa": "selesai"}, format="json")
        # Laporan kedua dari pihak lain tidak mengubah apa pun.
        assert _klien(staf).post(log, {"peristiwa": "selesai"}, format="json").json() == {"id": None}
        kedua.refresh_from_db()
        assert kedua.muatan["status"] == "selesai"
        assert 74 <= kedua.muatan["durasi"] <= 80
        assert kedua.isi.startswith("Voice call (1:1")

    @pytest.mark.django_db
    def test_bukan_anggota_ruang_ditolak(self, kantor):
        workspace, admin, staf, *_ = kantor
        ruang = Ruang.objects.create(workspace=workspace, tipe=Ruang.Tipe.PRIVAT, nama="rahasia")
        Langganan.objects.create(ruang=ruang, user=admin)
        log = f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang.id}/panggilan-log/"
        assert _klien(staf).post(log, {"peristiwa": "mulai"}, format="json").status_code == 404


@pytest.mark.unit
class TestKartuTugasLama:
    """DM penugasan teks dari sebelum 2.2.0 diubah jadi kartu (migrasi 0161)."""

    def _teks_lama(self, workspace, admin, staf, isi):
        from plane.utils.chat_ruang import ruang_dm  # noqa: PLC0415

        return PesanLangsung.objects.create(
            workspace=workspace, ruang=ruang_dm(workspace.id, admin.id, staf.id), pengirim=admin, penerima=staf, isi=isi
        )

    def test_baca_rujukan_tautan_dan_kode(self):
        from plane.utils.kartu_tugas_lama import baca_rujukan  # noqa: PLC0415

        iid = str(uuid4())
        isi = f"📋 Tugas baru untuk Anda\n\nGDG-7 · Hitung\n\nhttps://x/kantor/projects/p/issues/{iid}"
        assert baca_rujukan(isi) == (iid, ("GDG", 7))
        assert baca_rujukan("📋 Tugas baru untuk Anda\n\nGDG-7 · Hitung") == (None, ("GDG", 7))
        assert baca_rujukan("halo") == (None, None)

    @pytest.mark.django_db
    def test_teks_lama_jadi_kartu_dan_bisa_dibalik(self, tugas):
        from plane.db.models import IssueAssignee  # noqa: PLC0415
        from plane.utils.kartu_tugas_lama import kembalikan_ke_teks, ubah_ke_kartu  # noqa: PLC0415

        workspace, admin, staf, project, issue = tugas
        IssueAssignee.objects.create(issue=issue, assignee=staf, project=project, workspace=workspace)
        nomor = f"GDG-{issue.sequence_id}"
        lewat_tautan = self._teks_lama(
            workspace,
            admin,
            staf,
            f"📋 Tugas baru untuk Anda\n\n{nomor} · Hitung stok\n\nhttps://h/kantor-kartu/projects/{project.id}/issues/{issue.id}",
        )
        lewat_kode = self._teks_lama(workspace, admin, staf, f"📋 Tugas baru untuk Anda\n\n{nomor} · Hitung stok")
        yatim = self._teks_lama(workspace, admin, staf, "📋 Tugas baru untuk Anda\n\nGDG-999 · Hilang")
        biasa = self._teks_lama(workspace, admin, staf, "Tolong cek GDG-1")

        assert ubah_ke_kartu(PesanLangsung, Issue, IssueAssignee) == 2
        for p in (lewat_tautan, lewat_kode):
            p.refresh_from_db()
            assert p.jenis == JenisPesan.TUGAS
            assert p.muatan["tugas"]["id"] == str(issue.id)
            assert p.muatan["tugas"]["assignees"] == [str(staf.id)]
            assert p.muatan["aktor"] == str(admin.id)
            assert p.muatan["workspace_slug"] == workspace.slug
            assert p.isi.startswith("📋")  # teks cadangan tidak disentuh
        for p in (yatim, biasa):
            p.refresh_from_db()
            assert p.jenis == JenisPesan.TEKS

        # Idempoten: putaran kedua tidak menemukan apa-apa.
        assert ubah_ke_kartu(PesanLangsung, Issue, IssueAssignee) == 0

        assert kembalikan_ke_teks(PesanLangsung) == 2
        lewat_kode.refresh_from_db()
        assert (lewat_kode.jenis, lewat_kode.muatan) == (JenisPesan.TEKS, {})
