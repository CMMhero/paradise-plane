# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area B, apa yang boleh dilakukan tiap jenjang
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area B inventaris: menugaskan, mengubah, menyetujui, membuat.

Setiap `default` di bawah = perilaku sebelum aturannya ada. Nilai pilihan
(`STAF_*`, `UBAH_*`, ...) dipakai pembacanya; jangan dibandingkan dengan teks lepas.
"""

from plane.utils.aturan.jenis import BOOL, CHOICE, KEY_LIST, LEVEL, RENDAH, SEDANG, TINGGI, Rule

# Jenjang terendah yang boleh menyetujui pekerjaan selesai (`calon_penyetuju` di
# utils/hierarki.py). Leader (12) sengaja tidak ditawarkan: `divisi_diawasi`
# leader selalu kosong, jadi pilihan itu tidak akan mengubah apa pun.
APPROVER_MIN_LEVEL = "APPROVER_MIN_LEVEL"

# B3. Siapa yang boleh diajak staf jadi assignee (`_galat_kolaborasi_staf`,
# `rekan_staf_ids` di utils/hierarki.py). Dirinya sendiri selalu wajib ada.
STAFF_ASSIGN_RULE = "STAFF_ASSIGN_RULE"
STAF_DIRI_DAN_REKAN = "self_and_peers"
STAF_DIRI_SAJA = "self_only"

# B5. Larangan menugaskan atasan (`atasan_di_antara` di utils/atasan.py).
BLOCK_ASSIGN_UPWARD = "BLOCK_ASSIGN_UPWARD"

# B6. Assignee harus ditempatkan di departemen/divisi project (`tempat_penerima`).
ASSIGNEE_MUST_BE_PLACED = "ASSIGNEE_MUST_BE_PLACED"

# B7. Pembuat tugas tanpa assignee jadi assignee-nya (`penerima_otomatis`).
AUTO_ASSIGN_CREATOR = "AUTO_ASSIGN_CREATOR"

# B8. Assignee sub-item naik ke induk dan module (utils/naik_assignee.py, KEP-98).
BUBBLE_SUBITEM_ASSIGNEES = "BUBBLE_SUBITEM_ASSIGNEES"

# B9. Siapa yang boleh mengubah tugas (`galat_ubah_tugas`). Assignee tetap
# mengikuti aturan penugasan, dan hapus/arsip tetap ikut tangga jenjang kecuali
# TASK_DELETE_RULE = "yang boleh mengubah".
TASK_EDIT_RULE = "TASK_EDIT_RULE"
UBAH_TERLIBAT_DAN_ATASAN = "involved_and_superiors"
UBAH_SEMUA_ANGGOTA = "any_project_member"

# Bidang tugas yang bisa dikunci/dibuka per peran (utils/bidang_tugas.py).
# Due date dan assignee tidak di sini: keduanya punya aturan sendiri.
PILIHAN_BIDANG = (
    ("name", "Title"),
    ("description", "Description"),
    ("state", "Status"),
    ("priority", "Priority"),
    ("start_date", "Start date"),
    ("labels", "Labels"),
    ("estimate", "Estimate"),
    ("parent", "Parent"),
)
TASK_FIELDS_LOCKED_FOR_STAFF = "TASK_FIELDS_LOCKED_FOR_STAFF"
TASK_FIELDS_OPEN_TO_MEMBERS = "TASK_FIELDS_OPEN_TO_MEMBERS"

# B10. Siapa yang boleh berkomentar dan bereaksi (`galat_percakapan_tugas`).
TASK_COMMENT_RULE = "TASK_COMMENT_RULE"
KOMENTAR_SAMA_DENGAN_UBAH = "same_as_edit"
KOMENTAR_SEMUA_ANGGOTA = "any_project_member"

# B11. Tugas selesai terkunci, dan jenjang terendah yang membukanya kembali
# (utils/kunci_selesai.py). Admin workspace dan Super Admin selalu bisa membuka.
LOCK_COMPLETED_TASKS = "LOCK_COMPLETED_TASKS"
REOPEN_MIN_LEVEL = "REOPEN_MIN_LEVEL"

# B13. Kapan direktur ikut memutuskan (`direktur_ikut_memutuskan`).
DIRECTOR_APPROVES = "DIRECTOR_APPROVES"
DIREKTUR_SEMUA = "all"
DIREKTUR_BUATAN_MANAGER = "manager_created"
DIREKTUR_TIDAK_PERNAH = "never"

# B16. Grup status tujuan tugas yang ditolak (`_kembalikan_tugas`, KEP-55).
REJECT_TARGET_STATE_GROUP = "REJECT_TARGET_STATE_GROUP"

# B20. Penanggung jawab intake boleh mengisi Due date sebelum diterima
# (`bisa_ganti_tenggat_intake` di utils/task_access.py).
INTAKE_ADMIN_SETS_DUE_DATE = "INTAKE_ADMIN_SETS_DUE_DATE"

# B21. Jenjang terendah member workspace yang boleh membuat project
# (utils/izin_buat_project.py). Admin workspace dan Super Admin selalu boleh.
PROJECT_CREATE_MIN_LEVEL = "PROJECT_CREATE_MIN_LEVEL"

# G1 (diambil area B karena menyangkut tugas). Tenggat efektif = max(Due date,
# hari dicatat) (utils/ketepatan_waktu.py, KEP-62).
LATE_FROM_RECORDED_DAY = "LATE_FROM_RECORDED_DAY"

ATURAN = (
    Rule(
        key=APPROVER_MIN_LEVEL,
        kind=LEVEL,
        default=20,
        choices=(20, 25, 30),
        group="approvals",
        label="Lowest level that can approve",
        help=(
            "Finished work waits for someone at this level or above who oversees the department and sits above "
            "the person who finished it. Raising it to Manager takes approvals away from supervisors and "
            "assistant managers."
        ),
        risk=TINGGI,
        kep="P29",
    ),
    Rule(
        key=STAFF_ASSIGN_RULE,
        kind=CHOICE,
        default=STAF_DIRI_DAN_REKAN,
        choices=(
            (STAF_DIRI_DAN_REKAN, "Themselves and same-level colleagues in their department"),
            (STAF_DIRI_SAJA, "Only themselves"),
        ),
        group="assignment",
        label="Who staff can assign",
        help=(
            "Staff (below Leader) always stay on the work items they create and can never remove anyone. "
            "This decides whether they can also add same-level colleagues from their own department."
        ),
        risk=TINGGI,
        kep="KEP-25",
    ),
    Rule(
        key=BLOCK_ASSIGN_UPWARD,
        kind=BOOL,
        default=True,
        group="assignment",
        label="Nobody can assign their superior",
        help=(
            "When on, no one can make a person at a higher level the assignee, workspace admins with a level "
            "included. Super Admins and admins with no placement are never limited. Assigning yourself is always "
            "allowed."
        ),
        risk=TINGGI,
        kep="P29",
    ),
    Rule(
        key=ASSIGNEE_MUST_BE_PLACED,
        kind=BOOL,
        default=True,
        group="assignment",
        label="Assignees must be placed in the department",
        help=(
            "When on, only people placed in the department or division that owns the project can be assignees. "
            "Admin access alone is not enough. When off, any project member can be assigned. "
            "People already assigned are never removed."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=AUTO_ASSIGN_CREATOR,
        kind=BOOL,
        default=True,
        group="assignment",
        label="Creator becomes the assignee",
        help=(
            "When someone creates a work item without an assignee, they become the assignee if they can be "
            "assigned in that project. When off, the work item stays unassigned."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=BUBBLE_SUBITEM_ASSIGNEES,
        kind=BOOL,
        default=True,
        group="assignment",
        label="Sub-item assignees join the parent",
        help=(
            "Assignees of a sub-work item are added to every parent above it and to its modules. "
            "Nobody is ever removed. Turning it off stops new additions only."
        ),
        risk=SEDANG,
        kep="KEP-98",
    ),
    Rule(
        key=TASK_EDIT_RULE,
        kind=CHOICE,
        default=UBAH_TERLIBAT_DAN_ATASAN,
        choices=(
            (UBAH_TERLIBAT_DAN_ATASAN, "Creator, assignees, and their superiors"),
            (UBAH_SEMUA_ANGGOTA, "Any project member"),
        ),
        group="assignment",
        label="Who can edit a work item",
        help=(
            "Covers the work item and its links, files, relations, and dates. Admins and Super Admins can always "
            "edit. Assignees still follow the assignment rules, and deleting or archiving keeps the level ladder "
            "unless the delete rule is set to anyone who can edit."
        ),
        risk=TINGGI,
        kep="KEP-25",
    ),
    Rule(
        key=TASK_FIELDS_LOCKED_FOR_STAFF,
        kind=KEY_LIST,
        default=(),
        choices=PILIHAN_BIDANG,
        group="assignment",
        label="Fields staff cannot change",
        help=(
            "Staff (below Leader) cannot change these fields on any work item, their own included. "
            "Leaders and above, workspace admins, and Super Admins can. Due date and assignees follow their own "
            "rules."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=TASK_FIELDS_OPEN_TO_MEMBERS,
        kind=KEY_LIST,
        default=(),
        choices=PILIHAN_BIDANG,
        group="assignment",
        label="Fields any project member can change",
        help=(
            "Project members who are not involved in a work item can still change these fields on it. "
            "Fields locked for staff stay locked for them. Everything else follows who can edit a work item."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=TASK_COMMENT_RULE,
        kind=CHOICE,
        default=KOMENTAR_SAMA_DENGAN_UBAH,
        choices=(
            (KOMENTAR_SAMA_DENGAN_UBAH, "Same people who can edit it"),
            (KOMENTAR_SEMUA_ANGGOTA, "Any project member"),
        ),
        group="assignment",
        label="Who can comment and react",
        help=(
            "Comments, replies, and reactions on a work item. Guests still follow the project's guest rules, "
            "and finished work items stay locked while that lock is on."
        ),
        risk=SEDANG,
    ),
    Rule(
        key=LOCK_COMPLETED_TASKS,
        kind=BOOL,
        default=True,
        group="assignment",
        label="Finished work items are locked",
        help=(
            "When on, nobody can change a finished work item, admins included, until someone allowed to reopen it "
            "moves it out of Done. When off, finished work items follow the normal edit rules."
        ),
        risk=TINGGI,
        web=True,
        kep="P29",
    ),
    Rule(
        key=REOPEN_MIN_LEVEL,
        kind=LEVEL,
        default=20,
        choices=(20, 25, 30, 40),
        group="assignment",
        label="Lowest level that can reopen finished work",
        help=(
            "People at this level or above can reopen a finished work item when every assignee is their "
            "subordinate. Workspace admins and Super Admins can always reopen."
        ),
        risk=TINGGI,
        kep="P29",
    ),
    Rule(
        key=DIRECTOR_APPROVES,
        kind=CHOICE,
        default=DIREKTUR_BUATAN_MANAGER,
        choices=(
            (DIREKTUR_BUATAN_MANAGER, "Only work items created by managers and above"),
            (DIREKTUR_SEMUA, "All work items in their reach"),
            (DIREKTUR_TIDAK_PERNAH, "Never"),
        ),
        group="approvals",
        label="When directors approve",
        help=(
            "Which approval requests directors can decide. The rest are decided by supervisors and managers of "
            "the division. A request with no one left to decide falls to the Super Admin."
        ),
        risk=SEDANG,
    ),
    Rule(
        key=REJECT_TARGET_STATE_GROUP,
        kind=CHOICE,
        default="started",
        choices=(
            ("started", "In progress"),
            ("unstarted", "To do"),
            ("backlog", "Backlog"),
        ),
        group="approvals",
        label="Where rejected work goes",
        help=(
            "A rejected work item moves to the first status of this kind in its project. "
            "If the project has none, it goes back to the status it had before."
        ),
        risk=RENDAH,
        kep="KEP-55",
    ),
    Rule(
        key=INTAKE_ADMIN_SETS_DUE_DATE,
        kind=BOOL,
        default=True,
        group="assignment",
        label="Intake admins can set the due date",
        help=(
            "Project admins and workspace admins can set the due date of a work item that is still waiting in "
            "Intake. After it is accepted, the normal due date rule applies."
        ),
        risk=RENDAH,
        web=True,
    ),
    Rule(
        key=PROJECT_CREATE_MIN_LEVEL,
        kind=LEVEL,
        default=20,
        choices=(10, 12, 20, 25, 30, 40),
        group="projects",
        label="Lowest level that can create projects",
        help=(
            "Workspace members at this level or above can create projects through the API. "
            "Workspace admins and Super Admins always can, and guests never can."
        ),
        risk=SEDANG,
    ),
    Rule(
        key=LATE_FROM_RECORDED_DAY,
        kind=BOOL,
        default=True,
        group="dates",
        label="Late counts from the day work was recorded",
        help=(
            "When on, a finished work item is late only if it finishes after both its due date and the day it was "
            "recorded. When off, only the due date counts. Reports and KPI change for past work too."
        ),
        risk=SEDANG,
        kep="KEP-62",
    ),
)
