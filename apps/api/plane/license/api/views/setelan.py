# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: setelan instance God Mode (KEP-83)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""GET/PATCH /api/instances/settings/: seluruh setelan Paradise dalam satu registri.

Bentuk, bawaan, rentang, dan pilihan datang dari `plane/utils/setelan_instance.py`,
jadi God Mode tidak perlu lagi mencerminkan BAWAAN/ANGKA di kodenya sendiri.

PATCH bersifat semua-atau-tidak-sama-sekali: satu nilai tak sah = 400 dan tidak
satu baris pun ditulis. Kunci SENSITIF yang berubah wajib membawa
`"confirm": "CHANGE RULES"`, dan setiap kunci yang berubah (sensitif atau bukan)
dicatat satu baris di jejak audit God Mode (Logs > Audit log) sebagai
`instanceconfiguration`, lama -> baru.
"""

# Django imports
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

# Third party imports
from auditlog.models import LogEntry
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.license.api.views.base import BaseAPIView
from plane.license.models import InstanceConfiguration
from plane.utils.cache import invalidate_cache
from plane.utils.ip_address import get_client_ip
from plane.utils.setelan_instance import (
    FRASA_KONFIRMASI,
    SENSITIF,
    NilaiTidakSah,
    daftar_setelan,
    efektif,
    nilai_tersimpan,
    normalkan,
    semua_kunci,
)

KATEGORI = "PARADISE"
GALAT_KONFIRMASI = "confirm_required"


def catat_audit(request, kunci: str, lama: str, baru: str, baris: InstanceConfiguration) -> None:
    """Satu entri jejak audit untuk satu kunci yang berubah."""
    actor = request.user if getattr(request.user, "is_authenticated", False) else None
    LogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(InstanceConfiguration),
        object_pk=str(baris.pk),
        object_repr=kunci,
        action=LogEntry.Action.UPDATE,
        changes={"value": [lama, baru]},
        changes_text=f"{kunci}: {lama} -> {baru}",
        actor=actor,
        actor_email=getattr(actor, "email", None),
        remote_addr=get_client_ip(request) or None,
        additional_data={"key": kunci, "sensitive": kunci in SENSITIF},
    )


class InstanceSettingsEndpoint(BaseAPIView):
    """Hanya instance admin (`BaseAPIView` God Mode sudah memasang izinnya)."""

    def get(self, request):
        return Response({"settings": daftar_setelan()}, status=status.HTTP_200_OK)

    @invalidate_cache(path="/api/instances/configurations/", user=False)
    @invalidate_cache(path="/api/instances/", user=False)
    def patch(self, request):
        nilai = request.data.get("values") if hasattr(request.data, "get") else None
        if not isinstance(nilai, dict) or not nilai:
            return Response(
                {"error": 'Body must be {"values": {KEY: value, ...}}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Validasi SEMUA dulu. Satu galat = tidak ada yang ditulis.
        baru, galat = {}, {}
        for kunci, mentah in nilai.items():
            try:
                baru[kunci] = normalkan(kunci, mentah)
            except NilaiTidakSah as e:
                galat[kunci] = str(e)
        if galat:
            return Response({"errors": galat}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Yang benar-benar berubah, dibandingkan dengan nilai yang BERLAKU.
        tersimpan = nilai_tersimpan(baru.keys())
        lama = {k: efektif(k, tersimpan) for k in baru}
        berubah = {k: v for k, v in baru.items() if v != lama[k]}

        # 3. Aturan sensitif hanya berubah dengan frasa konfirmasi yang diketik.
        sensitif = sorted(k for k in berubah if k in SENSITIF)
        if sensitif and request.data.get("confirm") != FRASA_KONFIRMASI:
            return Response(
                {"error": GALAT_KONFIRMASI, "keys": sensitif},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4. Tulis + audit dalam satu transaksi.
        with transaction.atomic():
            for kunci in semua_kunci():
                if kunci not in berubah:
                    continue
                baris, _ = InstanceConfiguration.objects.get_or_create(
                    key=kunci, defaults={"category": KATEGORI, "is_encrypted": False}
                )
                baris.value = berubah[kunci]
                baris.save(update_fields=["value", "updated_at"])
                catat_audit(request, kunci, lama[kunci], berubah[kunci], baris)

        return Response({"settings": daftar_setelan()}, status=status.HTTP_200_OK)
