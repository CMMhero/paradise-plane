# Paradise Task Tracker

Internal work management system for PT Paradise Perkasa. It runs on our own
server, with no monthly subscription to anyone.

It is used by 16 divisions and 79 accounts today.

## Why it exists

The office needs one place to track work, log hours, and keep company
documentation. Commercial tools get expensive multiplied by 79 people, and the
data sits on someone else's server.

So I took a good open-source base (Plane CE, AGPL, see the bottom section) and
built the parts the office needs that it doesn't have.

## What I built myself

None of the following exists in the original base. All of it is from scratch:
database models, migrations, endpoints, permission rules, and the UI.

**Time tracking.** People log hours directly on the work item. Everyone can
delete only their own entries, and project admins can see all of them.

**Work item types, templates + recurring, and Cycles: removed (2 Nov 2026,
KEP-53).** All three were built, then dropped from the app because the office
didn't use them. The pages, menus, God Mode toggles, custom endpoints, and the
recurring schedule are gone. The tables were left in place on purpose, so old
data isn't lost. In their place, every project feature (Modules, Views, Pages,
Intake, Time tracking) is now on in every project, including old ones. Whether
it shows up is decided by the module toggle in God Mode.

**Personal and project settings are managed from God Mode (KEP-44, KEP-57).**
Every setting a person can change themselves (language, time zone, theme, week
start, notifications, items pinned in the sidebar, project list style, work item
layout) has a default under Members > New member defaults, and can be changed
per person from the member panel. The default work item layout is Board. New
account defaults don't silently overwrite existing accounts. For navigation and
layout there is an "Apply to everyone" button that asks for confirmation. New
projects follow Workspaces > New project defaults (visibility, time zone,
auto-archive/auto-close, guest access), and the creator can still change them in
the form.

**Design system (KEP-64).** Every color, radius, font, and motion value is a
token in `packages/tailwind-config/paradise-tampilan.css`. Components use token
classes and component props (`variant`, `size`) and don't write their own
colors, radii, or padding. Backgrounds are tinted to match the scheme, never
plain white or black. There are five schemes: Ember (default, red brand accent),
Dusk, Ink, Forest, and Neutral, each with its own accent. The fonts are Plus
Jakarta Sans and Geist Mono. Nothing is fully round except profile photos. In
Profile > Preferences each person can pick a color scheme, a font (Plus Jakarta
Sans, Inter, Geist, Figtree, Bricolage Grotesque, Archivo, Sora, Shantell Sans,
JetBrains Mono, Source Serif 4, or the system font), and reduce motion. The
default for new accounts follows the God Mode rules above.

**Company wiki.** This is the longest piece, built in three stages:

Stage A, pages accept every file type (pdf, docx, mp4, zip) up to 100 MB, plus a
"File" node in the editor that shows a PDF inline in the page.

Stage B, edit control per folder. Each top-level folder is owned by a specific
division. Only its members can edit and everyone else is read-only. This took
the most time, because it has to be enforced in **two places**: the REST API
and the real-time collaboration server. With REST only, someone outside the
division would see the page as editable, type a long text, and lose it on
reload. The `can-edit/` endpoint deliberately doesn't copy the permission
rules. It calls the exact same permission class, so REST and the editor can't
disagree.

Stage C, nested page tree. Sub-pages used to be not just invisible but a
**404 when opened**.

**Division dashboard.** Built for directors and Super Admins, so the first thing
shown is Summary mode: one sentence about which division has a problem, four
numbers (done on time, done in 7 days, overdue, waiting for your approval) with
a comparison to last week, the status of each division (On track / Needs
attention / Critical), and at most five things worth a look. Full numbers per
department, hours worked, and CSV export (opens directly in Excel) are in
Detail mode. The third mode, Report, answers "what got done": pick 7 days, 30
days, this month, or last month, then see the count done (compared with the
previous period), the on-time percentage, a bar per division, and the title of
every completed work item per division > project with the assignee and date.
The full list can be downloaded as CSV.

**KPI.** The KPI menu (`/kinerja`) is there for everyone. Staff see their own
numbers: done, on-time percentage, done late, overdue now, open work items,
average and median completion time, completions approved or rejected, plus a
trend per day or per week. Leaders and supervisors can also open their
department and each of their subordinates, managers open their division, and
secretaries, directors, and workspace admins open the whole organization.
Anything beyond that gets a 403 from the server. The period can be this week,
this month, 30 days, this quarter, or a custom range, always counted in working
days. A work item with several assignees counts in full for each person, and
once in the department, division, and organization numbers. The metric list is a
single table in `apps/api/plane/utils/kinerja.py` (`METRIK`), and the web page
follows that table. Status thresholds are set in God Mode > Features. Only
projects you are a member of are counted.

**Auto-archive.** Done work items that finished long ago move to Archives on
their own. A Super Admin picks the age in God Mode > Features > Work items: Off,
7, 14, 30, 60, 90 (default), 180, or 365 days. It applies to all projects, runs
once a day, and canceled items are skipped. Archived items can be restored from
Archives.

**Initiatives.** Workspace-level goals that tie together several division
projects. Progress is calculated from all the work items in the linked projects.

**Audit logs.** Records who changed what on the important models. The actor is
captured both through normal HTTP requests and through the collaborative editor.
I doubted the second one, but it works.

**God Mode lists can be filtered like work items.** Accounts, Activity, Audit
log, and Trash have a search box, a Filters button that adds chips (property,
is / is not, value), a Display menu for sort order, visible columns, and row
count, plus table headers you can click to sort. The choices are remembered per
page in the browser. Accounts are filtered in the browser (all accounts are
loaded once). Audit log and the login history are filtered on the server because
they can hold hundreds of thousands of rows.

**Notifications you choose yourself.** In Profile > Notifications there is one
table: each kind of update (assigned, mentioned, comment, approval, due and
overdue, work item done, status change, other changes, chat) has two toggles,
in-app inbox and email. The task digest arrives twice each working day, each
with its own toggle: 08:30 WIB to start the day, 17:30 WIB to close it (what got
done today, what is due today but not done, overdue, and what is due the next
working day). The contents of each digest can be picked per section. Defaults
follow the person's role, and the exact same table appears in God Mode, both for
a single person and for the staff and leadership defaults. The list of toggles
is written only once on each side (`preferensi_email.py` and
`notification-preferences.ts`), so those three screens can't drift apart.

**Export to Excel.** Project, workspace view, Your work, module and project view
lists have an Export to Excel button. The file follows the filters and order on
screen. Both the list and the export read one scoping function
(`plane/utils/daftar_tugas.py`), so permissions can't drift apart. Columns live
in one registry in `plane/utils/ekspor_tugas.py`. To try it:

```
GET /api/workspaces/<slug>/projects/<project-id>/issues/export-xlsx/?order_by=-created_at&export_name=gudang
```

**File cards.** A file dropped or pasted into a description or comment becomes a
card with a type icon, size, preview and download. A card may only point at this
app's own files, both in the sanitizer and in the preview.

**Chat as the news hub.** Every workspace has the system channels Announcements
and Changelog, and everyone is added automatically. The Changelog fills itself on
every deploy from `apps/api/plane/release_notes/<versi>.json`: write the new
version file (Added/Changed/Fixed entries) together with the version bump, and
the API posts it at startup, once. Work updates (approvals, mentions, comments,
changes) arrive as cards with buttons in the private "Paradise" space, and
Approve/Reject works right from the card. There is also a call log, online
indicators, channel management, and paste/drag-and-drop attachments.

Messages and announcements are Markdown. The browser renderer
(`apps/web/core/lib/markdown/`) and the server one
(`plane/utils/markdown_pesan.py`) share one fixture file,
`plane/tests/data/markdown_polos.json`. An announcement's author edits or deletes
it on the Announcements page.

Type `@` in the message box to mention people in that conversation. In a
channel, the mentioned person also gets a card in their Paradise space. Every
division and department has its own private channel, with members following the
placement in God Mode (`plane/utils/kanal_organisasi.py`, called from
`plane/db/jangkauan.py`): add someone to another department and they join its
channel, remove them and they leave. Directors and secretaries are not added
automatically.

**People placement (KEP-76).** Each person has one rank (Staff, Leader,
Supervisor, Assistant manager, Manager, Branch Manager, Secretary, Director) and one list of places. Every rank can be in
several departments, and a manager also leads one or more divisions. The
secretary (35, KEP-101) reaches the whole organization like a director without
being placed, but sits one step below: can't assign work to a director and
isn't an approver of the director's work. Adding a place never moves an old one,
and demoting a manager only releases their divisions. All placement writes go
through `plane/db/penempatan.py`. Example, adding Ani to a second department
from God Mode:

```
POST /api/instances/hierarki/
{ "member_id": "<ani>", "departemen_id": "<dep IT-SAP>" }   # add one
{ "member_id": "<ani>", "departemen_ids": ["<IT-AI>", "<IT-SAP>"] }  # full list
{ "member_id": "<budi>", "divisi_ids": ["<Sales>", "<HRGA>"] }       # manager of 2 divisions
```

**One design for email.** All email goes through `plane/utils/email_merek.py`
and `templates/emails/base.html`. The logo and photos are embedded because the
server is only on the LAN. To check how it looks, use God Mode > Email > Preview,
or send every sample to a test inbox with
`python manage.py kirim_contoh_email --kirim` (it only sends to
it.ai1@itechmandiri.com).

**Wiki folder ACL.** Folders map to divisions, sub-pages inherit from their
parent, and admins can override. I deliberately added no dependency: division
membership keeps changing, so a static grant drifts away from reality.

**Live screens, no F5.** When a work item, comment, or notification changes,
Django publishes a small hint to Redis (`data:<slug>`, only the id and field
names, no content), `apps/live` forwards it to the tabs of people allowed to
see it, and the screen refetches through the normal API. That keeps the
visibility rules in one place. There is also a refresh button in the top nav
that refreshes the screen contents without reloading the page. If the socket
drops, a fallback timer fires every 45 seconds. The design and its traps are in
the vault (KEP-102).

## The operations side

I run this myself too, and honestly this part teaches the most lessons:

- **CI/CD**: every push to `main` builds 6 images to GHCR. Tags use the commit
  SHA, then `latest` is moved with `imagetools create` (it copies the manifest,
  no rebuild). Builds use the GitHub Actions layer cache, and the Node
  Dockerfiles install dependencies before copying source, so a commit that only
  changes code doesn't redownload every package. A release is one command from
  the laptop, `paradise/bin/rilis.sh`: it waits for `latest` on GHCR to move to
  that commit, takes a backup, deploys detached from SSH, then matches the
  version being served. `deploy.sh` fails if a migration fails (it used to still
  report HEALTHY). Rollback is just `APP_RELEASE=<sha>`.
- **Backup**: compressed `pg_dump`, with retention, and the output is checked to
  be non-empty. It also **waits** for Postgres to actually be ready instead of
  giving up when Docker isn't up yet. That came from two mornings in a row of
  failed backups.
- **Healthchecks** for every service, plus a scheduled-task registration script
  that doesn't need admin rights on Windows.

## Running it locally

A guide from zero to a running app. It's written for Windows because that's what
is used here, but the bash steps are identical on macOS and Linux.

Read it all the way through before typing. There are seven steps, and steps 3
and 4 are the ones most often skipped, which makes `pnpm dev` look "broken".

### Step 1, install the tools

| Tool               | Minimum version | What for                                                              | Download                                          |
| ------------------ | --------------- | --------------------------------------------------------------------- | ------------------------------------------------- |
| **Docker Desktop** | latest          | Postgres, Redis, RabbitMQ, MinIO, and the Django backend all run here | <https://www.docker.com/products/docker-desktop/> |
| **Node.js**        | **22.18.0**     | frontend and the collaboration server                                 | <https://nodejs.org/en/download>                  |
| **pnpm**           | **11.3.0**      | monorepo package manager, see the note below                          | <https://pnpm.io/installation>                    |
| **Git**            | 2.40+           | Git for Windows also gives you Git Bash                               | <https://git-scm.com/downloads>                   |
| VS Code (optional) | latest          | the extensions in use are listed in `.vscode/`                        | <https://code.visualstudio.com/>                  |

The machine needs **12 GB of RAM** (8 GB often fails during the container build)
and about **15 GB** of free disk.

**Node 20 isn't enough.** `package.json` requires `>=22.18.0`, and pnpm will
refuse to install with `ERR_PNPM_UNSUPPORTED_ENGINE`. This differs from the old
docs, so check the actual version instead of assuming.

**Don't use just any pnpm version.** The version is pinned in `packageManager`
(`pnpm@11.3.0`). The safest way is through corepack, which ships with Node:

```powershell
corepack enable pnpm
corepack prepare pnpm@11.3.0 --activate
```

If `corepack` isn't in your Node install, `npm install -g pnpm@11.3.0` also
works. What you must not use is pnpm 9 or 10, which will reject the lockfile.

**Windows only**, once per machine, so deep `node_modules` paths don't hit the
260-character limit:

```powershell
git config --global core.longpaths true
```

Verify everything before moving on:

```powershell
node --version            # must be v22.18.0 or newer
pnpm --version            # must be 11.3.0
docker --version
docker compose version
git --version
```

### Step 2, get the code

```powershell
git clone <url-repo>
cd <folder-repo>
```

### Step 3, Windows only: fix the i18n symlink

This repo has **one** symlink tracked by git: `packages/i18n/locales` points to
`packages/i18n/src/locales`. Git on Windows doesn't create symlinks unless
Developer Mode is on, so what comes out of `git clone` is an **11-byte text
file** containing the text `src/locales`. As a result, no translations load.

The symptom is that the whole UI shows raw keys like `auth.common.email.label`
instead of text.

Check first:

```powershell
Get-Item packages\i18n\locales | Select-Object Name, LinkType
```

`LinkType` must be `Junction`. If it's empty, fix it:

```powershell
Remove-Item packages\i18n\locales -Force -Recurse -ErrorAction SilentlyContinue
cmd /c mklink /J packages\i18n\locales packages\i18n\src\locales
git update-index --skip-worktree packages/i18n/locales
Add-Content .git\info\exclude "/packages/i18n/locales/"
```

The last line stops VS Code from showing 532 shadow files. This is local, and
deliberately in `.git/info/exclude` rather than `.gitignore`, because it's a
problem with Windows machines, not with the project.

A cleaner alternative if you're allowed: turn on **Developer Mode** in Windows,
then `git config --global core.symlinks true`, then clone again. After that you
never need this step.

Never "fix" it by copying the contents of `src/locales` into `locales`. The copy
will silently drift.

### Step 4, create the `.env` files, all **SIX**

This is the number one cause of "I pulled but `pnpm dev` doesn't work". The old
guide only said to create two, and two isn't enough.

| File              | Read by                                                | If it's missing                                 |
| ----------------- | ------------------------------------------------------ | ----------------------------------------------- |
| `.env`            | `docker compose`, for Postgres, Redis, RabbitMQ, MinIO | containers fail to start, variables are empty   |
| `apps/api/.env`   | Django, Celery, migrator                               | API is down or rejects every call               |
| `apps/web/.env`   | Vite, for the web app                                  | **web runs but is completely dead**, see below  |
| `apps/admin/.env` | Vite, for God Mode                                     | same, God Mode can't call the API               |
| `apps/space/.env` | Vite, for the public pages                             | same                                            |
| `apps/live/.env`  | collaboration server                                   | **`live` crashes at once and restarts forever** |

The two most confusing results, and neither mentions `.env` anywhere in the
error message:

- **`apps/live/.env` is missing.** The command is `node --env-file=.env .`, and
  Node exits if the file isn't there. The supervisor starts it again, it dies
  again. In the `pnpm dev` output it looks like the whole dev server is failing.
- **`apps/web/.env` is missing.** `VITE_API_BASE_URL` is empty, and the code
  falls back to an empty string (`packages/constants/src/endpoints.ts`). Every
  API call then goes astray to `localhost:4000`, which has no backend. The page
  opens but stays blank or keeps spinning, and the only error is a 404 in the
  Network tab.

The quick way, through **Git Bash** (or macOS/Linux):

```bash
bash setup.sh
```

The script copies all six from their `.env.example` files, **doesn't overwrite
existing ones**, and fills in Django's `SECRET_KEY`.

Manually through PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item apps\api\.env.example   apps\api\.env
Copy-Item apps\web\.env.example   apps\web\.env
Copy-Item apps\admin\.env.example apps\admin\.env
Copy-Item apps\space\.env.example apps\space\.env
Copy-Item apps\live\.env.example  apps\live\.env

$chars = (48..57) + (97..122) | ForEach-Object { [char]$_ }
$key = -join (1..50 | ForEach-Object { $chars | Get-Random })
Add-Content apps\api\.env "SECRET_KEY=$key"
```

⚠️ If your clone of the repo **already has a `.env`**, skip this step entirely.
Don't overwrite it, it holds real credentials.

The defaults are right for local dev. One thing you must keep matched yourself if
you change things: **`LIVE_SERVER_SECRET_KEY` in `apps/api/.env` and
`apps/live/.env` must be exactly the same.** Even a small difference makes the
collaborative editor reject every connection as unauthorized, even for people
who are allowed in.

### Step 5, start the supporting services (Docker)

Docker Desktop has to be **already running**, not just installed.

PowerShell:

```powershell
docker compose -f docker-compose-local.yml up -d --build
```

Git Bash, macOS, Linux:

```bash
COMPOSE_FILE=docker-compose-local.yml docker compose up -d --build
```

⚠️ The `COMPOSE_FILE=... docker compose ...` form is **bash syntax**. Pasted into
PowerShell it fails right away with `The term 'COMPOSE_FILE=...' is not recognized`.
In PowerShell use `-f`.

The first build takes **5 to 15 minutes**, since the Django image is built from
source.

What comes up: `plane-db`, `plane-redis`, `plane-mq`, `plane-minio`, `api`,
`worker`, `beat-worker`, and `migrator`.

**`migrator` stops by itself with status `Exited (0)`, and that's normal.** It
only runs once to migrate the database. It isn't a dead container.

Check:

```powershell
docker compose -f docker-compose-local.yml ps
curl.exe http://localhost:8000/api/instances/
```

There is a thin wrapper too: `.\paradise\bin\dev.ps1 up|down|logs|ps|rebuild` on
Windows, or `make dev-up` / `make dev-logs svc=api` in bash.

### Step 6, install dependencies and run the frontend

```powershell
pnpm install
pnpm dev
```

The first `pnpm install` takes 3 to 8 minutes. `pnpm dev` **doesn't give you a
port right away**: turbo first builds 12 internal packages (`dev` has
`dependsOn: ["^build"]` in `turbo.json`), then starts the 4 apps. So 1 to 3
minutes of silence before any address you can open is normal. Don't Ctrl+C too
early.

**After every `git pull`, run `pnpm install` again** if `package.json` or
`pnpm-lock.yaml` changed too. This is the most common cause of "it worked
yesterday, broke after the pull", and the error is usually `Cannot find module`.

### Step 7, register the first admin

1. Open **<http://localhost:3001/god-mode/>** and register the first instance
   admin.
2. Only then open **<http://localhost:4000>** for the app.

The order can't be reversed: until an instance admin exists, the main app has
nothing to serve.

### Step 8, fill in a sample organization

A freshly registered instance is **empty**, and empty means most features can't
be tried at all. The Wiki is the most obvious case: the `/wiki` route looks for
a project with the identifier `WIKI` at runtime, and if it isn't found, all you
get is a "Wiki not available yet" screen with no buttons.

One command creates a full sample organization:

```bash
# dry run first, writes nothing
docker compose -f docker-compose-local.yml exec -T api     python manage.py shell < paradise/bin/seed-demo.py

# if the result looks right, apply it
docker compose -f docker-compose-local.yml exec -T api     -e SEED_DEMO_APPLY=1 python manage.py shell < paradise/bin/seed-demo.py
```

What it creates: the `nomaden-demo` workspace, five accounts, three division
projects (OPS, SALES, TECH), the `WIKI` project with its governance, plus three
Wiki folders that deliberately represent three different permission states (one
with an owning division, General open to everyone, and one deliberately left
locked).

All accounts use the password `Demo1234!`, and you sign in with
`owner@demo.local`. It can be changed through environment variables:

| Variable              | Default        |
| --------------------- | -------------- |
| `SEED_DEMO_WORKSPACE` | `nomaden-demo` |
| `SEED_DEMO_NAME`      | `Nomaden Demo` |
| `SEED_DEMO_DOMAIN`    | `demo.local`   |
| `SEED_DEMO_PASSWORD`  | `Demo1234!`    |

It's safe to run many times, nothing piles up. And it refuses to run if the
target workspace turns out to belong to someone else, so it can't be poured onto
real data by accident.

**Local only.** The password is the same for everyone and is written in the file.

#### Full sample company (hierarchy + work items)

The `seed-demo.py` above only fills the Wiki and doesn't know about the
hierarchy (KEP-29). To make the app feel alive, there is a second command that
fills the **main workspace**:

```bash
docker compose -f docker-compose-local.yml exec api python manage.py seed_demo_data --settings=plane.settings.local          # fill
docker compose -f docker-compose-local.yml exec api python manage.py seed_demo_data --reset --settings=plane.settings.local  # remove the old data, fill again
```

`--settings=plane.settings.local` is required. Without it `manage.py` runs with
the production settings (the `manage.py` default, including in the local
container), and the command refuses.

What's in it: 5 divisions, 12 departments (each department automatically gets
its project), 56 accounts across the ranks (2 directors, 5 managers, 11
supervisors, one of them holding two departments, and 38 staff), labels,
modules, pages, saved views, about 170 parent work items and sub-items with
assignees, comments, activity, attachments, links, relations, reactions, and
worklogs. There are also approvals (pending, approved, rejected), 6
cross-division requests in intake, drafts, and Inbox notifications.

Outside projects: Chat (General channel, Announcements, private per-division
channels, DMs between supervisor and staff, with replies, reactions,
attachments, and unread messages), Wiki (two sub-topics per division holding
material uploaded by that department's members), 14 days of login history for
God Mode > Logs, plus each account's sidebar pins, favorites, stickies, quick
links, and Recents.

Your Super Admin account (the real account, not a demo one) is included too: in
every department there are work items you created for staff and work items (plus
sub-items) a supervisor assigned to you, you also commented, you have a "Catatan
IT" page in every project, uploaded one Wiki item per division, have one draft,
are in the General channel, and got a DM from the director. Your personal
settings (sidebar pins, favorites, stickies) aren't touched, and everything
added is cleaned up on `--reset`.

The attachments are real files (PDF, PNG, CSV, TXT) uploaded to MinIO, so they
open. `--reset` also removes the objects from MinIO. Cycles aren't created
because the module was removed (KEP-53).

All emails use the `@paradise.test` domain, and the password is `P@ssw0rd`.
Sample accounts to try: `hendra.gunawan@` (director), `bambang.prasetyo@` (Sales
manager), `rudi.hartono@` (supervisor), `dimas.saputra@` (staff).

Project membership isn't written by hand. It all comes out of the same hierarchy
sync as God Mode, so if some access looks odd, that's a hierarchy bug, not a
seed bug. `--reset` only sweeps the `@paradise.test` accounts, the sample
divisions and departments, and anything tagged `seed-demo`.

**Local only, and it can't run on the server.** It isn't a data migration, so a
deploy never runs it. On top of that there are three guards with no shortcut:
settings must be `plane.settings.local`, an instance with more than 5 real
accounts is refused, and the seed files don't ship in the production image
(`apps/api/.dockerignore`), so the command doesn't even exist on the server.

### Port table

| Service              | Port     | Address                                |
| -------------------- | -------- | -------------------------------------- |
| Web (main app)       | **4000** | <http://localhost:4000>                |
| Admin / God Mode     | 3001     | <http://localhost:3001/god-mode/>      |
| Space (public pages) | 3002     | <http://localhost:3002/spaces/>        |
| Live (collaboration) | 3100     | <http://localhost:3100/live/health>    |
| API (Django)         | 8000     | <http://localhost:8000/api/instances/> |
| MinIO console        | 9090     | <http://localhost:9090>                |
| PostgreSQL           | 5432     |                                        |
| Redis                | 6379     |                                        |
| RabbitMQ             | 5672     |                                        |

**The web app is on 4000, not 3000.** Upstream uses 3000, and that still sticks
to a lot of docs and tutorials out there.

### Daily commands

```powershell
pnpm dev                  # start all frontends + live
pnpm check:types          # type check
pnpm check:lint           # oxlint
pnpm check:format         # oxfmt
pnpm build                # build the whole app
pnpm fix                  # auto-fix format + lint

docker compose -f docker-compose-local.yml logs -f api
docker compose -f docker-compose-local.yml restart api
docker compose -f docker-compose-local.yml down
```

Two things that will confuse you if you don't know them:

- Changed backend code? **`docker compose restart api`.** Autoreload doesn't
  work here, because the Windows bind mount into the container doesn't forward
  file change events. The symptom is an endpoint returning 404 even though the
  code is right.
- Changed `.env`? **`docker compose up -d`, not `restart`.** `restart` doesn't
  reread `env_file`.

### If it doesn't work

Find the symptom in the left column. Almost everything that has happened is
here.

| Symptom / error message                                                                                        | Cause                                                                             | Fix                                                                                            |
| -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `ERR_PNPM_UNSUPPORTED_ENGINE`, "Unsupported engine"                                                            | Node is below 22.18.0                                                             | install Node 22.18+, then `pnpm install` again                                                 |
| `pnpm` isn't recognized, or the version isn't 11.3.0                                                           | pnpm isn't enabled or is the wrong version                                        | `corepack enable pnpm` then `corepack prepare pnpm@11.3.0 --activate`                          |
| `ERR_PNPM_LOCKFILE_BREAKING_CHANGE` / `ERR_PNPM_OUTDATED_LOCKFILE`                                             | pnpm version mismatch, or the lockfile changed after a pull                       | make sure it's pnpm 11.3.0, then `pnpm install` (without `--frozen-lockfile`)                  |
| After `git pull`, `Cannot find module ...` appears                                                             | new dependencies aren't installed yet                                             | `pnpm install`                                                                                 |
| `live` dies then restarts over and over, `apps/live/live-dev.log` says `ENOENT ... .env`                       | `apps/live/.env` is missing                                                       | create it from `apps/live/.env.example`, see step 4                                            |
| The page on 4000 opens but stays blank or keeps spinning, Network tab full of 404s to `localhost:4000/api/...` | `apps/web/.env` is missing, `VITE_API_BASE_URL` is empty                          | create `apps/web/.env`, then **stop and restart** `pnpm dev` (Vite reads `.env` only at start) |
| The browser console says **CORS**                                                                              | `CORS_ALLOWED_ORIGINS` in `apps/api/.env` doesn't include `http://localhost:4000` | add it, then `docker compose -f docker-compose-local.yml up -d` (not `restart`)                |
| All text turns into raw keys, for example `auth.common.email.label`                                            | the i18n junction is broken or was never created                                  | step 3                                                                                         |
| `git status` suddenly shows hundreds of changes in `packages/i18n/locales/**`                                  | the junction was broken by the pre-commit hook                                    | **don't commit**, restore it first, steps are in [CONTRIBUTING.md](CONTRIBUTING.md)            |
| `EPERM` / `ENOENT` during `pnpm install`, paths too long                                                       | Windows 260-character limit                                                       | `git config --global core.longpaths true`, delete `node_modules`, install again                |
| `error during connect`, `docker daemon is not running`                                                         | Docker Desktop isn't running                                                      | start Docker Desktop, wait for the icon to turn green                                          |
| `The term 'COMPOSE_FILE=...' is not recognized`                                                                | bash syntax pasted into PowerShell                                                | use the `docker compose -f docker-compose-local.yml ...` form                                  |
| `port is already allocated`, or `EADDRINUSE` on 4000                                                           | the port is used by another process                                               | `netstat -ano \| findstr :4000` then `taskkill /PID <pid> /F`                                  |
| `migrator` status is `Exited (0)`                                                                              | that's how it's meant to be                                                       | not an error, ignore it                                                                        |
| A backend endpoint returns 404 even though the code is right                                                   | the backend doesn't autoreload                                                    | `docker compose -f docker-compose-local.yml restart api`                                       |
| Changed `.env` but nothing happened                                                                            | `restart` doesn't reread `env_file`                                               | `docker compose -f docker-compose-local.yml up -d`                                             |
| `pnpm dev` is silent for a long time with no port                                                              | turbo is still building 12 internal packages                                      | wait 1 to 3 minutes                                                                            |
| Strange turbo errors that make no sense                                                                        | the turbo daemon is stuck                                                         | `pnpm exec turbo daemon stop`, then try again                                                  |
| Attachments and avatars fail to load                                                                           | `MINIO_PUBLIC_ENDPOINT_URL` is empty in `apps/api/.env`                           | set it to `http://localhost:9000`, then `up -d`                                                |
| The collaborative editor rejects connections as unauthorized (close code 1008)                                 | `LIVE_SERVER_SECRET_KEY` differs between api and live                             | make them exactly the same, then `up -d` and restart `pnpm dev`                                |

If you're still stuck, send **the exact error text** plus the output of
`node --version`, `pnpm --version`, and
`docker compose -f docker-compose-local.yml ps`. Those three are usually enough
to point at the cause.

The rest (production deploy, the security checklist, how to sync from upstream)
is in the `paradise/` folder.

## Built with

Django REST Framework, PostgreSQL, Redis, RabbitMQ + Celery, and MinIO on the
backend. React + React Router, TypeScript, MobX, and Tailwind on the frontend.
Hocuspocus (Y.js) for the collaborative editor. All of it is wrapped in Docker
Compose, with Caddy in front.

## What isn't done

To be honest about it:

- **SMTP doesn't work yet.** The fields are filled in, but the host is still a
  placeholder that doesn't resolve from inside the container. So user invites and
  password resets won't arrive. Waiting on the mail server IP from IT.
- **There is no production server yet.** Everything still runs locally.
- **The Wiki content is still a skeleton.** The engine is finished, but the
  documents aren't written, and that's human work, not code work.
- **It has never synced from upstream.** There's a risk of conflicts, so it'll
  be done on its own branch.

## About the code base

This is built on **Plane Community Edition v0.24.0**, licensed under the
**GNU AGPL-3.0**. Attribution details and license obligations are in
[NOTICE.md](NOTICE.md) and [LICENSE.txt](LICENSE.txt).

I removed the original product's branding from the UI. This system isn't a
vendor product and isn't sold, so showing someone else's brand inside it would
only confuse people. But **the legal attribution stays**: the copyright headers
in the source files, the license text, and the NOTICE file. Those are two
different things, and the second one isn't mine to remove.

If you use this over a network, AGPL section 13 still applies, whether it's sold
or not.

## License

GNU Affero General Public License v3.0. See [LICENSE.txt](LICENSE.txt).
