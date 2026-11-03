# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.utils.email_merek import bahasa_untuk_alamat, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def susun_lupa_sandi(email, url, bahasa):
    """(subjek, html, teks)."""
    t = teks("lupa_sandi", bahasa, email=email)
    html, polos = render_email(
        "emails/auth/forgot_password.html",
        {"t": t, "forgot_password_url": url, "judul": t["judul"], "pratajuk": t["intro"], "email_penerima": email},
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def forgot_password(first_name, email, uidb64, token, current_site):
    try:
        relative_link = f"/accounts/reset-password/?uidb64={uidb64}&token={token}&email={email}"
        abs_url = str(current_site) + relative_link
        subjek, html, polos = susun_lupa_sandi(email, abs_url, bahasa_untuk_alamat(email))
        buat_pesan(ke=email, subjek=subjek, html=html, teks=polos).send()
        logging.getLogger("plane.worker").info("Email sent successfully")
        return
    except Exception as e:
        log_exception(e)
        return
