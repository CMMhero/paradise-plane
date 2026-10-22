# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: pemberitahuan persetujuan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Inbox + antrean email untuk persetujuan penugasan (KEP-30 lanjutan).

Aliran persetujuan sebelumnya diam: pengajuan muncul, diputuskan, diajukan
ulang — tanpa satu pun baris Notification atau EmailNotificationLog. Akibatnya
atasan tidak pernah diping saat ada yang menunggu, dan pemohon hanya tahu dari
membuka antrean. Modul ini menutup lubang itu di tiga titik:

- diajukan (pengajuan pertama via `catat_persetujuan`, pengajuan ulang via
  `ajukan_ulang`) → atasan yang boleh memutuskan
- diputuskan (setujui/tolak) → pemohon

Inbox SELALU ditulis (konsisten dengan notifikasi issue lain: saklar preferensi
hanya mengatur email). Email diatur per penerima lewat
`UserNotificationPreference.approval`; baris preferensi yang belum ada dianggap
True (pengguna lama tidak perlu migrasi manual).

Semua fungsi menelan galatnya sendiri: pemberitahuan tidak boleh menggagalkan
permintaan utama.
"""

import logging

logger = logging.getLogger(__name__)

# `entity_name` WAJIB "issue": daftar inbox memfilter entity_name="issue",
# dan kartu inbox butuh `data.issue.id` untuk peek + `data.issue_activity.field`
# untuk merender. `entity="approval"` hanya dipakai antrean email untuk
# memisahkan baris ini dari digest issue umum.
SENDER_DIAJUKAN = "in_app:approval:submitted"
SENDER_DIPUTUSKAN = "in_app:approval:decided"
ENTITY_EMAIL_APPROVAL = "approval"
FIELD_APPROVAL = "approval"


def bahasa_penerima(user) -> str:
    """'id' kalau preferensi bahasa penerima Indonesia, else 'en'.

    Bahasa tinggal di `Profile` (OneToOne), bukan di `User` — web menyimpannya
    lewat PATCH /api/users/me/profile/. Profil yang belum ada = 'en'.
    """
    try:
        profil = getattr(user, "profile", None)
        bahasa = getattr(profil, "language", None) if profil is not None else None
        return "id" if str(bahasa or "en").lower().startswith("id") else "en"
    except Exception:  # noqa: BLE001
        return "en"


def _boleh_email(user_id) -> bool:
    from plane.db.models import UserNotificationPreference

    try:
        pref = UserNotificationPreference.objects.filter(user_id=user_id).first()
    except Exception:  # noqa: BLE001
        return True
    if pref is None:
        return True
    return bool(getattr(pref, "approval", True))


def _penerima_aktif(user_ids):
    """Saring id ke User aktif non-bot, kembalikan dict id -> User."""
    from plane.db.models import User

    try:
        orang = User.objects.filter(id__in=list(user_ids), is_active=True, is_bot=False)
    except Exception:  # noqa: BLE001
        return {}
    return {u.id: u for u in orang}


def _data_issue(issue):
    project = getattr(issue, "project", None)
    state = getattr(issue, "state", None)
    return {
        "id": str(issue.id),
        "name": getattr(issue, "name", ""),
        "identifier": getattr(project, "identifier", "") if project else "",
        "sequence_id": getattr(issue, "sequence_id", None),
        "state_name": getattr(state, "name", "") if state else "",
        "state_group": getattr(state, "group", "") if state else "",
    }


def _tulis(workspace_id, project_id, issue, penerima_id, pemicu, sender, verb, keputusan=None, alasan=""):
    """Satu baris inbox + (kalau saklar email penerima hidup) satu baris email."""
    from plane.db.models import EmailNotificationLog, Notification, Project, Workspace

    try:
        workspace = Workspace.objects.filter(pk=workspace_id).first()
        project = Project.objects.filter(pk=project_id).first()
        if workspace is None or project is None:
            return
        data = {
            "issue": _data_issue(issue),
            "issue_activity": {
                "id": None,
                "verb": verb,
                "field": FIELD_APPROVAL,
                "actor": str(getattr(pemicu, "id", "")),
                "new_value": keputusan or "",
                "old_value": "",
                "issue_comment": alasan or "",
                "old_identifier": None,
                "new_identifier": None,
                "activity_time": None,
            },
        }
        Notification.objects.create(
            workspace=workspace,
            project=project,
            sender=sender,
            triggered_by=pemicu,
            receiver_id=penerima_id,
            entity_identifier=issue.id,
            entity_name="issue",
            title="",
            message={"keputusan": keputusan, "alasan": alasan},
            data=data,
        )
        if _boleh_email(penerima_id):
            EmailNotificationLog.objects.create(
                receiver_id=penerima_id,
                triggered_by=pemicu,
                entity_identifier=issue.id,
                entity_name="issue",
                entity=ENTITY_EMAIL_APPROVAL,
                data=data,
                old_value="",
                new_value=keputusan or "",
            )
    except Exception:  # noqa: BLE001
        logger.exception("Gagal menulis pemberitahuan persetujuan untuk %s", penerima_id)


def _muat_issue(issue_id):
    """Issue + project + state dalam satu query untuk payload notifikasi."""
    from plane.db.models import Issue

    try:
        return (
            Issue.objects.select_related("project", "project__workspace", "state")
            .filter(pk=issue_id)
            .first()
        )
    except Exception:  # noqa: BLE001
        return None


def beritahu_diajukan(baris, issue=None):
    """Pengajuan (baru atau ulang): beritahu atasan yang boleh memutuskan."""
    from plane.utils.hierarki import calon_penyetuju

    try:
        issue = _muat_issue(baris.issue_id) or issue or baris.issue
        if issue is None:
            return
        manajer = calon_penyetuju(baris.workspace_id, baris.project_id)
    except Exception:  # noqa: BLE001
        logger.exception("Gagal menghitung calon penyetuju untuk %s", getattr(baris, "id", "?"))
        return
    target = [uid for uid in manajer if uid != baris.pemohon_id]
    for uid in _penerima_aktif(target):
        _tulis(
            baris.workspace_id,
            baris.project_id,
            issue,
            uid,
            baris.pemohon,
            SENDER_DIAJUKAN,
            "submitted",
        )


def beritahu_diputuskan(baris, aksi, issue=None):
    """Keputusan (setujui/tolak): beritahu pemohon."""
    try:
        issue = _muat_issue(baris.issue_id) or issue or baris.issue
        if issue is None or baris.pemohon_id is None:
            return
        if baris.pemohon_id == getattr(baris.diputuskan_oleh, "id", None):
            return
        penerima = _penerima_aktif([baris.pemohon_id])
        if baris.pemohon_id not in penerima:
            return
        _tulis(
            baris.workspace_id,
            baris.project_id,
            issue,
            baris.pemohon_id,
            baris.diputuskan_oleh,
            SENDER_DIPUTUSKAN,
            "approved" if aksi == "setujui" else "rejected",
            keputusan="disetujui" if aksi == "setujui" else "ditolak",
            alasan=getattr(baris, "alasan", "") or "",
        )
    except Exception:  # noqa: BLE001
        logger.exception("Gagal memberitahu keputusan persetujuan %s", getattr(baris, "id", "?"))
