# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.management import BaseCommand, CommandError

from plane.utils.email_merek import bahasa_untuk_alamat, buat_pesan, render_email
from plane.utils.email_teks import teks


class Command(BaseCommand):
    """Kirim satu email uji ke alamat yang diberikan, lewat konfigurasi SMTP God Mode."""

    def add_arguments(self, parser):
        parser.add_argument("to_email", type=str, help="receiver's email")

    def handle(self, *args, **options):
        receiver_email = options.get("to_email")
        if not receiver_email:
            raise CommandError("Receiver email is required")

        bahasa = bahasa_untuk_alamat(receiver_email)
        t = teks("uji", bahasa)
        html, polos = render_email(
            "emails/test_email.html",
            {"t": t, "judul": t["subjek"], "pratajuk": t["intro"], "email_penerima": receiver_email},
            bahasa,
        )
        self.stdout.write(self.style.SUCCESS("Trying to send test email..."))
        try:
            buat_pesan(ke=receiver_email, subjek=t["subjek"], html=html, teks=polos).send()
            self.stdout.write(self.style.SUCCESS("Email successfully sent"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: Email could not be delivered due to {e}"))
