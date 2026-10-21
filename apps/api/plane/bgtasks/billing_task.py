# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Sapuan harian tagihan lewat tempo. Hanya berarti di deployment pemilik.

Task ini terdaftar di setiap instance karena `CELERY_IMPORTS` sama di mana-mana,
tapi di instance pelanggan aplikasi `plane.control` tidak dipasang sehingga
tabelnya tidak ada. Karena itu ia memeriksa saklarnya lebih dulu dan berhenti
tanpa menyentuh apa pun, bukan meledak dengan galat tabel tidak ditemukan tiap
pukul empat pagi di seluruh instance pelanggan.
"""

import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger("plane")


@shared_task
def sapu_tagihan_lewat_tempo():
    if not getattr(settings, "ENABLE_CONTROL_PLANE", False):
        return "bukan deployment pemilik, dilewati"

    from plane.control.billing import sapu_lewat_tempo

    hasil = sapu_lewat_tempo()
    logger.info(f"[tagihan] {hasil}")
    return hasil
