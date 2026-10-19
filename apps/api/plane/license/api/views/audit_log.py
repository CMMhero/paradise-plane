# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: jejak audit khusus God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from datetime import datetime, time

# Django imports
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

# Third Party imports
from rest_framework import status
from rest_framework.response import Response

# Auditlog (MIT, jazzband), lihat NOTICE.md
from auditlog.models import LogEntry

# Module imports
from plane.license.api.views.base import BaseAPIView

# Model yang dipantau (lihat plane/db/audit.py). Dibatasi ke daftar ini supaya
# registrasi lain, kalau kelak ditambah, tidak ikut bocor ke endpoint ini.
_TRACKED_MODELS = ["project", "projectmember", "workspacemember", "issue", "page"]

_ACTION_MAP = {
    "create": LogEntry.Action.CREATE,
    "update": LogEntry.Action.UPDATE,
    "delete": LogEntry.Action.DELETE,
}

_DEFAULT_PER_PAGE = 50
_MAX_PER_PAGE = 200


def _parse_tanggal(nilai, akhir_hari=False):
    """Terima 'YYYY-MM-DD'. Kembalikan None kalau tidak terbaca.

    Batas atas dinaikkan ke akhir hari, kalau tidak `date_to=2026-07-31` akan
    memotong tepat di 00:00 dan membuang seluruh isi hari itu, kesalahan yang
    diam dan bikin orang mengira lognya hilang.
    """
    if not nilai:
        return None
    try:
        d = datetime.strptime(nilai, "%Y-%m-%d").date()
    except ValueError:
        return None
    jam = time.max if akhir_hari else time.min
    return timezone.make_aware(datetime.combine(d, jam))


def _serialize(entry):
    actor = entry.actor
    return {
        "id": entry.id,
        "timestamp": entry.timestamp,
        "action": entry.get_action_display(),
        "model": entry.content_type.model if entry.content_type else None,
        "object_repr": entry.object_repr,
        "object_id": entry.object_pk,
        "changes": entry.changes,
        "remote_addr": entry.remote_addr,
        "actor": (
            {
                "id": str(actor.id),
                "email": actor.email,
                "display_name": actor.display_name,
            }
            if actor
            else None
        ),
    }


class InstanceAuditLogEndpoint(BaseAPIView):
    """Jejak audit seluruh instance, siapa mengubah apa.

    HANYA instance admin (God Mode). `BaseAPIView` God Mode sudah memasang
    `InstanceAdminPermission` sebagai default, jadi tidak ada dekorator izin
    tambahan di sini, dan itu memang disengaja: satu tempat yang menentukan.

    Endpoint ini MENGGANTIKAN versi workspace-level yang lama. Jejak audit
    sengaja tidak bisa dibaca dari aplikasi utama: admin divisi tidak boleh
    memeriksa jejak divisi lain, dan Super Admin yang bekerja tanpa terlihat
    hanya masuk akal kalau jejaknya berada di tempat yang mereka sendiri
    tidak bisa sembunyikan dari sesama Super Admin.

    Filter query:
      ?model=page|issue|project|projectmember|workspacemember
      ?action=create|update|delete
      ?actor=<user_id>
      ?date_from=YYYY-MM-DD  ?date_to=YYYY-MM-DD
      ?search=<teks pada object_repr / email aktor>
      ?page=  ?per_page=  (default 50, maks 200)
    """

    def get(self, request):
        qs = (
            LogEntry.objects.filter(content_type__model__in=_TRACKED_MODELS)
            .select_related("actor", "content_type")
            .order_by("-timestamp")
        )

        model = request.GET.get("model")
        if model in _TRACKED_MODELS:
            qs = qs.filter(content_type__model=model)

        action = request.GET.get("action")
        if action in _ACTION_MAP:
            qs = qs.filter(action=_ACTION_MAP[action])

        actor = request.GET.get("actor")
        if actor:
            qs = qs.filter(actor_id=actor)

        dari = _parse_tanggal(request.GET.get("date_from"))
        if dari:
            qs = qs.filter(timestamp__gte=dari)

        sampai = _parse_tanggal(request.GET.get("date_to"), akhir_hari=True)
        if sampai:
            qs = qs.filter(timestamp__lte=sampai)

        cari = (request.GET.get("search") or "").strip()
        if cari:
            qs = qs.filter(Q(object_repr__icontains=cari) | Q(actor__email__icontains=cari))

        try:
            per_page = min(int(request.GET.get("per_page", _DEFAULT_PER_PAGE)), _MAX_PER_PAGE)
        except ValueError:
            per_page = _DEFAULT_PER_PAGE
        per_page = max(per_page, 1)

        paginator = Paginator(qs, per_page)
        page = paginator.get_page(request.GET.get("page", 1))

        return Response(
            {
                "count": paginator.count,
                "total_pages": paginator.num_pages,
                "page": page.number,
                "per_page": per_page,
                "results": [_serialize(e) for e in page.object_list],
            },
            status=status.HTTP_200_OK,
        )
