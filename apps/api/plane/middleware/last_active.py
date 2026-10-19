# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jejak "sedang memakai"
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Memperbarui `User.last_active` dari lalu lintas yang memang sudah terjadi.

Sebelum ini `last_active` hanya diisi sekali saat login
(`authentication/adapter/base.py`), jadi namanya menjanjikan sesuatu yang tidak
pernah ia lakukan, praktis salinan `last_login_time`. Akibatnya tidak ada apa
pun di sistem yang tahu bedanya orang yang sedang bekerja dari orang yang
sesinya masih hidup tapi sudah pulang tiga jam lalu.

Kenapa middleware dan bukan ping dari browser: setiap layar di aplikasi ini
sudah memanggil API terus-menerus. Menumpang ke lalu lintas itu tidak menambah
satu pun request, dan tidak ada yang perlu diubah di frontend.
"""

# Python imports
import logging

# Django imports
from django.utils import timezone

logger = logging.getLogger("plane")

# Jeda tulis. Tanpa ini setiap request jadi satu UPDATE ke tabel users, dan
# satu layar Plane bisa menembakkan belasan request sekaligus.
#
# Angkanya harus LEBIH KECIL dari AMBANG_AKTIF_MENIT (5 menit) di
# `db/models/login_activity.py`. Kalau tidak, nilai yang tersimpan bisa lebih
# basi daripada ambangnya sendiri dan orang yang sedang mengetik terbaca
# "tidak aktif". 60 detik memberi jarak aman 4 menit.
JEDA_TULIS_DETIK = 60


class LastActiveMiddleware:
    """Stempel `last_active`, dibatasi supaya tidak satu tulis per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._stempel(request)
        except Exception:
            # Jejak keaktifan tidak pernah boleh menggagalkan request. Ditulis
            # sesudah response terbentuk, jadi kegagalan di sini tidak
            # mengubah apa pun yang dilihat pemakai.
            logger.exception("Gagal memperbarui last_active")
        return response

    @staticmethod
    def _stempel(request):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return

        sekarang = timezone.now()
        sebelumnya = getattr(user, "last_active", None)
        if sebelumnya and (sekarang - sebelumnya).total_seconds() < JEDA_TULIS_DETIK:
            return

        # Impor lokal: middleware dimuat sebelum app registry siap.
        from plane.db.models import User

        # `.update()` bukan `.save()`, save() memicu sinyal dan auditlog, dan
        # stempel keaktifan tiap menit akan membanjiri jejak audit dengan
        # perubahan yang tidak menarik bagi siapa pun.
        User.objects.filter(pk=user.pk).update(last_active=sekarang)
        # Selaraskan objek di memori supaya request berikutnya dalam proses yang
        # sama tidak menulis lagi karena membaca nilai lama.
        user.last_active = sekarang
