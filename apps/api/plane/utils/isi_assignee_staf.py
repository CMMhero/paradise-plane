# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: isi assignee tugas buatan staf (2.11)
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Isi assignee tugas yang dibuat staf dan masih kosong: assignee-nya pembuatnya.

Satu fungsi untuk migrasi `0186_isi_assignee_staf` dan perintah `isi_assignee_staf`.
Fungsi ini murni: modelnya diambil lewat `get_model` yang diberikan pemanggil
(`apps.get_model` di migrasi, `django.apps.apps.get_model` di perintah), jadi ia
tetap sah terhadap model historis. Model historis tidak punya manager kustom,
makanya `deleted_at` disaring eksplisit lewat `_base_manager`.

Aturan pilih, semuanya harus benar:
- tugas hidup (tidak dihapus), tidak diarsipkan, bukan draf, bukan triase, dan
  projectnya hidup dan tidak diarsipkan (sama dengan `Issue.issue_objects`);
- tidak pernah punya baris `IssueAssignee` sama sekali, hidup maupun soft-delete
  (assignee yang sengaja dicopot tidak boleh dipasang lagi);
- state apa pun, termasuk completed/cancelled (keputusan pemilik: tugas selesai ikut diisi;
  `include_closed=False` membatasi ke yang masih terbuka, karena mengisi tugas selesai
  menggeser angka KPI dan beban kerja);
- punya pembuat, dan pembuat itu user aktif bukan bot;
- pembuat itu staf: jenjang tertingginya di workspace tugas itu di bawah Leader,
  atau tidak punya baris `JabatanOrganisasi` hidup sama sekali (sama dengan
  `tingkat === null || tingkat < TINGKAT_LEADER` di halaman organisasi admin);
- pembuat anggota project yang aktif (`ProjectMember.is_active`, tidak dihapus).

`bulk_create` tidak memicu sinyal, dan tidak ada sinyal terpasang pada
`IssueAssignee`. Aktivitas, notifikasi, dan email berasal dari view, bukan dari
model, jadi jalur ini tidak mengirim satu pun.
"""

from django.db.models import Exists, Max, OuterRef

from plane.db.models.hierarki import TINGKAT_LEADER

BATCH = 2000

ALASAN = ("sudah_selesai", "pembuat_nonaktif", "bukan_staf", "bukan_anggota_project")

_GRUP_TUTUP = ("completed", "cancelled")


def isi_assignee_staf(get_model, *, apply: bool, batch: int = BATCH, include_closed: bool = True) -> dict:
    """Kembalikan {"diperiksa", "diisi", "dilewati": {alasan: n}}. Dengan `apply=False` tidak menulis apa pun.

    `diisi` pada dry-run adalah jumlah yang AKAN diisi.
    """
    Issue = get_model("db", "Issue")
    IssueAssignee = get_model("db", "IssueAssignee")
    JabatanOrganisasi = get_model("db", "JabatanOrganisasi")
    ProjectMember = get_model("db", "ProjectMember")
    User = get_model("db", "User")

    hasil = {"diperiksa": 0, "diisi": 0, "dilewati": {alasan: 0 for alasan in ALASAN}}

    # Tanpa saringan deleted_at: baris yang sudah di-soft-delete juga memblokir.
    punya_assignee = IssueAssignee._base_manager.filter(issue_id=OuterRef("pk"))
    kandidat = (
        Issue._base_manager.filter(
            deleted_at__isnull=True,
            archived_at__isnull=True,
            is_draft=False,
            created_by__isnull=False,
            project__deleted_at__isnull=True,
            project__archived_at__isnull=True,
        )
        .exclude(state__group="triage")
        .annotate(_ada=Exists(punya_assignee))
        .filter(_ada=False)
    )

    # Keyset per id: murah di ratusan ribu baris, dan stabil walau baris keluar dari saringan saat diisi.
    terakhir = None
    while True:
        qs = kandidat.order_by("id")
        if terakhir is not None:
            qs = qs.filter(id__gt=terakhir)
        baris = list(qs.values_list("id", "project_id", "workspace_id", "created_by_id", "state__group")[:batch])
        if not baris:
            break
        terakhir = baris[-1][0]
        hasil["diperiksa"] += len(baris)

        pembuat = {b[3] for b in baris}
        project_ids = {b[1] for b in baris}
        aktif = set(
            User.objects.filter(id__in=pembuat, is_active=True, is_bot=False).values_list("id", flat=True)
        )
        tertinggi = {
            (w, m): t
            for w, m, t in JabatanOrganisasi._base_manager.filter(
                member_id__in=pembuat, deleted_at__isnull=True
            )
            .values_list("workspace_id", "member_id")
            .annotate(t=Max("tingkat"))
            .values_list("workspace_id", "member_id", "t")
        }
        anggota = set(
            ProjectMember._base_manager.filter(
                project_id__in=project_ids, member_id__in=pembuat, is_active=True, deleted_at__isnull=True
            ).values_list("project_id", "member_id")
        )

        baru = []
        for issue_id, project_id, workspace_id, user_id, grup in baris:
            if not include_closed and grup in _GRUP_TUTUP:
                hasil["dilewati"]["sudah_selesai"] += 1
                continue
            if user_id not in aktif:
                hasil["dilewati"]["pembuat_nonaktif"] += 1
                continue
            tingkat = tertinggi.get((workspace_id, user_id))
            if tingkat is not None and tingkat >= TINGKAT_LEADER:
                hasil["dilewati"]["bukan_staf"] += 1
                continue
            if (project_id, user_id) not in anggota:
                hasil["dilewati"]["bukan_anggota_project"] += 1
                continue
            baru.append(
                IssueAssignee(issue_id=issue_id, assignee_id=user_id, project_id=project_id, workspace_id=workspace_id)
            )

        hasil["diisi"] += len(baru)
        if apply and baru:
            IssueAssignee._base_manager.bulk_create(baru, batch_size=batch, ignore_conflicts=True)

    return hasil


def ringkas(hasil: dict) -> str:
    d = hasil["dilewati"]
    return (
        f"checked {hasil['diperiksa']}, assigned {hasil['diisi']}, skipped "
        + ", ".join(f"{k}={d[k]}" for k in ALASAN)
    )
