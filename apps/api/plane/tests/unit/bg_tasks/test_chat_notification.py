# Kustomisasi Paradise Task Tracker: email pemberitahuan pesan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Yang diuji: kapan email TIDAK dikirim.

Bagian yang mudah adalah mengirim. Yang menentukan fitur ini dipakai atau
dimatikan orang sekantor adalah keempat rem di bawah, dan semuanya gagal
diam-diam kalau rusak: yang terlihat cuma kotak masuk yang penuh.
"""

from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.utils import timezone

from plane.bgtasks.chat_notification_task import kirim_pemberitahuan_pesan
from plane.db.models import Langganan, Ruang, PesanLangsung, User, Workspace, WorkspaceMember


def _orang(nama):
    return User.objects.create(
        id=uuid4(), username=nama, email=f"{nama}@paradise.test", display_name=nama, is_active=True
    )


@pytest.fixture
def kantor(db):
    pemilik = _orang("aku")
    workspace = Workspace.objects.create(id=uuid4(), name="Kantor", slug="kantor-uji", owner=pemilik)
    budi = _orang("budi")
    for satu in (pemilik, budi):
        WorkspaceMember.objects.create(workspace=workspace, member=satu, role=20)
    return workspace, pemilik, budi


def _ruang_dm(workspace, a, b):
    """Ruang DM antara dua orang, dibuat kalau belum ada.

    Ditambahkan bersama migrasi 0136: sejak pesan tinggal di dalam Ruang, model
    menolak pesan tanpa ruang. Penolakan itu disengaja, karena pesan yatim tidak
    muncul di percakapan mana pun dan tidak menimbulkan error di mana pun.
    """
    kunci = Ruang.buat_kunci_dm(a.id, b.id)
    ruang, dibuat = Ruang.objects.get_or_create(
        kunci_dm=kunci, defaults={"workspace": workspace, "tipe": Ruang.Tipe.DM}
    )
    if dibuat:
        Langganan.objects.bulk_create(
            [Langganan(ruang=ruang, user=a), Langganan(ruang=ruang, user=b)]
        )
    return ruang


def _pesan(workspace, dari, ke, isi, menit_lalu):
    pesan = PesanLangsung.objects.create(
        workspace=workspace, ruang=_ruang_dm(workspace, dari, ke), pengirim=dari, penerima=ke, isi=isi
    )
    PesanLangsung.objects.filter(pk=pesan.pk).update(created_at=timezone.now() - timedelta(minutes=menit_lalu))
    return pesan


@pytest.mark.unit
class TestEmailObrolan:
    @pytest.mark.django_db
    @patch.dict("os.environ", {"ENABLE_CHAT_EMAIL": "0"})
    @patch("plane.bgtasks.chat_notification_task.kirim_email_pesan")
    def test_saklar_mati_tidak_mengirim_apa_pun(self, kirim, kantor):
        workspace, aku, budi = kantor
        _pesan(workspace, budi, aku, "halo", menit_lalu=60)

        kirim_pemberitahuan_pesan()

        kirim.assert_not_called()

    @pytest.mark.django_db
    @patch.dict("os.environ", {"ENABLE_CHAT_EMAIL": "1"})
    @patch("plane.bgtasks.chat_notification_task.kirim_email_pesan")
    def test_pesan_yang_masih_baru_dibiarkan_dulu(self, kirim, kantor):
        """Orang yang membalas dalam beberapa menit tidak boleh memicu email."""
        workspace, aku, budi = kantor
        _pesan(workspace, budi, aku, "halo", menit_lalu=2)

        kirim_pemberitahuan_pesan()

        kirim.assert_not_called()

    @pytest.mark.django_db
    @patch.dict("os.environ", {"ENABLE_CHAT_EMAIL": "1"})
    @patch("plane.bgtasks.chat_notification_task.kirim_email_pesan")
    def test_pesan_yang_sudah_dibaca_tidak_diemailkan(self, kirim, kantor):
        workspace, aku, budi = kantor
        pesan = _pesan(workspace, budi, aku, "halo", menit_lalu=60)
        PesanLangsung.objects.filter(pk=pesan.pk).update(dibaca_pada=timezone.now())

        kirim_pemberitahuan_pesan()

        kirim.assert_not_called()

    @pytest.mark.django_db
    @patch.dict("os.environ", {"ENABLE_CHAT_EMAIL": "1"})
    @patch("plane.bgtasks.chat_notification_task.kirim_email_pesan")
    def test_satu_email_berisi_semua_lalu_tidak_diulang(self, kirim, kantor):
        workspace, aku, budi = kantor
        _pesan(workspace, budi, aku, "satu", menit_lalu=60)
        _pesan(workspace, budi, aku, "dua", menit_lalu=55)

        kirim_pemberitahuan_pesan()

        assert kirim.call_count == 1
        penerima, slug, ringkasan = kirim.call_args.args
        assert penerima.id == aku.id
        assert slug == workspace.slug
        assert ringkasan == [(budi, 2, "dua")], "dua pesan dari satu orang jadi satu baris"
        assert PesanLangsung.objects.filter(dinotifikasi_pada__isnull=True).count() == 0

        # Putaran berikutnya tidak boleh mengirim ulang isi yang sama.
        kirim_pemberitahuan_pesan()
        assert kirim.call_count == 1

    @pytest.mark.django_db
    @patch.dict("os.environ", {"ENABLE_CHAT_EMAIL": "1"})
    @patch("plane.bgtasks.chat_notification_task.kirim_email_pesan")
    def test_jeda_satu_jam_antar_email_dihormati(self, kirim, kantor):
        workspace, aku, budi = kantor
        _pesan(workspace, budi, aku, "satu", menit_lalu=60)
        kirim_pemberitahuan_pesan()
        assert kirim.call_count == 1

        # Pesan baru menyusul, sudah lewat jeda tenang, tapi email barusan
        # dikirim. Harus ditahan, dan TIDAK ditandai supaya tidak hilang.
        _pesan(workspace, budi, aku, "dua", menit_lalu=20)
        kirim_pemberitahuan_pesan()

        assert kirim.call_count == 1
        assert PesanLangsung.objects.filter(isi="dua", dinotifikasi_pada__isnull=True).count() == 1

    @pytest.mark.django_db
    @patch.dict("os.environ", {"ENABLE_CHAT_EMAIL": "1"})
    @patch("plane.bgtasks.chat_notification_task.kirim_email_pesan", side_effect=RuntimeError("smtp mati"))
    def test_email_gagal_tidak_menandai_pesan(self, kirim, kantor):
        """SMTP ngambek tidak boleh menelan pemberitahuan selamanya."""
        workspace, aku, budi = kantor
        _pesan(workspace, budi, aku, "halo", menit_lalu=60)

        kirim_pemberitahuan_pesan()

        assert PesanLangsung.objects.filter(dinotifikasi_pada__isnull=True).count() == 1
