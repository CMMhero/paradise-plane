# Production deployment, Paradise Task Tracker

Target: one office server (Linux) serving ~100 users. **No Kubernetes needed**,
Docker Compose is enough. K8s is only worth it if you need HA/autoscaling and an
ops team.

## Server prerequisites

- Docker Engine + Compose plugin
- 4 vCPU / 8 GB RAM minimum (more if the collaborative editor gets busy)
- Enough disk for Postgres + MinIO uploads + backups
- A domain or static LAN IP for `APP_DOMAIN`

## Steps

1. **Clone this repo** onto the server and check out the `main` branch.
2. **Configure env:** `cp paradise/.env.example .env`, then fill in every `<GANTI>`.
   Go through [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md), don't skip it.
3. **Pick a compose setup:**
   - **Recommended, CI-built images:** `./paradise/bin/deploy.sh`. The
     `paradise-build` workflow builds 6 images from the office's custom code on
     every push to `main` and pushes them to GHCR. The server just pulls them.
     The server doesn't need to build (saves CPU/RAM and avoids long downtime).
     See [CI/CD](#cicd) below.
   - Build from source (if CI is down or the server is air-gapped):
     `docker compose -f docker-compose.yml up -d --build`
   - Or the upstream prebuilt images (see `deployments/cli/community/`, which has
     `*_REPLICAS` knobs).
4. **Migrations and verification:** the `api` container runs migrations on start.
   Check with `paradise/bin/healthcheck.sh`.
5. **HTTPS:** set `SITE_ADDRESS=your-domain` + `CERT_EMAIL` and Caddy handles the
   certificate automatically. For a LAN without a domain, stay on HTTP at port 80.
6. **Public address and LAN address together.** If the server is reached through
   a domain and also through an IP, set this in `apps/api/.env` (the one the
   `api` container reads) and in the root `.env`:

   ```
   WEB_URL=https://your-domain
   APP_BASE_URL=https://your-domain
   ADMIN_BASE_URL=https://your-domain
   SPACE_BASE_URL=https://your-domain
   CORS_ALLOWED_ORIGINS=https://your-domain,http://server-IP
   SITE_ADDRESS=your-domain, http://server-IP
   ```

   `ADMIN_BASE_URL` and `SPACE_BASE_URL` hold the origin only, without
   `/god-mode` or `/spaces`. Don't set them to an IP. A God Mode login from the
   domain would be redirected to the IP, where the session cookie doesn't exist.
   The API now sends God Mode and space logins back to the address the browser is
   currently using, as long as that address is listed in one of the variables
   above, so the IP still works from the LAN. `deploy.sh` warns if
   `ADMIN_BASE_URL`/`SPACE_BASE_URL` have a different origin from `WEB_URL`. Env
   changes are only picked up after the `api` container is recreated
   (`docker compose up -d api`).

## CI/CD

The flow is deliberately **push images, pull manually**. A LAN server doesn't
need to open SSH to the internet, and nothing restarts suddenly during working
hours.

| Stage  | Where                             | What happens                                                                                                  |
| ------ | --------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Build  | GitHub Actions (`paradise-build`) | On every push to `main`: build 6 images, push to `ghcr.io/<repo-owner>/plane-*`, tags = commit SHA + `latest` |
| Deploy | Server, manual                    | `./paradise/bin/deploy.sh` → `git pull` + `compose pull` + `up -d` + healthcheck                              |

**The GHCR namespace follows the repo owner.** The workflow derives it from
`GITHUB_REPOSITORY_OWNER` and lowercases it, so nothing needs editing when the
repo is moved or forked. On the server side, the value comes from `GHCR_OWNER`
in `.env`, and that variable is required, with no default.

**Warning: GHCR packages do NOT move with the repo.** Packages belong to the
account namespace, not to the repo. The correct order for a move: move the repo,
let CI rebuild all the images in the new namespace, confirm the `latest` tag is
there, run `docker login ghcr.io` on the server with a token that can read it,
and **only then** set `GHCR_OWNER` in the server's `.env`. Doing it the other way
round makes `docker compose pull` fail and the release aborts. The running app
doesn't go down with it, because `deploy.sh` uses `set -e` and stops before
touching the containers that are serving.

**One-time setup, after the workflow's first run:** GHCR packages are private by
default even if the repo is public. Open the repo's `/pkgs` page → each package →
_Package settings_ → _Change visibility_ → **Public**. Without this, `docker pull`
on the server fails with a 401. (Alternative: `docker login ghcr.io` on the
server with a PAT scoped `read:packages`.)

**Rollback.** Every build has a commit SHA tag, so going back to an old version
doesn't need a rebuild:

```bash
APP_RELEASE=<old-git-sha> ./paradise/bin/deploy.sh
```

Keep `APP_RELEASE` in `.env` to pin it permanently. Clear it to go back to
following `latest`.

**If you later want it fully automatic**, `deploy.sh` already exits non-zero when
the healthcheck fails, so you can put it in cron (e.g. `0 2 * * *`) with no code
changes.

## Other sites on the same proxy

The proxy also serves sites outside Task Tracker (currently `cipl-saipem`). The
site files are in `paradise/sites/*.caddy`, imported by `apps/proxy/Caddyfile.ce`,
and that folder is mounted into the proxy as `/etc/caddy/sites`. How to install
one and what not to do are in [`sites/README.md`](sites/README.md).

Things to remember when deploying:

- `deploy.sh` doesn't touch that folder. `*.caddy` files are ignored by git, so
  `git pull` doesn't either.
- A regular deploy doesn't recreate the proxy, so those sites don't go down. The
  one exception is the first deploy after this change, because the Caddyfile and
  its mount changed. That recreates ALL services once, so do it during a quiet
  period.
- Pasting an `import` or a site block straight into the Caddyfile in the running
  container makes the next deploy recreate the proxy and wipe the pasted lines.
  Always go through the folder.

## Scaling to ~100 users

Raise the worker/web replicas to match the load (the `*_REPLICAS` env on the
community compose), and move Postgres to a fast volume/disk. Enable a read
replica only when heavy queries start to show.

## Backup and restore

Schedule `paradise/bin/backup-db.sh` through daily cron. Also keep the contents
of the MinIO bucket. Test restores regularly. A backup that has never been
tested is not a backup.
