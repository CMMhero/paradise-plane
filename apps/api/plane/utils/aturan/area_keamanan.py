# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area F, berkas, undangan, sesi, keamanan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area F inventaris: berkas, undangan, sesi, keamanan.

Area paling berbahaya: nilai yang salah bisa membuka sistem. Karena itu:

- Semua aturan di sini `risk=high` (frasa konfirmasi + audit), dan setiap angka
  punya lantai dan plafon (`min`/`max`) sehingga suntingan God Mode tidak pernah
  bisa mematikan perlindungannya (batas laju tidak bisa 0 atau tak terbatas,
  sandi tidak bisa lebih pendek dari 8 karakter, daftar tipe unggahan hanya bisa
  dicoret, tidak pernah ditambah).
- Semua dibaca per permintaan (`applies=live`), tidak ada yang dibaca saat
  proses mulai. Throttle DRF dibuat ulang per permintaan, jadi lajunya cukup
  dibaca di `get_rate`.
- Empat aturan dulu hanya env (AUTHENTICATION_RATE_LIMIT, API_KEY_RATE_LIMIT,
  ADMIN_SESSION_COOKIE_AGE, SESSION_SAVE_EVERY_REQUEST). Env lama itu kini
  BENIH bawaan, dijepit ke batas aman, pola yang sama dengan SESSION_DAYS di
  saklar_instance.py. Tidak ada nama env baru (KEP-48).

Tidak dipindah: siapa yang boleh mengundang (F4) tetap Admin workspace di kode.
Melebarkannya butuh gerbang di layar anggota apps/web dan membuka jalur izin
baru; itu keputusan pemilik terpisah. Batas paket dan dormansi (F14) tetap env.
"""

import os

from plane.utils.aturan.jenis import BOOL, CHOICE, INT, KEY_LIST, NEXT_RUN, TINGGI, Rule
from plane.utils.tipe_unggahan import TIPE_LAMPIRAN

UPLOAD_BLOCKED_FILE_TYPES = "UPLOAD_BLOCKED_FILE_TYPES"
EXPORT_FILE_KEEP_DAYS = "EXPORT_FILE_KEEP_DAYS"
PASSWORD_MIN_STRENGTH = "PASSWORD_MIN_STRENGTH"
LOGIN_ATTEMPTS_PER_MINUTE = "LOGIN_ATTEMPTS_PER_MINUTE"
EMAIL_CHANGE_CODES_PER_HOUR = "EMAIL_CHANGE_CODES_PER_HOUR"
SIGN_IN_CODE_MINUTES = "SIGN_IN_CODE_MINUTES"
SIGN_IN_CODE_WRONG_TRIES = "SIGN_IN_CODE_WRONG_TRIES"
SIGN_IN_CODE_RESENDS = "SIGN_IN_CODE_RESENDS"
PASSWORD_RESET_LINK_MINUTES = "PASSWORD_RESET_LINK_MINUTES"
GOD_MODE_SESSION_MINUTES = "GOD_MODE_SESSION_MINUTES"
APP_SESSION_SLIDING = "APP_SESSION_SLIDING"
API_KEY_REQUESTS_PER_MINUTE = "API_KEY_REQUESTS_PER_MINUTE"

_DETIK_PERIODE = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def _benih_laju_per_menit(env: str, cadangan: int, minimum: int, maksimum: int) -> int:
    """Env DRF lama ("10/minute", "600/hour") jadi angka per menit, dibulatkan ke bawah lalu dijepit.

    Env kosong atau rusak = `cadangan` (bawaan kode lama).
    """
    try:
        jumlah, periode = os.environ.get(env, "").strip().split("/")
        per_menit = int(jumlah) * 60 // _DETIK_PERIODE[periode.strip()[0]]
    except (ValueError, KeyError, IndexError):
        return cadangan
    return max(minimum, min(per_menit, maksimum))


def _benih_menit(env: str, cadangan: int, minimum: int, maksimum: int) -> int:
    """Env lama dalam detik jadi menit, dibulatkan ke bawah lalu dijepit. Kosong atau rusak = `cadangan`."""
    try:
        menit = int(os.environ.get(env, "").strip()) // 60
    except ValueError:
        return cadangan
    return max(minimum, min(menit, maksimum))


ATURAN = (
    Rule(
        key=UPLOAD_BLOCKED_FILE_TYPES,
        kind=KEY_LIST,
        default=(),
        choices=tuple((tipe, tipe) for tipe in TIPE_LAMPIRAN),
        group="files",
        label="File types blocked from upload",
        help=(
            "Ticked types can no longer be attached to work items, Wiki pages, Wiki files, chat, or the public API. "
            "Files already uploaded stay. This list can only block types. Types outside it, such as web pages and "
            "programs, are never accepted. Profile pictures and covers are not affected."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=EXPORT_FILE_KEEP_DAYS,
        kind=INT,
        default=8,
        min=1,
        max=30,
        group="files",
        label="Days an export file is kept",
        help=(
            "Exported files are deleted from storage this many days after the export. The download link itself "
            "stops working after 7 days whatever this says. Checked once a day."
        ),
        risk=TINGGI,
        applies=NEXT_RUN,
    ),
    Rule(
        key=PASSWORD_MIN_STRENGTH,
        kind=CHOICE,
        default=0,
        choices=((0, "Length only"), (3, "Strong"), (4, "Very strong")),
        group="security",
        label="Minimum password strength",
        help=(
            "Checked when someone signs up, sets, changes, or resets a password, Super Admins included. "
            "Existing passwords keep working. Every password needs at least 8 characters. Length only accepts "
            "any such password, including easy ones like 12345678. Strong and Very strong also refuse "
            "guessable passwords."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=LOGIN_ATTEMPTS_PER_MINUTE,
        kind=INT,
        default=_benih_laju_per_menit("AUTHENTICATION_RATE_LIMIT", 10, 3, 60),
        min=3,
        max=60,
        group="security",
        label="Sign-in attempts per minute",
        help=(
            "Sign-in, sign-up, code, and password reset requests allowed per minute from one network address. "
            "An office behind one internet connection shares this budget. The default comes from the server's "
            "AUTHENTICATION_RATE_LIMIT, if set."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=EMAIL_CHANGE_CODES_PER_HOUR,
        kind=INT,
        default=3,
        min=1,
        max=10,
        group="security",
        label="Email change codes per hour",
        help="How many verification codes one person can request per hour when changing their email address.",
        risk=TINGGI,
    ),
    Rule(
        key=SIGN_IN_CODE_MINUTES,
        kind=INT,
        default=10,
        min=5,
        max=30,
        group="security",
        label="Email code lifetime in minutes",
        help=(
            "How long a sign-in code or an email change code stays valid. The email states this number. "
            "Codes already sent keep the time they were sent with."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=SIGN_IN_CODE_WRONG_TRIES,
        kind=INT,
        default=5,
        min=3,
        max=10,
        group="security",
        label="Wrong sign-in code tries",
        help="After this many wrong entries the sign-in code stops working and a new one has to be requested.",
        risk=TINGGI,
    ),
    Rule(
        key=SIGN_IN_CODE_RESENDS,
        kind=INT,
        default=3,
        min=1,
        max=5,
        group="security",
        label="Sign-in code resends",
        help=(
            "How many extra sign-in codes one email address can request before it has to wait for the last "
            "code to expire."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=PASSWORD_RESET_LINK_MINUTES,
        kind=INT,
        default=60,
        min=10,
        max=1440,
        group="security",
        label="Password reset link lifetime in minutes",
        help="How long the link in a forgot password email works. Applies to links already sent as well.",
        risk=TINGGI,
    ),
    Rule(
        key=GOD_MODE_SESSION_MINUTES,
        kind=INT,
        default=_benih_menit("ADMIN_SESSION_COOKIE_AGE", 60, 5, 480),
        min=5,
        max=480,
        group="security",
        label="God Mode idle sign-out in minutes",
        help=(
            "A God Mode session ends after this many minutes without use. Each God Mode request extends it. "
            "The default comes from the server's ADMIN_SESSION_COOKIE_AGE, if set."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=APP_SESSION_SLIDING,
        kind=BOOL,
        default=os.environ.get("SESSION_SAVE_EVERY_REQUEST", "0") == "1",
        group="security",
        label="Keep active app sessions signed in",
        help=(
            "Off: an app session ends a fixed number of days after sign-in (Stay signed in for). On: each "
            "request restarts that count, so people who keep working are never signed out. The default comes "
            "from the server's SESSION_SAVE_EVERY_REQUEST, if set."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=API_KEY_REQUESTS_PER_MINUTE,
        kind=INT,
        default=_benih_laju_per_menit("API_KEY_RATE_LIMIT", 60, 10, 600),
        min=10,
        max=600,
        group="security",
        label="API key requests per minute",
        help=(
            "Requests one API key may make per minute on the public API. The default comes from the server's "
            "API_KEY_RATE_LIMIT, if set."
        ),
        risk=TINGGI,
    ),
)
