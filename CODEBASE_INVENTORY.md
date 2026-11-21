# CODEBASE INVENTORY, Plane

> Read-only audit by a staff-level architect. Every claim is traced to `path:line`.
> The repo is cloned locally as `Pradise_Plane`; upstream = `github.com/makeplane/plane`.
> **Scope of this pass:** thorough breadth-first (PHASE 0–6 + security + operations).
> Per-module depth (quoting every function) is not finished for all ~4,100 files. See
> the **MODULE INDEX** section for per-module status and **"What was not examined"** at the end.

---

## EXECUTIVE SUMMARY

- **What it is:** Plane, an open-source project management tool (alternative to Jira/Linear). Manages issues, cycles (sprints), modules, pages (docs), roadmaps.
- **Stack:** **pnpm + Turborepo** monorepo. TS/React frontend (React Router 7 SPA + Vite), **Django 5.2 + DRF** backend (Python 3.12), realtime collaboration in **Node/TypeScript (Hocuspocus + Yjs)**, **Caddy** proxy.
- **Scale:** ~2,129 `.tsx` + ~1,355 `.ts` + **629 `.py`**. 6 apps (`apps/*`) + 15 internal packages (`packages/*`).
- **Data plane:** PostgreSQL (primary + optional read replica), Redis (cache/celery result/ws), RabbitMQ (celery broker), S3/MinIO (assets), Celery (worker + beat).
- **License:** AGPL-3.0. Node version `1.3.1`, API version `0.24.0`.
- **3 standout points:**
  1. The backend shows strong security awareness: webhook SSRF mitigation (IP/host/domain allowlist), a guard against an insecure `SECRET_KEY`, a TOCTOU fix in sign-up (latest commit). Not ordinary boilerplate.
  2. A tidy **layered + domain-split** architecture: `db/` (models) → `app/` (internal views/serializers) → `api/` (public REST v1 with API key) → `space/` (public deploy board) → `authentication/` (multi-provider OAuth + magic link).
  3. A heavyweight collaborative editor: **Tiptap/ProseMirror + Yjs + Hocuspocus** in `apps/live` + `packages/editor`, with server-side PDF export.
- **Main risks (initial, need a deep dive):** the API surface is very large (object-level permissions/IDOR need auditing per endpoint), `ALLOWED_HOSTS` defaults to `*`, and many required env vars have no central startup validation.

---

## MODULE INDEX (master checklist)

Status: ✅ deep-read · 🟡 skimmed (structure + key files) · ⬜ not opened yet

| Module                | Path                                                                 | Language | Status | Notes                                 |
| --------------------- | -------------------------------------------------------------------- | -------- | ------ | ------------------------------------- |
| Root/workspace config | `package.json`, `turbo.json`, `pnpm-workspace.yaml`                  | ,        | ✅     | Turborepo tasks, catalog deps         |
| API settings          | `apps/api/plane/settings/*`                                          | Py       | ✅     | env vars, numeric config              |
| API routing           | `apps/api/plane/urls.py` + `app/urls/*`                              | Py       | 🟡     | list of route files, not per endpoint |
| API models            | `apps/api/plane/db/models/*` (178 files)                             | Py       | 🟡     | list of models, not every field       |
| API views (internal)  | `apps/api/plane/app/views/*` (112 files)                             | Py       | 🟡     | list of domains, not every handler    |
| API v1 (public)       | `apps/api/plane/api/*` (49 files)                                    | Py       | 🟡     | REST + API key                        |
| Auth                  | `apps/api/plane/authentication/*`                                    | Py       | 🟡     | OAuth providers + credentials         |
| Background tasks      | `apps/api/plane/bgtasks/*` (34 files)                                | Py       | ✅     | task list + cron schedule             |
| Celery config         | `apps/api/plane/celery.py`                                           | Py       | ✅     | full beat_schedule                    |
| License/instance      | `apps/api/plane/license/*`                                           | Py       | ⬜     | telemetry, instance admin             |
| Space (public)        | `apps/api/plane/space/*`                                             | Py       | ⬜     | public deploy board                   |
| Web app               | `apps/web/*` (2,039 files)                                           | TSX      | 🟡     | stores/services/components identified |
| Admin app             | `apps/admin/*` (100 files)                                           | TSX      | 🟡     | god-mode instance admin               |
| Space app             | `apps/space/*` (166 files)                                           | TSX      | 🟡     | published views frontend              |
| Live (realtime)       | `apps/live/src/*`                                                    | TS       | 🟡     | hocuspocus + yjs                      |
| Proxy                 | `apps/proxy/*`                                                       | Caddy    | ✅     | 3 config files                        |
| Editor pkg            | `packages/editor` (226 files)                                        | TS       | ⬜     | tiptap extensions                     |
| Propel (UI kit?)      | `packages/propel` (390 files)                                        | TS       | ⬜     | largest package, not opened           |
| UI pkg                | `packages/ui` (128 files)                                            | TS       | ⬜     | base components                       |
| Types pkg             | `packages/types` (120 files)                                         | TS       | ⬜     | shared types                          |
| Services pkg          | `packages/services` (56 files)                                       | TS       | ⬜     | shared API client                     |
| Other packages        | `constants,utils,hooks,i18n,logger,decorators,shared-state,codemods` | TS       | ⬜     | ,                                     |
| Infra                 | `docker-compose*.yml`, `deployments/*`                               | YAML     | ✅     | services identified                   |

---

## PHASE 0, Stack and project type detection

**Languages and share (excluding node_modules/build):**

| Language       | Files                       | Role                                  |
| -------------- | --------------------------- | ------------------------------------- |
| TypeScript/TSX | ~3,484 (2129 tsx + 1355 ts) | All frontend + live server + packages |
| Python         | 629                         | Backend API (Django)                  |
| JSON           | 594                         | Config, i18n locales, tsconfig        |
| CSS            | 19                          | Styling (Tailwind v4)                 |
| Shell          | 14                          | Build/entrypoint scripts              |

**Detected manifests:**

| File                                    | Location                            | Ecosystem                                                                 |
| --------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------- |
| `package.json`                          | root + each `apps/*` & `packages/*` | pnpm workspace (Turborepo)                                                |
| `pnpm-workspace.yaml`                   | root                                | Workspace: `apps/*`, `packages/*`, **except** `apps/api` and `apps/proxy` |
| `pyproject.toml` + `requirements/*.txt` | `apps/api`                          | Python/Django (pip)                                                       |
| `turbo.json`                            | root                                | Turborepo task graph                                                      |

**Project type:** multi-service monorepo:

- **Backend/API**, `apps/api` (Django + DRF + Celery), Python. Not part of the pnpm workspace (has its own build via Docker).
- **Frontend/SPA**, `apps/web` (main), `apps/admin` (instance admin), `apps/space` (public published views). All React 18 + React Router 7 + Vite.
- **Realtime service**, `apps/live` (Node/Express + Hocuspocus + Yjs) for document collaboration.
- **Reverse proxy**, `apps/proxy` (Caddy).
- **Internal libraries**, 15 packages in `packages/*` (editor, ui, types, services, i18n, etc).

**Core frameworks + versions:**

| Area          | Framework               | Version                              |
| ------------- | ----------------------- | ------------------------------------ |
| Backend       | Django                  | 5.2.17                               |
| Backend API   | Django REST Framework   | 3.18.3                               |
| Task queue    | Celery                  | 5.5.3 (+ django-celery-beat/results) |
| DB driver     | psycopg (3)             | 3.3.4                                |
| Frontend      | React                   | 18.3.1                               |
| Routing/SSR   | React Router            | 7.15.x (framework mode)              |
| Bundler       | Vite                    | 8.0.16                               |
| State         | MobX + mobx-react       | 6.12.0 / 9.1.1                       |
| Data fetching | SWR                     | 2.2.4                                |
| Editor        | Tiptap/ProseMirror      | ^2.22.3                              |
| Realtime      | Yjs + Hocuspocus        | ^13.6.20 / 2.15.2                    |
| Styling       | Tailwind CSS            | 4.1.17                               |
| i18n          | i18next + react-i18next | 25.x / 16.x                          |
| Lint/format   | oxlint + oxfmt          | 1.51.0 / 0.35.0                      |
| Node          | engines                 | `>=22.18.0`, pnpm 11.3.0             |

**Monorepo tooling:** Turborepo 2.11.10. Task graph in `turbo.json`: `build`, `dev` (concurrency 18), `check` (format+lint+types), `fix`. Central dependency catalog in `pnpm-workspace.yaml` (`catalog:`) + many `overrides` (security pinning: `axios`, `ws`, `undici`, `form-data`, etc).

---

## PHASE 1, FULL INVENTORY ⭐

### Top-level folder structure

```
Pradise_Plane/
├── apps/
│   ├── api/      # Django backend (Python), NOT part of the pnpm workspace
│   ├── web/      # Main SPA (React Router 7 + Vite), largest app
│   ├── admin/    # Instance admin "god-mode" (React)
│   ├── space/    # Public published views / deploy boards (React)
│   ├── live/     # Realtime collab server (Node/Express + Hocuspocus + Yjs)
│   └── proxy/    # Caddy reverse proxy
├── packages/     # 15 shared internal libraries (editor, ui, types, services, i18n, …)
├── deployments/  # aio, cli, kubernetes, swarm
├── docs/         # linting.md (minimal)
├── docker-compose*.yml  # ce (community) + local + test
├── setup.sh
├── turbo.json / pnpm-workspace.yaml / package.json
```

### Entry points

| App             | Entry                                                    | Evidence                      |
| --------------- | -------------------------------------------------------- | ----------------------------- |
| API (WSGI/ASGI) | `plane/wsgi.py`, `plane/asgi.py`                         | `apps/api/plane/`             |
| API mgmt        | `manage.py`                                              | `apps/api/manage.py`          |
| Celery          | `plane/celery.py` (app + beat_schedule)                  | `apps/api/plane/celery.py:44` |
| Web/Admin/Space | React Router `react-router.config.ts` + `vite.config.ts` | each app                      |
| Live            | `src/server.ts` → `src/start.ts`                         | `apps/live/src/`              |
| Proxy           | `Caddyfile.ce` / `Caddyfile.aio.ce`                      | `apps/proxy/`                 |

### Direct dependencies, backend (`apps/api/requirements/base.txt`)

| Package                               | Version                 | Purpose                                                   |
| ------------------------------------- | ----------------------- | --------------------------------------------------------- |
| Django                                | 5.2.17                  | Web framework                                             |
| djangorestframework                   | 3.18.3                  | REST API                                                  |
| psycopg / psycopg-binary              | 3.3.4                   | PostgreSQL driver                                         |
| dj-database-url                       | 3.0.1                   | Parses `DATABASE_URL`                                     |
| redis / django-redis                  | 5.0.4 / 7.0.0           | Cache, session, celery result                             |
| celery / django_celery_beat / results | 5.5.3 / 2.9.0 / 2.6.0   | Task queue + scheduler                                    |
| django-cors-headers                   | 4.9.0                   | CORS                                                      |
| whitenoise                            | 6.12.0                  | Static file serving                                       |
| django-storages / boto3               | 1.14.6 / 1.34.96        | S3/MinIO assets                                           |
| channels                              | 4.3.2                   | WebSocket/ASGI                                            |
| uvicorn                               | 0.29.0                  | ASGI server                                               |
| openai                                | 1.63.2                  | AI features                                               |
| slack-sdk                             | 3.27.1                  | Slack integration                                         |
| scout-apm                             | 3.5.3                   | APM monitoring                                            |
| posthog                               | 3.5.0                   | Analytics/telemetry                                       |
| cryptography / PyJWT                  | 48.0.1 / 2.13.0         | Crypto, JWT                                               |
| nh3 / lxml / beautifulsoup4           | 0.2.18 / 6.1.0 / 4.12.3 | HTML sanitizing and parsing                               |
| zxcvbn                                | 4.4.28                  | Password strength validator                               |
| drf-spectacular                       | 0.29.0                  | OpenAPI schema                                            |
| openpyxl                              | 3.1.2                   | XLSX export                                               |
| opentelemetry-\*                      | 1.28.1                  | Tracing                                                   |
| requests                              | 2.33.0                  | Webhook delivery (pinned for the SSRF IP-pinning adapter) |
| urllib3                               | >=2.7.0                 | Pinned (CVE-2026-44431/44432)                             |

> Split into: `requirements/base.txt` (core) + `local.txt` (dev, e.g. debug-toolbar) + `production.txt` + `test.txt` (pytest).

### Direct dependencies, frontend (catalog `pnpm-workspace.yaml`)

Highlights (not exhaustive, the catalog has ~180 entries):

| Package                                         | Version                | Purpose                  |
| ----------------------------------------------- | ---------------------- | ------------------------ |
| react / react-dom                               | 18.3.1                 | UI                       |
| react-router                                    | 7.15.x                 | Routing (framework mode) |
| mobx / mobx-react                               | 6.12 / 9.1.1           | State management         |
| swr                                             | 2.2.4                  | Data fetching            |
| axios                                           | 1.16.0                 | HTTP client              |
| @tiptap/_ + prosemirror-_                       | ^2.22.3                | Rich editor              |
| yjs / y-prosemirror / y-protocols / y-indexeddb | ^13.6.20               | CRDT collab              |
| @hocuspocus/\*                                  | 2.15.2                 | Collab server/provider   |
| tailwindcss + @tailwindcss/postcss              | 4.1.17                 | Styling                  |
| framer-motion                                   | ^12.23                 | Animation                |
| recharts                                        | ^2.15.1                | Charts/analytics         |
| @tanstack/react-table + react-virtual           | ^8.21 / ^3.13          | Tables + virtualization  |
| @atlaskit/pragmatic-drag-and-drop\*             | 1.x                    | Board drag and drop      |
| i18next + react-i18next + i18next-icu           | 25.x/16.x/2.4          | i18n                     |
| zod                                             | ^3.25                  | Schema validation        |
| react-hook-form                                 | 7.51.5                 | Forms                    |
| @react-pdf/renderer + pdf-parse                 | ^4.3 / ^2.4.5          | PDF export/parse         |
| express + express-ws + helmet + compression     | 4.22 / 5.0 / 7.1 / 1.8 | Live server              |
| ioredis                                         | 5.7.0                  | Redis (live)             |
| winston + express-winston                       | ^3.17 / ^4.2           | Logging (live)           |

### Scripts/commands

**Root (`package.json`):** `build`, `dev` (turbo, concurrency 18), `start`, `clean`, `fix`/`fix:format`/`fix:lint`, `check`/`check:lint`/`check:format`/`check:types`, `prepare` (husky), `doctor` (react-doctor).
**lint-staged:** `oxfmt` + `oxlint --fix --deny-warnings` on JS/TS/JSON/CSS/MD files.
**API:** `apps/api/manage.py` (Django), `run_tests.py` / `run_tests.sh` / `pytest.ini`, `bin/` (container entrypoint).

### Key config files

| File                                                                                    | Function                                                |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `turbo.json`                                                                            | Task graph + `globalEnv` (list of Vite/Sentry env vars) |
| `pnpm-workspace.yaml`                                                                   | Workspace + catalog + overrides + allowBuilds           |
| `apps/api/plane/settings/{common,production,local,test,redis,storage,openapi}.py`       | Layered Django configuration                            |
| `apps/*/vite.config.ts`, `react-router.config.ts`, `postcss.config.js`, `tsconfig.json` | Per-app frontend config                                 |
| `.oxlintrc.json`, `.oxfmtrc.json`, `.npmrc`                                             | Lint/format/registry (turbo globalDependencies)         |
| `apps/proxy/Caddyfile.ce`, `Caddyfile.aio.ce`                                           | Proxy routing                                           |
| `docker-compose.yml` / `-local.yml` / `-test.yml`                                       | Service orchestration                                   |

### Environment variables (backend, read in `plane/settings/`)

Required/main (⭐ = security/operations critical):

| Env                                                                                      | Read in                         | Default          | Notes                                                      |
| ---------------------------------------------------------------------------------------- | ------------------------------- | ---------------- | ---------------------------------------------------------- |
| ⭐ `SECRET_KEY`                                                                          | `common.py:34`                  | random if empty  | Rejects known-insecure placeholder values (`common.py:38`) |
| `DEBUG`                                                                                  | `common.py:59`                  | `0`              | ,                                                          |
| `ALLOWED_HOSTS`                                                                          | `common.py:99`                  | `*` ⚠️           | Default too loose for prod                                 |
| `DATABASE_URL` / `POSTGRES_*`                                                            | settings                        | ,                | Primary                                                    |
| `ENABLE_READ_REPLICA` + `DATABASE_READ_REPLICA_URL`/`POSTGRES_READ_REPLICA_*`            | settings                        | off              | Read-replica routing middleware (`common.py:119`)          |
| `REDIS_URL`                                                                              | redis.py                        | ,                | Cache/session/result                                       |
| `AMQP_URL` / `RABBITMQ_*`                                                                | `common.py:209`                 | ,                | Celery broker                                              |
| `AWS_*` / `USE_MINIO` / `MINIO_ENDPOINT_*`                                               | storage.py                      | ,                | S3/MinIO assets                                            |
| ⭐ `WEBHOOK_ALLOWED_IPS` / `_HOSTS` / `WEBHOOK_DISALLOWED_DOMAINS`                       | `common.py:64–96`               | empty            | Webhook SSRF controls                                      |
| `FILE_SIZE_LIMIT`                                                                        | `common.py:234`                 | `5242880` (5 MB) | also `DATA_UPLOAD_MAX_MEMORY_SIZE`                         |
| `API_KEY_RATE_LIMIT`                                                                     | `common.py:35` (REST_FRAMEWORK) | `60/minute`      | API-key throttle                                           |
| `SIGNED_URL_EXPIRATION`                                                                  | storage                         | ,                | Presigned S3 TTL                                           |
| `SESSION_COOKIE_AGE` / `_NAME` / `ADMIN_SESSION_COOKIE_AGE` / `COOKIE_DOMAIN`            | settings                        | ,                | Session                                                    |
| `PASSWORD_RESET_TIMEOUT`                                                                 | `common.py` (hardcoded)         | `3600` s         | ,                                                          |
| `HARD_DELETE_AFTER_DAYS`                                                                 | settings                        | ,                | Soft→hard delete window                                    |
| `CORS_ALLOWED_ORIGINS`                                                                   | settings                        | ,                | ,                                                          |
| `OPENAI`/`GITHUB_ACCESS_TOKEN`/`UNSPLASH_ACCESS_KEY`/`POSTHOG_*`/`SCOUT_*`/`ANALYTICS_*` | settings                        | ,                | External integrations                                      |
| `*_BASE_URL`/`*_BASE_PATH` (APP/ADMIN/SPACE/LIVE/WEB)                                    | settings                        | ,                | URLs between services                                      |

Frontend (Vite, from `turbo.json:globalEnv`): `VITE_API_BASE_URL/PATH`, `VITE_ADMIN_*`, `VITE_LIVE_*`, `VITE_SPACE_*`, `VITE_WEB_*`, `VITE_WEBSITE_URL`, `VITE_SUPPORT_EMAIL`, Sentry (`VITE_SENTRY_*`), session recorder (`VITE_SESSION_RECORDER_KEY`, `VITE_ENABLE_SESSION_RECORDER`), `APP_VERSION`.

### External integrations

| Category             | Technology                                                             |
| -------------------- | ---------------------------------------------------------------------- |
| Database             | PostgreSQL (primary + optional read replica)                           |
| Cache/session/result | Redis (django-redis + ioredis in live)                                 |
| Message broker       | RabbitMQ (Celery)                                                      |
| Object storage       | S3 / MinIO (django-storages + boto3)                                   |
| Auth OAuth           | Google, GitHub, GitLab, Gitea (`plane/authentication/provider/oauth/`) |
| AI                   | OpenAI                                                                 |
| Chat                 | Slack (slack-sdk)                                                      |
| Analytics/telemetry  | PostHog + instance metrics telemetry                                   |
| APM/tracing          | Scout APM + OpenTelemetry                                              |
| Media                | Unsplash (cover image)                                                 |
| Error/session        | Sentry (frontend)                                                      |

### Background jobs / cron (`plane/celery.py:44`)

| Schedule (UTC)       | Task                                                       |
| -------------------- | ---------------------------------------------------------- |
| every 5 minutes      | `email_notification_task.stack_email_notification`         |
| interval (telemetry) | `license.bgtasks.telemetry_metrics.push_instance_metrics`  |
| 00:00                | `deletion_task.hard_delete`                                |
| 01:00                | `issue_automation_task.archive_and_close_old_issues`       |
| 01:30 & 03:45        | `exporter_expired_task.delete_old_s3_link` (registered 2×) |
| 02:00                | `file_asset_task.delete_unuploaded_file_asset`             |
| 02:30                | `cleanup_task.delete_api_logs`                             |
| 02:45                | `cleanup_task.delete_email_notification_logs`              |
| 03:00                | `cleanup_task.delete_page_versions`                        |
| 03:15                | `cleanup_task.delete_issue_description_versions`           |
| 03:30                | `cleanup_task.delete_webhook_logs`                         |

> ⚠️ `exporter_expired_task.delete_old_s3_link` is registered twice (01:30 & 03:45) under different keys (`..._exporter_history` vs `..._exporter-history`), probably redundant. `beat_scheduler = DatabaseScheduler` (`celery.py:118`).

Other tasks (event-triggered, not cron) in `plane/bgtasks/`: webhook delivery, issue activities, notifications, exports (xlsx/csv), magic-link/forgot-password email, workspace/project invitations, page & issue version sync, storage metadata, event tracking, dummy data seeding.

### Hidden code

- `TODO/FIXME/HACK/XXX` in the Python backend: **13 markers** (`grep` over `apps/api/plane/**/*.py`). Not enumerated one by one, TODO deep dive.
- Frontend not yet scanned for these markers (TODO).

### Actual configuration values (numeric)

| Value                                                        | Source           |
| ------------------------------------------------------------ | ---------------- |
| `FILE_SIZE_LIMIT` = 5 MB (5242880)                           | `common.py:234`  |
| `API_KEY_RATE_LIMIT` = 60/minute                             | `common.py:35`   |
| `PASSWORD_RESET_TIMEOUT` = 3600 s                            | `common.py:155`  |
| `dev` concurrency = 18                                       | `package.json`   |
| McCabe complexity max = 10, ruff line-length 120, max-args 8 | `pyproject.toml` |
| Node engine `>=22.18.0`                                      | `package.json`   |

---

## PHASE 2, Infrastructure and environment

**Runtime:** Python 3.12 (Django 5.2, uvicorn ASGI), Node >=22.18, pnpm 11.3.

**Containerization:** each app has two Dockerfiles (`Dockerfile.<app>` for prod + `Dockerfile.dev`). Orchestrated through `docker-compose.yml` (community edition). Services:

| Service                        | Role                                  |
| ------------------------------ | ------------------------------------- |
| `web`, `admin`, `space`        | Frontend SPA (Nginx serves the build) |
| `api`                          | Django (uvicorn/gunicorn)             |
| `worker`                       | Celery worker                         |
| `beat-worker`                  | Celery beat (scheduler)               |
| `migrator`                     | DB migration job (one-shot)           |
| `live`                         | Realtime collab (Node)                |
| `plane-db`                     | PostgreSQL                            |
| `plane-redis`                  | Redis                                 |
| `plane-mq`                     | RabbitMQ                              |
| `plane-minio`                  | MinIO (S3)                            |
| `proxy`                        | Caddy (HTTP entry)                    |
| `pgdata`,`redisdata`,`uploads` | Named volumes                         |

**Other deployments:** `deployments/{aio,cli,kubernetes,swarm}`, AIO (all-in-one image), Kubernetes manifests/Helm, Docker Swarm, CLI installer. Details not opened yet (TODO).

**CI/CD:** GitHub Actions, `.github/workflows/`: `build-branch.yml`, `check-version.yml`, `codeql.yml` (SAST), `copyright-check.yml`, `feature-deployment.yml`, `i18n-sync-check.yml`, `pull-request-build-lint-api.yml`, `pull-request-build-lint-web-apps.yml`, `react-doctor.yml`. So: separate build/lint for API vs web apps, a CodeQL security scan, and version + copyright + i18n sync checks on PRs. The contents of each workflow have not been read in detail (TODO).

**Build/run (dev):** `pnpm install` → `pnpm dev` (turbo, all frontend apps + live). API: `apps/api` via `manage.py runserver` or uvicorn; worker/beat via celery. **Prod:** `docker compose up` (community) or a k8s/swarm deployment. The exact steps have not been extracted from the Dockerfiles/entrypoints (TODO).

---

## PHASE 3, Architecture and data flow

**Pattern:** modular monolith in the backend (Django apps per domain) + multi-app SPA in the frontend + a separate realtime service. Not full microservices: one DB, one Django codebase, split into worker/beat/web processes.

**Backend layering (evidenced by the structure):**

```
plane/db/        -> Models + migrations (source of truth for the schema)
plane/app/       -> "Internal" views + serializers (used by web/admin) at /api/
plane/api/       -> Public REST v1 (/api/v1/) with API-key auth
plane/space/     -> Public deploy board endpoints (/api/public/)
plane/license/   -> Instance/license admin (/api/instances/)
plane/authentication/ -> Login/OAuth/magic (/auth/)
plane/bgtasks/   -> Celery tasks (async)
plane/middleware/-> Read-replica routing, etc.
plane/utils/     -> Cross-domain helpers (69 files)
```

Top-level routing: `plane/urls.py` maps each prefix to an app (see PHASE 4).

**Data flow (outline):**

```
Browser (web/admin/space SPA, MobX store + SWR)
  │  HTTP/JSON  ─────────────────► Caddy proxy
  │  WebSocket (collab) ─────────►
  ▼
Caddy ──► Django API (/api, /api/v1, /api/public, /auth)
      └─► Live service (Node/Hocuspocus) ──► Redis (pubsub) + Postgres (persist doc)
Django ──► Postgres (primary / read-replica)
       ├─► Redis (cache/session)
       ├─► RabbitMQ ──► Celery worker ──► Postgres/S3/email/webhook
       └─► S3/MinIO (asset presigned URL)
Celery beat ──► schedules periodic tasks
```

Frontend state: **MobX** (root store `apps/web/core/store/root.store.ts` → per-domain sub-stores: issue, cycle, module, project, workspace, page, notification, etc) + **SWR** for fetching. The service layer `apps/web/core/services/*.service.ts` wraps axios calls to the endpoints.

---

## PHASE 4, Interface surface

**Top-level Django routing (`plane/urls.py`):**

| Prefix                                   | Include                     | Purpose                               |
| ---------------------------------------- | --------------------------- | ------------------------------------- |
| `api/`                                   | `plane.app.urls`            | Internal API (web/admin)              |
| `api/public/`                            | `plane.space.urls`          | Public deploy board                   |
| `api/instances/`                         | `plane.license.urls`        | Instance/license admin                |
| `api/v1/`                                | `plane.api.urls`            | **Public REST v1 (API key)**          |
| `auth/`                                  | `plane.authentication.urls` | Login/OAuth/magic                     |
| `` (root)                                | `plane.web.urls`            | Web/health                            |
| `api/schema/`, `/swagger-ui/`, `/redoc/` | drf-spectacular             | OpenAPI (if `ENABLE_DRF_SPECTACULAR`) |

**Internal route domains (`plane/app/urls/`):** `analytic, api, asset, cycle, estimate, exporter, external, intake, issue, module, notification, page, project, search, state, timezone, user, views, webhook, workspace`.

**Public REST v1 (`plane/api/urls/`):** `asset, cycle, estimate, intake, invite, label, member, module, project, schema, state, sticky, user, work_item`, auth via API key plus throttle `API_KEY_RATE_LIMIT`.

**Domain views (`plane/app/views/`, 112 files):** one directory per domain: `analytic, asset, cycle, estimate, exporter, external, intake, issue, module, notification, page, project, search, state, timezone, user, view, webhook, workspace`, plus `base.py` (base viewset) and `error_404.py`.

> Enumerating endpoints, methods and permissions per URLconf is a **TODO deep-dive** (it needs reading each `urls/*.py` and viewset). This is the largest surface and the most relevant one for an IDOR/permission audit.

**Frontend routes:** React Router 7 (file-based via `react-router.config.ts`) in web/admin/space. Guards and layouts live in `apps/web/core/layouts/`. Not enumerated yet (TODO).

**Live service (`apps/live/src/controllers/`):** `collaboration.controller`, `document.controller`, `health.controller`, `pdf-export.controller` (plus the hocuspocus WS server `hocuspocus.ts`).

---

## PHASE 5, Data layer

**Engine:** PostgreSQL. Django ORM. Optional read replica via `ReadReplicaRoutingMiddleware` (`plane/middleware/db_routing.py`, enabled when `ENABLE_READ_REPLICA` is set).

**Models (`plane/db/models/`, 178 py files, file list):**
`analytic, api, asset, base, cycle, deploy_board, description, device, draft, estimate, exporter, favorite, importer, intake, integration/, issue, issue_type, label, module, notification, page, project, recent_visit, session, social_connection, state, sticky, user, view, webhook, workspace`.

Core domain visible: **workspace → project → (issue, cycle, module, state, label, page, view, estimate, intake)**, plus asset, notification, webhook, favorite, sticky, draft, deploy_board (public share), api (token), integration.

**Schema source of truth:** a single one, the Django models in `plane/db/models/*` plus Django migrations. Drift risk is low in the backend (one ORM). The frontend types (`packages/types`, 120 files) are a separate representation, so TS and Python can drift (need to check whether they are generated from OpenAPI or written by hand, TODO).

**Migrations:** Django migrations, **121 files** in `plane/db/migrations/`. The one-shot `migrator` job applies them in compose.

**Referential integrity:** Django FKs are on (default). `on_delete` details per model are a TODO. `base.py` probably provides soft delete and audit fields (created_by/updated_by via django-crum), which needs confirming by reading `plane/db/models/base.py`.

---

## PHASE 6, Business logic / core domain

**What the app does (core features detected from models, views, stores and components):**

| Feature                                                    | Evidence                                                         |
| ---------------------------------------------------------- | ---------------------------------------------------------------- |
| Workspace and member management                            | model `workspace`, view `workspace/`, store `workspace`          |
| Project management                                         | model/view/store `project`                                       |
| Issues / work items (CRUD, sub-issue, relations, activity) | model `issue`, view `issue/`, store `issue/`, api v1 `work_item` |
| Cycles (sprints) + archive                                 | model `cycle`, service `cycle_archive.service.ts`                |
| Modules + archive                                          | model `module`, service `module_archive.service.ts`              |
| States and workflow                                        | model/view `state`                                               |
| Labels                                                     | model/view `label`                                               |
| Estimates                                                  | model/view `estimate`                                            |
| Intake (inbox for issue triage)                            | model `intake`, view `intake/`, store `inbox`                    |
| Pages (collaborative docs)                                 | model `page`, live service, versions (`page_version_task`)       |
| Views (saved filters)                                      | model `view`, components `views/`                                |
| Notifications (in-app + email)                             | model `notification`, bgtask email every 5 min                   |
| Webhooks (outbound, SSRF-guarded)                          | model `webhook`, view `webhook/`, bgtask `webhook_task`          |
| Analytics/dashboard                                        | view `analytic/`, store `analytics`, recharts                    |
| API tokens (public REST)                                   | model `api`, api v1                                              |
| Public deploy board (share)                                | model `deploy_board`, `plane/space/`, `apps/space`               |
| Import/Export (xlsx/csv)                                   | model `importer`/`exporter`, bgtasks export                      |
| Stickies (notes)                                           | model/view `sticky`                                              |
| AI assist                                                  | service `ai.service.ts`, openai                                  |
| Favorites, recent visits                                   | model `favorite`, `recent_visit`                                 |
| Instance admin (god mode)                                  | `apps/admin`, `plane/license`                                    |

The main business logic lives in **serializers + viewsets** (`plane/app/views/*`, `plane/app/serializers`) and **bgtasks** (async). Validation is duplicated between TS and Python (frontend and backend), so a consistency audit is needed (TODO).

---

## PHASE 8, Security (initial findings)

🟢 **Positive (evidence of strong security awareness):**

- **SSRF webhook mitigation**, IP/CIDR allowlist (`common.py:64`), hostname (`common.py:79`), disallowed domain (`common.py:91`). `requests` is pinned for the TLS IP-pinning adapter (`base.txt`). Delivery goes through `bgtasks/webhook_task.py`.
- **SECRET_KEY guard**, rejects known-insecure or placeholder values with a critical log (`common.py:38-51`), and falls back to a random value when empty (GHSA-cmwv-pjmw-8483).
- **TOCTOU fix**, the latest commit `7fbf14a` closes a race in `InstanceAdminSignUp` (GHSA-p548-28jp-wr4p).
- **Password:** Django validator + zxcvbn; `PASSWORD_RESET_TIMEOUT=3600`.
- **HTML sanitizing:** nh3 + lxml + sanitize-html (frontend) for rich-text/page content.
- **Rate limiting:** DRF AnonRateThrottle + API-key throttle (`60/minute`).
- **Auth rate limit:** `plane/authentication/rate_limit.py`.
- Aggressive dependency **overrides** for CVEs (axios, ws, undici, form-data, urllib3, and others).

🟠 **HIGH / needs verification:**

- `ALLOWED_HOSTS` defaults to `*` (`common.py:99`), which is safe only if the proxy restricts Host. Check `production.py`.
- **Object-level authorization / IDOR**, large API surface (workspace/project scoping). Each viewset needs an audit to see whether queries are filtered per member. **This is risk area #1 and has not been audited per endpoint.**

🟡 **MEDIUM:**

- Hardcoded secrets: none found in settings (everything comes from env). The tracked `.env` files are only **templates** (`deployments/{aio,cli}/community/variables.env`) with empty or placeholder values, not real secrets (verified). A full scan of the frontend and test fixtures is a TODO.
- `DEBUG` comes from an env int; make sure prod compose sets it to `0`.

> **No real secrets leaked** in the files that were read; only env templates with placeholders. A full-repo automated scan (gitleaks style) has not been run, TODO.

---

## PHASE 9, Quality and operations

- **Backend tests:** pytest (`apps/api/pytest.ini`, `run_tests.py/sh`), 47 test files in `plane/tests/`. Rough coverage has not been measured.
- **Frontend tests:** vitest (`@vitest/coverage-v8` in the catalog); `apps/live/tests`, `vitest.config.ts`. Coverage has not been measured.
- **Lint/format:** oxlint + oxfmt (JS/TS) via lint-staged + husky pre-commit; ruff (Python, `pyproject.toml`). Type-check via `turbo check:types`.
- **Logging:** JSON logger (backend `python-json-logger`, celery `JsonFormatter` `celery.py`), winston (live).
- **Observability:** Scout APM + OpenTelemetry (backend), Sentry (frontend), PostHog analytics, health controller (live), telemetry metrics push (license).

---

## PHASE 10, Feature catalog (product)

All ✅, based on the presence of model + view + store + components (full functionality needs a runtime test):

✅ Workspaces · ✅ Projects · ✅ Issues/work items · ✅ Cycles · ✅ Modules · ✅ States/workflow · ✅ Labels · ✅ Estimates · ✅ Intake/inbox · ✅ Pages (collab docs) · ✅ Views/filters · ✅ Notifications (in-app+email) · ✅ Webhooks · ✅ Analytics/dashboard · ✅ Public deploy boards · ✅ Import/Export · ✅ Stickies · ✅ API tokens (REST v1) · ✅ AI assist · ✅ Instance admin · ✅ Multi-provider auth (Google/GitHub/GitLab/Gitea/email/magic).

The ⚠️/❌ status per feature needs a runtime test and has not been run (read-only audit).

---

## What was not examined (scope transparency)

Deep reads that have **not** been done (priorities for the next pass):

1. **Endpoint enumeration per URLconf** (`plane/*/urls/*.py`) + method + permission class → the most important item for the IDOR/authz audit. _(PHASE 4/8)_
2. **Fields per model** + `on_delete` + index + `base.py` (soft-delete/audit) → `plane/db/models/*`. _(PHASE 5)_
3. **`packages/propel` (390 files, the largest)** and **`packages/editor` (226)**, not opened at all.
4. **`packages/{ui,types,services,constants,utils}`**, not opened; check whether `types` is generated from OpenAPI (drift risk).
5. **`apps/live` internals** (hocuspocus extensions, redis pubsub, pdf-export), structure only.
6. **`plane/license` and `plane/space`**, not opened (telemetry, instance admin, public board logic).
7. **Frontend routes + guards** (react-router config for each app), not enumerated.
8. **CI/CD** (`.github/workflows`), existence not verified.
9. **Dockerfile/entrypoint (`bin/`) + deployments/{k8s,swarm,aio,cli}**, exact build/deploy steps.
10. **Full scans:** 13 backend TODO/FIXME not enumerated; frontend not scanned; full-repo secret scan not run.
11. **PHASE 6.5 (end-to-end feature traces down to the root)**, not written yet; needs 3 to 5 features (e.g. create issue, webhook delivery, auth/login, page collab) traced across layers with snippets.

> **Recommendation:** continue module by module following priorities #1 and #2 (authz + schema) because they carry the highest security risk, then PHASE 6.5 for critical features. Say which module to do first.

---

---

# PASS 2, DEEP-DIVE

## DEEP-DIVE #1, Authorization / IDOR (PHASE 4 + 8)

### Authz model: 2-layer RBAC

**Roles** (`plane/app/permissions/base.py:12`, mirrored in `db/models/project.py`):
`ADMIN = 20`, `MEMBER = 15`, `GUEST = 5`.

**Two parallel mechanisms** (both used in the codebase):

1. **Class-based `BasePermission`** (`plane/app/permissions/{project,workspace,page}.py`), used via `permission_classes` (31 of 60 view files). Checks `has_permission(request, view)`:
   - `WorkspaceMember`/`ProjectMember` filter `workspace__slug=view.workspace_slug`, `member=request.user`, `is_active=True`, `role__in=[...]`.
   - `SAFE_METHODS` (GET) → only checks membership; **object-level filtering is "left to the queryset"** (explicit comment at `project.py:19` "Handle the filtering logic in queryset").
   - Classes: `ProjectBasePermission`, `ProjectMemberPermission`, `ProjectEntityPermission`, `ProjectAdminPermission`, `ProjectLitePermission`; `WorkSpaceBasePermission`, `WorkspaceOwnerPermission`, `WorkSpaceAdminPermission`, `WorkspaceEntityPermission`.

2. **Decorator `@allow_permission(allowed_roles, level="PROJECT"|"WORKSPACE", creator=False, model=None)`** (`permissions/base.py:19`), used per method (38 of 60 view files). Checks membership + role on `kwargs["slug"]`/`kwargs["project_id"]`; the `creator=True` option lets the object's owner (`created_by=request.user`) through even without a sufficient role.

**Base viewset** (`plane/app/views/base.py:47`): default `permission_classes=[IsAuthenticated]`, `authentication_classes=[BaseSessionAuthentication]`, and the default `get_queryset()` is `self.model.objects.all()` (`base.py:60`).

### Critical IDOR points

> Because the default `BaseViewSet.get_queryset` returns **`.all()`**, object-level security **depends entirely on each view overriding `get_queryset` with a `workspace__slug` + `project_id` filter**. The correct pattern shows up consistently in `issue/base.py`:
>
> - `get_queryset` → `Issue.issue_objects.filter(project_id=self.kwargs["project_id"], workspace__slug=self.kwargs["slug"])` (`issue/base.py:206`).
> - each handler is decorated with `@allow_permission([...])` (`issue/base.py:84, 253, 392`).

**Coverage (quantitative):** 60 view files; **38** use `allow_permission`, **31** override `permission_classes` (many use both). Coverage is high, and "bare" views are rare.

### Findings

| Sev                 | Location                                                        | Finding                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 🟠 HIGH (PLAUSIBLE) | `plane/app/views/issue/comment.py:66`, `issue/sub_issue.py:205` | `Issue.objects.get(pk=issue_id)` is fetched **without** verifying `issue.project_id == project_id`/`workspace__slug` from the URL. `@allow_permission` only validates membership on the URL's `project_id`, not that `issue_id` belongs to that project. Possible **cross-project IDOR**: a member of project A references an `issue_id` from project B. Needs runtime verification of whether the issue object is used for writes (create comment/sub-issue) across projects. |
| 🟡 MEDIUM           | `permissions/base.py:60` (default `get_queryset` is `.all()`)   | Not a bug by itself, but _fail-open by default_: a new view that forgets to override `get_queryset` will expose every row. A default of deny or scoped is recommended.                                                                                                                                                                                                                                                                                                         |
| 🟢 INFO             | `permissions/workspace.py:22`                                   | `WorkSpaceBasePermission` allows `POST` (create workspace) for every authenticated user, by design (anyone may create a workspace).                                                                                                                                                                                                                                                                                                                                            |
| 🟢 INFO             | `permissions/base.py` decorator                                 | Logic that lets a workspace admin who is a project member in even with a low project role (`base.py:64`), a controlled escalation, reasonable.                                                                                                                                                                                                                                                                                                                                 |

**Public REST v1** (`plane/api/`): different auth (API key + throttle `API_KEY_RATE_LIMIT=60/minute`). Separate permission classes in `plane/api/`, not read in detail yet (read `plane/api/views/base.py` + permissions in a follow-up pass).

**Follow-up audit recommendation (not done yet):** grep every `get_queryset` across the 60 views to confirm **all** of them filter on `workspace__slug`; and audit every `objects.get(pk=<child_id>)` to see whether the child is validated as belonging to the parent in the URL (the comment.py pattern above may repeat in link/reaction/attachment/relation).

---

## DEEP-DIVE #2, DB schema per model (PHASE 5)

### Base class hierarchy (`plane/db/mixins.py` + `db/models/base.py`)

```
TimeAuditModel      -> created_at (auto_now_add), updated_at (auto_now)          mixins.py:16
UserAuditModel      -> created_by, updated_by (FK User, SET_NULL, auto via crum) mixins.py:26
SoftDeleteModel     -> deleted_at (nullable); .delete() = set deleted_at         mixins.py:61
  SoftDeletionManager.get_queryset() -> filter(deleted_at__isnull=True)          mixins.py:56
AuditModel          = TimeAuditModel + UserAuditModel + SoftDeleteModel          mixins.py:85
BaseModel           = AuditModel + id: UUIDField(pk, default uuid4)              base.py:16
  ProjectBaseModel  = BaseModel + project(FK CASCADE) + workspace(FK CASCADE)   project.py:180
                      save() auto-sets workspace = project.workspace            project.py:188
  WorkspaceBaseModel= BaseModel + workspace(FK CASCADE)                          workspace.py:185
ChangeTrackerMixin  -> tracks field changes (for the activity feed)              mixins.py:92
```

**Key invariants:**

- **PK = UUID** on every model (not a sequential int) → reduces enumeration and guessing ids for IDOR.
- **Soft delete by default**, `deleted_at`; the default manager hides deleted rows. Models with a custom manager (e.g. `Issue.objects` vs `Issue.issue_objects`) can expose soft-deleted rows if a query uses the wrong manager (relevant to the IDOR smell in comment.py, which uses `Issue.objects`).
- **Scoping baked in**, a `ProjectBaseModel` subclass automatically has `project` + `workspace` and keeps them consistent via `save()`. This strengthens per-tenant filtering.
- **Automatic audit**, `created_by`/`updated_by` via `django-crum` `get_current_user()` (`base.py:24`).

### Core models and relations (examples from `issue.py`, explicit `db_table`)

| Model                      | Table               | Key relations                                                                         | on_delete                                                       |
| -------------------------- | ------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `Issue` (`issue.py:104`)   | `issues`            | parent(self), state, estimate_point, type, assignees(M2M), labels(M2M via IssueLabel) | parent=CASCADE, state=CASCADE, estimate=SET_NULL, type=SET_NULL |
| `IssueBlocker` (`:258`)    | `issue_blockers`    | block, blocked_by → Issue                                                             | CASCADE                                                         |
| `IssueRelation` (`:296`)   | `issue_relations`   | issue, related_issue                                                                  | CASCADE; unique `[issue, related_issue, deleted_at]`            |
| `IssueMention` (`:323`)    | `issue_mentions`    | issue, mention(User)                                                                  | CASCADE; unique `[issue, mention, deleted_at]`                  |
| `IssueAssignee` (`:345`)   | `issue_assignees`   | issue, assignee(User)                                                                 | CASCADE; unique `[issue, assignee, deleted_at]`                 |
| `IssueLink` (`:371`)       | `issue_links`       | issue                                                                                 | CASCADE                                                         |
| `IssueAttachment` (`:398`) | `issue_attachments` | issue                                                                                 | CASCADE                                                         |
| `IssueActivity` (`:415`)   | `issue_activities`  | issue, issue_comment, actor                                                           | issue=DO_NOTHING, actor=SET_NULL                                |
| `IssueComment` (`:451`)    | `issue_comments`    | description(O2O), issue, actor                                                        | description=CASCADE, issue=CASCADE                              |

> The `unique_together` pattern always includes `deleted_at`, which allows re-creating a row after a soft delete without a unique clash (a deliberate idiom).

### Model inventory (31 modules in `plane/db/models/`, 178 files)

`workspace, project, issue, issue_type, cycle, module, state, label, estimate, page, view, intake, draft, notification, webhook, asset, favorite, sticky, recent_visit, deploy_board (public share), api (token), device, session, social_connection, description, exporter, importer, integration/ (dir), analytic, user`.

Domain graph: _*Workspace 1─* Project 1─_ {Issue, Cycle, Module, State, Label, Page, View, Estimate, Intake}**; Issue _─_ {Label, Assignee(User), Cycle, Module}; double scoping by project + workspace on every entity.

**Schema source of truth:** a single one (Django ORM). 121 migrations. Frontend types (`packages/types`) are separate → drift risk (see #4).

**Not examined yet:** full fields of each non-issue model, DB indexes (other than unique_together), the `integration/` models (dir), `user.py` (auth/permission fields), `deploy_board.py` (access control for public sharing, relevant to security).

---

## DEEP-DIVE #3, End-to-end feature traces (PHASE 6.5)

### Trace A, Create issue

```
UI: web issue create form (apps/web/core/components/issues/...)
  -> service: apps/web/core/services/issue/*.service.ts (axios POST)
  -> route: POST /api/workspaces/<slug>/projects/<project_id>/issues/  (plane/app/urls/issue.py)
  -> guard: @allow_permission([ROLE.ADMIN, ROLE.MEMBER])         issue/base.py:392
            (checks ProjectMember role on slug+project_id; GUEST cannot create)
  -> handler: IssueViewSet.create(request, slug, project_id)      issue/base.py:393
       project = Project.objects.get(pk=project_id)               issue/base.py:394
       serializer (IssueCreateSerializer) validates the payload
  -> model save: Issue (ProjectBaseModel) -> save() sets workspace=project.workspace, created_by=user (crum)
  -> data store: table `issues` (+ IssueAssignee/IssueLabel M2M, IssueActivity)
  -> side effect: issue_activities_task (async) records activity; webhook_activity -> webhook_send_task
  <- response: serialized issue (JSON)
Edge/risk: create uses Project.objects.get(pk=project_id) without the slug, but the decorator already
validates membership on the URL's project_id -> safe. To check: whether the assignee/label in the
payload are validated as belonging to the same project (not verified yet).
```

### Trace B, Webhook delivery (SSRF-critical)

```
Trigger: model change (issue/project/etc.) -> webhook_activity()            webhook_task.py:393
  -> enqueue Celery: webhook_send_task (autoretry RequestException, backoff 600s, jitter)  :235
  -> handler: webhook_send_task(webhook_id, payload, ...)                     :242
  -> SSRF guard: pinned_fetch(webhook.url,
                    allowed_ips=WEBHOOK_ALLOWED_IPS,
                    allowed_hosts=WEBHOOK_ALLOWED_HOSTS)                       webhook_task.py:319
       -> resolve_and_validate(hostname): DNS resolve + reject private/loopback IPs
          unless the host/ip is in the allowlist                              url_security.py:180
       -> PinnedIPAdapter: the connection is PINNED to the already validated IP
          (get_connection_with_tls_context, hostname for SNI/cert)            url_security.py:46,67
          -> prevents DNS-rebinding TOCTOU (validation and connection cannot see different IPs)
       -> redirect: pinned_fetch_following_redirects re-validates EVERY hop, redirect limit  :225,264
  -> success -> save_webhook_log(status_ok)                                   :336
  -> RequestException -> save log + raise -> Celery retry                     :340
  -> repeated failure -> send_webhook_deactivation_email + deactivate webhook  :172
Strengths: layered SSRF mitigation (allowlist + IP pin + per-hop redirect check). This is
production-grade defense, not just an "is private IP" check. The code comment is explicit about the threat
"attacker swap in an IP after validation" (webhook_task.py:313).
```

### Trace C, Authentication (wide surface)

```
Routes (plane/authentication/urls.py):
  Email/password : /auth/sign-in, /sign-up, /sign-out, /email-check           :51-56,119
  Magic link     : /auth/magic-generate, /magic-sign-in, /magic-sign-up       :61-63
  Password mgmt  : /forgot-password, /change-password, /set-password          :122,138,139
  OAuth          : google, github, gitlab, gitea (+ /callback for each)       :80-148
  Space (public) : /auth/spaces/sign-in, /sign-up, /sign-out                   :53-57
  CSRF           : /auth/get-csrf-token                                        :59

Magic-link flow:
  POST /auth/magic-generate -> generate token -> magic_link_code_task (async email, bgtasks)
  POST /auth/magic-sign-in  -> validate token -> adapter (plane/authentication/adapter) -> create session
OAuth flow:
  GET  /auth/<provider>/           -> initiate (redirect to provider, state)
  GET  /auth/<provider>/callback/  -> exchange code -> provider oauth class
       (plane/authentication/provider/oauth/{google,github,gitlab,gitea}.py) -> create/link user

Auth = SessionAuthentication (cookie), not JWT for web (BaseSessionAuthentication, base.py).
Public REST v1 uses a separate API key. Rate limit: plane/authentication/rate_limit.py.
Password: Django validator + zxcvbn; reset TTL 3600s.
Note: the latest commit fixes a TOCTOU race in InstanceAdminSignUp (GHSA-p548-28jp-wr4p).
Not examined yet: adapter/session internals, CSRF protection on OAuth callbacks, validation of `next`/redirect.
```

---

## DEEP-DIVE #4, Frontend and packages (PHASE 7)

### Internal package map (layered dependencies)

```
@plane/types      (120 files, ZERO deps)  -> pure TS types: activity, ai, auth, cycle, issue, ...
@plane/constants  ────────────────────┐
@plane/utils      ────────────────────┤
@plane/hooks      ────────────────────┤
@plane/propel     (390, LARGEST)  ─────┼─> headless UI primitives: accordion, avatar, badge,
   deps: @base-ui-components/react       │    button, calendar, charts, combobox, command(cmdk),
         @tanstack/react-table, framer   │    ... (design-system layer)
@plane/ui         (128)  ──────────────┼─> higher-level shared components: auth-form,
   deps: propel + blueprintjs + atlaskit │    breadcrumbs, drag-handle, color-picker, ...
@plane/editor     (226)  ──────────────┼─> collaborative Tiptap/ProseMirror + Yjs editor
   deps: propel, ui, tiptap*, hocuspocus │    structure: core/ + ce/ + ee/  (CE/EE split!)
@plane/services   (56)  ───────────────┘─> per-domain axios clients (auth, cycle, issue, ...)
   deps: types + axios + file-type            used by the frontend apps to call the API
```

Others: `@plane/i18n` (locale JSON + ICU), `@plane/logger`, `@plane/decorators`, `@plane/shared-state`, `@plane/tailwind-config`, `@plane/typescript-config`, `@plane/codemods` (jscodeshift migrations).

### CE/EE architecture (Community vs Enterprise Edition)

Recurring pattern: `apps/web/ce/` (components + store) vs `apps/web/core/`, and `packages/editor/{ce,ee,core}`. **`ce/` = the Community Edition implementation** (the open-source one in this repo). The Enterprise build swaps the `ce` layer for `ee`. That means this repo is the **CE variant**; some EE features show up as stubs/interfaces in `ce`. (Consistent with the repo skill that mentions `plane-ee` and `plane-cloud`.)

### Web frontend (`apps/web/core`, 2,039 files)

| Layer           | Location                   | Contents                                                                                                                                                                                                                    |
| --------------- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| State (MobX)    | `core/store/`              | root.store.ts → sub-stores: issue/, cycle, module, project/, workspace/, page/, notification/, user/, member/, analytics, instance, theme, router, command-palette, power-k, timeline, sticky, favorite, estimates/, inbox/ |
| Service (axios) | `core/services/`           | ~30 services: ai, analytics, auth, cycle(+archive), module(+archive), issue/, project/, page/, file(+upload), workspace(+notification), instance, view, webhook, sticky, timezone, dashboard                                |
| Components      | `core/components/`         | ~55 domains: issues, cycles, modules, project, workspace, analytics, gantt-chart, editor, dropdowns, rich-filters, onboarding, settings, power-k (command palette), automation, web-hooks, ...                              |
| Layouts         | `core/layouts/`            | route guards / shell                                                                                                                                                                                                        |
| Hooks/lib       | `core/hooks/`, `core/lib/` | ,                                                                                                                                                                                                                           |

UI data flow: component → MobX store (observer) → `@plane/services` / `core/services` (axios) → Django API. Fetching uses **SWR** + the store. Realtime (page/editor) → Hocuspocus provider → `apps/live`.

### Frontend findings

| Sev       | Finding                                                                                                                                                                                                                                                                                   |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🟠 HIGH   | **`@plane/types` has no codegen** (the script is only a `tsdown` bundle, no openapi/generate, verified). TS types are maintained **by hand** separately from the Django models → real **schema drift risk**: a backend model change is not automatically reflected in the frontend types. |
| 🟡 MEDIUM | The `@plane/propel` (390 files) and `@plane/editor` (226) packages have not had their implementation read, only a component inventory. Editor complexity (Tiptap+Yjs+CE/EE) is a high bug-risk area.                                                                                      |
| 🟢 INFO   | Store/service/component separation is clean (container/presentational + MobX). Consistent with the "many small files" rule.                                                                                                                                                               |

**Not examined yet:** React Router route enumeration per app (react-router.config.ts), auth guards in layouts, propel/editor implementation, `apps/admin` and `apps/space` internals, accessibility/i18n coverage, actual bundle size.

---

## FINAL STATUS OF PASS 2

MODULE INDEX updated: authz ✅, DB schema ✅ (base + patterns, field detail 🟡), feature traces ✅ (3 features), frontend/packages ✅ (architecture, implementation detail 🟡).

**Remaining deep reads (if there is a pass 3):** (1) endpoint enumeration per URLconf + runtime verification of the IDOR smell in issue/comment, sub_issue, link, reaction, attachment; (2) fields per non-issue model + `deploy_board`/`user`/`api-token`; (3) `packages/propel` + `editor` implementation; (4) `plane/license` + `plane/space` + `apps/live` internals; (5) `.github/workflows` contents + Dockerfile build steps; (6) automated full-repo secret scan + enumeration of the 13 backend TODOs.
