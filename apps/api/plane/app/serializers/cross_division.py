# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: permintaan tugas lintas divisi
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Serialisasi permintaan tugas lintas divisi.

Aturan keras modul ini: **daftar-putih**. Peminta berada DI LUAR project
tujuan (KEP-02), jadi setiap medan yang dikembalikan ke dia adalah kebocoran
yang harus disengaja. Jangan pernah menyerahkan `IntakeIssue` atau `Issue`
mentah ke `Response` dari sini -- `IssueStateIntakeSerializer` misalnya memakai
`fields = "__all__"` dan memuat assignee, label, serta detail project
(`plane/app/serializers/intake.py:127`).

Medan yang sengaja TIDAK dikembalikan, beserta alasannya:

* `assignees` / `assignee_details` -- siapa yang mengerjakan di divisi tujuan.
  Berguna, tapi itu kebijakan, bukan kebutuhan teknis; lihat pertanyaan
  terbuka nomor 3 di `.herdr/crossdiv-desain.md`.
* `target_date` -- tenggat adalah janji antar-orang, bukan data publik.
* `labels`, `description_html` versi divisi tujuan, komentar -- paling sering
  memuat angka harga/tender.
"""

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Project

# Status permintaan dipetakan dari `IntakeIssue.status`.
#   -2 menunggu · -1 ditolak · 0 ditunda · 1 diterima · 2 duplikat
_STATUS_PERMINTAAN = {
    -2: "menunggu",
    -1: "ditolak",
    0: "ditunda",
    1: "diterima",
    2: "duplikat",
}

# Status tugas dipetakan dari `Issue.state.group`, dan sengaja KASAR
# (terbuka/selesai) supaya tidak membocorkan nama kolom papan divisi tujuan.
_GROUP_TERBUKA = {"backlog", "unstarted", "started"}
_GROUP_TUTUP = {"completed", "cancelled"}


class DivisiTujuanSerializer(serializers.ModelSerializer):
    """Divisi yang bisa menerima permintaan: id, kode, nama. Tidak lebih.

    Nama & kode project memang sudah terlihat seluruh anggota workspace lewat
    `GET /workspaces/<slug>/projects/` (`plane/app/views/project/base.py:176`,
    izin level WORKSPACE), jadi endpoint ini tidak membuka apa pun yang baru.
    """

    class Meta:
        model = Project
        fields = ["id", "identifier", "name"]
        read_only_fields = fields


def status_permintaan(intake_issue):
    """Teks status untuk peminta. `None` berarti permintaannya sudah lenyap."""
    if intake_issue is None:
        return "dibatalkan"
    return _STATUS_PERMINTAAN.get(intake_issue.status, "menunggu")


def status_tugas(intake_issue):
    """Kasar: belum diterima / terbuka / selesai / tidak dikerjakan."""
    if intake_issue is None:
        return "dibatalkan"
    if intake_issue.status != 1:
        return "belum_diterima" if intake_issue.status in (-2, 0) else "tidak_dikerjakan"
    group = getattr(getattr(intake_issue.issue, "state", None), "group", None)
    if group in _GROUP_TUTUP:
        return "selesai" if group == "completed" else "dibatalkan"
    if group in _GROUP_TERBUKA:
        return "terbuka"
    # Trio `state` NULL atau masih `triage` setelah diterima: jujur saja
    # "belum_diterima" daripada menebak "terbuka".
    return "belum_diterima"


def nomor_tugas(intake_issue, tujuan_project):
    """`IT-42`, atau `None` kalau divisi tujuan belum/tidak menerimanya."""
    if intake_issue is None or intake_issue.issue is None or intake_issue.status != 1:
        return None
    sequence = getattr(intake_issue.issue, "sequence_id", None)
    if sequence is None:
        return None
    return f"{tujuan_project.identifier}-{sequence}"


def serialize_permintaan(p):
    """Satu baris permintaan, bentuk yang dilihat PEMINTA.

    `judul` dan `catatan` ditulis peminta sendiri. `nomor_tugas`,
    `status_permintaan`, dan `status_tugas` adalah satu-satunya hal yang
    menyeberang dari project tujuan, dan ketiganya sengaja kasar.
    """
    intake_issue = p.intake_issue
    tujuan = p.tujuan_project
    return {
        "id": str(p.id),
        "dibuat_pada": p.created_at,
        "catatan": p.catatan or "",
        "asal": {
            "id": str(p.asal_project_id),
            "identifier": p.asal_project.identifier,
            "name": p.asal_project.name,
        },
        "tujuan": {
            "id": str(p.tujuan_project_id),
            "identifier": tujuan.identifier,
            "name": tujuan.name,
        },
        "judul": getattr(getattr(intake_issue, "issue", None), "name", None),
        "nomor_tugas_tujuan": nomor_tugas(intake_issue, tujuan),
        "status_permintaan": status_permintaan(intake_issue),
        "status_tugas": status_tugas(intake_issue),
    }
