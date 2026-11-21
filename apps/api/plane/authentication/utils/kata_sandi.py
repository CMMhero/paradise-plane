# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: kekuatan sandi dan umur tautan reset dari God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Dua aturan sandi area F, satu tempat untuk setiap pemeriksa.

- `sandi_cukup_kuat`: skor zxcvbn minimal PASSWORD_MIN_STRENGTH (3 atau 4; tidak
  pernah di bawah 3, pilihannya memang hanya itu). Dipakai daftar, atur sandi,
  ganti sandi, reset sandi (app dan space), sandi Super Admin, dan perintah
  `reset_password`.
- `TokenResetSandi`: token reset sandi Django dengan umur PASSWORD_RESET_LINK_MINUTES.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from zxcvbn import zxcvbn

from plane.utils import aturan
from plane.utils.aturan.area_keamanan import PASSWORD_MIN_STRENGTH, PASSWORD_RESET_LINK_MINUTES


def sandi_cukup_kuat(sandi: str) -> bool:
    return zxcvbn(sandi)["score"] >= int(aturan.get_choice(PASSWORD_MIN_STRENGTH))


class TokenResetSandi(PasswordResetTokenGenerator):
    """PasswordResetTokenGenerator yang umurnya dari God Mode, bukan settings.

    Django membandingkan umur token dengan settings.PASSWORD_RESET_TIMEOUT di
    dalam `check_token`. Daripada menyalin pemeriksaan hash-nya, jam yang dipakai
    `check_token` digeser sebesar selisih umur aturan dan settings: token sah
    selama `PASSWORD_RESET_LINK_MINUTES`. `make_token` tidak tergeser, jadi
    perubahan aturan juga berlaku untuk tautan yang sudah terkirim. Satu objek
    per panggilan, jadi geseran tidak bocor antar permintaan.
    """

    _geser_detik = 0

    def check_token(self, user, token):
        umur = aturan.get_int(PASSWORD_RESET_LINK_MINUTES) * 60
        self._geser_detik = umur - settings.PASSWORD_RESET_TIMEOUT
        try:
            return super().check_token(user, token)
        finally:
            self._geser_detik = 0

    def _now(self):
        return super()._now() - timedelta(seconds=self._geser_detik)
