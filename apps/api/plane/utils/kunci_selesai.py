# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: tugas selesai terkunci (P29, keputusan 6)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Tugas di status `completed` tidak bisa diubah oleh siapa pun, admin dan Super Admin termasuk.

Satu-satunya perubahan yang boleh adalah membuka kembali: memindahkan status keluar
dari selesai, tanpa perubahan lain di permintaan yang sama. Yang boleh membuka
kembali: Super Admin, admin workspace, dan atasan (Supervisor ke atas) yang semua
assignee-nya bawahannya. Leader tidak: ia tidak menyetujui, jadi ia juga tidak
membatalkan hasil persetujuan.

Kenapa tidak bergantung pada katup gerbang hierarki: kunci ini bukan tangga
jenjang, ia sifat tugas yang sudah selesai. Alur persetujuan (setujui ke selesai,
tolak ke In Progress) menulis langsung lewat `_pindahkan_tugas` dan tidak lewat sini.
"""

PESAN_TERKUNCI = (
    "Tugas ini sudah selesai dan dikunci. Buka kembali tugasnya (pindahkan statusnya "
    "keluar dari selesai) sebelum mengubah apa pun."
)
PESAN_BUKA_SAJA = "Tugas yang selesai hanya bisa dibuka kembali. Simpan perubahan status dulu, baru ubah yang lain."
PESAN_TAK_BOLEH_BUKA = (
    "Tugas yang selesai hanya bisa dibuka kembali oleh atasan assignee-nya, admin workspace, atau Super Admin."
)

# Kunci yang boleh ikut terkirim bersama pembukaan kembali: urutan kartu saat
# diseret antarkolom papan, bukan isi tugas.
_KUNCI_BUKA = frozenset({"state_id", "state", "sort_order"})


def tugas_selesai(issue):
    """True kalau status tugas ini berada di grup `completed`."""
    if issue is None or getattr(issue, "state_id", None) is None:
        return False
    return getattr(issue.state, "group", None) == "completed"


def boleh_buka_kembali(actor, issue):
    """Super Admin, admin workspace, atau Supervisor+ yang semua assignee-nya bawahannya."""
    from plane.db.models import TINGKAT_SUPERVISOR  # noqa: PLC0415
    from plane.utils.hierarki import (  # noqa: PLC0415
        _bawahan_ids,
        adalah_admin_penuh,
        divisi_diawasi,
        tingkat_anggota,
    )

    if actor is None or getattr(actor, "is_anonymous", True):
        return False
    if adalah_admin_penuh(actor, issue.workspace_id):
        return True
    tingkat = tingkat_anggota(actor.id, issue.workspace_id, issue.project_id)
    if tingkat is None or tingkat < TINGKAT_SUPERVISOR:
        return False
    if str(issue.project_id) not in {str(p) for p in divisi_diawasi(actor.id, issue.workspace_id)}:
        return False
    assignee_ids = set(issue.issue_assignee.values_list("assignee_id", flat=True))
    return assignee_ids <= _bawahan_ids(actor.id, issue.workspace_id, issue.project_id)


def _status_tujuan(issue, perubahan):
    nilai = perubahan.get("state_id", perubahan.get("state"))
    return getattr(nilai, "pk", nilai)


def galat_tugas_selesai(issue, actor, perubahan=None):
    """Pesan galat kalau `issue` selesai dan permintaan ini bukan pembukaan kembali yang sah.

    `perubahan` = isi PATCH. None = penulisan apa pun selain status (komentar,
    tautan, lampiran, sub-item, ...), yang selalu ditolak selama tugasnya selesai.
    """
    if not tugas_selesai(issue):
        return None
    if not hasattr(perubahan, "get"):
        return PESAN_TERKUNCI
    tujuan = _status_tujuan(issue, perubahan)
    if tujuan is None or str(tujuan) == str(issue.state_id):
        return PESAN_TERKUNCI

    from plane.db.models import State  # noqa: PLC0415

    grup = State.objects.filter(pk=tujuan, project_id=issue.project_id).values_list("group", flat=True).first()
    if grup is None or grup == "completed":
        return PESAN_TERKUNCI
    if set(perubahan.keys()) - _KUNCI_BUKA:
        return PESAN_BUKA_SAJA
    if not boleh_buka_kembali(actor, issue):
        return PESAN_TAK_BOLEH_BUKA
    return None


def galat_induk_selesai(induk_ids):
    """Sub-item tidak bisa ditambahkan ke, atau dilepas dari, tugas yang selesai."""
    from plane.db.models import Issue  # noqa: PLC0415

    ids = [i for i in induk_ids if i]
    if ids and any(tugas_selesai(i) for i in Issue.objects.filter(id__in=ids).select_related("state")):
        return PESAN_TERKUNCI
    return None
