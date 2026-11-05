# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: penulis jejak audit God Mode
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu pintu untuk entri audit yang bukan perubahan model terdaftar.

Perubahan model yang didaftarkan ke django-auditlog (plane/db/audit.py) tercatat
otomatis. Setelan instance, bawaan, akun, dan sesi bukan model terdaftar (nilainya
bisa rahasia atau modelnya tak diaudit), jadi endpoint God Mode menulis entrinya
lewat `catat_godmode`. Setiap entri SELALU membawa `content_type`, `object_repr`
yang terbaca, dan `additional_data = {kind, label}`, sehingga kolom "object type"
dan "object" di Logs > Audit tidak pernah kosong.
"""

from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType

from plane.license.models import InstanceConfiguration
from plane.utils.ip_address import get_client_ip

# kind -> jenis objek yang tampil di kolom "Object type" (English, God Mode).
JENIS_LABEL: dict[str, str] = {
    "instance_setting": "Instance setting",
    "instance_config": "Instance configuration",
    "instance_profile": "Instance profile",
    "member_defaults": "Member defaults",
    "member_defaults_apply": "Member defaults",
    "project_defaults": "Project defaults",
    "super_admin": "Super Admin",
    "account": "Account",
    "account_preferences": "Account preferences",
    "email_config": "Email configuration",
    "account_session": "Account session",
    "workspace": "Workspace",
    "hierarchy": "Organization hierarchy",
    "division_members": "Division members",
    "trash": "Trash",
}

LABEL_CADANGAN = "System setting"


def catat_godmode(
    request,
    *,
    kind: str,
    label: str,
    action: int = LogEntry.Action.UPDATE,
    changes: dict | None = None,
    object_pk: str = "",
    detail: str = "",
    extra: dict | None = None,
) -> LogEntry:
    """Tulis satu entri audit God Mode yang berlabel penuh."""
    actor = request.user if getattr(request.user, "is_authenticated", False) else None
    label = (label or "").strip() or LABEL_CADANGAN
    return LogEntry.objects.create(
        content_type=ContentType.objects.get_for_model(InstanceConfiguration),
        object_pk=str(object_pk or kind),
        object_repr=label[:200],
        action=action,
        changes=changes or {},
        changes_text=detail or label,
        actor=actor,
        actor_email=getattr(actor, "email", None),
        remote_addr=get_client_ip(request) or None,
        additional_data={**(extra or {}), "kind": kind, "label": label},
    )


def jenis_objek(entry) -> str:
    """Label jenis objek yang terbaca; tidak pernah kosong (juga untuk baris lama)."""
    data = entry.additional_data if isinstance(entry.additional_data, dict) else {}
    if data.get("kind") in JENIS_LABEL:
        return JENIS_LABEL[data["kind"]]
    ct = entry.content_type
    if ct is not None:
        model = ct.model_class()
        nama = str(model._meta.verbose_name) if model is not None else ct.model
        if ct.model == "instanceconfiguration":
            return JENIS_LABEL["instance_setting"]
        if nama:
            return nama[:1].upper() + nama[1:]
    return LABEL_CADANGAN


def label_objek(entry) -> str:
    """Nama objek yang terbaca; jatuh ke additional_data lalu label umum."""
    repr_ = (entry.object_repr or "").strip()
    if repr_:
        return repr_
    data = entry.additional_data if isinstance(entry.additional_data, dict) else {}
    cadangan = data.get("label") or data.get("key")
    if cadangan:
        return f"Instance setting: {cadangan}" if data.get("key") and not data.get("label") else str(cadangan)
    return LABEL_CADANGAN
