# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.utils import aturan
from plane.utils.aturan.area_keamanan import SIGN_IN_CODE_MINUTES
from plane.utils.email_merek import bahasa_untuk_alamat, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def menit_kode():
    """Umur kode yang disebut email: aturan God Mode SIGN_IN_CODE_MINUTES (sama dengan TTL kodenya)."""
    return aturan.get_int(SIGN_IN_CODE_MINUTES)


def susun_magic_link(email, token, bahasa, grup="magic", menit=None):
    """(subjek, html, teks). Murni: dipakai pengirim dan `kirim_contoh_email`.

    `grup="ganti_email"` = kode verifikasi alamat baru (templat yang sama).
    `menit` = umur kode; pengirim mengisinya dengan `menit_kode()`. Kosong = bawaan
    aturan, supaya contoh email tetap dirender tanpa database.
    """
    if menit is None:
        menit = aturan.REGISTRI[SIGN_IN_CODE_MINUTES].default
    t = teks(grup, bahasa, kode=token, menit=menit)
    html, polos = render_email(
        "emails/auth/magic_signin.html",
        {"t": t, "code": token, "judul": t["judul"], "pratajuk": t["intro"], "email_penerima": email},
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def magic_link(email, key, token):
    try:
        subjek, html, polos = susun_magic_link(email, token, bahasa_untuk_alamat(email), menit=menit_kode())
        buat_pesan(ke=email, subjek=subjek, html=html, teks=polos).send()
        logging.getLogger("plane.worker").info("Email sent successfully.")
        return
    except Exception as e:
        log_exception(e)
        return
