# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tes penggabungan kabar pembaruan beruntun
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Perubahan beruntun atas kolom bernilai tunggal jadi satu kabar.

Yang dikunci bukan hanya "digabung", tapi juga yang TIDAK boleh digabung: komentar,
kolom berdaftar, pelaku berbeda, kabar yang sudah dibaca.
"""

from uuid import uuid4

import pytest
from django.utils import timezone

from plane.db.models import EmailNotificationLog, Notification, User
from plane.utils.gabung_kabar import gabungkan_email, gabungkan_notifikasi, kolom_tunggal

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

    def test_komentar_dan_kolom_berdaftar_tidak_digabung(self, workspace, orang):
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
            ]
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
