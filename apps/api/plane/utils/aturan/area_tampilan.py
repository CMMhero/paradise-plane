# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area C, bawaan tampilan
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area C inventaris: bawaan tampilan.

Dua macam aturan di sini:

- `member_default="<bagian>.<kolom>"`: bawaan per AKUN. Nilainya disimpan di
  PARADISE_BAWAAN_MEMBER (God Mode > People > New member defaults), diberikan ke
  akun baru, dan bisa diterapkan ke semua akun dengan tombol "Apply to existing
  members" (`terapkan_ke_semua`, bagian `tampilan` atau `work_items`). Akun lama
  tidak pernah berubah diam-diam.
- Aturan biasa (`web=True` atau dibaca server): tampilan yang tidak punya
  pilihan per akun di server. Yang pilihannya hanya hidup di localStorage
  memakai nilai aturan selama orangnya belum memilih sendiri di peramban itu.
"""

from plane.utils.aturan.jenis import BOOL, CHOICE, INT, KEY_LIST, RENDAH, Rule

# --- Linimasa aktivitas work item -------------------------------------------------

# Per akun di `Profile.theme["urutan_aktivitas"]`; kosong = terbaru di atas
# (apps/web/core/hooks/use-urutan-aktivitas.ts).
ACTIVITY_NEWEST_FIRST = "ACTIVITY_NEWEST_FIRST"
# localStorage `issue_activity_filters`; aturan ini dipakai selama belum ada pilihan lokal.
ACTIVITY_DEFAULT_FILTERS = "ACTIVITY_DEFAULT_FILTERS"
COMMENT_BOX_POSITION = "COMMENT_BOX_POSITION"
COMMENT_REPLY_ORDER = "COMMENT_REPLY_ORDER"

# --- Daftar work item (ProjectUserProperty, bagian `work_items`) -----------------

# `layout` sendiri tetap kolom tulis tangan di bagian yang sama (People > New
# member defaults); kolom di bawah ini melengkapinya, bukan menggandakannya.
WORK_ITEMS_GROUP_BY = "WORK_ITEMS_GROUP_BY"
WORK_ITEMS_ORDER_BY = "WORK_ITEMS_ORDER_BY"
WORK_ITEMS_SHOW_SUB_ISSUES = "WORK_ITEMS_SHOW_SUB_ISSUES"
WORK_ITEMS_SHOW_EMPTY_GROUPS = "WORK_ITEMS_SHOW_EMPTY_GROUPS"
WORK_ITEMS_FIELDS = "WORK_ITEMS_FIELDS"
PEEK_MODE_DEFAULT = "PEEK_MODE_DEFAULT"

# Kunci `display_properties` di db/models/issue.py `get_default_display_properties`,
# ditambah approval_status yang hanya ada di web (kunci yang tak ada = tampil).
KOLOM_WORK_ITEM = (
    ("key", "ID"),
    ("assignee", "Assignees"),
    ("start_date", "Start date"),
    ("due_date", "Due date"),
    ("labels", "Labels"),
    ("priority", "Priority"),
    ("state", "State"),
    ("approval_status", "Approval status"),
    ("sub_issue_count", "Sub-work item count"),
    ("link", "Links"),
    ("attachment_count", "Attachment count"),
    ("estimate", "Estimate"),
    ("created_on", "Created on (spreadsheet)"),
    ("updated_on", "Updated on (spreadsheet)"),
)

# --- Home ----------------------------------------------------------------------

# Per akun per workspace di `WorkspaceHomePreference` (app/views/workspace/home.py).
HOME_WIDGETS = "HOME_WIDGETS"
ATTENTION_ITEMS_PER_GROUP = "ATTENTION_ITEMS_PER_GROUP"
ATTENTION_DISMISS_DAYS = "ATTENTION_DISMISS_DAYS"
CHANGELOG_RELEASES_SHOWN = "CHANGELOG_RELEASES_SHOWN"

# --- KPI dan Division dashboard ------------------------------------------------

KPI_DEFAULT_PERIOD = "KPI_DEFAULT_PERIOD"
KPI_LIST_SIZE = "KPI_LIST_SIZE"
DIVISION_DASHBOARD_DEFAULT_MODE = "DIVISION_DASHBOARD_DEFAULT_MODE"
DIVISION_REPORT_DEFAULT_PERIOD = "DIVISION_REPORT_DEFAULT_PERIOD"

ATURAN = (
    Rule(
        key=ACTIVITY_NEWEST_FIRST,
        kind=BOOL,
        default=True,
        group="display",
        label="Activity timeline shows newest first",
        help=(
            "The order of activity and comments on a work item for new accounts. "
            "Each person can still flip it on the work item or in their preferences."
        ),
        risk=RENDAH,
        member_default="tampilan.aktivitas_terbaru_di_atas",
        profile_theme_key="urutan_aktivitas",
        profile_values={True: "desc", False: "asc"},
    ),
    Rule(
        key=ACTIVITY_DEFAULT_FILTERS,
        kind=KEY_LIST,
        web=True,
        default=("ACTIVITY", "COMMENT", "STATE", "ASSIGNEE"),
        choices=(
            ("ACTIVITY", "Updates"),
            ("COMMENT", "Comments"),
            ("STATE", "State changes"),
            ("ASSIGNEE", "Assignee changes"),
        ),
        group="display",
        label="Activity timeline shows at first",
        help=(
            "What the activity list on a work item shows until a person picks their own filter. "
            "Their pick is kept in their browser and wins. Leaving all off shows everything."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=COMMENT_BOX_POSITION,
        kind=CHOICE,
        web=True,
        default="follow",
        choices=(
            ("follow", "Follows the timeline order"),
            ("top", "Always above the timeline"),
            ("bottom", "Always below the timeline"),
        ),
        group="display",
        label="Comment box position",
        help=(
            "Where the comment box sits on a work item. By default it is at the top when newest is first "
            "and at the bottom when oldest is first. Applies to everyone."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=COMMENT_REPLY_ORDER,
        kind=CHOICE,
        web=True,
        default="oldest",
        choices=(
            ("oldest", "Oldest first"),
            ("timeline", "Same as the timeline"),
        ),
        group="display",
        label="Replies inside a comment thread",
        help="The order of replies under a comment. Applies to everyone. The timeline order itself does not change.",
        risk=RENDAH,
    ),
    Rule(
        key=WORK_ITEMS_GROUP_BY,
        kind=CHOICE,
        default="none",
        choices=(
            ("none", "None (Board still groups by state)"),
            ("state", "State"),
            ("state_detail.group", "State group"),
            ("priority", "Priority"),
            ("labels", "Labels"),
            ("assignees", "Assignees"),
            ("created_by", "Created by"),
        ),
        group="display",
        label="Work item grouping",
        help=(
            "How a project's work item list is grouped the first time a member opens it. "
            "Each person can still change it per project."
        ),
        risk=RENDAH,
        member_default="work_items.group_by",
    ),
    Rule(
        key=WORK_ITEMS_ORDER_BY,
        kind=CHOICE,
        default="-created_at",
        choices=(
            ("-created_at", "Last created"),
            ("-updated_at", "Last updated"),
            ("sort_order", "Manual"),
            ("start_date", "Start date"),
            ("target_date", "Due date"),
            ("-priority", "Priority"),
            ("approval_status", "Waiting for approval first"),
        ),
        group="display",
        label="Work item order",
        help=(
            "How a project's work items are sorted the first time a member opens it. "
            "Each person can still change it per project."
        ),
        risk=RENDAH,
        member_default="work_items.order_by",
    ),
    Rule(
        key=WORK_ITEMS_SHOW_SUB_ISSUES,
        kind=BOOL,
        default=True,
        group="display",
        label="Work item list shows sub-work items",
        help="Whether sub-work items appear in a project's list for a member who has not changed it.",
        risk=RENDAH,
        member_default="work_items.sub_issue",
    ),
    Rule(
        key=WORK_ITEMS_SHOW_EMPTY_GROUPS,
        kind=BOOL,
        default=True,
        group="display",
        label="Work item list shows empty groups",
        help="Whether groups with no work items still appear, for a member who has not changed it.",
        risk=RENDAH,
        member_default="work_items.show_empty_groups",
    ),
    Rule(
        key=WORK_ITEMS_FIELDS,
        kind=KEY_LIST,
        default=tuple(k for k, _ in KOLOM_WORK_ITEM),
        choices=KOLOM_WORK_ITEM,
        group="display",
        label="Fields shown on work items",
        help=(
            "Which fields a member sees on list rows and board cards in a project they open for the first time. "
            "Each person can still change them per project."
        ),
        risk=RENDAH,
        member_default="work_items.display_properties",
    ),
    Rule(
        key=PEEK_MODE_DEFAULT,
        kind=CHOICE,
        web=True,
        default="side-peek",
        choices=(
            ("side-peek", "Side panel"),
            ("modal", "Pop-up"),
            ("full-screen", "Full screen"),
        ),
        group="display",
        label="Work item preview opens as",
        help="How a work item opens from a list or board. A person can still switch it for the item they have open.",
        risk=RENDAH,
    ),
    Rule(
        key=HOME_WIDGETS,
        kind=KEY_LIST,
        ordered=True,
        default=("needs_attention", "quick_links", "recents", "my_stickies", "announcements", "changelog"),
        choices=(
            ("needs_attention", "Needs attention"),
            ("quick_links", "Quick links"),
            ("recents", "Recents"),
            ("my_stickies", "Your stickies"),
            ("announcements", "Announcements"),
            ("changelog", "Changelog"),
        ),
        group="display",
        label="Home widgets and their order",
        help=(
            "Which widgets Home shows, top to bottom, the first time a member opens Home in a workspace. "
            "Widgets left off stay available under Manage widgets."
        ),
        risk=RENDAH,
        member_default="tampilan.home_widgets",
    ),
    Rule(
        key=ATTENTION_ITEMS_PER_GROUP,
        kind=INT,
        default=5,
        min=1,
        max=20,
        group="display",
        label="Needs attention: rows per group",
        help="How many work items each group in Needs attention lists. The count beside the group stays exact.",
        risk=RENDAH,
    ),
    Rule(
        key=ATTENTION_DISMISS_DAYS,
        kind=INT,
        web=True,
        default=30,
        min=1,
        max=365,
        group="display",
        label="Needs attention: hidden cards return after (days)",
        help=(
            "A card someone hides comes back after this many days, or sooner when the work item changes. "
            "Applies to everyone."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=CHANGELOG_RELEASES_SHOWN,
        kind=INT,
        web=True,
        default=1,
        min=0,
        max=10,
        group="display",
        label="Home: releases shown in What's new",
        help="How many releases the What's new card on Home shows before the rest are folded. 0 hides the card.",
        risk=RENDAH,
    ),
    Rule(
        key=KPI_DEFAULT_PERIOD,
        kind=CHOICE,
        web=True,
        default="this_month",
        choices=(
            ("this_week", "This week"),
            ("this_month", "This month"),
            ("30d", "Last 30 days"),
            ("this_quarter", "This quarter"),
        ),
        group="display",
        label="KPI page opens on",
        help="The period the KPI page shows until a person picks their own. Their pick is kept in their browser.",
        risk=RENDAH,
    ),
    Rule(
        key=KPI_LIST_SIZE,
        kind=INT,
        default=20,
        min=1,
        max=100,
        group="display",
        label="KPI page: rows per list",
        help="How many overdue and completed work items each KPI list shows. Totals are not affected.",
        risk=RENDAH,
    ),
    Rule(
        key=DIVISION_DASHBOARD_DEFAULT_MODE,
        kind=CHOICE,
        web=True,
        default="ringkas",
        choices=(
            ("ringkas", "Summary"),
            ("rinci", "Detail"),
            ("laporan", "Report"),
        ),
        group="display",
        label="Division dashboard opens on",
        help=(
            "The tab the Division dashboard shows until a person picks their own. Their pick is kept in their browser."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=DIVISION_REPORT_DEFAULT_PERIOD,
        kind=CHOICE,
        web=True,
        default="7d",
        choices=(
            ("7d", "Last 7 days"),
            ("30d", "Last 30 days"),
            ("this_month", "This month"),
            ("last_month", "Last month"),
        ),
        group="display",
        label="Division report period",
        help="The period the completed work report on the Division dashboard shows until a person picks their own.",
        risk=RENDAH,
    ),
)
