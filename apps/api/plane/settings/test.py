# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Test Settings"""

import os

# Bidang kendali dinyalakan di seluruh uji. Ia dipasang bersyarat lewat variabel
# lingkungan yang dibaca `common.py` saat diimpor, jadi menyetelnya HARUS terjadi
# sebelum baris impor di bawah. Kalau ia hanya menyala di produksi pemilik,
# satu-satunya tempat kodenya pernah dijalankan adalah produksi itu sendiri.
#
# Ditulis TEGAS, bukan setdefault: berkas .env yang dipakai compose (contohnya
# menonaktifkan bidang kendali, yang benar untuk instance pelanggan) ikut masuk
# ke lingkungan container uji dan setdefault kalah darinya -- akibatnya
# `plane.control` tidak terpasang dan seluruh uji penagihan gagal saat import.
# Uji SELALU butuh bidang kendali menyala, di mesin mana pun dijalankannya.
os.environ["ENABLE_CONTROL_PLANE"] = "1"

from .common import *  # noqa

DEBUG = True

# Send it in a dummy outbox
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

INSTALLED_APPS.append(  # noqa
    "plane.tests"
)
