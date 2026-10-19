# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: siaran real-time obrolan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Siaran real-time: bentuknya, dan yang lebih penting, ketahanannya.

Sifat yang paling ingin dijaga di berkas ini BUKAN "siarannya sampai", tapi
"pesannya tetap terkirim walau siarannya gagal". Real-time itu percepatan, bukan
syarat. Kalau Redis mati lalu orang tidak bisa mengirim pesan sama sekali, kita
menukar fitur nyaman dengan fitur pokok, dan itu pertukaran yang salah.
"""

import json
from unittest.mock import patch
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.db.models import Langganan, Ruang, User, Workspace, WorkspaceMember
from plane.utils.obrolan_siaran import kanal_ruang, siarkan


def _orang(nama):
    return User.objects.create(
        id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama, is_active=True
    )


@pytest.fixture
def kantor(db):
    aku = _orang("siar-aku")
    workspace = Workspace.objects.create(id=uuid4(), name="Kantor", slug="siar-uji", owner=aku)
    budi = _orang("siar-budi")
    for orang in (aku, budi):
        WorkspaceMember.objects.create(workspace=workspace, member=orang, role=15, is_active=True)
    return workspace, aku, budi


def test_kanal_memakai_awalan_yang_sama_dengan_pelanggannya():
    """`apps/live` berlangganan pola `obrolan:*`. Mengubah salah satu sisi tanpa
    yang lain membuat siarannya hilang tanpa error di mana pun."""
    assert kanal_ruang("abc").startswith("obrolan:")
    assert kanal_ruang("abc") == "obrolan:abc"


def test_siaran_membawa_ruang_tipe_dan_pengirimnya():
    with patch("plane.utils.obrolan_siaran.redis_instance") as ri:
        siarkan("R1", "pesan", oleh_id="U1")

    kanal, muatan = ri.return_value.publish.call_args[0]
    isi = json.loads(muatan)

    assert kanal == "obrolan:R1"
    assert isi["tipe"] == "pesan"
    assert isi["ruang"] == "R1"
    # `oleh` dipakai penerima untuk membuang gaung kirimannya sendiri.
    assert isi["oleh"] == "U1"


def test_redis_mati_tidak_melempar():
    """Ditelan, dan itu disengaja. Lihat alasannya di docstring modul."""
    with patch("plane.utils.obrolan_siaran.redis_instance", side_effect=ConnectionError("mati")):
        siarkan("R1", "pesan", oleh_id="U1")  # tidak boleh melempar


@pytest.mark.django_db
def test_mengirim_pesan_ikut_menyiarkan(kantor):
    workspace, aku, budi = kantor
    client = APIClient()
    client.force_authenticate(user=aku)

    with patch("plane.app.views.chat.siarkan") as siar:
        r = client.post(
            f"/api/workspaces/{workspace.slug}/chat/{budi.id}/", {"isi": "halo"}, format="json"
        )

    assert r.status_code == 201
    assert siar.called
    ruang_id, tipe, oleh = siar.call_args[0]
    assert str(ruang_id) == str(Ruang.objects.get(tipe=Ruang.Tipe.DM).id)
    assert tipe == "pesan"
    # Pengirim ikut disebut supaya penerima bisa membuang gaung kirimannya sendiri.
    assert oleh == aku.id


@pytest.mark.django_db
def test_pesan_tetap_terkirim_walau_redis_mati(kantor):
    """Sifat yang paling penting di berkas ini.

    Kalau siaran boleh menjatuhkan pengiriman, satu Redis yang ngambek berubah
    jadi obrolan yang mati total, dan sebabnya akan dicari di tempat yang salah.
    """
    workspace, aku, budi = kantor
    client = APIClient()
    client.force_authenticate(user=aku)

    with patch("plane.utils.obrolan_siaran.redis_instance", side_effect=ConnectionError("mati")):
        r = client.post(
            f"/api/workspaces/{workspace.slug}/chat/{budi.id}/", {"isi": "tetap sampai"}, format="json"
        )

    assert r.status_code == 201
    assert r.data["isi"] == "tetap sampai"


@pytest.mark.django_db
def test_sunting_hapus_dan_reaksi_ikut_menyiarkan(kantor):
    workspace, aku, budi = kantor
    slug = workspace.slug
    client = APIClient()
    client.force_authenticate(user=aku)

    with patch("plane.app.views.chat.siarkan") as siar:
        pesan_id = client.post(
            f"/api/workspaces/{slug}/chat/{budi.id}/", {"isi": "asli"}, format="json"
        ).data["id"]
        client.patch(f"/api/workspaces/{slug}/chat/pesan/{pesan_id}/", {"isi": "disunting"}, format="json")
        client.post(f"/api/workspaces/{slug}/chat/pesan/{pesan_id}/reaksi/", {"emoji": "128077"}, format="json")
        client.delete(f"/api/workspaces/{slug}/chat/pesan/{pesan_id}/")

    tipe = [panggilan[0][1] for panggilan in siar.call_args_list]
    assert tipe == ["pesan", "sunting", "reaksi", "hapus"]


@pytest.mark.django_db
def test_pesan_kanal_juga_disiarkan(kantor):
    workspace, aku, _ = kantor
    slug = workspace.slug
    client = APIClient()
    client.force_authenticate(user=aku)
    ruang_id = client.post(
        f"/api/workspaces/{slug}/chat/ruang/", {"nama": "siaran", "tipe": "kanal"}, format="json"
    ).data["id"]

    with patch("plane.app.views.chat.siarkan") as siar:
        client.post(f"/api/workspaces/{slug}/chat/ruang/{ruang_id}/", {"isi": "hai kanal"}, format="json")

    assert siar.called
    assert str(siar.call_args[0][0]) == ruang_id
    # Langganan pembuat kanal harus ada, kalau tidak siarannya tidak punya
    # penerima sama sekali dan ujinya lulus tanpa membuktikan apa pun.
    assert Langganan.objects.filter(ruang_id=ruang_id, user=aku).exists()
