# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging

from celery import shared_task

from plane.bgtasks.magic_link_code_task import susun_magic_link
from plane.utils.email_merek import bahasa_untuk_alamat, buat_pesan, render_email
from plane.utils.email_teks import teks
from plane.utils.exception_logger import log_exception


def susun_email_diubah(email, bahasa):
    """(subjek, html, teks) sesudah alamat email berhasil diganti."""
    t = teks("email_diubah", bahasa, email=email)
    html, polos = render_email(
        "emails/user/email_updated.html",
        {"t": t, "judul": t["judul"], "pratajuk": t["intro"], "email_penerima": email},
        bahasa,
    )
    return t["subjek"], html, polos


@shared_task
def send_email_update_magic_code(email, token):
    # Alamat baru belum tersimpan di akun mana pun, jadi bahasanya bahasa bawaan
    # kecuali alamat itu sudah milik akun lain (yang memang akan ditolak).
    try:
        subjek, html, polos = susun_magic_link(email, token, bahasa_untuk_alamat(email), grup="ganti_email")
        buat_pesan(ke=email, subjek=subjek, html=html, teks=polos).send()
        logging.getLogger("plane.worker").info("Email sent successfully.")
        return
    except Exception as e:
        log_exception(e)
        return


@shared_task
def send_email_update_confirmation(email):
    """Konfirmasi ke alamat BARU sesudah penggantian berhasil."""
    try:
        subjek, html, polos = susun_email_diubah(email, bahasa_untuk_alamat(email))
        buat_pesan(ke=email, subjek=subjek, html=html, teks=polos).send()
        logging.getLogger("plane.worker").info(f"Email update confirmation sent successfully to {email}.")
        return
    except Exception as e:
        log_exception(e)
        return
