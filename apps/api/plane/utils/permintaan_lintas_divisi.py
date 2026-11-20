# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: keputusan atas permintaan lintas departemen
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Peminta diberi tahu saat departemen tujuan menerima atau menolak permintaannya.

Keputusannya tetap diambil lewat jalur Intake bawaan (`IntakeIssueSerializer.update`),
supaya wewenang terima/tolak hanya ada di satu tempat. Modul ini cuma menempel di
ujung jalur itu: menyimpan alasan tolak dan menulis satu baris inbox untuk peminta.

Peminta bukan anggota departemen tujuan (KEP-02), jadi baris inbox-nya menumpang
project ASAL (tempat ia anggota) dan hanya membawa yang memang boleh ia lihat:
judul yang ia tulis sendiri, kode departemen tujuan, dan nomor tugas kalau diterima.
Tidak ada kartu obrolan: kartu membawa assignee, status, dan tenggat tugas di
departemen tujuan, dan itulah yang sengaja tidak diseberangkan
(`serializers/cross_division.py`).

Menelan galatnya sendiri: pemberitahuan tidak boleh menggagalkan keputusan.
"""

import logging

logger = logging.getLogger(__name__)

# Nilai `IntakeIssue.source` permintaan lintas departemen (CharField tanpa `choices`).
SOURCE_LINTAS_DIVISI = "CROSSDIV"
SENDER_DIPUTUSKAN = "in_app:cross_division:decided"
FIELD_LINTAS_DIVISI = "cross_division"
# `IntakeIssue.status` -> verb baris inbox. Status lain (ditunda, duplikat) tidak dikabarkan.
VERB_KEPUTUSAN = {1: "accepted", -1: "declined"}


def catat_keputusan(intake_issue, aktor, alasan=""):
    """Dipanggil sesudah status `intake_issue` berubah. Selain terima/tolak lintas departemen: diam."""
    verb = VERB_KEPUTUSAN.get(intake_issue.status)
    if intake_issue.source != SOURCE_LINTAS_DIVISI or verb is None:
        return
    try:
        _catat(intake_issue, aktor, verb, (alasan or "").strip() if verb == "declined" else "")
    except Exception:  # noqa: BLE001
        logger.exception("Gagal mencatat keputusan permintaan lintas departemen %s", intake_issue.id)


def _catat(intake_issue, aktor, verb, alasan):
    from plane.db.models import Notification, PermintaanLintasDivisi  # noqa: PLC0415
    from plane.utils.preferensi_email import boleh  # noqa: PLC0415
    from plane.utils.sinyal_data import siarkan_notifikasi_baris  # noqa: PLC0415

    permintaan = (
        PermintaanLintasDivisi.objects.filter(intake_issue=intake_issue)
        .select_related("asal_project", "tujuan_project", "intake_issue__issue")
        .first()
    )
    if permintaan is None:
        return

    crossdiv = {**(intake_issue.extra or {}).get("crossdiv", {}), "alasan_tolak": alasan}
    intake_issue.extra = {**(intake_issue.extra or {}), "crossdiv": crossdiv}
    intake_issue.save(update_fields=["extra", "updated_at"])

    if not boleh(permintaan.diminta_oleh_id, "inbox_approval"):
        return
    issue = intake_issue.issue
    tujuan = permintaan.tujuan_project
    notif = Notification.objects.create(
        workspace_id=permintaan.workspace_id,
        project=permintaan.asal_project,
        sender=SENDER_DIPUTUSKAN,
        triggered_by=aktor,
        receiver_id=permintaan.diminta_oleh_id,
        entity_identifier=issue.id,
        entity_name="issue",
        title="",
        message={"keputusan": verb, "alasan": alasan},
        data={
            "issue": {
                "id": str(issue.id),
                "name": issue.name,
                "identifier": tujuan.identifier,
                "sequence_id": issue.sequence_id if verb == "accepted" else None,
                "state_name": "",
                "state_group": "",
            },
            "issue_activity": {
                "id": None,
                "verb": verb,
                "field": FIELD_LINTAS_DIVISI,
                "actor": str(aktor.id) if aktor else "",
                "new_value": tujuan.name,
                "old_value": "",
                "issue_comment": alasan,
                "old_identifier": None,
                "new_identifier": None,
                "activity_time": None,
            },
        },
    )
    siarkan_notifikasi_baris([notif])
