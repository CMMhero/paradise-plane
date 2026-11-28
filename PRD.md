# Paradise Task Tracker, product requirements

## Concept

One internal place for PT Paradise Perkasa to track work, log hours and keep
company documentation, on our own server. It is a fork of Plane Community
Edition (AGPL-3.0). [`README.md`](README.md) describes how each custom part
works, and [`CHANGELOG.md`](CHANGELOG.md) is the release history.

## Users and positions

Positions are ordered by level. Higher levels supervise lower ones inside the
places they hold.

| Level | Position          | Placed in               |
| ----- | ----------------- | ----------------------- |
| 10    | Staff             | departments             |
| 12    | Leader            | departments             |
| 20    | Supervisor        | departments             |
| 25    | Assistant manager | departments             |
| 30    | Manager           | departments, divisions  |
| 33    | Branch Manager    | a branch                |
| 35    | Secretary         | whole organization view |
| 40    | Director          | whole organization      |

## Features built on top of Plane

- Time logging on work items.
- Personal and project settings managed from God Mode.
- Company wiki with per-folder edit control and nested pages.
- Division dashboard, KPI pages, audit logs, initiatives.
- Work approvals by position level, with God Mode work rules.
- Notifications per person (inbox and email), twice-daily digest.
- Chat with system channels for announcements and the changelog.
- Announcements page with a Markdown editor.
- One email design with a preview page in God Mode.

## Requirements added in 2.15.0

| Requirement                     | Acceptance                                                                                               |
| ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Export work item lists to Excel | Same filters and order as the list; never a row the list hides; guests refused; over 10,000 rows refused |
| Assistant manager position      | Assignable in God Mode, survives placement saves, outranks supervisors, below managers                   |
| Authors manage announcements    | Edit and delete from the Announcements page while the author may still post; nobody else                 |
| Announcement email              | Markdown rendered; button opens the Announcements page; preview sample in God Mode                       |
| Markdown in chat                | Rendered in every conversation; mentions and links keep working; typed text keeps its meaning            |
| File cards                      | Icon, name, size, preview, download; only this app's files are previewed or kept                         |
| Usable mentions                 | Cards and chips work inside the work item panel; description mentions notify                             |

## Requirements added in 2.15.1

| Requirement                          | Acceptance                                                                                            |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| Descriptions, comments, history      | Description column plus Comments and Activity sheets, one row per entry, only for exported work items |
| Export never shows more than the app | Entries from departments the user is not in are left out; unseen work items are never named           |

## Requirements added in 2.15.2

| Requirement                 | Acceptance                                                                                       |
| --------------------------- | ------------------------------------------------------------------------------------------------ |
| Easy-to-remember passwords  | Any 8 or more characters are accepted on sign-up, set, change and reset; no character mix needed |
| Strictness stays adjustable | God Mode can require Strong or Very strong; nothing below 8 characters is ever accepted          |

## Requirements added in 2.15.3

| Requirement             | Acceptance                                                                                      |
| ----------------------- | ----------------------------------------------------------------------------------------------- |
| Inbox cleanup runs      | The worker registers the task; once a day, older notifications are archived or deleted as set   |
| No silent dead schedule | The test suite fails when any scheduled task is not registered in a freshly started interpreter |

## Architecture

- `apps/web` React Router app, `apps/admin` God Mode, `apps/live` collaborative
  editing, `apps/api` Django API with Celery workers.
- PostgreSQL, Redis, RabbitMQ, MinIO, Caddy. Docker Compose.
- Work rules live in `plane/utils/aturan`. Positions and placement live in
  `plane/db/models/hierarki.py` and `plane/db/penempatan.py`.

## Implementation notes for 2.15.3

- Task modules under `plane/bgtasks` are not discovered automatically. A new
  scheduled task goes into `CELERY_IMPORTS` in `plane/settings/common.py`.
- Archiving sets `archived_at` to one timestamp per run, so a run can be undone
  by clearing the rows that carry it.

## Implementation notes for 2.15.2

- The server check is `sandi_cukup_kuat` in
  `plane/authentication/utils/kata_sandi.py`. Screens check only the length
  (`getPasswordStrength` in `packages/utils`), so a password refused by a
  stricter God Mode setting is reported after submit.
- Login rate limits are unchanged.

## Implementation notes for 2.15.1

- Comments and history are loaded with a fixed number of queries. Mentions are
  resolved in one pass (`sebutan_massal` in `plane/utils/teks_html.py`).
- The history leaves out comment, reaction, vote and draft rows, as the app does.
- Excel cuts a cell at 32,767 characters. There is no separate limit on the
  number of comment or activity rows.

## Implementation notes for 2.15.0

- Export is synchronous. `plane/utils/daftar_tugas.py` holds the scoping shared
  by lists and export, `plane/utils/ekspor_tugas.py` the column registry.
- Markdown has two renderers (TypeScript and Python) checked against one
  fixture, `plane/tests/data/markdown_polos.json`.
- File cards use the existing `fileComponent` editor node. The server sanitizer
  is the boundary for its `src`.

## Known gaps

- Opening a work item panel can reload it on a background refresh and drop an
  unsent comment.
- Mentions typed on the Announcements page do not notify anyone.
- Announcement edits change text only, not attachments, and send no new email.
- The author of an announcement receives no email copy.
