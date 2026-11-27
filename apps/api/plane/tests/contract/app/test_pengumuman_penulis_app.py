# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penulis menyunting dan menghapus pengumumannya
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Penulis pengumuman boleh menyunting dan menghapusnya kapan pun; orang lain tidak,
dan batas waktu obrolan tetap berlaku di ruang lain."""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from plane.db.models import (
    KUNCI_PENGUMUMAN,
    Langganan,
    PenulisKanal,
    PesanLangsung,
    Ruang,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.utils.kanal_sistem import ikutkan_ke_kanal_sistem

SETAHUN = timedelta(days=365)


def _orang(nama):
    return User.objects.create(id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama)


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


@pytest.fixture
def kantor(db):
    """Admin, penulis (staf), dan pembaca (staf). Satu pengumuman dan satu pesan kanal, keduanya setahun lalu."""
    admin, penulis, pembaca, luar = (_orang(n) for n in ("bos", "penulis", "pembaca", "luar"))
    ws = Workspace.objects.create(id=uuid4(), name="Kantor", slug="penulis-uji", owner=admin)
    for orang, peran in ((admin, 20), (penulis, 15), (pembaca, 15)):
        WorkspaceMember.objects.create(workspace=ws, member=orang, role=peran)
    ikutkan_ke_kanal_sistem(ws.id)
    pengumuman = Ruang.objects.get(workspace=ws, kunci_sistem=KUNCI_PENGUMUMAN)
    PenulisKanal.objects.create(workspace=ws, ruang=pengumuman, user=penulis)
    umum = Ruang.objects.create(workspace=ws, tipe=Ruang.Tipe.KANAL, nama="umum")
    Langganan.objects.bulk_create([Langganan(ruang=umum, user=u) for u in (admin, penulis, pembaca)])
    return {
        "ws": ws,
        "admin": admin,
        "penulis": penulis,
        "pembaca": pembaca,
        "luar": luar,
        "pengumuman": _lama(pengumuman, penulis, "**Rapat** jam 9"),
        "obrolan": _lama(umum, penulis, "halo"),
    }


def _lama(ruang, dari, isi, umur=SETAHUN):
    pesan = PesanLangsung.objects.create(workspace=ruang.workspace, ruang=ruang, pengirim=dari, isi=isi)
    PesanLangsung.objects.filter(pk=pesan.pk).update(created_at=timezone.now() - umur)
    return PesanLangsung.objects.get(pk=pesan.pk)


def _url(k, pesan, akhir=""):
    return f"/api/workspaces/{k['ws'].slug}/chat/pesan/{pesan.id}/{akhir}"


@pytest.mark.contract
class TestPenulisPengumuman:
    @pytest.mark.django_db
    def test_penulis_menyunting_pengumuman_lama(self, kantor):
        k = kantor
        jawab = _klien(k["penulis"]).patch(_url(k, k["pengumuman"]), {"isi": "**Rapat** jam 10"}, format="json")
        assert jawab.status_code == 200
        assert jawab.json()["isi"] == "**Rapat** jam 10" and jawab.json()["disunting"] is True
        k["pengumuman"].refresh_from_db()
        assert k["pengumuman"].disunting_pada is not None

    @pytest.mark.django_db
    def test_penulis_menghapus_pengumuman_lama_yang_tersemat(self, kantor):
        k = kantor
        ruang = k["pengumuman"].ruang_id
        daftar = f"/api/workspaces/{k['ws'].slug}/chat/ruang/{ruang}/sematan/"
        assert _klien(k["admin"]).post(_url(k, k["pengumuman"], "sematkan/")).status_code == 200
        assert len(_klien(k["pembaca"]).get(daftar).json()["pesan"]) == 1

        assert _klien(k["penulis"]).delete(_url(k, k["pengumuman"])).status_code == 204

        assert _klien(k["pembaca"]).get(daftar).json()["pesan"] == []
        assert not PesanLangsung.objects.filter(pk=k["pengumuman"].pk).exists()

    @pytest.mark.django_db
    @pytest.mark.parametrize("siapa", ["admin", "pembaca"])
    def test_orang_lain_termasuk_admin_dapat_403(self, kantor, siapa):
        k = kantor
        klien = _klien(k[siapa])
        assert klien.patch(_url(k, k["pengumuman"]), {"isi": "diubah"}, format="json").status_code == 403
        assert klien.delete(_url(k, k["pengumuman"])).status_code == 403
        k["pengumuman"].refresh_from_db()
        assert k["pengumuman"].isi == "**Rapat** jam 9" and k["pengumuman"].deleted_at is None

    @pytest.mark.django_db
    def test_penulis_yang_izinnya_dicabut_kembali_kena_batas_waktu(self, kantor):
        k = kantor
        PenulisKanal.all_objects.filter(user=k["penulis"]).delete()
        klien = _klien(k["penulis"])
        assert klien.patch(_url(k, k["pengumuman"]), {"isi": "diubah"}, format="json").status_code == 403
        assert klien.delete(_url(k, k["pengumuman"])).status_code == 403
        k["pengumuman"].refresh_from_db()
        assert k["pengumuman"].isi == "**Rapat** jam 9" and k["pengumuman"].deleted_at is None

    @pytest.mark.django_db
    def test_bukan_anggota_workspace_ditolak(self, kantor):
        k = kantor
        assert _klien(k["luar"]).delete(_url(k, k["pengumuman"])).status_code == 403
        assert PesanLangsung.objects.filter(pk=k["pengumuman"].pk).exists()

    @pytest.mark.django_db
    def test_batas_waktu_tetap_berlaku_di_ruang_lain(self, kantor):
        k = kantor
        klien = _klien(k["penulis"])
        assert klien.patch(_url(k, k["obrolan"]), {"isi": "diubah"}, format="json").status_code == 403
        assert klien.delete(_url(k, k["obrolan"])).status_code == 403
        k["obrolan"].refresh_from_db()
        assert k["obrolan"].isi == "halo"

    @pytest.mark.django_db
    def test_pesan_orang_lain_di_ruang_biasa_tetap_404(self, kantor):
        k = kantor
        assert _klien(k["admin"]).delete(_url(k, k["obrolan"])).status_code == 404

    @pytest.mark.django_db
    def test_kanal_privat_yang_baru_dirujuk_saat_menyunting_ikut_disamarkan(self, kantor):
        k = kantor
        rahasia = Ruang.objects.create(workspace=k["ws"], tipe=Ruang.Tipe.PRIVAT, nama="akuisisi")
        Langganan.objects.create(ruang=rahasia, user=k["penulis"])
        isi = "Bahas di #akuisisi"
        assert (
            _klien(k["penulis"])
            .patch(_url(k, k["pengumuman"]), {"isi": isi, "kanal": [str(rahasia.id)]}, format="json")
            .status_code
            == 200
        )
        ruang = f"/api/workspaces/{k['ws'].slug}/chat/ruang/{k['pengumuman'].ruang_id}/"
        assert _klien(k["pembaca"]).get(ruang).json()[-1]["isi"] == "Bahas di #private-channel"
        # Suntingan berikutnya tanpa daftar rujukan tidak membuka kembali namanya.
        _klien(k["penulis"]).patch(_url(k, k["pengumuman"]), {"isi": isi + " ya"}, format="json")
        assert _klien(k["pembaca"]).get(ruang).json()[-1]["isi"] == "Bahas di #private-channel ya"
