# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.db.models import User
from plane.utils.email_merek import bahasa_penerima, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def susun_deaktivasi(email, url, bahasa):
    """(subjek, html, teks) untuk akun yang dinonaktifkan."""
    t = teks("deaktivasi", bahasa)
    html, polos = render_email(
        "emails/user/user_deactivation.html",
        {"t": t, "login_url": url, "judul": t["judul"], "pratajuk": t["intro"], "email_penerima": email},
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def user_deactivation_email(current_site, user_id):
    try:
        user = User.objects.get(id=user_id)
        subjek, html, polos = susun_deaktivasi(user.email, current_site + "/login", bahasa_penerima(user))
        buat_pesan(ke=user.email, subjek=subjek, html=html, teks=polos).send()
        logging.getLogger("plane.worker").info("Email sent successfully.")
        return
    except Exception as e:
        log_exception(e)
        return
