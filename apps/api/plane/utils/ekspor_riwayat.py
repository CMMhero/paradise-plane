# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: riwayat work item di unduhan Excel
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Satu baris `IssueActivity` jadi tiga sel: apa yang berubah, dari apa, menjadi apa."""

# Python imports
from dataclasses import dataclass

# Module imports
from plane.db.models.issue import IssueRelationChoices
from plane.utils.email_teks import PRIORITAS

# Sama dengan riwayat di aplikasi (`IssueActivityEndpoint`). Komentar punya lembar sendiri.
FIELD_TERSEMBUNYI = ("comment", "vote", "reaction", "draft")

_RELASI = frozenset(nama for pasangan in IssueRelationChoices._RELATION_PAIRS for nama in pasangan)

# field -> (id, en). Field yang tidak ada di sini ditulis apa adanya.
_NAMA = {
    "name": ("Judul", "Title"),
    "description": ("Deskripsi", "Description"),
    "state": ("Status", "State"),
    "priority": ("Prioritas", "Priority"),
    "assignees": ("Penanggung jawab", "Assignee"),
    "labels": ("Label", "Label"),
    "modules": ("Modul", "Module"),
    "cycles": ("Siklus", "Cycle"),
    "parent": ("Induk", "Parent"),
    "start_date": ("Tanggal mulai", "Start date"),
    "target_date": ("Tenggat", "Due date"),
    "estimate": ("Estimasi", "Estimate"),
    "link": ("Tautan", "Link"),
    "attachment": ("Lampiran", "Attachment"),
    "approval": ("Persetujuan", "Approval"),
    "archived_at": ("Arsip", "Archive"),
    "is_private": ("Privat", "Private"),
    "intake": ("Intake", "Intake"),
    "relates_to": ("Terkait", "Related to"),
    "duplicate": ("Duplikat", "Duplicate"),
    "blocked_by": ("Diblokir oleh", "Blocked by"),
    "blocking": ("Memblokir", "Blocking"),
    "start_before": ("Mulai sebelum", "Starts before"),
    "start_after": ("Mulai sesudah", "Starts after"),
    "finish_before": ("Selesai sebelum", "Finishes before"),
    "finish_after": ("Selesai sesudah", "Finishes after"),
    "implemented_by": ("Dikerjakan oleh", "Implemented by"),
    "implements": ("Mengerjakan", "Implements"),
}
_KATA = {
    "id": {
        "dibuat": "Work item dibuat",
        "diubah": "Diubah",
        "dihapus": "Dihapus",
        "requested": "Diajukan",
        "approved": "Disetujui",
        "rejected": "Ditolak",
        "diarsipkan": "Diarsipkan",
        "dipulihkan": "Dipulihkan",
        "true": "Ya",
        "false": "Tidak",
        "tersembunyi": "Work item lain",
        "berkas": "berkas",
    },
    "en": {
        "dibuat": "Work item created",
        "diubah": "Changed",
        "dihapus": "Removed",
        "requested": "Requested",
        "approved": "Approved",
        "rejected": "Rejected",
        "diarsipkan": "Archived",
        "dipulihkan": "Restored",
        "true": "Yes",
        "false": "No",
        "tersembunyi": "Another work item",
        "berkas": "file",
    },
}


@dataclass(frozen=True)
class Perubahan:
    apa: str
    dari: str
    menjadi: str


def merujuk_tugas(field) -> bool:
    """Nilai field ini adalah kode work item lain."""
    return field == "parent" or field in _RELASI


def uraikan(baris: dict, bahasa: str, tugas_terlihat: set, nama_lampiran: dict) -> Perubahan:
    """`baris` = satu `IssueActivity` sebagai dict, nilainya di kunci `lama` dan `baru`."""
    field, verb = baris["field"], baris["verb"]
    kata = _KATA[bahasa]
    dari, menjadi = baris["lama"] or "", baris["baru"] or ""
    if not field:
        return Perubahan(kata["dibuat"] if verb == "created" else verb, dari, menjadi)

    kunci = "estimate" if field.startswith("estimate_") else field
    nama = _NAMA.get(kunci)
    apa = nama[0 if bahasa == "id" else 1] if nama else field.replace("_", " ")

    if field == "description":
        dari, menjadi = "", kata["diubah"]
    elif field == "priority":
        dari, menjadi = (PRIORITAS[bahasa].get(v, v) for v in (dari, menjadi))
    elif field == "is_private":
        dari, menjadi = (kata.get(v, v) for v in (dari, menjadi))
    elif field == "archived_at":
        dari, menjadi = "", kata["dipulihkan" if menjadi == "restore" else "diarsipkan"]
    elif field == "approval":
        # `new_value` berisi alasan penolakan.
        keputusan = kata.get(verb, verb)
        dari, menjadi = "", f"{keputusan}: {menjadi}" if menjadi else keputusan
    elif field == "attachment":
        # `new_value` berisi alamat berkas di penyimpanan: yang dibaca orang namanya.
        if verb == "deleted":
            dari, menjadi = "", kata["dihapus"]
        else:
            dari, menjadi = "", nama_lampiran.get(baris["new_identifier"]) or kata["berkas"]
    elif merujuk_tugas(field):
        # Baris relasi menyimpan id work item lawannya di `old_identifier`, juga saat ditambahkan.
        id_baru = baris["new_identifier"] or (baris["old_identifier"] if field in _RELASI else None)
        # Penghapusan relasi menulis baris di sisi lawan dengan id work item baris itu sendiri, padahal
        # nilainya kode work item pertama. Id seperti itu tidak membuktikan apa pun.
        terlihat = tugas_terlihat - {baris["issue_id"]}
        if dari and baris["old_identifier"] not in terlihat:
            dari = kata["tersembunyi"]
        if menjadi and id_baru not in terlihat:
            menjadi = kata["tersembunyi"]
    return Perubahan(apa, dari, menjadi)
