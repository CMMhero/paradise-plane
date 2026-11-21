# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area A, apa yang dilihat tiap jenjang
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area A inventaris: apa yang dilihat tiap jenjang (menu, halaman, data).

Dua definisi "direktur" sengaja tetap hidup (A8, KEP-101): API memberi jangkauan
seluruh organisasi mulai jenjang 35 (`menjangkau_seluruh_organisasi`, sekretaris
dan direktur), sedangkan menu web menyembunyikan untuk jenjang 40 saja. Teks
bantuan setiap aturan menyebut jenjangnya dengan angka; DIRECTOR_MENUS_APPLY_TO
yang memilih apakah aturan menu ikut berlaku untuk sekretaris.

Ditunda (lihat paradise/aturan-godmode.md): A1 ambang jangkauan seluruh
organisasi dan A2 cakupan pengawasan per jenjang.
"""

from plane.utils.aturan.jenis import BOOL, CHOICE, LEVEL, RENDAH, SEDANG, TINGGI, Rule

# Menu sidebar yang disembunyikan dari Direktur. Dulu
# `DIRECTOR_HIDDEN_NAV_KEYS = ["archives"]` di apps/web/core/hooks/use-is-direktur.ts.
# Tampilan saja: API arsip tidak memeriksa jenjang, jadi risikonya rendah.
DIRECTOR_SIDEBAR_HIDES = "DIRECTOR_SIDEBAR_HIDES"
# Siapa "direktur" bagi aturan menu (DIRECTOR_SIDEBAR_HIDES, KPI_EXTRA_TABS). Dulu
# `isDirektur` = persis 40 di packages/services/src/instance/hierarki.service.ts.
DIRECTOR_MENUS_APPLY_TO = "DIRECTOR_MENUS_APPLY_TO"
# Tab Analytics dan Division dashboard di halaman KPI. Dulu `isAdmin && !isDirektur`
# di apps/web/app/(all)/[workspaceSlug]/(projects)/kinerja/layout.tsx. Endpoint-nya
# melayani anggota mana pun; aturan ini hanya tab.
KPI_EXTRA_TABS = "KPI_EXTRA_TABS"
# Tugas privat (utils/akses_privat.py, P29 #8). Keduanya membuka, tidak pernah menutup.
PRIVATE_VISIBLE_TO_WORKSPACE_ADMINS = "PRIVATE_VISIBLE_TO_WORKSPACE_ADMINS"
PRIVATE_VISIBLE_TO_CREATOR_SUPERIOR = "PRIVATE_VISIBLE_TO_CREATOR_SUPERIOR"
# Cakupan KPI (utils/kinerja.py `lingkup_untuk`). Leader (12) dulu `> TINGKAT_MEMBER`.
KPI_TEAM_MIN_LEVEL = "KPI_TEAM_MIN_LEVEL"
KPI_WORKSPACE_ADMINS_SEE_ALL = "KPI_WORKSPACE_ADMINS_SEE_ALL"
# Angka pimpinan seluruh organisasi hanya dari tugas buatan Supervisor ke atas
# (utils/statistik_pimpinan.py, keputusan 2026-11-20).
ORG_VIEW_LEADER_CREATED_ONLY = "ORG_VIEW_LEADER_CREATED_ONLY"
# Siapa yang dikabari saat disebut (@) di work item (utils/jangkauan_sebutan.py).
MENTION_NOTIFY_REACH = "MENTION_NOTIFY_REACH"
# Halaman privat orang lain di project departemen (utils/wiki_mandiri.py, KEP-95).
PRIVATE_PAGE_OVERSEERS = "PRIVATE_PAGE_OVERSEERS"
# Layar "pilih departemenmu" untuk staf tanpa penempatan (app/views/penempatan_saya.py).
ASK_UNPLACED_TO_CHOOSE_DEPARTMENT = "ASK_UNPLACED_TO_CHOOSE_DEPARTMENT"

# Nilai pilihan yang dibaca kode API. Teks sama persis dengan `choices` di bawah.
SEBUTAN_PROJECT = "project"
SEBUTAN_PROJECT_ORGANISASI = "project_org_wide"
SEBUTAN_WORKSPACE = "workspace"
HALAMAN_ADMIN_WIKI = "wiki_admins"
HALAMAN_ORGANISASI = "org_wide"
HALAMAN_PIMPINAN_DIVISI = "division_leaders"

ATURAN = (
    Rule(
        key=DIRECTOR_SIDEBAR_HIDES,
        kind=CHOICE,
        default="archives",
        choices=(
            ("none", "Everything"),
            ("archives", "Everything except Archives"),
            ("archives_your_work", "Everything except Archives and Your work"),
        ),
        group="visibility",
        label="What directors see in the sidebar",
        help=(
            "Menus hidden from directors. By default that means level 40 only; secretaries (35) keep every menu "
            "unless 'Who counts as a director for menus' says otherwise. Hidden Archives also sends them back from "
            "the Archives page. This only changes the sidebar; it does not block access to data."
        ),
        risk=RENDAH,
        web=True,
    ),
    Rule(
        key=DIRECTOR_MENUS_APPLY_TO,
        kind=CHOICE,
        default="director",
        choices=(
            ("director", "Directors only (level 40)"),
            ("org_wide", "Directors and secretaries (level 35 and up)"),
        ),
        group="visibility",
        label="Who counts as a director for menus",
        help=(
            "Which levels the director menu rules apply to: the hidden sidebar menus and the KPI tabs. "
            "Secretaries (35) already see every department's data like directors; this only decides whether "
            "their menus are trimmed the same way. It does not change data access."
        ),
        risk=RENDAH,
        web=True,
        kep="KEP-101",
    ),
    Rule(
        key=KPI_EXTRA_TABS,
        kind=CHOICE,
        default="admins_except_directors",
        choices=(
            ("admins_except_directors", "Workspace admins, except directors"),
            ("admins", "All workspace admins"),
            ("nobody", "Nobody"),
        ),
        group="visibility",
        label="Who sees the Analytics and Division dashboard tabs",
        help=(
            "The extra tabs on the KPI page. Directors are level 40, or 35 and up if 'Who counts as a director "
            "for menus' says so; they are sent back to KPI if they open a tab by link. This hides the tabs; it is "
            "not an access control. The Analytics and Division dashboard data still answer any workspace member."
        ),
        risk=SEDANG,
        web=True,
    ),
    Rule(
        key=PRIVATE_VISIBLE_TO_WORKSPACE_ADMINS,
        kind=BOOL,
        default=False,
        group="visibility",
        label="Workspace admins see private work items",
        help=(
            "Private work items are seen by their assignees, their creator, the direct superiors of an assignee, "
            "and Super Admins. Turn this on to add every workspace admin, in lists, details, and notifications. "
            "Off keeps admins out unless they are one of those people."
        ),
        risk=TINGGI,
        kep="P29",
    ),
    Rule(
        key=PRIVATE_VISIBLE_TO_CREATOR_SUPERIOR,
        kind=BOOL,
        default=False,
        group="visibility",
        label="The creator's superiors see private work items",
        help=(
            "Private work items are already seen by the direct superiors of each assignee. Turn this on to add the "
            "direct superiors of the person who created it, in lists, details, and notifications. Direct superiors "
            "are the people above that person in the project's department or division."
        ),
        risk=TINGGI,
        kep="P29",
    ),
    Rule(
        key=KPI_TEAM_MIN_LEVEL,
        kind=LEVEL,
        default=12,
        choices=(12, 20, 30),
        group="visibility",
        label="Lowest level that sees team KPI",
        help=(
            "From this level up, people see the KPI of the departments they lead and of the people below them "
            "there. Below it, people see only their own KPI. Managers (30) and branch directors (33) always see "
            "their division or branch; secretaries (35) and directors (40) always see the whole organisation."
        ),
        risk=TINGGI,
        kep="KEP-93",
    ),
    Rule(
        key=KPI_WORKSPACE_ADMINS_SEE_ALL,
        kind=BOOL,
        default=True,
        group="visibility",
        label="Workspace admins see KPI for the whole organisation",
        help=(
            "On: every workspace admin can open the KPI of the whole organisation. Off: a workspace admin sees the "
            "KPI their level and placement give them. Super Admins always see everything."
        ),
        risk=TINGGI,
        kep="KEP-29",
    ),
    Rule(
        key=ORG_VIEW_LEADER_CREATED_ONLY,
        kind=BOOL,
        default=True,
        group="visibility",
        label="Directors count only work created by supervisors and above",
        help=(
            "For people with organisation-wide reach (secretaries 35 and directors 40): overdue counts, statistics, "
            "dashboards, and the director report leave out work items created by staff and leaders. Off: they count "
            "every work item. Supervisors and managers always see their full team numbers."
        ),
        risk=SEDANG,
    ),
    Rule(
        key=MENTION_NOTIFY_REACH,
        kind=CHOICE,
        default="project_org_wide",
        choices=(
            ("project", "Project members only"),
            ("project_org_wide", "Project members, secretaries, and directors"),
            ("workspace", "Every active workspace member"),
        ),
        group="notifications",
        label="Who is notified when mentioned in a work item",
        help=(
            "Anyone can be @mentioned; this decides who is told about it. Secretaries (35) and directors (40) "
            "can open every project. With every workspace member, people who cannot open the work item still get "
            "its title and the text around the mention. Private work items stay limited to the people who can see them."
        ),
        risk=TINGGI,
    ),
    Rule(
        key=PRIVATE_PAGE_OVERSEERS,
        kind=CHOICE,
        default="division_leaders",
        choices=(
            ("wiki_admins", "Wiki admins only"),
            ("org_wide", "Wiki admins, secretaries, and directors"),
            ("division_leaders", "Wiki admins, secretaries, directors, and the division's manager or branch director"),
        ),
        group="wiki",
        label="Who sees other people's private pages",
        help=(
            "Private pages in a department project are always seen by their owner. Wiki admins are Super Admins "
            "and workspace admins. Secretaries are level 35, directors 40. The division's manager (30) and its "
            "branch director (33) see private pages in that division only. Department members keep seeing their own "
            "department's pages in the Wiki tree."
        ),
        risk=TINGGI,
        kep="KEP-95",
    ),
    Rule(
        key=ASK_UNPLACED_TO_CHOOSE_DEPARTMENT,
        kind=BOOL,
        default=True,
        group="visibility",
        label="Ask unplaced staff to choose a department",
        help=(
            "Staff with no department are asked once to pick one, and then see that department's work. Off: they "
            "are not asked and stay unplaced until an admin places them. People at supervisor level or above are "
            "never asked."
        ),
        risk=RENDAH,
    ),
)
