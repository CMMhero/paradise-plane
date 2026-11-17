# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes penggabungan kabar pembaruan beruntun
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Perubahan beruntun atas kolom bernilai tunggal jadi satu kabar.

Yang dikunci bukan hanya "digabung", tapi juga yang TIDAK boleh digabung: komentar,
kolom berdaftar, pelaku berbeda, kabar yang sudah dibaca.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from plane.db.models import EmailNotificationLog, Notification, User
from plane.utils.gabung_kabar import (
    JUDUL_BALASAN,
    gabungkan_email,
    gabungkan_notifikasi,
    gabungkan_notifikasi_rinci,
    kolom_hidup,
    kolom_tunggal,
    lipat,
    ringkasan,
    terapkan,
)

SENDER = "in_app:issue_activities:subscribed"


@pytest.fixture
def orang(db):
    def buat(nama):
        unik = uuid4().hex[:8]
        return User.objects.create(email=f"{nama}-{unik}@plane.so", username=f"{nama}_{unik}")

    return buat


def _notif(workspace, penerima, pelaku, issue_id, kolom, lama, baru, sender=SENDER):
    return Notification(
        workspace=workspace,
        sender=sender,
        triggered_by=pelaku,
        receiver=penerima,
        entity_identifier=issue_id,
        entity_name="issue",
        title=f"mengubah {kolom} jadi {baru}",
        data={"issue_activity": {"field": kolom, "old_value": lama, "new_value": baru, "old_identifier": None}},
    )


def _simpan(daftar):
    Notification.objects.bulk_create(daftar)
    return daftar


@pytest.mark.unit
class TestGabungkanNotifikasi:
    def test_perubahan_beruntun_jadi_satu_dengan_nilai_awal_dan_akhir(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        _simpan([_notif(workspace, penerima, pelaku, issue, "state", "To Do", "In Progress")])

        sisa = gabungkan_notifikasi([_notif(workspace, penerima, pelaku, issue, "state", "In Progress", "Done")])

        assert sisa == []
        baris = Notification.objects.get(receiver=penerima)
        assert baris.data["issue_activity"]["old_value"] == "To Do"
        assert baris.data["issue_activity"]["new_value"] == "Done"
        assert "Done" in baris.title

    def test_kembali_ke_nilai_awal_menghapus_kabar(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        _simpan([_notif(workspace, penerima, pelaku, issue, "priority", "low", "high")])

        sisa = gabungkan_notifikasi([_notif(workspace, penerima, pelaku, issue, "priority", "high", "low")])

        assert sisa == []
        assert not Notification.objects.filter(receiver=penerima).exists()

    def test_dua_perubahan_dalam_satu_gelombang_dilipat(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        sisa = gabungkan_notifikasi(
            [
                _notif(workspace, penerima, pelaku, issue, "state", "A", "B"),
                _notif(workspace, penerima, pelaku, issue, "state", "B", "C"),
            ]
        )
        assert len(sisa) == 1
        assert sisa[0].data["issue_activity"]["old_value"] == "A"
        assert sisa[0].data["issue_activity"]["new_value"] == "C"

    def test_pelaku_lain_tidak_digabung(self, workspace, orang):
        penerima, a, b, issue = orang("p"), orang("a"), orang("b"), uuid4()
        _simpan([_notif(workspace, penerima, a, issue, "state", "A", "B")])
        sisa = gabungkan_notifikasi([_notif(workspace, penerima, b, issue, "state", "B", "C")])
        assert len(sisa) == 1
        assert Notification.objects.filter(receiver=penerima).count() == 1

    def test_kabar_yang_sudah_dibaca_tidak_ditulis_ulang(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        _simpan([_notif(workspace, penerima, pelaku, issue, "state", "A", "B")])
        Notification.objects.filter(receiver=penerima).update(read_at=timezone.now())
        sisa = gabungkan_notifikasi([_notif(workspace, penerima, pelaku, issue, "state", "B", "C")])
        assert len(sisa) == 1

    def test_mode_sekolom_komentar_dan_kolom_berdaftar_tidak_digabung(self, workspace, orang):
        """Saklar ENABLE_EMAIL_BATCH mati = perilaku lama: hanya kolom tunggal yang sama."""
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        _simpan(
            [
                _notif(workspace, penerima, pelaku, issue, "comment", None, "satu"),
                _notif(workspace, penerima, pelaku, issue, "assignees", None, "Budi"),
            ]
        )
        sisa = gabungkan_notifikasi(
            [
                _notif(workspace, penerima, pelaku, issue, "comment", None, "dua"),
                _notif(workspace, penerima, pelaku, issue, "assignees", None, "Citra"),
            ],
            semua=False,
        )
        assert len(sisa) == 2

    def test_sebutan_tidak_disentuh(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        sebut = "in_app:issue_activities:mentioned"
        _simpan([_notif(workspace, penerima, pelaku, issue, "state", "A", "B", sender=sebut)])
        sisa = gabungkan_notifikasi([_notif(workspace, penerima, pelaku, issue, "state", "B", "C", sender=sebut)])
        assert len(sisa) == 1

    def test_kolom_tunggal(self):
        assert kolom_tunggal(Notification(data={"issue_activity": {"field": "state"}})) == "state"
        assert kolom_tunggal(Notification(data={"issue_activity": {"field": "labels"}})) is None
        assert kolom_tunggal(Notification(data=None)) is None


def _email(penerima, pelaku, issue_id, kolom, lama, baru, entity=""):
    return EmailNotificationLog(
        receiver=penerima,
        triggered_by=pelaku,
        entity_identifier=issue_id,
        entity_name="issue",
        entity=entity,
        data={"issue_activity": {"field": kolom, "old_value": lama, "new_value": baru}},
    )


@pytest.mark.unit
class TestGabungkanEmail:
    def test_antrean_yang_belum_diproses_digabung(self, db, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        EmailNotificationLog.objects.bulk_create([_email(penerima, pelaku, issue, "state", "A", "B")])
        sisa = gabungkan_email([_email(penerima, pelaku, issue, "state", "B", "C")])
        assert sisa == []
        baris = EmailNotificationLog.objects.get(receiver=penerima)
        assert baris.data["issue_activity"]["old_value"] == "A"
        assert baris.data["issue_activity"]["new_value"] == "C"

    def test_yang_sudah_diproses_tidak_disentuh(self, db, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        EmailNotificationLog.objects.bulk_create([_email(penerima, pelaku, issue, "state", "A", "B")])
        EmailNotificationLog.objects.update(processed_at=timezone.now())
        assert len(gabungkan_email([_email(penerima, pelaku, issue, "state", "B", "C")])) == 1

    def test_baris_persetujuan_tidak_digabung(self, db, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        EmailNotificationLog.objects.bulk_create(
            [_email(penerima, pelaku, issue, "state", "A", "B", entity="approval")]
        )
        assert len(gabungkan_email([_email(penerima, pelaku, issue, "state", "B", "C", entity="approval")])) == 1


# ---------------------------------------------------------------- lebur penuh (2026-11-17)


def _akt(kolom, lama, baru, detik, ident=None, verb="updated", **ekstra):
    return {
        "id": ident or str(uuid4()),
        "field": kolom,
        "verb": verb,
        "old_value": lama,
        "new_value": baru,
        "old_identifier": ekstra.pop("old_identifier", None),
        "new_identifier": ekstra.pop("new_identifier", None),
        "activity_time": f"2026-11-17T10:00:{detik:02d}Z",
        **ekstra,
    }


def _kabar(workspace, penerima, pelaku, issue_id, aktivitas, sender=SENDER, title=None):
    return Notification(
        workspace=workspace,
        sender=sender,
        triggered_by=pelaku,
        receiver=penerima,
        entity_identifier=issue_id,
        entity_name="issue",
        title=title or f"mengubah {aktivitas['field']}",
        data={"issue_activity": aktivitas},
    )


def _komentar(n, detik):
    return _akt("comment", None, f"<p>komentar {n}</p>", detik, verb="created", issue_comment_id=f"c{n}")


@pytest.mark.unit
class TestLeburPenuh:
    """Semua kabar pembaruan satu pelaku atas satu work item = satu baris per penerima."""

    def test_beberapa_kolom_dan_komentar_jadi_satu_baris(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()

        def k(a):
            return _kabar(workspace, penerima, pelaku, issue, a)

        _simpan([k(_akt("state", "Todo", "Doing", 1))])

        sisa = gabungkan_notifikasi(
            [
                k(_akt("priority", "low", "high", 2)),
                k(_akt("labels", "", "Bug", 3, new_identifier="L1")),
                k(_komentar(1, 4)),
                k(_komentar(2, 5)),
                k(_akt("state", "Doing", "Done", 6)),
            ],
            semua=True,
        )

        assert sisa == []
        baris = Notification.objects.get(receiver=penerima)
        gab = baris.data["gabungan"]
        assert gab["jumlah"] == 6
        assert gab["komentar"] == 2
        assert [p["field"] for p in gab["perubahan"]] == ["state", "priority", "labels"]
        assert gab["perubahan"][0] == {"field": "state", "lama": "Todo", "baru": "Done"}
        assert gab["perubahan"][2]["tambah"] == ["Bug"]
        # Pembaca lama tetap mendapat aktivitas terakhir yang masih hidup.
        assert baris.data["issue_activity"]["field"] == "state"
        assert baris.data["issue_activity"]["old_value"] == "Todo"

    def test_rentetan_komentar_jadi_satu_baris_n_komentar(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()
        sisa = gabungkan_notifikasi(
            [_kabar(workspace, penerima, pelaku, issue, _komentar(n, n)) for n in range(1, 4)], semua=True
        )
        assert len(sisa) == 1
        assert sisa[0].data["gabungan"]["komentar"] == 3
        assert sisa[0].data["issue_activity"]["new_value"] == "<p>komentar 3</p>"

    def test_bolak_balik_hanya_membatalkan_kolom_itu(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()

        def k(a):
            return _kabar(workspace, penerima, pelaku, issue, a)

        _simpan([k(_akt("priority", "low", "high", 1))])
        gabungkan_notifikasi([k(_akt("state", "A", "B", 2)), k(_akt("priority", "high", "low", 3))], semua=True)
        baris = Notification.objects.get(receiver=penerima)
        assert [p["field"] for p in baris.data["gabungan"]["perubahan"]] == ["state"]
        assert baris.data["issue_activity"]["field"] == "state"

    def test_semua_batal_menghapus_baris(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()

        def k(a):
            return _kabar(workspace, penerima, pelaku, issue, a)

        _simpan([k(_akt("labels", "", "Bug", 1, new_identifier="L1"))])
        hasil = gabungkan_notifikasi_rinci([k(_akt("labels", "Bug", "", 2, old_identifier="L1"))], semua=True)
        assert hasil.baru == [] and len(hasil.dihapus) == 1
        assert not Notification.objects.filter(receiver=penerima).exists()

    def test_urutan_tiba_terbalik_tetap_benar(self, workspace, orang):
        """Tugas Celery kedua selesai lebih dulu: nilai lama dari aktivitas paling awal menurut waktunya."""
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()

        def k(a):
            return _kabar(workspace, penerima, pelaku, issue, a)

        _simpan([k(_akt("state", "B", "C", 20))])
        gabungkan_notifikasi([k(_akt("state", "A", "B", 10))], semua=True)
        baris = Notification.objects.get(receiver=penerima)
        assert baris.data["issue_activity"]["old_value"] == "A"
        assert baris.data["issue_activity"]["new_value"] == "C"

    def test_aktivitas_yang_dikirim_ulang_tidak_dihitung_dua_kali(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()

        def k(a):
            return _kabar(workspace, penerima, pelaku, issue, a)

        _simpan([k(_komentar(1, 1))])
        ulang = _komentar(2, 2)
        gabungkan_notifikasi([k(dict(ulang))], semua=True)
        gabungkan_notifikasi([k(dict(ulang))], semua=True)
        baris = Notification.objects.get(receiver=penerima)
        assert baris.data["gabungan"]["komentar"] == 2
        assert baris.data["gabungan"]["jumlah"] == 2

    def test_penugasan_ke_penerima_tugas_baru_dan_balasan_tetap_terpisah(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()

        def k(a, **x):
            return _kabar(workspace, penerima, pelaku, issue, a, **x)

        _simpan([k(_akt("state", "A", "B", 1))])
        sisa = gabungkan_notifikasi(
            [
                k(_akt("assignees", "", "Saya", 2, new_identifier=str(penerima.id))),
                k(_komentar(9, 3), title=JUDUL_BALASAN),
                k(_akt("None", None, None, 4, verb="created")),
            ],
            semua=True,
        )
        assert len(sisa) == 3
        assert Notification.objects.get(receiver=penerima).data["issue_activity"]["new_value"] == "B"

    def test_baris_ditunda_atau_di_luar_jendela_tidak_ditulis_ulang(self, workspace, orang):
        penerima, pelaku, issue = orang("p"), orang("a"), uuid4()

        def k(a):
            return _kabar(workspace, penerima, pelaku, issue, a)

        _simpan([k(_akt("state", "A", "B", 1))])
        Notification.objects.filter(receiver=penerima).update(snoozed_till=timezone.now() + timedelta(hours=1))
        assert len(gabungkan_notifikasi([k(_akt("priority", "low", "high", 2))], semua=True)) == 1

        Notification.objects.filter(receiver=penerima).delete()
        _simpan([k(_akt("state", "A", "B", 1))])
        Notification.objects.filter(receiver=penerima).update(created_at=timezone.now() - timedelta(days=2))
        assert len(gabungkan_notifikasi([k(_akt("priority", "low", "high", 2))], semua=True)) == 1

    def test_penerima_lain_dan_pelaku_lain_tetap_terpisah(self, workspace, orang):
        p1, p2, a, b, issue = orang("p1"), orang("p2"), orang("a"), orang("b"), uuid4()
        sisa = gabungkan_notifikasi(
            [
                _kabar(workspace, p1, a, issue, _akt("state", "A", "B", 1)),
                _kabar(workspace, p2, a, issue, _akt("state", "A", "B", 1)),
                _kabar(workspace, p1, b, issue, _akt("priority", "low", "high", 2)),
            ],
            semua=True,
        )
        assert len(sisa) == 3


@pytest.mark.unit
class TestLipatMurni:
    """Fungsi murni, tanpa database."""

    def test_tambah_lalu_hapus_label_dan_komentar_saling_meniadakan(self):
        k = lipat(lipat({}, _akt("labels", "", "Bug", 1, new_identifier="L1")), _komentar(1, 2))
        k = lipat(k, _akt("labels", "Bug", "", 3, old_identifier="L1"))
        k = lipat(k, _akt("comment", "<p>x</p>", "", 4, verb="deleted", issue_comment_id="c1"))
        assert kolom_hidup(k) == []
        assert terapkan(Notification(data={}), k) is False

    def test_menyunting_komentar_baru_tidak_menambah_hitungan(self):
        k = lipat({}, _komentar(1, 1))
        k = lipat(k, _akt("comment", "<p>a</p>", "<p>b</p>", 2, issue_comment_id="c1"))
        assert ringkasan(k)["komentar"] == 1
        assert kolom_hidup(k) == ["comment"]
