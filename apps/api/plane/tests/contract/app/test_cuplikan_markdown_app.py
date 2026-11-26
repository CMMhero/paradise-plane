# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: cuplikan pesan tanpa sintaks Markdown
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi obrolan adalah Markdown. Yang tampil sebagai cuplikan (kutipan balasan, bilah
sematan, inbox, email obrolan) adalah teksnya saja, dipotong sesudah sintaks dibuang."""

from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from plane.bgtasks.chat_email import susun_email_pesan
from plane.db.models import Langganan, Notification, Ruang, User, Workspace, WorkspaceMember


def _orang(nama):
    return User.objects.create(id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama)


def _klien(user):
    klien = APIClient()
    klien.force_authenticate(user=user)
    return klien


@pytest.fixture
def kantor(db):
    penulis, pembaca = _orang("penulis"), _orang("pembaca")
    ws = Workspace.objects.create(id=uuid4(), name="Kantor", slug="cuplikan-uji", owner=penulis)
    for orang in (penulis, pembaca):
        WorkspaceMember.objects.create(workspace=ws, member=orang, role=15)
    umum = Ruang.objects.create(workspace=ws, tipe=Ruang.Tipe.KANAL, nama="umum")
    Langganan.objects.bulk_create([Langganan(ruang=umum, user=u) for u in (penulis, pembaca)])
    return {"ws": ws, "penulis": penulis, "pembaca": pembaca, "umum": umum}


@pytest.mark.contract
class TestCuplikanTeksPolos:
    ISI = "**Selamat** [@pembaca](https://x.id/w/profile/1)\n\n* satu"

    @pytest.mark.django_db
    def test_kutipan_dan_sematan_tanpa_sintaks_markdown(self, kantor):
        k = kantor
        url = f"/api/workspaces/{k['ws'].slug}/chat/ruang/{k['umum'].id}/"
        asli = _klien(k["penulis"]).post(url, {"isi": self.ISI}, format="json").json()
        balas = _klien(k["pembaca"]).post(url, {"isi": "ok", "balasan_ke": asli["id"]}, format="json").json()
        assert balas["balasan_ke"]["isi"] == "Selamat @pembaca\n\n• satu"
        # Isi pesannya sendiri tetap Markdown apa adanya.
        assert asli["isi"] == self.ISI

        sematan = _klien(k["penulis"]).post(f"/api/workspaces/{k['ws'].slug}/chat/pesan/{asli['id']}/sematkan/")
        assert sematan.json()["isi"] == "Selamat @pembaca\n\n• satu"

    @pytest.mark.django_db
    def test_dipotong_sesudah_sintaks_dibuang(self, kantor):
        k = kantor
        url = f"/api/workspaces/{k['ws'].slug}/chat/ruang/{k['umum'].id}/"
        asli = _klien(k["penulis"]).post(url, {"isi": "**" + "a" * 150 + "**"}, format="json").json()
        balas = _klien(k["pembaca"]).post(url, {"isi": "ok", "balasan_ke": asli["id"]}, format="json").json()
        assert balas["balasan_ke"]["isi"] == "a" * 120

    @pytest.mark.django_db
    def test_inbox_dm_tanpa_sintaks_markdown(self, kantor):
        k = kantor
        url = f"/api/workspaces/{k['ws'].slug}/chat/{k['pembaca'].id}/"
        assert _klien(k["penulis"]).post(url, {"isi": self.ISI}, format="json").status_code == 201
        baris = Notification.objects.get(receiver=k["pembaca"], entity_name="chat")
        assert baris.data["issue_activity"]["new_value"] == "Selamat @pembaca • satu"

    @pytest.mark.django_db
    def test_email_obrolan_tanpa_sintaks_markdown(self, kantor):
        k = kantor
        _, teks, html = susun_email_pesan(k["pembaca"], k["ws"].slug, [(k["penulis"], 1, self.ISI)])
        for bagian in (teks, html):
            assert "Selamat @pembaca • satu" in bagian
            assert "**" not in bagian and "](" not in bagian
