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

Inbox diatur saklar `inbox_approval` (bawaan hidup untuk semua jabatan, keputusan
user 2026-11-02). Email diatur per penerima lewat saklar `approval` yang
BERLAKU (plane/utils/preferensi_email.py): bawaan hidup untuk staf, mati untuk
pimpinan, kecuali orangnya menyalakan sendiri.

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


def _boleh(user_id, kunci) -> bool:
    """Saklar `approval` (email) atau `inbox_approval` yang berlaku (preferensi_email.py).

    Galat membaca preferensi: email dianggap mati, inbox dianggap hidup. Atasan yang
    tak pernah melihat pengajuannya lebih buruk daripada satu baris inbox berlebih.
    """
    from plane.utils.preferensi_email import boleh

    try:
        return boleh(user_id, kunci)
    except Exception:  # noqa: BLE001
        return kunci.startswith("inbox_")


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


def _tulis(
    workspace_id, project_id, issue, penerima_id, pemicu, sender, verb, keputusan=None, alasan="", persetujuan=None
):
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
        if _boleh(penerima_id, "inbox_approval"):
            notif = Notification.objects.create(
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
            # Kartu di ruang "Paradise" obrolan, dengan tombol Approve/Reject
            # untuk atasan. Ikut saklar inbox yang sama; menelan galatnya sendiri.
            from plane.utils.kartu_obrolan import kirim_kartu_notifikasi  # noqa: PLC0415

            kirim_kartu_notifikasi([notif], persetujuan=persetujuan)
            from plane.utils.sinyal_data import siarkan_notifikasi_baris  # noqa: PLC0415

            siarkan_notifikasi_baris([notif])
        if _boleh(penerima_id, "approval"):
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


def _data_persetujuan(baris):
    """Bagian `persetujuan` kartu obrolan: cukup untuk memanggil endpoint keputusan."""
    return {
        "id": baris.id,
        "project_id": baris.project_id,
        "status": baris.status,
        "pemohon": baris.pemohon_id,
        "alasan": getattr(baris, "alasan", "") or "",
    }


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
    from plane.utils.hierarki import calon_penyetuju, peta_tingkat, saring_penyetuju

    try:
        issue = _muat_issue(baris.issue_id) or issue or baris.issue
        if issue is None:
            return
        peta = peta_tingkat(baris.workspace_id, baris.project_id)
        # Pengajuan atasan (KEP-83) hanya dikirim ke yang lebih tinggi darinya;
        # pengajuan staf tetap ke semua calon, sama seperti sebelumnya.
        manajer = saring_penyetuju(
            calon_penyetuju(baris.workspace_id, baris.project_id, peta=peta),
            peta,
            baris.pemohon_id,
            issue.created_by_id,
        )
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
            persetujuan=_data_persetujuan(baris),
        )


def _calon_penerima_keputusan(baris, pemutus_id) -> list:
    """Pemohon lebih dulu, lalu assignee tugas yang lain. Pemutus tidak ikut.

    Pekerjaan yang disetujui adalah milik semua yang memegang tugasnya. Dulu hanya
    pemohon yang diberi kabar, jadi rekan sesama assignee (staf yang ditambahkan
    ke tugas itu) tidak pernah menerima email maupun kartu "approved".
    """
    from plane.db.models import IssueAssignee  # noqa: PLC0415

    urut = [baris.pemohon_id] if baris.pemohon_id else []
    if baris.issue_id:
        lain = IssueAssignee.objects.filter(issue_id=baris.issue_id).values_list("assignee_id", flat=True)
        urut += [a for a in lain if a not in urut]
    return [u for u in urut if u != pemutus_id]


def beritahu_diputuskan(baris, aksi, issue=None):
    """Keputusan (setujui/tolak): beritahu pemohon dan assignee tugasnya."""
    try:
        issue = _muat_issue(baris.issue_id) or issue or baris.issue
        if issue is None:
            return
        pemutus_id = getattr(baris.diputuskan_oleh, "id", None)
        target = _calon_penerima_keputusan(baris, pemutus_id)
        for uid in _penerima_aktif(target):
            _tulis(
                baris.workspace_id,
                baris.project_id,
                issue,
                uid,
                baris.diputuskan_oleh,
                SENDER_DIPUTUSKAN,
                "approved" if aksi == "setujui" else "rejected",
                keputusan="disetujui" if aksi == "setujui" else "ditolak",
                alasan=getattr(baris, "alasan", "") or "",
                persetujuan=_data_persetujuan(baris),
            )
    except Exception:  # noqa: BLE001
        logger.exception("Gagal memberitahu keputusan persetujuan %s", getattr(baris, "id", "?"))
