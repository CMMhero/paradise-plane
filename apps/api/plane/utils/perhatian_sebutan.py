# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: bahan kartu aksi di widget "Needs attention"
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Pelengkap baris widget "Needs attention" (`plane/utils/perhatian.py`).

Kartu aksi butuh tiga hal yang tidak ada di kueri kelompok: komentar yang
menyebut saya (sebutan di komentar tidak disimpan di `IssueMention`), isi
sebutan sebagai teks biasa, dan assignee tiap tugas untuk aturan hak ubah di
web. Semuanya dikerjakan sekali per panggilan, bukan per baris.
"""

import re

from bs4 import BeautifulSoup
from django.db.models import Q

from plane.db.models import IssueAssignee, IssueComment, Notification, User
from plane.utils.akses_privat import saring_tugas_privat

BATAS_CUPLIKAN = 200
_PENGIRIM_SEBUTAN = "in_app:issue_activities:mentioned"
_ID_PENGGUNA = re.compile(r'entity_identifier="([0-9a-f-]{36})"')


def sebutan_komentar(user, project_ids, sejak, kecuali_grup):
    """Komentar hidup di tugas aktif yang menyebut `user` secara langsung (bukan @all), bukan tulisannya sendiri.

    Tugas privat yang tak boleh ia lihat tidak ikut, walau komentarnya menyebut dia.
    """
    return saring_tugas_privat(
        IssueComment.objects.filter(
            project_id__in=project_ids,
            created_at__gte=sejak,
            comment_html__contains=f'entity_identifier="{user.id}"',
            issue__deleted_at__isnull=True,
            issue__is_draft=False,
            issue__archived_at__isnull=True,
        )
        .exclude(issue__state__group__in=kecuali_grup)
        .exclude(actor=user),
        user,
        prefix="issue__",
    )


def teks_polos(html, nama_by_id):
    """HTML komentar jadi satu baris teks; `<mention-component>` jadi `@Nama`. Tidak ada tag yang lolos."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all("mention-component"):
        jenis = tag.get("entity_name")
        if jenis == "everyone_mention":
            tag.replace_with("@all")
        elif jenis == "user_mention":
            tag.replace_with(f"@{nama_by_id.get(tag.get('entity_identifier'), '')}".rstrip("@"))
        else:
            tag.replace_with("")
    teks = " ".join(soup.get_text(" ").split())
    return teks if len(teks) <= BATAS_CUPLIKAN else teks[: BATAS_CUPLIKAN - 1].rstrip() + "…"


def _notifikasi_sebutan(user, workspace_id, issue_ids):
    """{(issue_id, comment_id | None): notification_id} untuk sebutan yang belum dibaca."""
    peta = {}
    for nid, issue_id, data in Notification.objects.filter(
        Q(archived_at__isnull=True),
        receiver=user,
        workspace_id=workspace_id,
        sender=_PENGIRIM_SEBUTAN,
        read_at__isnull=True,
        entity_identifier__in=issue_ids,
    ).values_list("id", "entity_identifier", "data"):
        aktivitas = (data or {}).get("issue_activity") or {}
        komentar = aktivitas.get("new_identifier") if aktivitas.get("field") == "comment" else None
        peta.setdefault((str(issue_id), komentar), str(nid))
    return peta


def lengkapi_baris(user, workspace_id, items):
    """Isi `assignee_ids` di semua baris dan cuplikan + `notification_id` di baris sebutan. Tiga kueri tetap."""
    if not items:
        return
    issue_ids = {i["id"] for i in items}
    assignee = {}
    for issue_id, assignee_id in IssueAssignee.objects.filter(issue_id__in=issue_ids).values_list(
        "issue_id", "assignee_id"
    ):
        assignee.setdefault(str(issue_id), []).append(str(assignee_id))

    sebutan = [i for i in items if "comment_id" in i]
    nama = {}
    if sebutan:
        dicari = {uid for i in sebutan if i.get("_html") for uid in _ID_PENGGUNA.findall(i["_html"])}
        nama = {str(pk): n for pk, n in User.objects.filter(pk__in=dicari).values_list("pk", "display_name")}
        notifikasi = _notifikasi_sebutan(user, workspace_id, issue_ids)

    for i in items:
        i["assignee_ids"] = assignee.get(i["id"], [])
    for i in sebutan:
        i["snippet"] = teks_polos(i.pop("_html", None), nama) if i["comment_id"] else None
        i["notification_id"] = notifikasi.get((i["id"], i["comment_id"]))
