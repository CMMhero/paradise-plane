# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pratinjau semua email dari God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pratinjau semua email aplikasi di God Mode > Email > Preview.

Baca-saja: tidak menyentuh database dan tidak membuka SMTP. Daftar contoh
diambil dari `kirim_contoh_email` supaya God Mode, berkas pratinjau, dan email
uji selalu memakai susunan yang SAMA dengan pengirim sungguhan. Gambar CID
(logo, foto profil) diganti data: URI karena peramban tidak bisa membaca cid:.
"""

import base64
import re
from contextlib import contextmanager
from unittest import mock

from django.core.mail import get_connection
from django.test import override_settings
from rest_framework import status
from rest_framework.response import Response

from plane.license.api.views.base import BaseAPIView

_BAHASA = ("id", "en")
_KUNCI = re.compile(r"^[a-z0-9-]{1,64}$")


def _bahasa(request) -> str:
    kode = request.query_params.get("lang", "id")
    return kode if kode in _BAHASA else "id"


@contextmanager
def _daftar_contoh():
    """Daftar [(kunci, buat)] dalam konteks yang sama dengan `kirim_contoh_email.handle`."""
    from plane.db.management.commands import kirim_contoh_email as k

    foto = k._png_contoh()
    with (
        override_settings(APP_BASE_URL=k.URL),
        mock.patch("plane.utils.email_merek._baca_avatar", lambda u: (foto, "png") if u.avatar_asset else None),
    ):
        yield k.Command()._daftar()


def _render(buat, bahasa) -> dict:
    from plane.utils.email_merek import buat_pesan

    subjek, html, teks, gambar, lampiran = buat(bahasa)
    # Pesan dirakit lewat jalur kirim yang sama supaya logo CID ikut terpasang,
    # lalu dibuang: backend locmem tidak pernah mengirim apa pun.
    pesan = buat_pesan(
        ke="pratinjau@localhost",
        subjek=subjek,
        html=html,
        teks=teks,
        koneksi=get_connection("django.core.mail.backends.locmem.EmailBackend"),
        dari="noreply@localhost",
        gambar=gambar,
        lampiran=lampiran,
    )
    for g in pesan.gambar:
        html = html.replace(f"cid:{g.cid}", f"data:image/{g.subtipe};base64,{base64.b64encode(g.data).decode()}")
    return {
        "subject": subjek,
        "html": html,
        "text": teks,
        "attachments": [nama for nama, *_ in (lampiran or [])],
    }


class InstanceEmailPreviewEndpoint(BaseAPIView):
    """GET /api/instances/email-preview/?lang=id        -> daftar {key, subject}
    GET /api/instances/email-preview/<key>/?lang=id  -> {key, subject, html, text, attachments}

    Izin: `InstanceAdminPermission` dari `BaseAPIView` (hanya God Mode).
    """

    def get(self, request, key=None):
        bahasa = _bahasa(request)
        with _daftar_contoh() as daftar:
            if key is None:
                hasil = []
                for kunci, buat in daftar:
                    # Satu templat rusak tidak boleh mengosongkan seluruh daftar.
                    try:
                        hasil.append({"key": kunci, "subject": buat(bahasa)[0], "error": False})
                    except Exception as e:  # noqa: BLE001
                        hasil.append({"key": kunci, "subject": f"Render failed: {e.__class__.__name__}", "error": True})
                return Response({"lang": bahasa, "results": hasil}, status=status.HTTP_200_OK)

            if not _KUNCI.match(key):
                return Response({"error": "Invalid template key"}, status=status.HTTP_400_BAD_REQUEST)
            buat = dict(daftar).get(key)
            if buat is None:
                return Response({"error": "Template not found"}, status=status.HTTP_404_NOT_FOUND)
            try:
                isi = _render(buat, bahasa)
            except Exception as e:  # noqa: BLE001
                return Response(
                    {"error": f"Render failed: {e.__class__.__name__}: {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return Response({"key": key, "lang": bahasa, **isi}, status=status.HTTP_200_OK)
