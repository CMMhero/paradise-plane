# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: sambungan Google Calendar
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Menyambungkan dan memutuskan Google Calendar milik satu pengguna.

Alur persetujuan sengaja TIDAK memakai adapter OAuth login yang sudah ada.
Adapter itu bertugas MEMBUAT SESI dari identitas Google, dan menyambungkan
kalender bukan itu: penggunanya sudah masuk, yang diminta cuma izin tambahan.
Menumpanginya berarti satu bug di sana bisa berubah jadi jalur masuk yang
melewati pemeriksaan sesi.
"""

# Python imports
from urllib.parse import urlencode

# Django imports
from django.conf import settings
from django.core import signing
from django.shortcuts import redirect

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.db.models import AcaraKalender, KalenderGoogle, SCOPE_KALENDER
from plane.license.utils.encryption import encrypt_data
from plane.utils import google_calendar as gcal
from plane.utils.exception_logger import log_exception

from .base import BaseAPIView

# Umur `state`. Cukup panjang untuk orang yang ragu di layar persetujuan
# Google, cukup pendek supaya tautan yang bocor tidak berguna besok.
UMUR_STATE = 600
GARAM_STATE = "paradise.google-calendar.connect"


def _redirect_uri(request):
    """Harus SAMA PERSIS dengan yang didaftarkan di Google Cloud Console.

    Beda satu garis miring pun ditolak dengan `redirect_uri_mismatch`, dan
    pesannya tidak menyebut bagian mana yang berbeda.
    """
    skema = "https" if request.is_secure() else "http"
    return f"{skema}://{request.get_host()}/api/google-calendar/callback/"


def _kembali_ke(pesan):
    """Kembalikan pengguna ke setelan, bawa hasilnya di query string."""
    dasar = (settings.APP_BASE_URL or "").rstrip("/")
    return redirect(f"{dasar}/settings/profile/connections?{urlencode(pesan)}")


class GoogleCalendarConnectEndpoint(BaseAPIView):
    """Mulai alur persetujuan. Membalas URL, bukan langsung mengalihkan.

    Peramban memanggil ini lewat fetch dengan kredensial sesi, lalu berpindah
    sendiri ke URL yang dibalas. Kalau endpoint ini yang mengalihkan, alihannya
    terjadi di dalam permintaan XHR dan pengguna tidak ke mana-mana.
    """

    def get(self, request):
        client_id, client_secret = gcal.kredensial()
        if not (client_id and client_secret):
            return Response(
                {"error": "Google Calendar belum dikonfigurasi di instance ini."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = signing.dumps({"user_id": str(request.user.id)}, salt=GARAM_STATE)
        params = {
            "client_id": client_id,
            "redirect_uri": _redirect_uri(request),
            "response_type": "code",
            "scope": SCOPE_KALENDER,
            # Keduanya WAJIB. Tanpa `access_type=offline` Google tidak pernah
            # memberi refresh token, dan tanpa `prompt=consent` orang yang
            # pernah menyetujui kembali TANPA refresh token. Dua-duanya membuat
            # sambungan tampak berhasil lalu mati diam-diam sejam kemudian.
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
        url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return Response({"url": url}, status=status.HTTP_200_OK)


class GoogleCalendarCallbackEndpoint(BaseAPIView):
    """Titik balik dari Google. Menukar kode jadi refresh token lalu menyimpan."""

    # Google memanggil ini lewat peramban pengguna, bukan lewat XHR, jadi
    # tidak ada header autentikasi. Identitas diambil dari `state` yang
    # ditandatangani, dan itulah sebabnya `state` tidak boleh sekadar acak.
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        if request.GET.get("error"):
            # Pengguna menekan "Batal" di layar Google. Bukan galat sistem.
            return _kembali_ke({"status": "batal"})

        code = request.GET.get("code")
        state = request.GET.get("state")
        if not (code and state):
            return _kembali_ke({"status": "gagal", "sebab": "balasan tidak lengkap"})

        try:
            data = signing.loads(state, salt=GARAM_STATE, max_age=UMUR_STATE)
        except signing.BadSignature:
            # Tanda tangan tidak cocok atau sudah kedaluwarsa. Keduanya berarti
            # permintaan ini tidak berasal dari alur yang kita mulai.
            return _kembali_ke({"status": "gagal", "sebab": "permintaan tidak sah"})

        from plane.db.models import User

        pengguna = User.objects.filter(id=data["user_id"], is_active=True).first()
        if not pengguna:
            return _kembali_ke({"status": "gagal", "sebab": "pengguna tidak ditemukan"})

        try:
            token = gcal.tukar_kode(code, _redirect_uri(request))
            refresh_token = token.get("refresh_token")
            if not refresh_token:
                # Terjadi kalau `prompt=consent` hilang dan orangnya sudah
                # pernah menyetujui. Lebih baik menolak sekarang daripada
                # menyimpan sambungan yang mati besok.
                return _kembali_ke(
                    {"status": "gagal", "sebab": "Google tidak memberi refresh token"}
                )

            KalenderGoogle.objects.update_or_create(
                user=pengguna,
                deleted_at=None,
                defaults={
                    "refresh_token": encrypt_data(refresh_token),
                    "galat_terakhir": "",
                },
            )
        except Exception as e:  # noqa: BLE001
            log_exception(e)
            return _kembali_ke({"status": "gagal", "sebab": "penukaran token gagal"})

        return _kembali_ke({"status": "tersambung"})


class GoogleCalendarStatusEndpoint(BaseAPIView):
    """Keadaan sambungan pengguna yang sedang masuk, dan pemutusannya."""

    def get(self, request):
        s = KalenderGoogle.objects.filter(user=request.user).first()
        client_id, _ = gcal.kredensial()
        return Response(
            {
                # Dipakai UI untuk menjelaskan kenapa tombolnya mati, alih-alih
                # membiarkan orang menekan tombol yang tidak akan pernah jalan.
                "tersedia": bool(client_id),
                "tersambung": bool(s),
                "terakhir_sinkron": s.terakhir_sinkron if s else None,
                "galat_terakhir": s.galat_terakhir if s else "",
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        """Putuskan sambungan.

        Acara yang sudah terlanjur dibuat di kalender orang itu SENGAJA
        ditinggalkan. Menghapusnya berarti tenggat yang sudah mereka lihat dan
        rencanakan lenyap mendadak dari kalender karena menekan tombol yang
        bunyinya cuma "putuskan sambungan". Yang dihentikan adalah pembaruan
        berikutnya, bukan yang sudah ada.
        """
        AcaraKalender.objects.filter(user=request.user).delete()
        KalenderGoogle.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
