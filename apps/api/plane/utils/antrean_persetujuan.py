# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: antrean persetujuan satu workspace
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Semua yang menunggu keputusan saya, dari semua departemen yang saya awasi.

Keputusan user 2026-11-20: supervisor, manager, sekretaris, dan direktur tidak
perlu membuka tab Persetujuan tiap departemen satu per satu. Halaman ini hanya
MEMBACA; keputusan tetap lewat endpoint per project yang sudah ada, supaya
aturan wewenang tetap di satu tempat:

* `selesai` = pengajuan selesai (`PersetujuanPenugasan`). Wewenang per baris dari
  `pengajuan_boleh_diputuskan`, aturan yang sama dengan POST setuju/tolak.
  Diputuskan lewat `POST .../persetujuan-penugasan/<id>/`.
* `permintaan` = permintaan lintas departemen yang masih di Intake tujuan.
  Tampil untuk yang mengawasi departemen tujuan (`divisi_diawasi`) DAN admin di
  project itu, karena terima/tolak Intake menuntut admin project. Diputuskan
  lewat `PATCH .../intake-issues/<issue_id>/`.

Jumlah kueri tetap berapa pun banyaknya baris: dua kueri baris, satu assignee,
satu peta departemen, ditambah biaya `pengajuan_boleh_diputuskan` (peta jenjang
sekali per project yang punya antrean).
"""

from plane.db.models.project import ROLE
from plane.db.models import (
    IssueAssignee,
    PermintaanLintasDivisi,
    PersetujuanPenugasan,
    ProjectMember,
    STATUS_PERSETUJUAN_MENUNGGU,
    Workspace,
)
from plane.db.superadmin import is_super_admin
from plane.utils.hierarki import divisi_diawasi, pengajuan_boleh_diputuskan
from plane.utils.ringkasan_divisi import _peta_departemen, project_terjangkau

JENIS_SELESAI = "selesai"
JENIS_PERMINTAAN = "permintaan"
# `IntakeIssue.status` yang belum dijawab: menunggu dan ditunda.
_INTAKE_BELUM_DIJAWAB = (-2, 0)


def _unit(record):
    return {"id": str(record.id), "kode": record.kode, "nama": record.nama} if record else None


def _tempat(dp):
    """(departemen, divisi, cabang) project ini; cabang None = kantor pusat."""
    if dp is None:
        return None, None, None
    dep = dp.departemen
    return _unit(dep), _unit(dep.divisi), _unit(dep.divisi.cabang)


def _item(jenis, id_, issue, pemohon, diminta_pada, peta, assignees, **tambahan):
    project = issue.project
    departemen, divisi, cabang = _tempat(peta.get(project.id))
    state = issue.state
    return {
        "jenis": jenis,
        "id": str(id_),
        "project": {"id": str(project.id), "identifier": project.identifier, "name": project.name},
        "departemen": departemen,
        "divisi": divisi,
        "cabang": cabang,
        "tugas": {
            "id": str(issue.id),
            "nomor": f"{project.identifier}-{issue.sequence_id}",
            "judul": issue.name,
            "state": (
                {"id": str(state.id), "name": state.name, "group": state.group, "color": state.color} if state else None
            ),
            "assignee_ids": assignees.get(issue.id, []),
            "target_date": issue.target_date,
        },
        "pemohon": {"id": str(pemohon.id), "nama": pemohon.display_name} if pemohon else None,
        "diminta_pada": diminta_pada,
        **tambahan,
    }


def _pengajuan_selesai(user, workspace_id, project_ids):
    # Saringan tugas sama dengan kelompok `decide` di widget Needs attention.
    baris = list(
        PersetujuanPenugasan.objects.filter(
            project_id__in=project_ids,
            status=STATUS_PERSETUJUAN_MENUNGGU,
            issue__deleted_at__isnull=True,
            issue__archived_at__isnull=True,
            issue__is_draft=False,
        )
        .exclude(pemohon=user)
        .exclude(issue__state__group="cancelled")
        .select_related("issue", "issue__project", "issue__state", "pemohon")
    )
    kunci = {(b.project_id, b.pemohon_id, b.issue.created_by_id) for b in baris}
    sah = pengajuan_boleh_diputuskan(user, workspace_id, kunci) if kunci else set()
    return [b for b in baris if (b.project_id, b.pemohon_id, b.issue.created_by_id) in sah]


def _permintaan_masuk(user, project_ids):
    admin_di = ProjectMember.objects.filter(
        member=user, is_active=True, role=ROLE.ADMIN.value, project_id__in=project_ids
    ).values_list("project_id", flat=True)
    return list(
        PermintaanLintasDivisi.objects.filter(
            tujuan_project_id__in=admin_di,
            intake_issue__status__in=_INTAKE_BELUM_DIJAWAB,
            intake_issue__deleted_at__isnull=True,
            intake_issue__issue__deleted_at__isnull=True,
        ).select_related(
            "asal_project",
            "diminta_oleh",
            "intake_issue__issue__project",
            "intake_issue__issue__state",
        )
    )


def susun_antrean(user, slug):
    """Balasan `GET /workspaces/<slug>/persetujuan/`."""
    workspace_id = Workspace.objects.values_list("id", flat=True).get(slug=slug)
    diawasi = divisi_diawasi(user.id, workspace_id)
    # Super Admin memutuskan pengajuan di departemen tanpa atasan sama sekali.
    boleh = bool(diawasi) or is_super_admin(user)
    if not boleh:
        return {"boleh_memutuskan": False, "jumlah": 0, "hasil": []}

    project_ids = set(project_terjangkau(user, slug).values_list("id", flat=True))
    selesai = _pengajuan_selesai(user, workspace_id, project_ids)
    permintaan = _permintaan_masuk(user, project_ids & diawasi)

    issue_ids = [b.issue_id for b in selesai] + [p.intake_issue.issue_id for p in permintaan]
    assignees = {}
    for issue_id, assignee_id in IssueAssignee.objects.filter(issue_id__in=issue_ids).values_list(
        "issue_id", "assignee_id"
    ):
        assignees.setdefault(issue_id, []).append(str(assignee_id))
    peta = _peta_departemen({b.project_id for b in selesai} | {p.tujuan_project_id for p in permintaan})

    hasil = [_item(JENIS_SELESAI, b.id, b.issue, b.pemohon, b.created_at, peta, assignees) for b in selesai] + [
        _item(
            JENIS_PERMINTAAN,
            p.id,
            p.intake_issue.issue,
            p.diminta_oleh,
            p.created_at,
            peta,
            assignees,
            asal={"id": str(p.asal_project_id), "identifier": p.asal_project.identifier, "name": p.asal_project.name},
            catatan=p.catatan,
            ditunda=p.intake_issue.status == 0,
        )
        for p in permintaan
    ]
    hasil.sort(key=lambda i: i["diminta_pada"])
    return {"boleh_memutuskan": True, "jumlah": len(hasil), "hasil": hasil}
