# Upgrade, syncing with upstream Plane

Run:

```bash
./paradise/bin/upstream-sync.sh check     # what's new since the baseline
./paradise/bin/upstream-sync.sh apply     # apply it
./paradise/bin/upstream-sync.sh verify    # are our customizations still intact?
```

The baseline, the list of commits that were deliberately rejected, and the list
of files that must survive are in [`upstream-sync.json`](upstream-sync.json).
Read that first.

The rest of this page covers what the script can't do.

## Why `git merge` doesn't work

This repo is **vendored, not forked**: the files were copied in. There is no
common ancestor with `makeplane/plane`, so `git merge upstream/preview` refuses
to run, and if forced with `--allow-unrelated-histories`, the result is
conflicts in almost every file. What we use instead: a three-way patch per
commit.

An older version of this page said to run `git merge upstream/main`. That was
wrong.

## Sync to a release tag, not to `preview`

`preview` is their working branch and contains half-finished work. `v*` tags have
passed their QA. Syncing to `preview` means becoming someone else's beta tester,
on a server used by 79 people.

## Our customizations are NOT isolated in `paradise/`

That assumption held while we were vendoring. It no longer does. What is spread
through the upstream code:

| Where                                                           | What                                                                                                                                  |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web/ce/` (246 files)                                      | Extension layer: Time Tracking, Custom Properties, sidebar fixes. Fills the stubs upstream provides through the `@/plane-web/*` alias |
| `apps/api/plane/db/superadmin.py`                               | Hidden Super Admin                                                                                                                    |
| `apps/api/plane/utils/trash.py` + `app/views/paradise_trash.py` | Trash bin & TPA                                                                                                                       |
| `apps/api/plane/license/api/views/`                             | Audit log, recovery, member management (God Mode)                                                                                     |
| `apps/api/plane/app/views/asset/v2.py`                          | Wiki attachment gate. **Upstream periodically tries to drop the `import Page` it relies on**                                          |
| `packages/i18n/src/locales/`                                    | Debranding, ~1,700 lines across 19 locales                                                                                            |
| `apps/web/core/components/instance/edition-badge.tsx`           | Upgrade-prompt modal removed (KEP-14). **Upstream periodically puts it back**                                                         |
| `apps/api/plane/authentication/utils/login.py`                  | One `LoginActivity.catat()` call after `session.save()`                                                                               |
| `apps/api/plane/authentication/views/{app,space}/signout.py`    | One `LoginActivity.catat()` call **before** `logout()`                                                                                |
| `apps/api/plane/settings/common.py`                             | `LastActiveMiddleware` in `MIDDLEWARE` + `login_activity_retention` in `CELERY_IMPORTS`                                               |
| `apps/api/plane/celery.py`                                      | The `bersihkan-login-activity` schedule (17:00 UTC = 00:00 WIB)                                                                       |
| `apps/admin/app/routes.ts` + `hooks/use-sidebar-menu/`          | God Mode routes & menu: Audit log, TPA, Members, Activity                                                                             |

### Activity monitoring traps (2026-08-07)

Each of the four hook points above is only one or two lines, and that is exactly
the danger. A patch that fails there **raises no error at all**. It just quietly
turns the dashboard numbers into zero. After every sync, check:

- `LoginActivity.catat()` is still called on the login path **and** all three
  logouts. Lost on logout alone means sessions hang forever and durations are
  never computed.
- `session_key` is read **after** `request.session.save()`. Django regenerates
  the key on login, and reading it earlier pairs the logout with the wrong login.
- `LastActiveMiddleware` is still **after** `AuthenticationMiddleware`. If the
  order changes, `request.user` doesn't exist yet and the middleware fails
  silently.
- The retention task is registered on the **worker**, not just beat:
  `docker compose exec worker celery -A plane inspect registered | grep login_activity`.
  Beat alone means the task is sent, the worker answers "unregistered", and the
  message is dropped.

The rest are our own files (`db/models/login_activity.py`,
`middleware/last_active.py`, `bgtasks/login_activity_retention.py`,
`license/api/views/activity.py`, `apps/admin/.../activity/`) and will never
conflict with upstream.

## When a patch fails

The script reports failures one by one and doesn't abort the rest. Handle them by
hand, using these rules:

- The conflicting lines are **our customization**: keep ours.
- The conflicting lines are **their security fix**: take theirs, then reapply our
  customization on top.

Don't pick a side blindly. Two asset security patches (July 2026) both wanted to
drop `import Page`. Taken raw, the Wiki gate breaks without a single error.

## What must be rejected permanently

`8ef78bf0c1` "store and components consolidation to core" deletes the whole of
`apps/web/ce/` (249 files down to zero). Three of our features would lose their
interface while their backend keeps running, and their callers disappear too, so
**nothing fails loudly**. Moving to the `core/` structure is a port. Do it
separately, not bundled with a security patch.

## After a sync

1. `./paradise/bin/upstream-sync.sh verify`, must be green before merging to `main`.
2. Check for new migrations: `git show <commit> --stat | grep migrations/`. If
   there are any, **dump the DB first** (`paradise/bin/backup-db.sh`) before
   merging.
3. `paradise/bin/healthcheck.sh`.
4. Repeat [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md) if upstream added new env.

> The `api`, `worker`, and `beat-worker` containers bind-mount `apps/api` to
> `/code`. **Whatever branch is checked out is what the backend runs.** While the
> sync result is still sitting on its own branch, `git checkout main` silently
> removes all of its security patches.
