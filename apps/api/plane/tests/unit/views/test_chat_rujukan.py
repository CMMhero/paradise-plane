# Kustomisasi Paradise Task Tracker: rujukan #kanal, #work item, @all, @yourself (KEP-91)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Rujukan di obrolan dan editor teks kaya.

ORM langsung, tanpa factory_boy (tidak ada di image runtime).
"""

import json
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueMention,
    IssueSubscriber,
    JenisPesan,
    Langganan,
    Notification,
    PesanLangsung,
    Project,
    ProjectMember,
    Ruang,
    State,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.kanal_sistem import kunci_kabar, ruang_kabar
from plane.utils.rujukan_obrolan import NAMA_PRIVAT, samarkan, samarkan_teks


def _orang(nama):
    return User.objects.create(id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama)


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


def _project(ws, nama, kode, anggota):
    project = Project.objects.create(name=nama, identifier=kode, workspace=ws)
    for u in anggota:
        ProjectMember.objects.create(project=project, workspace=ws, member=u, role=15, is_active=True)
    state = State.objects.create(name="Todo", project=project, workspace=ws, group="unstarted")
    issue = Issue.objects.create(name=f"Tugas {kode}", project=project, workspace=ws, state=state)
    return project, issue


@pytest.fixture
def kantor(db):
    """ani & budi di kanal privat `rahasia`; ani, budi, cici di kanal publik `umum`.

    Project GDG beranggota ani & budi; project RHS hanya budi.
    """
    ani, budi, cici = _orang("ani"), _orang("budi"), _orang("cici")
    ws = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kantor-rujukan", owner=ani)
    for u in (ani, budi, cici):
        WorkspaceMember.objects.create(workspace=ws, member=u, role=15)
    umum = Ruang.objects.create(workspace=ws, tipe=Ruang.Tipe.KANAL, nama="umum")
    rahasia = Ruang.objects.create(workspace=ws, tipe=Ruang.Tipe.PRIVAT, nama="rahasia")
    for u in (ani, budi, cici):
        Langganan.objects.create(ruang=umum, user=u)
    for u in (ani, budi):
        Langganan.objects.create(ruang=rahasia, user=u)
    _, tugas_gdg = _project(ws, "Gudang", "GDG", [ani, budi])
    _, tugas_rhs = _project(ws, "Rahasia", "RHS", [budi])
    return {
        "ws": ws,
        "ani": ani,
        "budi": budi,
        "cici": cici,
        "umum": umum,
        "rahasia": rahasia,
        "gdg": tugas_gdg,
        "rhs": tugas_rhs,
    }


def _url(k, akhir):
    return f"/api/workspaces/{k['ws'].slug}/chat/{akhir}"


# ---------------------------------------------------------------- penyamaran murni


@pytest.mark.unit
class TestSamarkanTeks:
    def test_hanya_nama_yang_berdiri_sendiri(self):
        isi = "cek #rahasia, #rahasia-2 dan #Rahasia. bukan a#rahasia atau #rahasiaku atau #rahasia_x"
        hasil = samarkan_teks(isi, ["rahasia", "rahasia-2"])
        assert hasil == (
            "cek #private-channel, #private-channel dan #private-channel. "
            "bukan a#rahasia atau #rahasiaku atau #rahasia_x"
        )

    def test_unicode_dan_nama_berspasi(self):
        assert samarkan_teks("#SMT 1 lalu #SMT 12", ["SMT 1"]) == "#private-channel lalu #SMT 12"
        assert samarkan_teks("#kopié", ["kopi"]) == "#kopié"

    def test_kosong(self):
        assert samarkan_teks("", ["a"]) == ""
        assert samarkan_teks("halo #a", []) == "halo #a"

    def test_tanpa_kanal_privat_tidak_menyentuh_database_dan_tidak_mengubah_masukan(self):
        # Tanpa django_db: kueri apa pun di sini akan gagal.
        muatan = {"sebut": ["x"], "kanal": [{"id": "1", "nama": "umum", "privat": False}]}
        isi, baru = samarkan("lihat #umum", muatan, None)
        assert isi == "lihat #umum"
        assert baru["kanal"] == [{"id": "1", "nama": "umum", "privat": False, "boleh": True}]
        assert "boleh" not in muatan["kanal"][0]
        assert samarkan("x", {}, None) == ("x", {})

    def test_penonton_tak_dikenal_tanpa_kueri(self):
        muatan = {"kanal": [{"id": "1", "nama": "rahasia", "privat": True}]}
        isi, baru = samarkan("ke #rahasia", muatan, None)
        assert isi == f"ke #{NAMA_PRIVAT}"
        assert baru["kanal"] == [{"id": "1", "nama": NAMA_PRIVAT, "privat": True, "boleh": False}]
        assert muatan["kanal"][0]["nama"] == "rahasia"


# ---------------------------------------------------------------- saran & info


@pytest.mark.unit
class TestSaranRujukan:
    @pytest.mark.django_db
    def test_kanal_privat_hanya_untuk_anggotanya(self, kantor):
        k = kantor
        punya_ani = _klien(k["ani"]).get(_url(k, "rujukan/"), {"q": "rah"}).json()
        assert [r["nama"] for r in punya_ani["kanal"]] == ["rahasia"]
        assert punya_ani["kanal"][0]["tipe"] == Ruang.Tipe.PRIVAT
        punya_cici = _klien(k["cici"]).get(_url(k, "rujukan/"), {"q": "rah"}).json()
        assert punya_cici["kanal"] == []
        # Kanal publik terlihat oleh semua.
        assert [r["nama"] for r in _klien(k["cici"]).get(_url(k, "rujukan/"), {"q": "umu"}).json()["kanal"]] == ["umum"]

    @pytest.mark.django_db
    def test_dm_dan_ruang_kabar_tidak_pernah_disarankan(self, kantor):
        k = kantor
        kabar = ruang_kabar(k["ws"].id, k["ani"].id)
        assert kabar.kunci_sistem == kunci_kabar(k["ani"].id)
        _klien(k["ani"]).post(_url(k, f"{k['budi'].id}/"), {"isi": "hai"}, format="json")
        semua = _klien(k["ani"]).get(_url(k, "rujukan/"), {"count": 20}).json()["kanal"]
        ids = {r["id"] for r in semua}
        assert str(kabar.id) not in ids
        assert all(r["tipe"] != Ruang.Tipe.DM for r in semua)
        info = _klien(k["ani"]).get(_url(k, "rujukan/info/"), {"kanal": str(kabar.id)}).json()
        assert info["kanal"][str(kabar.id)] == {"id": str(kabar.id), "boleh": False}

    @pytest.mark.django_db
    def test_tugas_hanya_dari_project_yang_diikuti(self, kantor):
        k = kantor
        nomor_gdg = f"GDG-{k['gdg'].sequence_id}"
        hasil = _klien(k["ani"]).get(_url(k, "rujukan/"), {"q": nomor_gdg}).json()["tugas"]
        assert [t["id"] for t in hasil] == [str(k["gdg"].id)]
        assert hasil[0]["nomor"] == nomor_gdg
        assert hasil[0]["judul"] == "Tugas GDG"
        assert hasil[0]["state_group"] == "unstarted"
        assert _klien(k["ani"]).get(_url(k, "rujukan/"), {"q": "RHS"}).json()["tugas"] == []
        assert _klien(k["ani"]).get(_url(k, "rujukan/"), {"q": "Tugas"}).json()["tugas"][0]["id"] == str(k["gdg"].id)
        assert len(_klien(k["budi"]).get(_url(k, "rujukan/"), {"q": "Tugas"}).json()["tugas"]) == 2

    @pytest.mark.django_db
    def test_info_tidak_membocorkan_nama_atau_judul(self, kantor):
        k = kantor
        jawab = _klien(k["cici"]).get(
            _url(k, "rujukan/info/"),
            {
                "kanal": f"{k['rahasia'].id},{k['umum'].id},bukan-uuid",
                "tugas": f"{k['gdg'].id},{uuid4()}",
            },
        )
        assert jawab.status_code == 200
        data = jawab.json()
        assert data["kanal"][str(k["rahasia"].id)] == {"id": str(k["rahasia"].id), "boleh": False}
        umum = data["kanal"][str(k["umum"].id)]
        assert umum["boleh"] is True
        assert (umum["nama"], umum["tipe"]) == ("umum", Ruang.Tipe.KANAL)
        # Bahan kartu pratinjau hover: topik dan jumlah anggota aktif.
        assert umum["topik"] == k["umum"].topik
        assert umum["jumlah_anggota"] == Langganan.objects.filter(ruang=k["umum"]).count() >= 1
        assert data["kanal"]["bukan-uuid"] == {"id": "bukan-uuid", "boleh": False}
        # cici bukan anggota project GDG.
        assert data["tugas"][str(k["gdg"].id)] == {"id": str(k["gdg"].id), "boleh": False}

        punya_ani = _klien(k["ani"]).get(_url(k, "rujukan/info/"), {"tugas": str(k["gdg"].id)}).json()
        assert punya_ani["tugas"][str(k["gdg"].id)]["boleh"] is True
        assert punya_ani["tugas"][str(k["gdg"].id)]["judul"] == "Tugas GDG"
        pratinjau = punya_ani["tugas"][str(k["gdg"].id)]
        assert pratinjau["project_nama"] == k["gdg"].project.name
        assert pratinjau["state_nama"] == k["gdg"].state.name
        assert pratinjau["prioritas"] in ("none", "low", "medium", "high", "urgent")
        assert pratinjau["assignee_jumlah"] == len(pratinjau["assignee"]) <= 3

    @pytest.mark.django_db
    def test_anonim_ditolak(self, kantor):
        k = kantor
        assert APIClient().get(_url(k, "rujukan/")).status_code in (401, 403)
        assert APIClient().get(_url(k, "rujukan/info/")).status_code in (401, 403)


# ---------------------------------------------------------------- pengiriman


def _kartu(user):
    return PesanLangsung.objects.filter(ruang__kunci_sistem=kunci_kabar(user.id), jenis=JenisPesan.MENTION)


@pytest.mark.unit
class TestKirimRujukan:
    @pytest.mark.django_db
    def test_muatan_disaring_dan_all_mengirim_kartu_ke_semua_kecuali_pengirim(self, kantor):
        k = kantor
        jawab = _klien(k["ani"]).post(
            _url(k, f"ruang/{k['umum'].id}/"),
            {
                "isi": "@all @ani lihat #rahasia dan #umum soal GDG",
                "sebut": [str(k["ani"].id)],
                "kanal": [str(k["rahasia"].id), str(k["umum"].id), "rusak"],
                "tugas": [str(k["gdg"].id), str(k["rhs"].id)],
                "semua": True,
            },
            format="json",
        )
        assert jawab.status_code == 201
        tersimpan = PesanLangsung.objects.get(id=jawab.json()["id"]).muatan
        assert tersimpan == {
            # @yourself tetap tersimpan supaya tersorot.
            "sebut": [str(k["ani"].id)],
            "kanal": [
                {"id": str(k["rahasia"].id), "nama": "rahasia", "privat": True},
                {"id": str(k["umum"].id), "nama": "umum", "privat": False},
            ],
            # RHS bukan project ani.
            "tugas": [
                {
                    "id": str(k["gdg"].id),
                    "nomor": f"GDG-{k['gdg'].sequence_id}",
                    "project_id": str(k["gdg"].project_id),
                }
            ],
            "semua": True,
        }
        # Pengirim melihat semuanya, dengan `boleh`.
        assert all(e["boleh"] for e in jawab.json()["muatan"]["kanal"])

        # @all: budi & cici dapat kartu tepat satu, ani tidak sama sekali.
        assert _kartu(k["budi"]).count() == 1
        assert _kartu(k["cici"]).count() == 1
        assert not _kartu(k["ani"]).exists()
        # Cuplikan kartu disamarkan per penerima.
        assert "#rahasia" in _kartu(k["budi"]).first().isi
        isi_cici = _kartu(k["cici"]).first()
        assert "rahasia" not in isi_cici.isi and f"#{NAMA_PRIVAT}" in isi_cici.isi
        assert "rahasia" not in isi_cici.muatan["detail"]["komentar"]

    @pytest.mark.django_db
    def test_sebut_diri_sendiri_tanpa_kartu(self, kantor):
        k = kantor
        jawab = _klien(k["ani"]).post(
            _url(k, f"ruang/{k['umum'].id}/"),
            {"isi": "@ani @budi catatan", "sebut": [str(k["ani"].id), str(k["budi"].id)]},
            format="json",
        )
        assert jawab.json()["muatan"] == {"sebut": [str(k["ani"].id), str(k["budi"].id)]}
        assert not _kartu(k["ani"]).exists()
        assert _kartu(k["budi"]).count() == 1
        assert not _kartu(k["cici"]).exists()

    @pytest.mark.django_db
    def test_all_diabaikan_di_dm(self, kantor):
        k = kantor
        jawab = _klien(k["ani"]).post(_url(k, f"{k['budi'].id}/"), {"isi": "@all hai", "semua": True}, format="json")
        assert jawab.status_code == 201
        assert jawab.json()["muatan"] == {}
        assert not PesanLangsung.objects.filter(jenis=JenisPesan.MENTION).exists()

    @pytest.mark.django_db
    def test_bukan_anggota_kanal_privat_melihat_private_channel(self, kantor):
        k = kantor
        dasar = _url(k, f"ruang/{k['umum'].id}/")
        induk = (
            _klien(k["ani"])
            .post(dasar, {"isi": "pindah ke #rahasia ya", "kanal": [str(k["rahasia"].id)]}, format="json")
            .json()
        )
        _klien(k["budi"]).post(dasar, {"isi": "oke", "balasan_ke": induk["id"]}, format="json")

        isi_cici = _klien(k["cici"]).get(dasar).json()
        pesan_induk = next(p for p in isi_cici if p["id"] == induk["id"])
        assert pesan_induk["isi"] == f"pindah ke #{NAMA_PRIVAT} ya"
        assert pesan_induk["muatan"]["kanal"] == [
            {"id": str(k["rahasia"].id), "nama": NAMA_PRIVAT, "privat": True, "boleh": False}
        ]
        balasan = next(p for p in isi_cici if p["balasan_ke"])
        assert balasan["balasan_ke"]["isi"] == f"pindah ke #{NAMA_PRIVAT} ya"

        # Daftar percakapan dan pencarian juga tersamar.
        daftar = _klien(k["cici"]).get(_url(k, "")).json()
        assert all("rahasia" not in (r.get("isi") or "") for r in daftar)
        assert _klien(k["cici"]).get(_url(k, "cari/"), {"q": "rahasia"}).json() == []
        cari = _klien(k["cici"]).get(_url(k, "cari/"), {"q": "pindah"}).json()
        assert cari and cari[0]["isi"] == f"pindah ke #{NAMA_PRIVAT} ya"

        # Anggota kanal privat melihat namanya.
        isi_budi = _klien(k["budi"]).get(dasar).json()
        assert next(p for p in isi_budi if p["id"] == induk["id"])["isi"] == "pindah ke #rahasia ya"

        # Sematan juga.
        _klien(k["budi"]).post(_url(k, f"pesan/{induk['id']}/sematkan/"))
        sematan = _klien(k["cici"]).get(_url(k, f"ruang/{k['umum'].id}/sematan/")).json()["pesan"]
        assert sematan[0]["isi"] == f"pindah ke #{NAMA_PRIVAT} ya"


# ---------------------------------------------------------------- teks kaya


def _mention(nama, ident):
    return f'<mention-component id="{uuid4()}" entity_name="{nama}" entity_identifier="{ident}"></mention-component>'


@pytest.mark.unit
class TestSebutanTeksKaya:
    @pytest.mark.django_db
    def test_process_mention_semua_jenis_tanpa_galat(self, kantor):
        from plane.bgtasks.email_notification_task import process_mention

        k = kantor
        html = " ".join(
            [
                _mention("user_mention", k["budi"].id),
                _mention("user_mention", uuid4()),
                _mention("everyone_mention", "all"),
                _mention("channel_mention", k["umum"].id),
                _mention("channel_mention", k["rahasia"].id),
                _mention("channel_mention", "rusak"),
                _mention("issue_mention", k["gdg"].id),
                _mention("issue_mention", uuid4()),
            ]
        )
        hasil = process_mention(f"<p>{html}</p>")
        assert hasil == (
            f"<p>@budi @unknown @all #umum #{NAMA_PRIVAT} #{NAMA_PRIVAT} GDG-{k['gdg'].sequence_id} #work-item</p>"
        )

    def test_deteksi_all_baru(self):
        from plane.bgtasks.notification_task import (
            extract_comment_mentions,
            sebut_semua_baru_di_deskripsi,
            sebut_semua_baru_di_komentar,
        )

        semua = f"<p>{_mention('everyone_mention', 'all')}</p>"
        assert sebut_semua_baru_di_komentar(semua, None)
        assert sebut_semua_baru_di_komentar(semua, "<p>lama</p>")
        assert not sebut_semua_baru_di_komentar(semua, semua)
        assert not sebut_semua_baru_di_komentar("<p>x</p>", None)
        baru = json.dumps({"description_html": semua})
        assert sebut_semua_baru_di_deskripsi(baru, json.dumps({"description_html": "<p></p>"}))
        assert sebut_semua_baru_di_deskripsi(baru, None)
        assert not sebut_semua_baru_di_deskripsi(baru, baru)
        # @all tidak pernah dianggap id orang.
        assert extract_comment_mentions(semua) == []

    @pytest.mark.django_db
    def test_all_di_deskripsi_mengabari_anggota_project_tanpa_jadi_subscriber(self, kantor):
        from plane.bgtasks.notification_task import notifications

        k = kantor
        issue = k["gdg"]
        aktivitas = [
            {
                "id": str(uuid4()),
                "verb": "updated",
                "field": "description",
                "actor_id": str(k["ani"].id),
                "new_value": "",
                "old_value": "",
                "issue_detail": {"id": str(issue.id)},
                "created_at": "2026-11-05T10:00:00Z",
            }
        ]
        notifications(
            type="issue.activity.updated",
            issue_id=str(issue.id),
            project_id=str(issue.project_id),
            actor_id=str(k["ani"].id),
            subscriber=False,
            issue_activities_created=json.dumps(aktivitas),
            requested_data=json.dumps({"description_html": f"<p>{_mention('everyone_mention', 'all')}</p>"}),
            current_instance=json.dumps({"description_html": "<p></p>"}),
        )
        sebutan = Notification.objects.filter(
            entity_identifier=issue.id, sender="in_app:issue_activities:mentioned"
        ).values_list("receiver_id", flat=True)
        # budi anggota project; ani pelakunya; cici bukan anggota project.
        assert set(sebutan) == {k["budi"].id}
        assert not IssueMention.objects.filter(issue=issue).exists()
        assert not IssueSubscriber.objects.filter(issue=issue, subscriber=k["budi"]).exists()
