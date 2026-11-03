# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.utils.email_merek import bahasa_untuk_alamat, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def susun_magic_link(email, token, bahasa, grup="magic"):
    """(subjek, html, teks). Murni: dipakai pengirim dan `kirim_contoh_email`.

    `grup="ganti_email"` = kode verifikasi alamat baru (templat yang sama).
    """
    t = teks(grup, bahasa, kode=token)
    html, polos = render_email(
        "emails/auth/magic_signin.html",
        {"t": t, "code": token, "judul": t["judul"], "pratajuk": t["intro"], "email_penerima": email},
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def magic_link(email, key, token):
    try:
        subjek, html, polos = susun_magic_link(email, token, bahasa_untuk_alamat(email))
        buat_pesan(ke=email, subjek=subjek, html=html, teks=polos).send()
        logging.getLogger("plane.worker").info("Email sent successfully.")
        return
    except Exception as e:
        log_exception(e)
        return
