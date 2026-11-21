# Contributing guide, Paradise Task Tracker

Internal repository of PT Paradise Perkasa. This guide is for anyone working on
the code.

---

## Setting up your environment

**The full guide is in [README.md, section "Running it locally"](README.md#running-it-locally).**
It lives in one place on purpose. A short version here once drifted from
reality and cost people time.

**Prerequisites:** Docker, **Node >= 22.18.0** (not 20), **pnpm 11.3.0** via
corepack, 12 GB RAM (8 GB often fails during the container build).

In short, seven steps: install the tools, clone, fix the i18n junction on
Windows, create **six** `.env` files (not two),
`docker compose -f docker-compose-local.yml up -d --build`,
`pnpm install && pnpm dev`, then register the first admin instance at
`http://localhost:3001/god-mode/`.

If something doesn't work, a table of symptoms and fixes is at the end of that
section.

| Service          | Port                |
| ---------------- | ------------------- |
| Web              | **4000** (not 3000) |
| Admin / God Mode | 3001                |
| Space            | 3002                |
| Live             | 3100                |
| API              | 8000                |

---

## Three environment traps you MUST remember

Each of them has already cost hours. Read this before reporting "the code
doesn't work".

**1. Changed backend code? Run `docker compose restart api`**
`runserver` doesn't auto-reload here. The Windows-to-container bind mount
doesn't forward file change events. The symptom is an endpoint returning 404
even though the code is correct.

**2. Changed `.env`? Run `docker compose up -d`, NOT `restart`**
`restart` doesn't re-read `env_file`. The container has to be recreated.

**3. Just committed something that touches locale files? Check `git status`**
`packages/i18n/locales` is a junction to `packages/i18n/src/locales`. The
`git stash` run by the pre-commit hook can break it into a real directory
holding hundreds of duplicates. If `git status` suddenly shows hundreds of
changes, the junction is broken. Don't commit, restore it first.

Also, don't put temporary files in `packages/*` or `apps/live` while `pnpm dev`
is running. The watcher will rebuild and restart the Live server in the middle
of your test.

---

## Gate before committing

Run all of it. The pre-commit hook runs lint and format on staged files, but it
doesn't run tsc or `sync:check`.

```bash
pnpm --filter web exec tsc --noEmit          # repeat for space, admin, constants
pnpm exec oxlint --deny-warnings <path>
pnpm exec oxfmt --check <path>
```

If you **add a new** `.py`, `.ts`, or `.tsx` file, it must start with a license
header that matches `COPYRIGHT.txt` exactly:

```python
# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
```

TypeScript uses the `/** ... */` block style with the same three lines. If the
file has a shebang, the header goes AFTER the first line.

This isn't a formality. The repo serves its own source code at `/source/` to
satisfy AGPL-3.0 section 13, and `copyright-check` rejects pull requests that
carry a file without a license notice. Excluded: `**/migrations/**`,
`*.config.ts`, and `*.d.ts`.

If you touch locale files, also run:

```bash
pnpm --filter @plane/i18n run sync:check     # must report 19/19
pnpm --filter @plane/i18n run generate:types
```

Notes:

- `oxlint <path>` **without** `--deny-warnings` gives a false green.
- Don't pipe the output into `tail` and then read `$?`. You'd be reading the
  exit code of `tail`. Write to a file first, or use `${PIPESTATUS[0]}`.
- Pre-existing warnings in a file you touch: **fix** them, don't silence them.

---

## Running backend tests

This was never written down anywhere before, and the cost was real. The test
module `bg_tasks/test_cleanup_task.py` imports `factory`, which only exists in
`requirements/test.txt`, and the API container doesn't install it. The result
isn't one failing test. The WHOLE collection stops with `ModuleNotFoundError`.

```bash
# once, inside the API container
docker compose -f docker-compose-local.yml exec -T api     pip install -r requirements/test.txt

# run
docker compose -f docker-compose-local.yml exec -T api     python -m pytest plane/tests/unit/ -q < /dev/null
```

Three things that save time:

- `< /dev/null` isn't decoration. Without it, `exec -T` can hang waiting for
  stdin.
- `pytest.ini` already uses `--nomigrations` and `--reuse-db`, so the schema is
  built straight from the models. A new model doesn't need its migration run
  before it can be tested, but you still MUST create the migration before
  committing.
- Available markers: `unit`, `contract`, `smoke`, `slow`. `--strict-markers` is
  on, so a mistyped marker fails instead of being ignored.

If you add a scheduled task, add its module to `CELERY_IMPORTS` in
`plane/settings/common.py`. `test_celery_registry` catches it if you forget, and
it's the most valuable guard in this suite. A task that is scheduled but not
registered gets dropped by the worker silently as "Received unregistered
task", with no symptom on screen at all.

## Adding i18n keys

- A file name in `packages/i18n/src/locales/en/` is a **namespace name**. A leaf
  key must not use the same name. `"wiki"` is rejected because `wiki.json`
  already forms the `wiki.*` namespace. Neither tsc nor oxlint detects this
  clash, only `sync:check` does.
- Keys in `common.json` can be called without a prefix (`defaultNS: "common"`).
- A new key must be added to **all 19 locales**, and then `sync:check` must
  report 19/19.

---

## Adding a background task

Register it in **two places**, otherwise the task will never run:

1. `apps/api/plane/celery.py` → `beat_schedule` (when it's sent)
2. `apps/api/plane/settings/common.py` → `CELERY_IMPORTS` (so the worker
   knows about it)

`autodiscover_tasks()` only looks for `tasks.py` in each app, while the tasks in
this repo live in `plane/bgtasks/*.py`. An unregistered task is sent by beat and
then **silently dropped** by the worker.

Verify:

```bash
docker exec pradise_plane-worker-1 celery -A plane inspect registered
```

---

## Adding a feature

Check **`apps/web/ce/`** first. The `@/plane-web/*` alias points there, and many
UI slots are already wired to empty stubs. Filling one in is much cheaper than
building a new path.

A new navigation item must be registered in **two** places, otherwise it will
never be visible:

1. the nav item list (`packages/constants/src/workspace.ts`)
2. `getSidebarNavigationItemIcon` in `apps/web/ce/.../sidebar/helper.tsx`. This
   `switch` has no `default`, so an unregistered key renders without an icon
   and without any error

Dynamic nav items are also hidden when they aren't pinned. Register them through
`additionalStaticItems` so they always show.

---

## Commit conventions

```
<type>(<scope>): <short description, lowercase>

The body explains WHY, not just what. Name the wrong behavior being fixed, and
also name what was deliberately NOT done and why.
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`, `build`.

Write down what you verified and how. "Tested" without saying how is useless to
the next person, including yourself three weeks from now.

---

## Operations docs

Guides for deploy, backup, pre-production security, and upstream sync are in
`paradise/`. The operations scripts are in `paradise/bin/`.

An upstream sync must be diffed against the **`v0.24.0` tag**, not
`upstream/main`. This repo was vendored from v0.24.0, so a diff against `main`
would report thousands of lines of version distance as "our changes".

---

## License

Contributions to this repository are covered by **GNU AGPL-3.0**
([LICENSE.txt](LICENSE.txt)). Don't remove the copyright headers in source
files, `LICENSE.txt`, or [NOTICE.md](NOTICE.md). See NOTICE for why removing
the product brand is different from removing legal attribution.
