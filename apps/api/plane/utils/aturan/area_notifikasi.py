# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Kustomisasi Paradise Task Tracker: aturan area D, notifikasi, ringkasan, pengingat
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Area D inventaris: notifikasi, ringkasan, pengingat.

Jam, hari kirim, jendela, dan saklar kirim yang SUDAH ada di God Mode (D12) tetap
di registri lama (`setelan_instance.py`, `saklar_instance.py`). Di sini hanya
aturan yang tadinya terkunci di kode. Task terjadwal membaca aturannya tiap
putaran, jadi perubahan berlaku pada kiriman berikutnya.

Aturan yang mengubah SIAPA dikabari atau apa isinya tidak pernah boleh membuat
data tugas privat sampai ke orang yang tidak bisa membukanya: bagian tim ringkasan
harian tetap lewat saringan privat (P29), dan laporan direktur hanya berisi angka.
"""

from plane.utils.aturan.jenis import BOOL, CHOICE, INT, KEY_LIST, LEVEL, NEXT_RUN, RENDAH, SEDANG, Rule

NOTIFY_GROUP_LEADER = "NOTIFY_GROUP_LEADER"
NOTIFY_GROUP_BRANCH_DIRECTOR = "NOTIFY_GROUP_BRANCH_DIRECTOR"
NOTIFY_GROUP_SECRETARY = "NOTIFY_GROUP_SECRETARY"
DIRECTOR_DEFAULTS_ARE_CEILING = "DIRECTOR_DEFAULTS_ARE_CEILING"
DIRECTOR_REPORT_RECIPIENTS = "DIRECTOR_REPORT_RECIPIENTS"
DIRECTOR_REPORT_ATTENTION_UNITS = "DIRECTOR_REPORT_ATTENTION_UNITS"
DIGEST_TEAM_MIN_LEVEL = "DIGEST_TEAM_MIN_LEVEL"
DIGEST_TEAM_FOR_ORG_WIDE = "DIGEST_TEAM_FOR_ORG_WIDE"
DIGEST_PERSONAL_ROW_CAP = "DIGEST_PERSONAL_ROW_CAP"
DIGEST_TEAM_ROW_CAP = "DIGEST_TEAM_ROW_CAP"
DEADLINE_REMINDER_WEEKDAYS = "DEADLINE_REMINDER_WEEKDAYS"
ANNOUNCEMENT_EMAIL = "ANNOUNCEMENT_EMAIL"
ANNOUNCEMENT_EMAIL_ACTIVE_ONLY = "ANNOUNCEMENT_EMAIL_ACTIVE_ONLY"
ALL_MENTION_MIN_LEVEL = "ALL_MENTION_MIN_LEVEL"
LOGIN_RETENTION_WARNING_DAYS = "LOGIN_RETENTION_WARNING_DAYS"
# Pembersihan harian inbox (bgtasks/notifikasi_retensi.py).
NOTIFICATION_CLEANUP_DAYS = "NOTIFICATION_CLEANUP_DAYS"
NOTIFICATION_CLEANUP_ACTION = "NOTIFICATION_CLEANUP_ACTION"
# Nilai pilihan yang dibaca task. Teks sama persis dengan `choices` di bawah.
PEMBERSIHAN_ARSIP = "archive"
PEMBERSIHAN_HAPUS = "delete"

# Nama kelompok = baris tabel di God Mode > Notifications > Roles (`KELOMPOK_JABATAN`).
KELOMPOK_STAF, KELOMPOK_PIMPINAN, KELOMPOK_DIREKTUR = "staf", "pimpinan", "direktur"
_PILIHAN_KELOMPOK = (
    (KELOMPOK_STAF, "Staff column"),
    (KELOMPOK_PIMPINAN, "Supervisors and managers column"),
    (KELOMPOK_DIREKTUR, "Directors and secretaries column"),
)
_AKHIR_BAGIAN = "A change applies from the next email or notification. All other levels keep their own column."

_HARI = (
    ("1", "Monday"),
    ("2", "Tuesday"),
    ("3", "Wednesday"),
    ("4", "Thursday"),
    ("5", "Friday"),
    ("6", "Saturday"),
    ("7", "Sunday"),
)

ATURAN = (
    Rule(
        key=NOTIFY_GROUP_LEADER,
        kind=CHOICE,
        default=KELOMPOK_STAF,
        choices=_PILIHAN_KELOMPOK[:2],
        group="notifications",
        label="Leaders follow which notification column",
        help=(
            "Which column of Notifications > Roles gives Leaders their default notifications. "
            f"Choose Staff to keep Leaders with the staff. {_AKHIR_BAGIAN}"
        ),
        risk=SEDANG,
        kep="KEP-42",
    ),
    Rule(
        key=NOTIFY_GROUP_BRANCH_DIRECTOR,
        kind=CHOICE,
        default=KELOMPOK_PIMPINAN,
        choices=_PILIHAN_KELOMPOK,
        group="notifications",
        label="Branch managers follow which notification column",
        help=(
            "Which column of Notifications > Roles gives Branch managers their default notifications. "
            f"The directors column is also a hard limit. {_AKHIR_BAGIAN}"
        ),
        risk=SEDANG,
        kep="KEP-42",
    ),
    Rule(
        key=NOTIFY_GROUP_SECRETARY,
        kind=CHOICE,
        default=KELOMPOK_DIREKTUR,
        choices=_PILIHAN_KELOMPOK,
        group="notifications",
        label="Secretaries follow which notification column",
        help=(
            "Which column of Notifications > Roles gives Secretaries their default notifications. "
            f"The directors column is also a hard limit. {_AKHIR_BAGIAN}"
        ),
        risk=SEDANG,
        kep="KEP-101",
    ),
    Rule(
        key=DIRECTOR_DEFAULTS_ARE_CEILING,
        kind=BOOL,
        default=True,
        group="notifications",
        label="Directors column is a hard limit",
        help=(
            "On: anything off in the directors column stays off for every person in that column, whatever "
            "their own settings. Off: they can turn those notifications on for themselves. Their column "
            "values still apply to anyone who has not changed anything."
        ),
        risk=SEDANG,
        kep="KEP-59",
    ),
    Rule(
        key=DIRECTOR_REPORT_RECIPIENTS,
        kind=KEY_LIST,
        default=("35", "40"),
        choices=(("33", "Branch managers"), ("35", "Secretaries"), ("40", "Directors")),
        group="notifications",
        label="Who gets the director report",
        help=(
            "The daily report with numbers per division and department. Each person gets the part they "
            "oversee, with counts only: no task titles or staff names. Taking a level off stops its report."
        ),
        risk=SEDANG,
        kep="KEP-42",
        applies=NEXT_RUN,
    ),
    Rule(
        key=DIRECTOR_REPORT_ATTENTION_UNITS,
        kind=INT,
        default=3,
        min=1,
        max=10,
        group="notifications",
        label="Needs attention list length",
        help="How many departments the director report lists under Needs attention, most overdue first.",
        risk=RENDAH,
        applies=NEXT_RUN,
    ),
    Rule(
        key=DIGEST_TEAM_MIN_LEVEL,
        kind=LEVEL,
        default=20,
        choices=(20, 30, 33),
        group="notifications",
        label="Lowest level with a team section in the daily summary",
        help=(
            "The team section lists work in the departments or divisions the person oversees. Levels below "
            "this one get only their own and assigned work. Private work items still show only when one of "
            "the assignees reports to the reader."
        ),
        risk=SEDANG,
        kep="KEP-43",
        applies=NEXT_RUN,
    ),
    Rule(
        key=DIGEST_TEAM_FOR_ORG_WIDE,
        kind=BOOL,
        default=False,
        group="notifications",
        label="Team section for Secretaries and Directors",
        help=(
            "Off: they get no team section, their overview comes from the director report. On: they get a "
            "team section for every project. Private work items still show only when one of the assignees "
            "reports to the reader."
        ),
        risk=SEDANG,
        kep="KEP-43",
        applies=NEXT_RUN,
    ),
    Rule(
        key=DIGEST_PERSONAL_ROW_CAP,
        kind=INT,
        default=15,
        min=5,
        max=100,
        group="notifications",
        label="Daily summary rows per list",
        help="How many work items each list in the daily summary shows before it says how many more there are.",
        risk=RENDAH,
        applies=NEXT_RUN,
    ),
    Rule(
        key=DIGEST_TEAM_ROW_CAP,
        kind=INT,
        default=5,
        min=1,
        max=50,
        group="notifications",
        label="Daily summary rows per project in the team section",
        help="How many work items each project shows in the team section before it says how many more there are.",
        risk=RENDAH,
        applies=NEXT_RUN,
    ),
    Rule(
        key=DEADLINE_REMINDER_WEEKDAYS,
        kind=KEY_LIST,
        default=tuple(v for v, _ in _HARI),
        choices=_HARI,
        group="notifications",
        label="Deadline reminder days",
        help=(
            "Days of the week the deadline reminders go out. The default is every day, weekends included. "
            "A reminder that falls on a day left out is not sent later."
        ),
        risk=RENDAH,
        kep="KEP-83",
        applies=NEXT_RUN,
    ),
    Rule(
        key=ANNOUNCEMENT_EMAIL,
        kind=BOOL,
        default=True,
        group="notifications",
        label="Email every announcement",
        help=(
            "Off: announcements stay in the app and nobody gets an email for them. On: each announcement is "
            "emailed to every active member who has announcement email turned on."
        ),
        risk=SEDANG,
        applies=NEXT_RUN,
    ),
    Rule(
        key=ANNOUNCEMENT_EMAIL_ACTIVE_ONLY,
        kind=BOOL,
        default=False,
        group="notifications",
        label="Announcement email only to recently active members",
        help=(
            "On: announcement email skips members who have not opened the app within the active window of "
            "Notifications > Sending rules. Off: it reaches everyone, as the announcements are meant to."
        ),
        risk=SEDANG,
        applies=NEXT_RUN,
    ),
    Rule(
        key=ALL_MENTION_MIN_LEVEL,
        kind=LEVEL,
        default=10,
        choices=(10, 12, 20, 30, 33, 35, 40),
        group="notifications",
        label="Lowest level that can notify everyone with @all",
        help=(
            "@all in a work item description or comment notifies every active member of the project. Below "
            "this level it stays plain text and nobody is notified. Member means anyone."
        ),
        risk=SEDANG,
        kep="KEP-91",
        applies=NEXT_RUN,
    ),
    Rule(
        key=LOGIN_RETENTION_WARNING_DAYS,
        kind=INT,
        default=7,
        min=1,
        max=30,
        group="security",
        label="Login history warning lead time (days)",
        help=(
            "How many days before login records are purged the warning and admin email start. Does not "
            "change how long records are kept."
        ),
        risk=RENDAH,
    ),
    Rule(
        key=NOTIFICATION_CLEANUP_DAYS,
        kind=INT,
        default=7,
        min=0,
        max=365,
        group="notifications",
        label="Clean up inbox notifications older than (days)",
        help=(
            "Once a day, notifications that arrived more than this many days ago are archived or deleted, "
            "whichever is chosen below. Read or unread makes no difference. Snoozed notifications wait until "
            "the snooze ends. 0 turns the cleanup off."
        ),
        risk=SEDANG,
        applies=NEXT_RUN,
    ),
    Rule(
        key=NOTIFICATION_CLEANUP_ACTION,
        kind=CHOICE,
        default=PEMBERSIHAN_ARSIP,
        choices=(
            (PEMBERSIHAN_ARSIP, "Archive them (people can still find them under Archived)"),
            (PEMBERSIHAN_HAPUS, "Delete them"),
        ),
        group="notifications",
        label="What the inbox cleanup does",
        help=(
            "Archive keeps old notifications under the Archived filter of the inbox. Delete removes them for "
            "good from everyone's inbox. Only matters while the cleanup above is not 0."
        ),
        risk=SEDANG,
        applies=NEXT_RUN,
    ),
)
