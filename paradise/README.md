# Paradise Task Tracker

An internal office deployment based on [Plane CE](https://github.com/makeplane/plane).
A project and issue management tool for the team (~100 members across divisions).

> This is an operational fork, not a rewrite. The application code is the work of
> the Plane team (AGPL-3.0). See [`../NOTICE.md`](../NOTICE.md).

## Two phases

| Phase               | Goal                                              | How                                                            |
| ------------------- | ------------------------------------------------- | -------------------------------------------------------------- |
| **1, Dev (now)**    | Tinker with the source and fit it to office needs | Build from source via `docker-compose-local.yml`               |
| **2, Prod (later)** | Serve ~100 users, update via CI/CD                | Build our own images → registry → deploy compose on the server |

## Quick start (Dev)

```bash
cp paradise/.env.example .env      # then fill in the values
paradise/bin/dev.sh up             # Linux/macOS
paradise\bin\dev.ps1 up            # Windows PowerShell
```

Default web: http://localhost (Caddy proxy). God Mode admin: `/god-mode`.

## Document map

- [`.env.example`](.env.example), every required variable + notes.
- [`DEPLOYMENT.md`](DEPLOYMENT.md), production deploy on the office server.
- [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md), **required** before prod.
- [`UPGRADE.md`](UPGRADE.md), how to pull updates from upstream Plane.
- [`GITHUB-RULES.md`](GITHUB-RULES.md), GitHub repo rules: PRs required, reviews
  required, and how to set them up.
- [`../CODEBASE_INVENTORY.md`](../CODEBASE_INVENTORY.md), architecture audit.

## Services (compose)

`web` · `space` · `admin` · `live` (collab) · `api` (Django) · `worker`/`beat`
(Celery) · `proxy` (Caddy) · Postgres · Redis · RabbitMQ · MinIO.

## Interface text (i18n)

All user-facing text in `apps/web` goes through `useTranslation()` from
`@plane/i18n`, not Indonesian strings written directly in components.

- Custom Paradise text lives in the `paradise` namespace
  (`packages/i18n/src/locales/<language>/paradise.json`). Keys are grouped per
  feature with a `_ui` suffix (`wiki_ui`, `chat_ui`, `cross_division_ui`,
  `notification_ui`, and so on). Don't give a top-level key the same name as a
  namespace file (`paradise`, `wiki`, ...), because `sync:check` rejects it.
- All 19 locales must have the same keys. `id` holds Indonesian text, `en`
  English, and the rest temporarily copy `en` until a translation exists.
- Common buttons (Save, Cancel, Delete, Close, Search) use the `common` keys
  (`t("save")`, `t("cancel")`). Don't rewrite them.
- Pure modules tested through `*.check.ts` (`galat-media`, `baris`, `teks`)
  don't call hooks. They receive `t` as an argument, and the `*.check.ts` files
  borrow the `id/paradise.json` dictionary. Run them from `packages/i18n`.
- God Mode (`apps/admin`) doesn't use `@plane/i18n` on purpose. It has its own
  dictionary in `apps/admin/app/i18n/godmode.tsx`.

Checks: `pnpm --filter @plane/i18n sync:check`, then `pnpm --filter @plane/i18n generate:types`.
