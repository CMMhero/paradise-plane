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
_TRACKED_MODELS = ["project", "projectmember", "workspacemember", "issue", "page", "instanceconfiguration"]
# `instanceconfiguration` TIDAK didaftarkan ke auditlog (nilainya bisa rahasia
# terenkripsi). Entrinya ditulis tangan oleh PATCH /api/instances/settings/
# (license/api/views/setelan.py), satu per kunci yang berubah, lama -> baru (KEP-83).

_ACTION_MAP = {
    "create": LogEntry.Action.CREATE,
    "update": LogEntry.Action.UPDATE,
    "delete": LogEntry.Action.DELETE,
}

_DEFAULT_PER_PAGE = 50
_MAX_PER_PAGE = 200

# Urutan yang boleh diminta lewat ?sort=. Kunci lain jatuh ke terbaru dulu.
_URUTAN = {
    "-timestamp": ("-timestamp", "-id"),
    "timestamp": ("timestamp", "id"),
    "actor": ("actor__display_name", "-timestamp"),
    "-actor": ("-actor__display_name", "-timestamp"),
    "action": ("action", "-timestamp"),
    "-action": ("-action", "-timestamp"),
    "model": ("content_type__model", "-timestamp"),
    "-model": ("-content_type__model", "-timestamp"),
    "object": ("object_repr", "-timestamp"),
    "-object": ("-object_repr", "-timestamp"),
    "ip": ("remote_addr", "-timestamp"),
    "-ip": ("-remote_addr", "-timestamp"),
}

# Nilai `actor` khusus untuk entri tanpa aktor (skrip shell, task Celery).
AKTOR_SISTEM = "system"


def _daftar(request, kunci: str) -> list[str]:
    """`?kunci=a,b` -> ["a", "b"]. Kosong dan spasi dibuang."""
    return [v.strip() for v in (request.GET.get(kunci) or "").split(",") if v.strip()]


def _saring_aktor(qs, nilai: list[str], negasi: bool = False):
    """Aktor bisa id user atau `system` (entri tanpa aktor)."""
    if not nilai:
        return qs
    q = Q()
    ids = [v for v in nilai if v != AKTOR_SISTEM]
    if ids:
        q |= Q(actor_id__in=ids)
    if AKTOR_SISTEM in nilai:
        q |= Q(actor__isnull=True)
    return qs.exclude(q) if negasi else qs.filter(q)


def _saring_kolom(qs, kolom: list[str], negasi: bool = False):
    """Entri yang mengubah salah satu kolom ini (`changes` JSONField, auditlog 3.x)."""
    if not kolom:
        return qs
    q = Q()
    for k in kolom:
        q |= Q(changes__has_key=k)
    return qs.exclude(q) if negasi else qs.filter(q)


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

    Filter query (nilai ganda dipisah koma, `*_not` = kebalikannya):
      ?model= / ?model_not=     page,issue,project,projectmember,workspacemember
      ?action= / ?action_not=   create,update,delete
      ?actor= / ?actor_not=     <user_id>,... atau `system` (entri tanpa aktor)
      ?field= / ?field_not=     nama kolom yang berubah (mis. state,target_date)
      ?ip=<sebagian alamat IP>
      ?date_from=YYYY-MM-DD  ?date_to=YYYY-MM-DD
      ?search=<teks pada object_repr / nama atau email aktor / IP>
      ?sort=-timestamp|timestamp|actor|action|model|object|ip (awalan - = menurun)
      ?page=  ?per_page=  (default 50, maks 200)
    """

    def get(self, request):
        urutan = _URUTAN.get(request.GET.get("sort") or "", _URUTAN["-timestamp"])
        qs = (
            LogEntry.objects.filter(content_type__model__in=_TRACKED_MODELS)
            .select_related("actor", "content_type")
            .order_by(*urutan)
        )

        if model := [m for m in _daftar(request, "model") if m in _TRACKED_MODELS]:
            qs = qs.filter(content_type__model__in=model)
        if model_not := [m for m in _daftar(request, "model_not") if m in _TRACKED_MODELS]:
            qs = qs.exclude(content_type__model__in=model_not)

        if action := [_ACTION_MAP[a] for a in _daftar(request, "action") if a in _ACTION_MAP]:
            qs = qs.filter(action__in=action)
        if action_not := [_ACTION_MAP[a] for a in _daftar(request, "action_not") if a in _ACTION_MAP]:
            qs = qs.exclude(action__in=action_not)

        qs = _saring_aktor(qs, _daftar(request, "actor"))
        qs = _saring_aktor(qs, _daftar(request, "actor_not"), negasi=True)
        qs = _saring_kolom(qs, _daftar(request, "field"))
        qs = _saring_kolom(qs, _daftar(request, "field_not"), negasi=True)

        if ip := (request.GET.get("ip") or "").strip():
            qs = qs.filter(remote_addr__icontains=ip)

        dari = _parse_tanggal(request.GET.get("date_from"))
        if dari:
            qs = qs.filter(timestamp__gte=dari)

        sampai = _parse_tanggal(request.GET.get("date_to"), akhir_hari=True)
        if sampai:
            qs = qs.filter(timestamp__lte=sampai)

        cari = (request.GET.get("search") or "").strip()
        if cari:
            qs = qs.filter(
                Q(object_repr__icontains=cari)
                | Q(actor__email__icontains=cari)
                | Q(actor__display_name__icontains=cari)
                | Q(remote_addr__icontains=cari)
            )

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
