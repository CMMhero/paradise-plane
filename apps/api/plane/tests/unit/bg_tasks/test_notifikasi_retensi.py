# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pembersihan harian inbox
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Arsipkan atau hapus notifikasi yang lebih tua dari N hari (God Mode).

Bawaan 7 hari, arsip. Yang dijaga: umur dihitung dari `created_at` tanpa melihat
dibaca atau belum, notifikasi yang ditunda dilewati, 0 mematikannya, pilihan
"hapus" membuang baris sungguhan, dan hanya yang LEBIH tua dari batas yang tersentuh.
"""

from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from plane.bgtasks.notifikasi_retensi import bersihkan_notifikasi_lama
from plane.db.models import Notification
from plane.license.models import InstanceConfiguration
from plane.utils import aturan
from plane.utils.aturan.area_notifikasi import (
    NOTIFICATION_CLEANUP_ACTION,
    NOTIFICATION_CLEANUP_DAYS,
    PEMBERSIHAN_HAPUS,
)

pytestmark = pytest.mark.unit


def _atur(kunci, nilai):
    InstanceConfiguration.objects.update_or_create(
        key=kunci, defaults={"value": aturan.ke_teks(aturan.REGISTRI[kunci], nilai), "category": "PARADISE"}
    )


def _notif(workspace, user, umur_hari, **lain):
    n = Notification.objects.create(
        workspace=workspace,
        receiver=user,
        title="t",
        entity_name="issue",
        sender="issue.activity.updated",
        **lain,
    )
    # created_at diisi otomatis; mundurkan lewat UPDATE.
    Notification.objects.filter(pk=n.pk).update(created_at=timezone.now() - timedelta(days=umur_hari))
    return n


@pytest.fixture(autouse=True)
def tanpa_siaran():
    with mock.patch("plane.bgtasks.notifikasi_retensi.siarkan_notifikasi") as siaran:
        yield siaran


@pytest.mark.django_db
class TestPembersihanNotifikasi:
    def test_bawaan_7_hari_dan_arsip(self):
        assert aturan.get_int(NOTIFICATION_CLEANUP_DAYS) == 7
        assert aturan.get_choice(NOTIFICATION_CLEANUP_ACTION) == "archive"

    def test_arsipkan_yang_lewat_batas_dibaca_atau_belum(self, workspace, create_user):
        lama = _notif(workspace, create_user, 8)
        lama_dibaca = _notif(workspace, create_user, 30, read_at=timezone.now())
        baru = _notif(workspace, create_user, 6)

        assert bersihkan_notifikasi_lama() == 2

        for n in (lama, lama_dibaca):
            n.refresh_from_db()
            assert n.archived_at is not None
        baru.refresh_from_db()
        assert baru.archived_at is None

    def test_yang_sudah_diarsipkan_tidak_ditimpa_waktunya(self, workspace, create_user):
        sebelumnya = timezone.now() - timedelta(days=2)
        n = _notif(workspace, create_user, 20, archived_at=sebelumnya)
        assert bersihkan_notifikasi_lama() == 0
        n.refresh_from_db()
        assert n.archived_at == sebelumnya

    def test_yang_sedang_ditunda_dilewati(self, workspace, create_user):
        ditunda = _notif(workspace, create_user, 20, snoozed_till=timezone.now() + timedelta(days=1))
        selesai_ditunda = _notif(workspace, create_user, 20, snoozed_till=timezone.now() - timedelta(hours=1))
        assert bersihkan_notifikasi_lama() == 1
        ditunda.refresh_from_db()
        selesai_ditunda.refresh_from_db()
        assert ditunda.archived_at is None
        assert selesai_ditunda.archived_at is not None

    def test_nol_mematikan_pembersihan(self, workspace, create_user):
        _atur(NOTIFICATION_CLEANUP_DAYS, 0)
        n = _notif(workspace, create_user, 400)
        assert bersihkan_notifikasi_lama() == 0
        n.refresh_from_db()
        assert n.archived_at is None

    def test_batas_hari_mengikuti_god_mode(self, workspace, create_user):
        _atur(NOTIFICATION_CLEANUP_DAYS, 30)
        sembilan_hari = _notif(workspace, create_user, 9)
        empat_puluh = _notif(workspace, create_user, 40)
        assert bersihkan_notifikasi_lama() == 1
        sembilan_hari.refresh_from_db()
        empat_puluh.refresh_from_db()
        assert sembilan_hari.archived_at is None
        assert empat_puluh.archived_at is not None

    def test_hapus_membuang_baris_termasuk_yang_sudah_diarsipkan(self, workspace, create_user):
        _atur(NOTIFICATION_CLEANUP_ACTION, PEMBERSIHAN_HAPUS)
        lama = _notif(workspace, create_user, 10)
        lama_arsip = _notif(workspace, create_user, 10, archived_at=timezone.now())
        baru = _notif(workspace, create_user, 1)

        assert bersihkan_notifikasi_lama() == 2

        assert not Notification.all_objects.filter(pk__in=[lama.pk, lama_arsip.pk]).exists()
        assert Notification.objects.filter(pk=baru.pk).exists()

    def test_hapus_melewati_yang_ditunda(self, workspace, create_user):
        _atur(NOTIFICATION_CLEANUP_ACTION, PEMBERSIHAN_HAPUS)
        ditunda = _notif(workspace, create_user, 10, snoozed_till=timezone.now() + timedelta(days=2))
        assert bersihkan_notifikasi_lama() == 0
        assert Notification.objects.filter(pk=ditunda.pk).exists()

    def test_penerima_yang_terdampak_diberi_sinyal(self, workspace, create_user, tanpa_siaran):
        _notif(workspace, create_user, 10)
        bersihkan_notifikasi_lama()
        tanpa_siaran.assert_called_once_with(workspace.id, {create_user.id})

    def test_tanpa_yang_lama_tidak_ada_sinyal(self, workspace, create_user, tanpa_siaran):
        _notif(workspace, create_user, 1)
        assert bersihkan_notifikasi_lama() == 0
        tanpa_siaran.assert_not_called()
