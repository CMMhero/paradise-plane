# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: DM penugasan lama jadi kartu
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Ubah DM penugasan berbentuk teks (sebelum 2.2.0) jadi kartu `tugas`.

Sebelum kartu obrolan ada, `tugas_ke_dm_task` mengirim teks polos:

    📋 Tugas baru untuk Anda

    PRJ-12 · Judul tugas
    ...
    https://host/<slug>/projects/<project_id>/issues/<issue_id>

Hanya pesan itu yang pernah dikirim sistem ke obrolan sebelum 2.2.0. Sebutan,
komentar, pembaruan, persetujuan, dan undangan project belum pernah masuk
obrolan, jadi tidak ada yang perlu diubah untuk jenis itu.

Kelas model diterima sebagai argumen supaya migrasi bisa memakai model
historisnya dan tes bisa memakai model sungguhan. `isi` tidak disentuh: tetap
jadi teks cadangan untuk pencarian dan email. Penanda `asal` membuat migrasinya
bisa dibalik tanpa menyentuh kartu yang lahir sebagai kartu.
"""

import re

AWALAN = "📋 Tugas baru untuk Anda"
ASAL = "teks_lama"
BATAS_CUPLIKAN = 200
BATAS_DESKRIPSI = 280
BATAS_ASSIGNEE = 5

_TAUTAN = re.compile(r"/issues/([0-9a-fA-F-]{36})")
_KODE = re.compile(r"^([A-Za-z0-9]+)-(\d+) · ")


def _potong(teks, batas) -> str:
    rapi = " ".join(str(teks or "").split())
    return rapi if len(rapi) <= batas else rapi[: batas - 1] + "…"


def baca_rujukan(isi: str) -> tuple:
    """(issue_id, (identifier, nomor)) dari isi pesan lama. Murni.

    Tautan lebih dulu karena id-nya pasti. Kode jadi cadangan untuk server tanpa
    `APP_BASE_URL`, yang mengirim pesan tanpa tautan.
    """
    tautan = _TAUTAN.search(isi or "")
    baris = (isi or "").split("\n")
    kode = _KODE.match(baris[2]) if len(baris) > 2 else None
    return (
        tautan.group(1).lower() if tautan else None,
        (kode.group(1), int(kode.group(2))) if kode else None,
    )


def muatan_tugas(issue, aktor_id, assignee_ids) -> dict:
    """Bentuk yang sama dengan `tugas_ke_dm_task` hari ini."""
    project = issue.project
    state = issue.state
    return {
        "aksi": "tugas",
        "asal": ASAL,
        "aktor": str(aktor_id) if aktor_id else None,
        "workspace_slug": project.workspace.slug,
        "project": {"id": str(project.id), "nama": project.name, "identifier": project.identifier},
        "tugas": {
            "id": str(issue.id),
            "nomor": f"{project.identifier}-{issue.sequence_id}",
            "judul": _potong(issue.name, BATAS_CUPLIKAN),
            "state": state.name if state else "",
            "state_group": state.group if state else "",
            "prioritas": issue.priority or "",
            "tenggat": issue.target_date.isoformat() if issue.target_date else None,
            "assignees": [str(a) for a in assignee_ids][:BATAS_ASSIGNEE],
        },
        "detail": {"deskripsi": _potong(issue.description_stripped, BATAS_DESKRIPSI)},
    }


def ubah_ke_kartu(PesanLangsung, Issue, IssueAssignee, batch: int = 500) -> int:
    """Ubah semua DM penugasan teks yang tugasnya masih ada. Mengembalikan jumlahnya.

    Tugas yang sudah dihapus dibiarkan sebagai teks: kartu tanpa tugas tidak
    punya tombol yang bisa dibuka, teksnya setidaknya masih menyebut judulnya.
    """
    pesan = list(
        PesanLangsung._default_manager.filter(jenis="teks", isi__startswith=AWALAN).only(
            "id", "isi", "workspace_id", "pengirim_id"
        )
    )
    if not pesan:
        return 0

    rujukan = {p.id: baca_rujukan(p.isi) for p in pesan}
    hidup = Issue._default_manager.filter(deleted_at__isnull=True, project__deleted_at__isnull=True).select_related(
        "project", "project__workspace", "state"
    )

    lewat_id = {str(i.id): i for i in hidup.filter(id__in={r[0] for r in rujukan.values() if r[0]})}
    kode_dicari = {r[1] for r in rujukan.values() if not r[0] and r[1]}
    lewat_kode = {}
    if kode_dicari:
        for i in hidup.filter(
            project__identifier__in={k[0] for k in kode_dicari},
            sequence_id__in={k[1] for k in kode_dicari},
        ):
            lewat_kode[(i.project.workspace_id, i.project.identifier, i.sequence_id)] = i

    cocok = {}
    for p in pesan:
        issue_id, kode = rujukan[p.id]
        issue = lewat_id.get(issue_id) if issue_id else None
        if issue is None and kode:
            issue = lewat_kode.get((p.workspace_id, kode[0], kode[1]))
        if issue is not None and issue.project.workspace_id == p.workspace_id:
            cocok[p] = issue
    if not cocok:
        return 0

    assignees = {}
    for issue_id, user_id in (
        IssueAssignee._default_manager.filter(issue_id__in={i.id for i in cocok.values()}, deleted_at__isnull=True)
        .order_by("created_at")
        .values_list("issue_id", "assignee_id")
    ):
        assignees.setdefault(issue_id, []).append(user_id)

    for p, issue in cocok.items():
        p.jenis = "tugas"
        p.muatan = muatan_tugas(issue, p.pengirim_id, assignees.get(issue.id, []))
    PesanLangsung._default_manager.bulk_update(list(cocok), ["jenis", "muatan"], batch_size=batch)
    return len(cocok)


def kembalikan_ke_teks(PesanLangsung) -> int:
    """Kebalikan `ubah_ke_kartu`: hanya kartu yang lahir dari teks lama."""
    return PesanLangsung._default_manager.filter(jenis="tugas", muatan__asal=ASAL).update(jenis="teks", muatan={})
