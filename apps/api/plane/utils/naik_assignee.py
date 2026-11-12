# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: assignee anak naik ke induk dan module
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Assignee sub-work item otomatis ikut jadi assignee induknya dan anggota module-nya.

Keputusan user 2026-11-12: orang yang mengerjakan sebagian sebuah tugas ikut
tercatat di tugas induknya (berantai ke atas) dan di module tempat tugas-tugas
itu berada, tanpa ada yang menambahkan tangan.

Aturan:

* Hanya MENAMBAH. Melepas assignee dari anak tidak mencabutnya dari induk: induk
  bisa saja dipegang orang itu karena alasan lain, dan menebaknya berarti
  menghapus data.
* Berlaku untuk seluruh rantai induk (anak, induk, kakek, ...), dengan batas
  kedalaman dan penjaga siklus.
* Module: anggota module = assignee semua tugas di rantai itu yang berada di
  module tersebut. Module milik induk ikut, karena induk kini ditugaskan ke
  orang itu juga.
* Sengaja TIDAK melewati gerbang penugasan hierarki (`galat_penugasan`): ini
  turunan dari penugasan yang sudah lolos gerbang pada anaknya, bukan penugasan
  baru oleh seseorang.

Dipanggil sesudah assignee, induk, atau module sebuah tugas berubah (serializer
buat/ubah tugas, tambah sub-work item, tambah tugas ke module). Idempoten dan
murah: dua baca, tulis hanya yang belum ada.
"""

from django.db import IntegrityError

BATAS_KEDALAMAN = 20


def _rantai(issue_id):
    """[issue, induk, kakek, ...] sebagai baris (id, parent_id, project_id, workspace_id, created_by_id)."""
    from plane.db.models import Issue  # noqa: PLC0415

    hasil, terlihat, kini = [], set(), issue_id
    while kini is not None and kini not in terlihat and len(hasil) <= BATAS_KEDALAMAN:
        terlihat.add(kini)
        baris = (
            Issue.objects.filter(pk=kini)
            .values_list("id", "parent_id", "project_id", "workspace_id", "created_by_id")
            .first()
        )
        if baris is None:
            break
        hasil.append(baris)
        kini = baris[1]
    return hasil


def naikkan_assignee(issue_id):
    """Sebarkan assignee `issue_id` ke induknya dan ke module-module di rantai itu.

    Mengembalikan (jumlah assignee induk ditambah, jumlah anggota module ditambah).
    """
    from plane.db.models import IssueAssignee, ModuleIssue, ModuleMember  # noqa: PLC0415

    rantai = _rantai(issue_id)
    if not rantai:
        return 0, 0
    asal = set(IssueAssignee.objects.filter(issue_id=issue_id).values_list("assignee_id", flat=True))
    if not asal:
        return 0, 0

    ditambah_induk = 0
    for induk_id, _, project_id, workspace_id, pembuat_id in rantai[1:]:
        ada = set(IssueAssignee.objects.filter(issue_id=induk_id).values_list("assignee_id", flat=True))
        baru = asal - ada
        if not baru:
            continue
        try:
            IssueAssignee.objects.bulk_create(
                [
                    IssueAssignee(
                        issue_id=induk_id,
                        assignee_id=uid,
                        project_id=project_id,
                        workspace_id=workspace_id,
                        created_by_id=pembuat_id,
                        updated_by_id=pembuat_id,
                    )
                    for uid in baru
                ],
                ignore_conflicts=True,
            )
        except IntegrityError:
            continue
        ditambah_induk += len(baru)

    ditambah_module = 0
    ids_rantai = [b[0] for b in rantai]
    module_ke_proj = {
        module_id: (project_id, workspace_id)
        for module_id, project_id, workspace_id in ModuleIssue.objects.filter(issue_id__in=ids_rantai).values_list(
            "module_id", "project_id", "workspace_id"
        )
    }
    for module_id, (project_id, workspace_id) in module_ke_proj.items():
        ada = set(ModuleMember.objects.filter(module_id=module_id).values_list("member_id", flat=True))
        baru = asal - ada
        if not baru:
            continue
        try:
            ModuleMember.objects.bulk_create(
                [
                    ModuleMember(module_id=module_id, member_id=uid, project_id=project_id, workspace_id=workspace_id)
                    for uid in baru
                ],
                ignore_conflicts=True,
            )
        except IntegrityError:
            continue
        ditambah_module += len(baru)
    return ditambah_induk, ditambah_module
