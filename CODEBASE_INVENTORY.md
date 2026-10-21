# CODEBASE INVENTORY, Plane

> Audit read-only oleh staff-level architect. Semua klaim dilacak ke `path:baris`.
> Repo di-clone lokal sebagai `Pradise_Plane`; upstream = `github.com/makeplane/plane`.
> **Cakupan pass ini:** breadth-first menyeluruh (FASE 0–6 + keamanan + operasional).
> Depth per-modul (kutipan tiap fungsi) belum tuntas untuk semua ~4.100 file, lihat
> bagian **MODULE INDEX** untuk status per-modul dan **"Yang Belum Sempat Didalami"** di akhir.

---

## EXECUTIVE SUMMARY

- **Apa ini:** Plane, tool project management open-source (alternatif Jira/Linear). Kelola issue, cycle (sprint), module, page (docs), roadmap.
- **Stack:** Monorepo **pnpm + Turborepo**. Frontend TS/React (React Router 7 SPA + Vite), backend **Django 4.2 + DRF** (Python 3), realtime collab **Node/TypeScript (Hocuspocus + Yjs)**, proxy **Caddy**.
- **Skala:** ~2.129 `.tsx` + ~1.355 `.ts` + **629 `.py`**. 6 aplikasi (`apps/*`) + 15 package internal (`packages/*`).
- **Data plane:** PostgreSQL (utama + read-replica opsional), Redis (cache/celery result/ws), RabbitMQ (celery broker), S3/MinIO (asset), Celery (worker + beat).
- **Lisensi:** AGPL-3.0. Versi node `1.3.1`, versi API `0.24.0`.
- **3 hal paling menonjol:**
  1. Backend punya **kesadaran keamanan tinggi**, mitigasi SSRF webhook (allowlist IP/host/domain), guard `SECRET_KEY` insecure, TOCTOU fix di sign-up (commit terakhir). Bukan boilerplate biasa.
  2. Arsitektur **layered + domain-split** rapi: `db/` (model) → `app/` (views/serializers internal) → `api/` (REST publik v1 dgn API-key) → `space/` (public deploy board) → `authentication/` (multi-provider OAuth+magic).
  3. Editor kolaboratif kelas berat: **Tiptap/ProseMirror + Yjs + Hocuspocus** di `apps/live` + `packages/editor`, dengan export PDF server-side.
- **Risiko utama (awal, perlu deep-dive):** permukaan API sangat besar (permission/IDOR object-level perlu diaudit per-endpoint), `ALLOWED_HOSTS` default `*`, banyak env var wajib tanpa validasi startup terpusat.

---

## MODULE INDEX (master checklist)

Status: ✅ deep-read · 🟡 di-skim (struktur + file kunci) · ⬜ belum dibuka

| Modul                 | Path                                                                 | Bahasa | Status | Catatan                                   |
| --------------------- | -------------------------------------------------------------------- | ------ | ------ | ----------------------------------------- |
| Root/workspace config | `package.json`, `turbo.json`, `pnpm-workspace.yaml`                  | ,      | ✅     | Turborepo tasks, catalog deps             |
| API settings          | `apps/api/plane/settings/*`                                          | Py     | ✅     | env var, config numerik                   |
| API routing           | `apps/api/plane/urls.py` + `app/urls/*`                              | Py     | 🟡     | daftar route file, belum per-endpoint     |
| API models            | `apps/api/plane/db/models/*` (178 file)                              | Py     | 🟡     | daftar model, belum tiap field            |
| API views (internal)  | `apps/api/plane/app/views/*` (112 file)                              | Py     | 🟡     | daftar domain, belum tiap handler         |
| API v1 (publik)       | `apps/api/plane/api/*` (49 file)                                     | Py     | 🟡     | REST + API-key                            |
| Auth                  | `apps/api/plane/authentication/*`                                    | Py     | 🟡     | provider OAuth + credentials              |
| Background tasks      | `apps/api/plane/bgtasks/*` (34 file)                                 | Py     | ✅     | daftar task + jadwal cron                 |
| Celery config         | `apps/api/plane/celery.py`                                           | Py     | ✅     | beat_schedule lengkap                     |
| License/instance      | `apps/api/plane/license/*`                                           | Py     | ⬜     | telemetry, instance admin                 |
| Space (public)        | `apps/api/plane/space/*`                                             | Py     | ⬜     | deploy board publik                       |
| Web app               | `apps/web/*` (2.039 file)                                            | TSX    | 🟡     | store/services/components teridentifikasi |
| Admin app             | `apps/admin/*` (100 file)                                            | TSX    | 🟡     | god-mode instance admin                   |
| Space app             | `apps/space/*` (166 file)                                            | TSX    | 🟡     | published views frontend                  |
| Live (realtime)       | `apps/live/src/*`                                                    | TS     | 🟡     | hocuspocus + yjs                          |
| Proxy                 | `apps/proxy/*`                                                       | Caddy  | ✅     | 3 file config                             |
| Editor pkg            | `packages/editor` (226 file)                                         | TS     | ⬜     | tiptap extensions                         |
| Propel (UI kit?)      | `packages/propel` (390 file)                                         | TS     | ⬜     | package terbesar, belum dibuka            |
| UI pkg                | `packages/ui` (128 file)                                             | TS     | ⬜     | komponen dasar                            |
| Types pkg             | `packages/types` (120 file)                                          | TS     | ⬜     | tipe bersama                              |
| Services pkg          | `packages/services` (56 file)                                        | TS     | ⬜     | client API bersama                        |
| Lainnya pkg           | `constants,utils,hooks,i18n,logger,decorators,shared-state,codemods` | TS     | ⬜     | ,                                         |
| Infra                 | `docker-compose*.yml`, `deployments/*`                               | YAML   | ✅     | services teridentifikasi                  |

---

## FASE 0, Deteksi Stack & Tipe Project

**Bahasa & porsi (di luar node_modules/build):**

| Bahasa         | File                        | Peran                                  |
| -------------- | --------------------------- | -------------------------------------- |
| TypeScript/TSX | ~3.484 (2129 tsx + 1355 ts) | Semua frontend + live server + package |
| Python         | 629                         | Backend API (Django)                   |
| JSON           | 594                         | Config, i18n locales, tsconfig         |
| CSS            | 19                          | Styling (Tailwind v4)                  |
| Shell          | 14                          | Script build/entrypoint                |

**Manifest terdeteksi:**

| File                                    | Lokasi                              | Ekosistem                                                                |
| --------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------ |
| `package.json`                          | root + tiap `apps/*` & `packages/*` | pnpm workspace (Turborepo)                                               |
| `pnpm-workspace.yaml`                   | root                                | Workspace: `apps/*`, `packages/*`, **kecuali** `apps/api` & `apps/proxy` |
| `pyproject.toml` + `requirements/*.txt` | `apps/api`                          | Python/Django (pip)                                                      |
| `turbo.json`                            | root                                | Turborepo task graph                                                     |

**Tipe project:** Monorepo multi-service:

- **Backend/API**, `apps/api` (Django + DRF + Celery), Python. Tidak ikut pnpm workspace (punya build sendiri via Docker).
- **Frontend/SPA**, `apps/web` (utama), `apps/admin` (instance admin), `apps/space` (public published views). Semua React 18 + React Router 7 + Vite.
- **Realtime service**, `apps/live` (Node/Express + Hocuspocus + Yjs) untuk kolaborasi dokumen.
- **Reverse proxy**, `apps/proxy` (Caddy).
- **Library internal**, 15 package di `packages/*` (editor, ui, types, services, i18n, dst).

**Framework inti + versi:**

| Area          | Framework               | Versi                                |
| ------------- | ----------------------- | ------------------------------------ |
| Backend       | Django                  | 4.2.30                               |
| Backend API   | Django REST Framework   | 3.15.2                               |
| Task queue    | Celery                  | 5.4.0 (+ django-celery-beat/results) |
| DB driver     | psycopg (3)             | 3.3.0                                |
| Frontend      | React                   | 18.3.1                               |
| Routing/SSR   | React Router            | 7.15.x (mode framework)              |
| Bundler       | Vite                    | 8.0.16                               |
| State         | MobX + mobx-react       | 6.12.0 / 9.1.1                       |
| Data fetching | SWR                     | 2.2.4                                |
| Editor        | Tiptap/ProseMirror      | ^2.22.3                              |
| Realtime      | Yjs + Hocuspocus        | ^13.6.20 / 2.15.2                    |
| Styling       | Tailwind CSS            | 4.1.17                               |
| i18n          | i18next + react-i18next | 25.x / 16.x                          |
| Lint/format   | oxlint + oxfmt          | 1.51.0 / 0.35.0                      |
| Node          | engines                 | `>=22.18.0`, pnpm 11.3.0             |

**Monorepo tooling:** Turborepo 2.9.18. Task graph di `turbo.json`: `build`, `dev` (concurrency 18), `check` (format+lint+types), `fix`. Catalog dependency terpusat di `pnpm-workspace.yaml` (`catalog:`) + banyak `overrides` (pinning keamanan: `axios`, `ws`, `undici`, `form-data`, dst).

---

## FASE 1, INVENTARIS LENGKAP ⭐

### Struktur folder top-level

```
Pradise_Plane/
├── apps/
│   ├── api/      # Django backend (Python), TIDAK ikut pnpm workspace
│   ├── web/      # SPA utama (React Router 7 + Vite), app terbesar
│   ├── admin/    # Instance admin "god-mode" (React)
│   ├── space/    # Public published views / deploy boards (React)
│   ├── live/     # Realtime collab server (Node/Express + Hocuspocus + Yjs)
│   └── proxy/    # Caddy reverse proxy
├── packages/     # 15 library internal bersama (editor, ui, types, services, i18n, …)
├── deployments/  # aio, cli, kubernetes, swarm
├── docs/         # linting.md (minim)
├── docker-compose*.yml  # ce (community) + local + test
├── setup.sh
├── turbo.json / pnpm-workspace.yaml / package.json
```

### Entry point

| App             | Entry                                                    | Bukti                         |
| --------------- | -------------------------------------------------------- | ----------------------------- |
| API (WSGI/ASGI) | `plane/wsgi.py`, `plane/asgi.py`                         | `apps/api/plane/`             |
| API mgmt        | `manage.py`                                              | `apps/api/manage.py`          |
| Celery          | `plane/celery.py` (app + beat_schedule)                  | `apps/api/plane/celery.py:44` |
| Web/Admin/Space | React Router `react-router.config.ts` + `vite.config.ts` | tiap app                      |
| Live            | `src/server.ts` → `src/start.ts`                         | `apps/live/src/`              |
| Proxy           | `Caddyfile.ce` / `Caddyfile.aio.ce`                      | `apps/proxy/`                 |

### Dependency langsung, backend (`apps/api/requirements/base.txt`)

| Paket                                 | Versi                   | Untuk apa                                             |
| ------------------------------------- | ----------------------- | ----------------------------------------------------- |
| Django                                | 4.2.30                  | Web framework                                         |
| djangorestframework                   | 3.15.2                  | REST API                                              |
| psycopg / psycopg-binary              | 3.3.0                   | Driver PostgreSQL                                     |
| dj-database-url                       | 2.1.0                   | Parse `DATABASE_URL`                                  |
| redis / django-redis                  | 5.0.4 / 5.4.0           | Cache, session, celery result                         |
| celery / django_celery_beat / results | 5.4.0 / 2.6.0 / 2.5.1   | Task queue + scheduler                                |
| django-cors-headers                   | 4.3.1                   | CORS                                                  |
| whitenoise                            | 6.11.0                  | Static serve                                          |
| django-storages / boto3               | 1.14.2 / 1.34.96        | S3/MinIO asset                                        |
| channels                              | 4.1.0                   | WebSocket/ASGI                                        |
| uvicorn                               | 0.29.0                  | ASGI server                                           |
| openai                                | 1.63.2                  | Fitur AI                                              |
| slack-sdk                             | 3.27.1                  | Integrasi Slack                                       |
| scout-apm                             | 3.1.0                   | APM monitoring                                        |
| posthog                               | 3.5.0                   | Analytics/telemetry                                   |
| cryptography / PyJWT                  | 48.0.1 / 2.13.0         | Crypto, JWT                                           |
| nh3 / lxml / beautifulsoup4           | 0.2.18 / 6.1.0 / 4.12.3 | Sanitasi & parse HTML                                 |
| zxcvbn                                | 4.4.28                  | Validator kekuatan password                           |
| drf-spectacular                       | 0.28.0                  | OpenAPI schema                                        |
| openpyxl                              | 3.1.2                   | Export XLSX                                           |
| opentelemetry-\*                      | 1.28.1                  | Tracing                                               |
| requests                              | 2.33.0                  | Webhook delivery (pinned utk SSRF IP-pinning adapter) |
| urllib3                               | >=2.7.0                 | Pinned (CVE-2026-44431/44432)                         |

> Split: `requirements/base.txt` (inti) + `local.txt` (dev, mis. debug-toolbar) + `production.txt` + `test.txt` (pytest).

### Dependency langsung, frontend (catalog `pnpm-workspace.yaml`)

Highlight (bukan exhaustif, catalog ~180 entri):

| Paket                                           | Versi                  | Untuk apa                |
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
| framer-motion                                   | ^12.23                 | Animasi                  |
| recharts                                        | ^2.15.1                | Chart/analytics          |
| @tanstack/react-table + react-virtual           | ^8.21 / ^3.13          | Tabel + virtualisasi     |
| @atlaskit/pragmatic-drag-and-drop\*             | 1.x                    | Drag & drop board        |
| i18next + react-i18next + i18next-icu           | 25.x/16.x/2.4          | i18n                     |
| zod                                             | ^3.25                  | Validasi schema          |
| react-hook-form                                 | 7.51.5                 | Form                     |
| @react-pdf/renderer + pdf-parse                 | ^4.3 / ^2.4.5          | PDF export/parse         |
| express + express-ws + helmet + compression     | 4.22 / 5.0 / 7.1 / 1.8 | Live server              |
| ioredis                                         | 5.7.0                  | Redis (live)             |
| winston + express-winston                       | ^3.17 / ^4.2           | Logging (live)           |

### Script/command

**Root (`package.json`):** `build`, `dev` (turbo, concurrency 18), `start`, `clean`, `fix`/`fix:format`/`fix:lint`, `check`/`check:lint`/`check:format`/`check:types`, `prepare` (husky), `doctor` (react-doctor).
**lint-staged:** `oxfmt` + `oxlint --fix --deny-warnings` pada file JS/TS/JSON/CSS/MD.
**API:** `apps/api/manage.py` (Django), `run_tests.py` / `run_tests.sh` / `pytest.ini`, `bin/` (entrypoint container).

### File konfigurasi kunci

| File                                                                                    | Fungsi                                            |
| --------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `turbo.json`                                                                            | Task graph + `globalEnv` (daftar env Vite/Sentry) |
| `pnpm-workspace.yaml`                                                                   | Workspace + catalog + overrides + allowBuilds     |
| `apps/api/plane/settings/{common,production,local,test,redis,storage,openapi}.py`       | Konfigurasi Django berlapis                       |
| `apps/*/vite.config.ts`, `react-router.config.ts`, `postcss.config.js`, `tsconfig.json` | Config frontend per-app                           |
| `.oxlintrc.json`, `.oxfmtrc.json`, `.npmrc`                                             | Lint/format/registry (globalDependencies turbo)   |
| `apps/proxy/Caddyfile.ce`, `Caddyfile.aio.ce`                                           | Routing proxy                                     |
| `docker-compose.yml` / `-local.yml` / `-test.yml`                                       | Orkestrasi service                                |

### Environment variables (backend, dibaca di `plane/settings/`)

Wajib/utama (⭐ = kritikal keamanan/operasi):

| Env                                                                                      | Dibaca di                       | Default            | Catatan                                                   |
| ---------------------------------------------------------------------------------------- | ------------------------------- | ------------------ | --------------------------------------------------------- |
| ⭐ `SECRET_KEY`                                                                          | `common.py:34`                  | random jika kosong | Menolak nilai placeholder known-insecure (`common.py:38`) |
| `DEBUG`                                                                                  | `common.py:59`                  | `0`                | ,                                                         |
| `ALLOWED_HOSTS`                                                                          | `common.py:99`                  | `*` ⚠️             | Default terlalu longgar utk prod                          |
| `DATABASE_URL` / `POSTGRES_*`                                                            | settings                        | ,                  | Utama                                                     |
| `ENABLE_READ_REPLICA` + `DATABASE_READ_REPLICA_URL`/`POSTGRES_READ_REPLICA_*`            | settings                        | off                | Routing middleware read-replica (`common.py:119`)         |
| `REDIS_URL`                                                                              | redis.py                        | ,                  | Cache/session/result                                      |
| `AMQP_URL` / `RABBITMQ_*`                                                                | `common.py:209`                 | ,                  | Celery broker                                             |
| `AWS_*` / `USE_MINIO` / `MINIO_ENDPOINT_*`                                               | storage.py                      | ,                  | S3/MinIO asset                                            |
| ⭐ `WEBHOOK_ALLOWED_IPS` / `_HOSTS` / `WEBHOOK_DISALLOWED_DOMAINS`                       | `common.py:64–96`               | kosong             | Kontrol SSRF webhook                                      |
| `FILE_SIZE_LIMIT`                                                                        | `common.py:234`                 | `5242880` (5 MB)   | juga `DATA_UPLOAD_MAX_MEMORY_SIZE`                        |
| `API_KEY_RATE_LIMIT`                                                                     | `common.py:35` (REST_FRAMEWORK) | `60/minute`        | Throttle API-key                                          |
| `SIGNED_URL_EXPIRATION`                                                                  | storage                         | ,                  | TTL presigned S3                                          |
| `SESSION_COOKIE_AGE` / `_NAME` / `ADMIN_SESSION_COOKIE_AGE` / `COOKIE_DOMAIN`            | settings                        | ,                  | Session                                                   |
| `PASSWORD_RESET_TIMEOUT`                                                                 | `common.py` (hardcoded)         | `3600` s           | ,                                                         |
| `HARD_DELETE_AFTER_DAYS`                                                                 | settings                        | ,                  | Soft→hard delete window                                   |
| `CORS_ALLOWED_ORIGINS`                                                                   | settings                        | ,                  | ,                                                         |
| `OPENAI`/`GITHUB_ACCESS_TOKEN`/`UNSPLASH_ACCESS_KEY`/`POSTHOG_*`/`SCOUT_*`/`ANALYTICS_*` | settings                        | ,                  | Integrasi eksternal                                       |
| `*_BASE_URL`/`*_BASE_PATH` (APP/ADMIN/SPACE/LIVE/WEB)                                    | settings                        | ,                  | URL antar-service                                         |

Frontend (Vite, dari `turbo.json:globalEnv`): `VITE_API_BASE_URL/PATH`, `VITE_ADMIN_*`, `VITE_LIVE_*`, `VITE_SPACE_*`, `VITE_WEB_*`, `VITE_WEBSITE_URL`, `VITE_SUPPORT_EMAIL`, Sentry (`VITE_SENTRY_*`), session recorder (`VITE_SESSION_RECORDER_KEY`, `VITE_ENABLE_SESSION_RECORDER`), `APP_VERSION`.

### Integrasi eksternal

| Kategori             | Teknologi                                                              |
| -------------------- | ---------------------------------------------------------------------- |
| Database             | PostgreSQL (utama + read-replica opsional)                             |
| Cache/session/result | Redis (django-redis + ioredis di live)                                 |
| Message broker       | RabbitMQ (Celery)                                                      |
| Object storage       | S3 / MinIO (django-storages + boto3)                                   |
| Auth OAuth           | Google, GitHub, GitLab, Gitea (`plane/authentication/provider/oauth/`) |
| AI                   | OpenAI                                                                 |
| Chat                 | Slack (slack-sdk)                                                      |
| Analytics/telemetry  | PostHog + instance metrics telemetry                                   |
| APM/tracing          | Scout APM + OpenTelemetry                                              |
| Media                | Unsplash (cover image)                                                 |
| Error/session        | Sentry (frontend)                                                      |

### Background job / cron (`plane/celery.py:44`)

| Jadwal (UTC)         | Task                                                      |
| -------------------- | --------------------------------------------------------- |
| tiap 5 menit         | `email_notification_task.stack_email_notification`        |
| interval (telemetry) | `license.bgtasks.telemetry_metrics.push_instance_metrics` |
| 00:00                | `deletion_task.hard_delete`                               |
| 01:00                | `issue_automation_task.archive_and_close_old_issues`      |
| 01:30 & 03:45        | `exporter_expired_task.delete_old_s3_link` (terdaftar 2×) |
| 02:00                | `file_asset_task.delete_unuploaded_file_asset`            |
| 02:30                | `cleanup_task.delete_api_logs`                            |
| 02:45                | `cleanup_task.delete_email_notification_logs`             |
| 03:00                | `cleanup_task.delete_page_versions`                       |
| 03:15                | `cleanup_task.delete_issue_description_versions`          |
| 03:30                | `cleanup_task.delete_webhook_logs`                        |

> ⚠️ `exporter_expired_task.delete_old_s3_link` terdaftar dua kali (01:30 & 03:45) dengan key beda (`..._exporter_history` vs `..._exporter-history`), kemungkinan redundan. `beat_scheduler = DatabaseScheduler` (`celery.py:118`).

Task lain (dipicu event, bukan cron) di `plane/bgtasks/`: webhook delivery, issue activities, notifications, exports (xlsx/csv), magic-link/forgot-password email, workspace/project invitation, page & issue version sync, storage metadata, event tracking, dummy data seeding.

### Kode tersembunyi

- `TODO/FIXME/HACK/XXX` di backend Python: **13 penanda** (`grep` `apps/api/plane/**/*.py`). Belum dienumerasi satu-satu, TODO deep-dive.
- Frontend belum discan utk penanda ini (TODO).

### Nilai konfigurasi aktual (numerik)

| Nilai                                                        | Sumber           |
| ------------------------------------------------------------ | ---------------- |
| `FILE_SIZE_LIMIT` = 5 MB (5242880)                           | `common.py:234`  |
| `API_KEY_RATE_LIMIT` = 60/minute                             | `common.py:35`   |
| `PASSWORD_RESET_TIMEOUT` = 3600 s                            | `common.py:155`  |
| `dev` concurrency = 18                                       | `package.json`   |
| McCabe complexity max = 10, ruff line-length 120, max-args 8 | `pyproject.toml` |
| Node engine `>=22.18.0`                                      | `package.json`   |

---

## FASE 2, Infrastruktur & Environment

**Runtime:** Python 3 (Django 4.2, uvicorn ASGI), Node >=22.18, pnpm 11.3.

**Containerization:** tiap app punya Dockerfile ganda (`Dockerfile.<app>` prod + `Dockerfile.dev`). Orkestrasi via `docker-compose.yml` (community edition). Services:

| Service                        | Peran                            |
| ------------------------------ | -------------------------------- |
| `web`, `admin`, `space`        | Frontend SPA (Nginx serve build) |
| `api`                          | Django (uvicorn/gunicorn)        |
| `worker`                       | Celery worker                    |
| `beat-worker`                  | Celery beat (scheduler)          |
| `migrator`                     | Job migrasi DB (one-shot)        |
| `live`                         | Realtime collab (Node)           |
| `plane-db`                     | PostgreSQL                       |
| `plane-redis`                  | Redis                            |
| `plane-mq`                     | RabbitMQ                         |
| `plane-minio`                  | MinIO (S3)                       |
| `proxy`                        | Caddy (entry HTTP)               |
| `pgdata`,`redisdata`,`uploads` | Named volumes                    |

**Deployments lain:** `deployments/{aio,cli,kubernetes,swarm}`, AIO (all-in-one image), Kubernetes manifest/Helm, Docker Swarm, CLI installer. Belum dibuka detail (TODO).

**CI/CD:** GitHub Actions, `.github/workflows/`: `build-branch.yml`, `check-version.yml`, `codeql.yml` (SAST), `copyright-check.yml`, `feature-deployment.yml`, `i18n-sync-check.yml`, `pull-request-build-lint-api.yml`, `pull-request-build-lint-web-apps.yml`, `react-doctor.yml`. Jadi: build/lint terpisah API vs web-apps, CodeQL security scan, cek versi + copyright + i18n sync di PR. Isi tiap workflow belum dibaca detail (TODO).

**Build/run (dev):** `pnpm install` → `pnpm dev` (turbo, semua app frontend + live). API: `apps/api` via `manage.py runserver` atau uvicorn; worker/beat via celery. **Prod:** `docker compose up` (community) atau deployment k8s/swarm. Detail langkah persis → belum diekstrak dari Dockerfile/entrypoint (TODO).

---

## FASE 3, Arsitektur & Alur Data

**Pola:** Monolith modular di backend (Django apps per-domain) + SPA multi-app di frontend + service realtime terpisah. Bukan microservices penuh, satu DB, satu codebase Django, dipisah jadi worker/beat/web process.

**Layering backend (dibuktikan dari struktur):**

```
plane/db/        -> Model + migrasi (sumber kebenaran skema)
plane/app/       -> Views + serializers "internal" (dipakai web/admin) di /api/
plane/api/       -> REST publik v1 (/api/v1/) dgn API-key auth
plane/space/     -> Endpoint publik deploy board (/api/public/)
plane/license/   -> Instance/license admin (/api/instances/)
plane/authentication/ -> Login/OAuth/magic (/auth/)
plane/bgtasks/   -> Celery tasks (async)
plane/middleware/-> Read-replica routing, dll
plane/utils/     -> Helper lintas domain (69 file)
```

Routing puncak: `plane/urls.py` memetakan tiap prefix ke app (lihat FASE 4).

**Alur data (garis besar):**

```
Browser (web/admin/space SPA, MobX store + SWR)
  │  HTTP/JSON  ─────────────────► Caddy proxy
  │  WebSocket (collab) ─────────►
  ▼
Caddy ──► Django API (/api, /api/v1, /api/public, /auth)
      └─► Live service (Node/Hocuspocus) ──► Redis (pubsub) + Postgres (persist doc)
Django ──► Postgres (utama / read-replica)
       ├─► Redis (cache/session)
       ├─► RabbitMQ ──► Celery worker ──► Postgres/S3/email/webhook
       └─► S3/MinIO (asset presigned URL)
Celery beat ──► jadwalkan task periodik
```

Frontend state: **MobX** (root store `apps/web/core/store/root.store.ts` → sub-store per domain: issue, cycle, module, project, workspace, page, notification, dst) + **SWR** utk fetch. Service layer `apps/web/core/services/*.service.ts` membungkus axios ke endpoint.

---

## FASE 4, Permukaan Antarmuka

**Routing Django puncak (`plane/urls.py`):**

| Prefix                                   | Include                     | Guna                                    |
| ---------------------------------------- | --------------------------- | --------------------------------------- |
| `api/`                                   | `plane.app.urls`            | API internal (web/admin)                |
| `api/public/`                            | `plane.space.urls`          | Deploy board publik                     |
| `api/instances/`                         | `plane.license.urls`        | Instance/license admin                  |
| `api/v1/`                                | `plane.api.urls`            | **REST publik v1 (API-key)**            |
| `auth/`                                  | `plane.authentication.urls` | Login/OAuth/magic                       |
| `` (root)                                | `plane.web.urls`            | Web/health                              |
| `api/schema/`, `/swagger-ui/`, `/redoc/` | drf-spectacular             | OpenAPI (jika `ENABLE_DRF_SPECTACULAR`) |

**Domain route internal (`plane/app/urls/`):** `analytic, api, asset, cycle, estimate, exporter, external, intake, issue, module, notification, page, project, search, state, timezone, user, views, webhook, workspace`.

**REST publik v1 (`plane/api/urls/`):** `asset, cycle, estimate, intake, invite, label, member, module, project, schema, state, sticky, user, work_item`, auth via API key + throttle `API_KEY_RATE_LIMIT`.

**View domain (`plane/app/views/`, 112 file):** direktori per-domain: `analytic, asset, cycle, estimate, exporter, external, intake, issue, module, notification, page, project, search, state, timezone, user, view, webhook, workspace` + `base.py` (base viewset) + `error_404.py`.

> Enumerasi endpoint + method + permission per-URLconf = **TODO deep-dive** (butuh baca tiap `urls/*.py` & viewset). Ini permukaan terbesar & paling relevan utk audit IDOR/permission.

**Frontend routes:** React Router 7 (file-based via `react-router.config.ts`) di web/admin/space. Guard/layout via `apps/web/core/layouts/`. Belum dienumerasi (TODO).

**Live service (`apps/live/src/controllers/`):** `collaboration.controller`, `document.controller`, `health.controller`, `pdf-export.controller` (+ hocuspocus WS server `hocuspocus.ts`).

---

## FASE 5, Lapisan Data

**Engine:** PostgreSQL. ORM Django. Read-replica opsional via `ReadReplicaRoutingMiddleware` (`plane/middleware/db_routing.py`, diaktifkan bila `ENABLE_READ_REPLICA`).

**Model (`plane/db/models/`, 178 file py, daftar file):**
`analytic, api, asset, base, cycle, deploy_board, description, device, draft, estimate, exporter, favorite, importer, intake, integration/, issue, issue_type, label, module, notification, page, project, recent_visit, session, social_connection, state, sticky, user, view, webhook, workspace`.

Domain inti terlihat: **workspace → project → (issue, cycle, module, state, label, page, view, estimate, intake)**, plus asset, notification, webhook, favorite, sticky, draft, deploy_board (public share), api (token), integration.

**Sumber kebenaran skema:** tunggal, model Django `plane/db/models/*` + migrasi Django. Risiko drift rendah di backend (satu ORM). Tipe frontend (`packages/types`, 120 file) adalah representasi terpisah → potensi drift TS↔Python (perlu cek apakah di-generate dari OpenAPI atau manual, TODO).

**Migrasi:** Django migrations, **121 file** di `plane/db/migrations/`. Job `migrator` (one-shot) menerapkannya di compose.

**Integritas referensial:** Django FK aktif (default). Detail on_delete per-model = TODO. `base.py` kemungkinan menyediakan soft-delete + audit fields (created_by/updated_by via django-crum), perlu konfirmasi baca (`plane/db/models/base.py`).

---

## FASE 6, Logika Bisnis / Domain Inti

**Apa yang app lakukan (fitur inti terdeteksi dari model+view+store+components):**

| Fitur                                                   | Bukti                                                            |
| ------------------------------------------------------- | ---------------------------------------------------------------- |
| Workspace & member management                           | model `workspace`, view `workspace/`, store `workspace`          |
| Project management                                      | model/view/store `project`                                       |
| Issues / work items (CRUD, sub-issue, relasi, activity) | model `issue`, view `issue/`, store `issue/`, api v1 `work_item` |
| Cycles (sprint) + archive                               | model `cycle`, service `cycle_archive.service.ts`                |
| Modules + archive                                       | model `module`, service `module_archive.service.ts`              |
| States & workflow                                       | model/view `state`                                               |
| Labels                                                  | model/view `label`                                               |
| Estimates                                               | model/view `estimate`                                            |
| Intake (inbox triage issue)                             | model `intake`, view `intake/`, store `inbox`                    |
| Pages (docs kolaboratif)                                | model `page`, live service, versi (`page_version_task`)          |
| Views (saved filters)                                   | model `view`, components `views/`                                |
| Notifications (in-app + email)                          | model `notification`, bgtask email tiap 5 mnt                    |
| Webhooks (outbound, SSRF-guarded)                       | model `webhook`, view `webhook/`, bgtask `webhook_task`          |
| Analytics/dashboard                                     | view `analytic/`, store `analytics`, recharts                    |
| API tokens (REST publik)                                | model `api`, api v1                                              |
| Public deploy board (share)                             | model `deploy_board`, `plane/space/`, `apps/space`               |
| Import/Export (xlsx/csv)                                | model `importer`/`exporter`, bgtasks export                      |
| Stickies (notes)                                        | model/view `sticky`                                              |
| AI assist                                               | service `ai.service.ts`, openai                                  |
| Favorites, recent visits                                | model `favorite`, `recent_visit`                                 |
| Instance admin (god mode)                               | `apps/admin`, `plane/license`                                    |

Business logic utama ada di **serializers + viewsets** (`plane/app/views/*`, `plane/app/serializers`) dan **bgtasks** (async). Duplikasi TS↔Py (validasi di frontend & backend), perlu audit konsistensi (TODO).

---

## FASE 8, Keamanan (temuan awal)

🟢 **Positif (bukti kesadaran keamanan tinggi):**

- **SSRF webhook mitigation**, allowlist IP/CIDR (`common.py:64`), hostname (`common.py:79`), disallowed-domain (`common.py:91`); `requests` di-pin utk adapter IP-pinning TLS (`base.txt`). Delivery via `bgtasks/webhook_task.py`.
- **SECRET_KEY guard**, menolak nilai known-insecure/placeholder dgn log critical (`common.py:38-51`), fallback random bila kosong (GHSA-cmwv-pjmw-8483).
- **TOCTOU fix**, commit terakhir `7fbf14a` menutup race di `InstanceAdminSignUp` (GHSA-p548-28jp-wr4p).
- **Password:** validator Django + zxcvbn; `PASSWORD_RESET_TIMEOUT=3600`.
- **Sanitasi HTML:** nh3 + lxml + sanitize-html (frontend) utk konten rich-text/page.
- **Rate limiting:** DRF AnonRateThrottle + API-key throttle (`60/minute`).
- **Auth rate limit:** `plane/authentication/rate_limit.py`.
- Dependency **overrides** agresif utk CVE (axios, ws, undici, form-data, urllib3, dst).

🟠 **HIGH / perlu verifikasi:**

- `ALLOWED_HOSTS` default `*` (`common.py:99`), aman hanya jika proxy membatasi Host. Perlu cek `production.py`.
- **Object-level authorization / IDOR**, permukaan API besar (workspace/project scoping). Perlu audit tiap viewset apakah query difilter per-member. **Ini area risiko #1, belum diaudit per-endpoint.**

🟡 **MEDIUM:**

- Secret hardcoded: tidak ditemukan di settings (semua via env). File `.env` yang ter-track hanya **template** (`deployments/{aio,cli}/community/variables.env`) dgn nilai kosong/placeholder, bukan secret asli (diverifikasi). Scan menyeluruh frontend/test fixtures = TODO.
- `DEBUG` dari env int, pastikan compose prod `0`.

> **Tidak ada secret asli bocor** pada file yang dibaca; hanya template env berisi placeholder. Scan full-repo otomatis (gitleaks style) belum dijalankan, TODO.

---

## FASE 9, Kualitas & Operasional

- **Test backend:** pytest (`apps/api/pytest.ini`, `run_tests.py/sh`), 47 file test di `plane/tests/`. Coverage kasar belum diukur.
- **Test frontend:** vitest (`@vitest/coverage-v8` di catalog); `apps/live/tests`, `vitest.config.ts`. Cakupan belum diukur.
- **Lint/format:** oxlint + oxfmt (JS/TS) via lint-staged + husky pre-commit; ruff (Python, `pyproject.toml`). Type-check via `turbo check:types`.
- **Logging:** JSON logger (backend `python-json-logger`, celery `JsonFormatter` `celery.py`), winston (live).
- **Observability:** Scout APM + OpenTelemetry (backend), Sentry (frontend), PostHog analytics, health controller (live), telemetry metrics push (license).

---

## FASE 10, Katalog Fitur (produk)

Semua ✅ berdasarkan keberadaan model+view+store+components (fungsional penuh perlu runtime test):

✅ Workspaces · ✅ Projects · ✅ Issues/work items · ✅ Cycles · ✅ Modules · ✅ States/workflow · ✅ Labels · ✅ Estimates · ✅ Intake/inbox · ✅ Pages (collab docs) · ✅ Views/filters · ✅ Notifications (in-app+email) · ✅ Webhooks · ✅ Analytics/dashboard · ✅ Public deploy boards · ✅ Import/Export · ✅ Stickies · ✅ API tokens (REST v1) · ✅ AI assist · ✅ Instance admin · ✅ Multi-provider auth (Google/GitHub/GitLab/Gitea/email/magic).

Status ⚠️/❌ per-fitur butuh runtime test, belum dijalankan (audit read-only).

---

## Yang Belum Sempat Didalami (transparansi cakupan)

Depth-read yang **belum** dilakukan (prioritas untuk pass berikutnya):

1. **Enumerasi endpoint per-URLconf** (`plane/*/urls/*.py`) + method + permission class → paling penting utk audit IDOR/authz. _(FASE 4/8)_
2. **Field per-model** + `on_delete` + index + `base.py` (soft-delete/audit) → `plane/db/models/*`. _(FASE 5)_
3. **`packages/propel` (390 file, terbesar)** dan **`packages/editor` (226)**, belum dibuka sama sekali.
4. **`packages/{ui,types,services,constants,utils}`**, belum dibuka; cek apakah `types` di-generate dari OpenAPI (risiko drift).
5. **`apps/live` internal** (hocuspocus extensions, redis pubsub, pdf-export), hanya struktur.
6. **`plane/license` & `plane/space`**, belum dibuka (telemetry, instance admin, public board logic).
7. **Frontend routes + guards** (react-router config tiap app), belum dienumerasi.
8. **CI/CD** (`.github/workflows`), belum diverifikasi keberadaannya.
9. **Dockerfile/entrypoint (`bin/`) + deployments/{k8s,swarm,aio,cli}**, langkah build/deploy persis.
10. **Scan menyeluruh:** 13 TODO/FIXME backend belum dienumerasi; frontend belum discan; secret scan full-repo belum dijalankan.
11. **FASE 6.5 (trace fitur end-to-end sampai akar)**, belum ditulis; perlu ambil 3–5 fitur (mis. create issue, webhook delivery, auth/login, page collab) dan trace lintas layer dgn snippet.

> **Rekomendasi:** lanjut per-modul mengikuti prioritas #1–#2 (authz + skema) karena risiko keamanan tertinggi, lalu FASE 6.5 utk fitur kritikal. Bilang modul mana yang mau didahulukan.

---

---

# PASS 2, DEEP-DIVE

## DEEP-DIVE #1, Authorization / IDOR (FASE 4 + 8)

### Model authz: RBAC 2-layer

**Role** (`plane/app/permissions/base.py:12`, dan mirror di `db/models/project.py`):
`ADMIN = 20`, `MEMBER = 15`, `GUEST = 5`.

**Dua mekanisme paralel** (keduanya dipakai di codebase):

1. **Class-based `BasePermission`** (`plane/app/permissions/{project,workspace,page}.py`), dipakai via `permission_classes` (31 dari 60 file view). Cek `has_permission(request, view)`:
   - `WorkspaceMember`/`ProjectMember` filter `workspace__slug=view.workspace_slug`, `member=request.user`, `is_active=True`, `role__in=[...]`.
   - `SAFE_METHODS` (GET) → hanya cek membership; **filtering object-level "diserahkan ke queryset"** (komentar eksplisit `project.py:19` "Handle the filtering logic in queryset").
   - Kelas: `ProjectBasePermission`, `ProjectMemberPermission`, `ProjectEntityPermission`, `ProjectAdminPermission`, `ProjectLitePermission`; `WorkSpaceBasePermission`, `WorkspaceOwnerPermission`, `WorkSpaceAdminPermission`, `WorkspaceEntityPermission`.

2. **Decorator `@allow_permission(allowed_roles, level="PROJECT"|"WORKSPACE", creator=False, model=None)`** (`permissions/base.py:19`), dipakai per-method (38 dari 60 file view). Cek membership+role pada `kwargs["slug"]`/`kwargs["project_id"]`; opsi `creator=True` mengizinkan pemilik objek (`created_by=request.user`) meski bukan role cukup.

**Base viewset** (`plane/app/views/base.py:47`): default `permission_classes=[IsAuthenticated]`, `authentication_classes=[BaseSessionAuthentication]`, dan `get_queryset()` default = `self.model.objects.all()` (`base.py:60`).

### Titik kritikal IDOR

> Karena `BaseViewSet.get_queryset` default mengembalikan **`.all()`**, keamanan object-level **bergantung sepenuhnya pada tiap view meng-override `get_queryset` dengan filter `workspace__slug` + `project_id`**. Pola yang benar terlihat konsisten di `issue/base.py`:
>
> - `get_queryset` → `Issue.issue_objects.filter(project_id=self.kwargs["project_id"], workspace__slug=self.kwargs["slug"])` (`issue/base.py:206`).
> - tiap handler di-dekor `@allow_permission([...])` (`issue/base.py:84, 253, 392`).

**Cakupan (kuantitatif):** 60 file view; **38** pakai `allow_permission`, **31** pakai `permission_classes` override (banyak pakai keduanya). Cakupan tinggi, jarang ada view "telanjang".

### Temuan

| Sev                 | Lokasi                                                          | Temuan                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| ------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🟠 HIGH (PLAUSIBLE) | `plane/app/views/issue/comment.py:66`, `issue/sub_issue.py:205` | `Issue.objects.get(pk=issue_id)` diambil **tanpa** memverifikasi `issue.project_id == project_id`/`workspace__slug` URL. `@allow_permission` hanya memvalidasi membership pada `project_id` URL, bukan bahwa `issue_id` milik project itu. Potensi **cross-project IDOR**: member project A me-referensikan `issue_id` project B. Perlu verifikasi runtime apakah objek issue dipakai utk menulis (create comment/sub-issue) lintas project. |
| 🟡 MEDIUM           | `permissions/base.py:60` (`get_queryset` default `.all()`)      | Bukan bug sendiri, tapi _fail-open by default_, view baru yang lupa override `get_queryset` akan expose semua row. Disarankan default deny/scoped.                                                                                                                                                                                                                                                                                           |
| 🟢 INFO             | `permissions/workspace.py:22`                                   | `WorkSpaceBasePermission` mengizinkan `POST` (create workspace) utk semua user terautentikasi, by design (siapa pun boleh bikin workspace).                                                                                                                                                                                                                                                                                                  |
| 🟢 INFO             | `permissions/base.py` decorator                                 | Logika "workspace admin yang jadi anggota project boleh akses meski role project rendah" (`base.py:64`), eskalasi terkontrol, wajar.                                                                                                                                                                                                                                                                                                         |

**REST publik v1** (`plane/api/`): auth berbeda (API key + throttle `API_KEY_RATE_LIMIT=60/minute`). Permission class terpisah di `plane/api/`, belum dibaca detail (baca `plane/api/views/base.py` + permissions utk pass lanjutan).

**Rekomendasi audit lanjutan (belum dilakukan):** grep tiap `get_queryset` di 60 view utk memastikan **semua** memfilter `workspace__slug`; dan audit tiap `objects.get(pk=<child_id>)` apakah child divalidasi milik parent di URL (pola comment.py di atas mungkin berulang di link/reaction/attachment/relation).

---

## DEEP-DIVE #2, Skema DB per-model (FASE 5)

### Hierarki base class (`plane/db/mixins.py` + `db/models/base.py`)

```
TimeAuditModel      -> created_at (auto_now_add), updated_at (auto_now)          mixins.py:16
UserAuditModel      -> created_by, updated_by (FK User, SET_NULL, auto via crum) mixins.py:26
SoftDeleteModel     -> deleted_at (nullable); .delete() = set deleted_at         mixins.py:61
  SoftDeletionManager.get_queryset() -> filter(deleted_at__isnull=True)          mixins.py:56
AuditModel          = TimeAuditModel + UserAuditModel + SoftDeleteModel          mixins.py:85
BaseModel           = AuditModel + id: UUIDField(pk, default uuid4)              base.py:16
  ProjectBaseModel  = BaseModel + project(FK CASCADE) + workspace(FK CASCADE)   project.py:180
                      save() auto-set workspace = project.workspace             project.py:188
  WorkspaceBaseModel= BaseModel + workspace(FK CASCADE)                          workspace.py:185
ChangeTrackerMixin  -> lacak perubahan field (untuk activity feed)              mixins.py:92
```

**Invariant penting:**

- **PK = UUID** di semua model (bukan sequential int) → mengurangi enumerasi/IDOR tebak-id.
- **Soft delete default**, `deleted_at`; manager default menyembunyikan row terhapus. ⚠️ Model dengan manager kustom (mis. `Issue.objects` vs `Issue.issue_objects`) bisa meng-expose row soft-deleted jika query pakai manager yang salah (relevan dgn smell IDOR di comment.py yang pakai `Issue.objects`).
- **Scoping baked-in**, subclass `ProjectBaseModel` otomatis punya `project`+`workspace` dan menjaga konsistensi via `save()`. Ini memperkuat filtering per-tenant.
- **Audit otomatis**, `created_by`/`updated_by` via `django-crum` `get_current_user()` (`base.py:24`).

### Model inti & relasi (contoh dari `issue.py`, `db_table` eksplisit)

| Model                      | Tabel               | Relasi kunci                                                                          | on_delete                                                       |
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

> Pola `unique_together` selalu menyertakan `deleted_at` → memungkinkan re-create setelah soft-delete tanpa bentrok unique (idiom yang disengaja).

### Inventaris model (31 modul di `plane/db/models/`, 178 file)

`workspace, project, issue, issue_type, cycle, module, state, label, estimate, page, view, intake, draft, notification, webhook, asset, favorite, sticky, recent_visit, deploy_board (public share), api (token), device, session, social_connection, description, exporter, importer, integration/ (dir), analytic, user`.

Domain graph: **Workspace 1─* Project 1─* {Issue, Cycle, Module, State, Label, Page, View, Estimate, Intake}**; Issue _─_ {Label, Assignee(User), Cycle, Module}; scoping ganda project+workspace di tiap entity.

**Sumber kebenaran skema:** tunggal (Django ORM). 121 migrasi. Tipe frontend (`packages/types`) terpisah → risiko drift (lihat #4).

**Belum didalami:** field lengkap tiap model non-issue, index DB (selain unique_together), model `integration/` (dir), `user.py` (auth/permission fields), `deploy_board.py` (kontrol akses share publik, relevan keamanan).

---

## DEEP-DIVE #3, Trace fitur end-to-end (FASE 6.5)

### Trace A, Create Issue

```
UI: web issue create form (apps/web/core/components/issues/...)
  -> service: apps/web/core/services/issue/*.service.ts (axios POST)
  -> route: POST /api/workspaces/<slug>/projects/<project_id>/issues/  (plane/app/urls/issue.py)
  -> guard: @allow_permission([ROLE.ADMIN, ROLE.MEMBER])         issue/base.py:392
            (cek ProjectMember role di slug+project_id; GUEST tak boleh create)
  -> handler: IssueViewSet.create(request, slug, project_id)      issue/base.py:393
       project = Project.objects.get(pk=project_id)               issue/base.py:394
       serializer (IssueCreateSerializer) validasi payload
  -> model save: Issue (ProjectBaseModel) -> save() set workspace=project.workspace, created_by=user (crum)
  -> data store: tabel `issues` (+ IssueAssignee/IssueLabel M2M, IssueActivity)
  -> side-effect: issue_activities_task (async) rekam aktivitas; webhook_activity -> webhook_send_task
  <- response: serialized issue (JSON)
Edge/risiko: create pakai Project.objects.get(pk=project_id) tanpa slug, tapi decorator sudah
memvalidasi membership pada project_id URL -> aman. Cek: apakah assignee/label di payload
divalidasi milik project yang sama (belum diverifikasi).
```

### Trace B, Webhook delivery (SSRF-critical) ⭐

```
Trigger: perubahan model (issue/project/dst) -> webhook_activity()          webhook_task.py:393
  -> enqueue Celery: webhook_send_task (autoretry RequestException, backoff 600s, jitter)  :235
  -> handler: webhook_send_task(webhook_id, payload, ...)                     :242
  -> SSRF guard: pinned_fetch(webhook.url,
                    allowed_ips=WEBHOOK_ALLOWED_IPS,
                    allowed_hosts=WEBHOOK_ALLOWED_HOSTS)                       webhook_task.py:319
       -> resolve_and_validate(hostname): DNS resolve + tolak IP privat/loopback
          kecuali host/ip ada di allowlist                                    url_security.py:180
       -> PinnedIPAdapter: koneksi DIPAKU ke IP yang sudah divalidasi
          (get_connection_with_tls_context, hostname utk SNI/cert)            url_security.py:46,67
          -> mencegah DNS-rebinding TOCTOU (validasi vs koneksi tak bisa beda IP)
       -> redirect: pinned_fetch_following_redirects re-validasi TIAP hop, batas redirect  :225,264
  -> sukses -> save_webhook_log(status_ok)                                    :336
  -> RequestException -> save log + raise -> Celery retry                     :340
  -> gagal berulang -> send_webhook_deactivation_email + nonaktifkan webhook  :172
Kekuatan: mitigasi SSRF berlapis (allowlist + IP-pin + per-hop redirect check). Ini defense
kelas produksi, bukan sekadar cek "is private IP". Komentar kode eksplisit soal ancaman
"attacker swap in an IP after validation" (webhook_task.py:313).
```

### Trace C, Authentication (permukaan luas)

```
Routes (plane/authentication/urls.py):
  Email/password : /auth/sign-in, /sign-up, /sign-out, /email-check           :51-56,119
  Magic link     : /auth/magic-generate, /magic-sign-in, /magic-sign-up       :61-63
  Password mgmt  : /forgot-password, /change-password, /set-password          :122,138,139
  OAuth          : google, github, gitlab, gitea (+ /callback masing-masing)  :80-148
  Space (public) : /auth/spaces/sign-in, /sign-up, /sign-out                   :53-57
  CSRF           : /auth/get-csrf-token                                        :59

Flow magic-link:
  POST /auth/magic-generate -> generate token -> magic_link_code_task (email async, bgtasks)
  POST /auth/magic-sign-in  -> validasi token -> adapter (plane/authentication/adapter) -> buat sesi
Flow OAuth:
  GET  /auth/<provider>/           -> initiate (redirect ke provider, state)
  GET  /auth/<provider>/callback/  -> tukar code -> provider oauth class
       (plane/authentication/provider/oauth/{google,github,gitlab,gitea}.py) -> buat/link user

Auth = SessionAuthentication (cookie), bukan JWT untuk web (BaseSessionAuthentication, base.py).
REST v1 publik pakai API key terpisah. Rate limit: plane/authentication/rate_limit.py.
Password: validator Django + zxcvbn; reset TTL 3600s.
Catatan: commit terakhir memperbaiki TOCTOU race di InstanceAdminSignUp (GHSA-p548-28jp-wr4p).
Belum didalami: isi adapter/session, proteksi CSRF pada callback OAuth, validasi `next`/redirect.
```

---

## DEEP-DIVE #4, Frontend & Packages (FASE 7)

### Peta package internal (dependency berlapis)

```
@plane/types      (120 file, ZERO deps)  -> tipe TS murni: activity, ai, auth, cycle, issue, ...
@plane/constants  ────────────────────┐
@plane/utils      ────────────────────┤
@plane/hooks      ────────────────────┤
@plane/propel     (390, TERBESAR)  ────┼─> primitives/headless UI: accordion, avatar, badge,
   deps: @base-ui-components/react       │    button, calendar, charts, combobox, command(cmdk),
         @tanstack/react-table, framer   │    ... (design-system layer)
@plane/ui         (128)  ──────────────┼─> komponen shared tingkat lebih tinggi: auth-form,
   deps: propel + blueprintjs + atlaskit │    breadcrumbs, drag-handle, color-picker, ...
@plane/editor     (226)  ──────────────┼─> editor kolaboratif Tiptap/ProseMirror + Yjs
   deps: propel, ui, tiptap*, hocuspocus │    struktur: core/ + ce/ + ee/  (split CE/EE!)
@plane/services   (56)  ───────────────┘─> client axios per-domain (auth, cycle, issue, ...)
   deps: types + axios + file-type            dipakai app frontend utk panggil API
```

Lainnya: `@plane/i18n` (locales JSON + ICU), `@plane/logger`, `@plane/decorators`, `@plane/shared-state`, `@plane/tailwind-config`, `@plane/typescript-config`, `@plane/codemods` (jscodeshift migrations).

### Arsitektur CE/EE (Community vs Enterprise Edition)

Pola berulang: `apps/web/ce/` (components + store) vs `apps/web/core/`, dan `packages/editor/{ce,ee,core}`. **`ce/` = implementasi Community Edition** (open-source ini). Build Enterprise mengganti layer `ce`→`ee`. Artinya repo ini adalah **varian CE**; sebagian fitur EE hadir sebagai stub/interface di `ce`. (Konsisten dgn skill repo yang menyebut `plane-ee` & `plane-cloud`.)

### Frontend web (`apps/web/core`, 2.039 file)

| Layer           | Lokasi                     | Isi                                                                                                                                                                                                                        |
| --------------- | -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| State (MobX)    | `core/store/`              | root.store.ts → sub-store: issue/, cycle, module, project/, workspace/, page/, notification/, user/, member/, analytics, instance, theme, router, command-palette, power-k, timeline, sticky, favorite, estimates/, inbox/ |
| Service (axios) | `core/services/`           | ~30 service: ai, analytics, auth, cycle(+archive), module(+archive), issue/, project/, page/, file(+upload), workspace(+notification), instance, view, webhook, sticky, timezone, dashboard                                |
| Components      | `core/components/`         | ~55 domain: issues, cycles, modules, project, workspace, analytics, gantt-chart, editor, dropdowns, rich-filters, onboarding, settings, power-k (command palette), automation, web-hooks, ...                              |
| Layouts         | `core/layouts/`            | route guards / shell                                                                                                                                                                                                       |
| Hooks/lib       | `core/hooks/`, `core/lib/` | ,                                                                                                                                                                                                                          |

Data flow UI: komponen → MobX store (observer) → `@plane/services` / `core/services` (axios) → Django API. Fetch pakai **SWR** + store. Realtime (page/editor) → Hocuspocus provider → `apps/live`.

### Temuan frontend

| Sev       | Temuan                                                                                                                                                                                                                                                              |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 🟠 HIGH   | **`@plane/types` tanpa codegen** (script hanya `tsdown` bundle, tak ada openapi/generate, diverifikasi). Tipe TS di-maintain **manual** terpisah dari model Django → **risiko drift skema** nyata: perubahan model backend tak otomatis tercermin di tipe frontend. |
| 🟡 MEDIUM | Package `@plane/propel` (390 file) & `@plane/editor` (226) belum dibaca isi implementasinya, hanya inventaris komponen. Kompleksitas editor (Tiptap+Yjs+CE/EE) area risiko bug tinggi.                                                                              |
| 🟢 INFO   | Pemisahan store/service/component rapi (container/presentational + MobX). Konsisten dgn rule "many small files".                                                                                                                                                    |

**Belum didalami:** enumerasi route React Router per-app (react-router.config.ts), guard auth di layouts, isi implementasi propel/editor, `apps/admin` & `apps/space` internal, aksesibilitas/i18n coverage, bundle size aktual.

---

## STATUS AKHIR PASS 2

MODULE INDEX ter-update: authz ✅, skema DB ✅ (base+pola, field-detail 🟡), trace fitur ✅ (3 fitur), frontend/packages ✅ (arsitektur, implementasi-detail 🟡).

**Sisa deep-read (jika mau pass 3):** (1) enumerasi endpoint per-URLconf + verifikasi runtime IDOR smell di issue/comment,sub_issue,link,reaction,attachment; (2) field per-model non-issue + `deploy_board`/`user`/`api-token`; (3) implementasi `packages/propel`+`editor`; (4) `plane/license`+`plane/space`+`apps/live` internal; (5) `.github/workflows` isi + Dockerfile build steps; (6) secret scan otomatis full-repo + enumerasi 13 TODO backend.
