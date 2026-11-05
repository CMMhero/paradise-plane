# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sematan pesan & reaksi emoji bebas
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sematan pesan dan reaksi emoji apa pun.

Yang diuji: siapa boleh menyematkan (anggota ruang, dan di kanal sistem hanya yang
boleh menulis), bahwa bukan anggota tidak bisa menebak id pesan, dan bahwa reaksi
menerima emoji majemuk (ZWJ, bendera, warna kulit) sambil tetap satu orang satu
emoji per pesan.
"""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import (
    KUNCI_CHANGELOG,
    KUNCI_PENGUMUMAN,
    Langganan,
    PesanLangsung,
    ReaksiPesan,
    Ruang,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.kanal_sistem import ikutkan_ke_kanal_sistem


def _orang(nama):
    return User.objects.create(
        id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama, is_active=True
    )


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


@pytest.fixture
def kantor(db):
    """Workspace dengan satu admin dan dua staf, plus kanal biasa berisi admin & budi."""
    admin = _orang("sematan-admin")
    workspace = Workspace.objects.create(id=uuid4(), name="Kantor", slug="sematan-uji", owner=admin)
    budi = _orang("sematan-budi")
    citra = _orang("sematan-citra")
    WorkspaceMember.objects.create(workspace=workspace, member=admin, role=20, is_active=True)
    for orang in (budi, citra):
        WorkspaceMember.objects.create(workspace=workspace, member=orang, role=15, is_active=True)
    kanal = Ruang.objects.create(workspace=workspace, tipe=Ruang.Tipe.KANAL, nama="umum")
    Langganan.objects.bulk_create([Langganan(ruang=kanal, user=admin), Langganan(ruang=kanal, user=budi)])
    return workspace, admin, budi, citra, kanal


def _pesan(ruang, dari, isi="halo"):
    return PesanLangsung.objects.create(workspace=ruang.workspace, ruang=ruang, pengirim=dari, isi=isi)


def _url_sematkan(workspace, pesan):
    return f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/sematkan/"


def _url_daftar(workspace, ruang):
    return f"/api/workspaces/{workspace.slug}/chat/ruang/{ruang.id}/sematan/"


@pytest.mark.unit
class TestSematan:
    @pytest.mark.django_db
    def test_anggota_bisa_menyematkan_pesan_orang_lain_dan_melepasnya(self, kantor):
        workspace, admin, budi, _citra, kanal = kantor
        pesan = _pesan(kanal, admin)

        jawab = _klien(budi).post(_url_sematkan(workspace, pesan))
        assert jawab.status_code == 200
        pesan.refresh_from_db()
        assert pesan.disematkan_pada is not None
        assert pesan.disematkan_oleh_id == budi.id

        daftar = _klien(admin).get(_url_daftar(workspace, kanal)).json()
        assert daftar["boleh_sematkan"] is True
        assert [p["id"] for p in daftar["pesan"]] == [str(pesan.id)]

        # Isi ruang ikut membawa tanda sematan untuk ikon di gelembung.
        isi = _klien(admin).get(f"/api/workspaces/{workspace.slug}/chat/ruang/{kanal.id}/").json()
        assert isi[0]["disematkan"] is True

        # Admin melepas sematan yang dibuat budi: sematan milik ruang, bukan orang.
        assert _klien(admin).delete(_url_sematkan(workspace, pesan)).status_code == 204
        pesan.refresh_from_db()
        assert pesan.disematkan_pada is None
        assert pesan.disematkan_oleh_id is None
        assert _klien(admin).get(_url_daftar(workspace, kanal)).json()["pesan"] == []

    @pytest.mark.django_db
    def test_sematkan_dua_kali_tidak_membatalkan(self, kantor):
        workspace, admin, budi, _citra, kanal = kantor
        pesan = _pesan(kanal, admin)
        assert _klien(admin).post(_url_sematkan(workspace, pesan)).status_code == 200
        assert _klien(budi).post(_url_sematkan(workspace, pesan)).status_code == 200
        pesan.refresh_from_db()
        # Tetap tersemat, dan pencatatnya yang pertama.
        assert pesan.disematkan_oleh_id == admin.id

    @pytest.mark.django_db
    def test_bukan_anggota_tidak_bisa_menyematkan_atau_melihat(self, kantor):
        workspace, admin, _budi, citra, kanal = kantor
        pesan = _pesan(kanal, admin)
        klien = _klien(citra)
        # 404, bukan 403: id pesan di ruang orang lain tidak boleh terkonfirmasi ada.
        assert klien.post(_url_sematkan(workspace, pesan)).status_code == 404
        assert klien.delete(_url_sematkan(workspace, pesan)).status_code == 404
        assert klien.get(_url_daftar(workspace, kanal)).status_code == 404
        pesan.refresh_from_db()
        assert pesan.disematkan_pada is None

    @pytest.mark.django_db
    def test_pengumuman_hanya_admin_changelog_tidak_siapa_pun(self, kantor):
        workspace, admin, budi, *_ = kantor
        ikutkan_ke_kanal_sistem(workspace.id)
        pengumuman = Ruang.objects.get(workspace=workspace, kunci_sistem=KUNCI_PENGUMUMAN)
        changelog = Ruang.objects.get(workspace=workspace, kunci_sistem=KUNCI_CHANGELOG)
        di_pengumuman = _pesan(pengumuman, admin)
        di_changelog = PesanLangsung.objects.create(workspace=workspace, ruang=changelog, isi="rilis")

        assert _klien(budi).post(_url_sematkan(workspace, di_pengumuman)).status_code == 403
        assert _klien(budi).get(_url_daftar(workspace, pengumuman)).json()["boleh_sematkan"] is False
        assert _klien(admin).post(_url_sematkan(workspace, di_pengumuman)).status_code == 200

        assert _klien(admin).post(_url_sematkan(workspace, di_changelog)).status_code == 403
        assert _klien(budi).post(_url_sematkan(workspace, di_changelog)).status_code == 403

    @pytest.mark.django_db
    def test_pesan_dihapus_hilang_dari_daftar_sematan(self, kantor):
        workspace, admin, _budi, _citra, kanal = kantor
        pesan = _pesan(kanal, admin)
        _klien(admin).post(_url_sematkan(workspace, pesan))
        assert _klien(admin).delete(f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/").status_code == 204
        assert _klien(admin).get(_url_daftar(workspace, kanal)).json()["pesan"] == []

    @pytest.mark.django_db
    def test_batas_sematan_per_ruang(self, kantor, monkeypatch):
        from plane.app.views import chat as chat_views  # noqa: PLC0415

        monkeypatch.setattr(chat_views, "BATAS_SEMATAN", 2)
        workspace, admin, _budi, _citra, kanal = kantor
        tiga = [_pesan(kanal, admin, f"p{i}") for i in range(3)]
        klien = _klien(admin)
        assert klien.post(_url_sematkan(workspace, tiga[0])).status_code == 200
        assert klien.post(_url_sematkan(workspace, tiga[1])).status_code == 200
        assert klien.post(_url_sematkan(workspace, tiga[2])).status_code == 400


@pytest.mark.unit
class TestReaksiEmojiBebas:
    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "emoji",
        [
            "😮",
            "🧑🏽‍💻",  # ZWJ + warna kulit
            "🇮🇩",  # bendera: dua regional indicator
            "👨‍👩‍👧‍👦",  # keluarga: tujuh code point
            "❤️",  # dengan variation selector
        ],
    )
    def test_emoji_apa_pun_diterima_dan_tetap_satu_per_orang(self, kantor, emoji):
        workspace, admin, budi, _citra, kanal = kantor
        pesan = _pesan(kanal, admin)
        url = f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/reaksi/"

        assert _klien(budi).post(url, {"emoji": emoji}, format="json").status_code == 201
        assert _klien(admin).post(url, {"emoji": emoji}, format="json").status_code == 201
        assert ReaksiPesan.objects.filter(pesan=pesan, emoji=emoji).count() == 2

        isi = _klien(admin).get(f"/api/workspaces/{workspace.slug}/chat/ruang/{kanal.id}/").json()
        assert isi[0]["reaksi"] == [{"emoji": emoji, "orang": [str(budi.id), str(admin.id)]}]

        # Klik kedua oleh orang yang sama membatalkan miliknya saja, tidak membuat kembar.
        assert _klien(budi).post(url, {"emoji": emoji}, format="json").data["aktif"] is False
        assert list(ReaksiPesan.objects.filter(pesan=pesan).values_list("user_id", flat=True)) == [admin.id]

    @pytest.mark.django_db
    def test_emoji_kosong_atau_terlalu_panjang_ditolak(self, kantor):
        workspace, admin, budi, _citra, kanal = kantor
        pesan = _pesan(kanal, admin)
        url = f"/api/workspaces/{workspace.slug}/chat/pesan/{pesan.id}/reaksi/"
        assert _klien(budi).post(url, {"emoji": "  "}, format="json").status_code == 400
        assert _klien(budi).post(url, {"emoji": "😀" * 33}, format="json").status_code == 400
        assert ReaksiPesan.objects.count() == 0
