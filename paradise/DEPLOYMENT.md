# Production deployment, Paradise Task Tracker

Target: one office server (Linux) serving ~100 users. **No Kubernetes needed**,
Docker Compose is enough. K8s is only worth it if you need HA/autoscaling and an
ops team.

Shipping a release to the existing server: jump to
[Releasing a version to production](#releasing-a-version-to-production-runbook-for-agents).
Setting up a new server: start at [Server prerequisites](#server-prerequisites).

## Releasing a version to production (runbook for agents)

This section takes finished local work to the production server (`space`):
gates, commits, PR, merge, image build, deploy, proof. The rest of this file
covers setting up a server. An agent that is asked to ship ("yeet and deploy",
"rilis", "deploy to space") follows this section from top to bottom and stops
only on a red gate or in the cases listed under [Stop and ask](#stop-and-ask).

Everything below assumes `paradise/bin/rilis.sh` exists. Release always goes
through a pull request. Never push to `main` directly.

### Fixed facts

| Thing                     | Value                                                                                                                                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Repo                      | `CMMhero/paradise-plane`, a fork of `makeplane/plane`. Every `gh` call needs `-R CMMhero/paradise-plane`, because plain `gh` targets upstream.                                                                |
| Server                    | SSH alias `space` (tailnet `100.103.153.3`, user `it`, key `~/.ssh/space`). App directory `~/paradise-app`. The login shell there is fish.                                                                    |
| Images                    | Built by the `paradise-build` workflow on every push to `main`, pushed to `ghcr.io/<GHCR_OWNER>/plane-*` with the commit SHA and `latest` as tags.                                                            |
| `GHCR_OWNER`              | Required in `~/paradise-app/.env`, deliberately without a default.                                                                                                                                            |
| Version                   | One number everywhere, bumped with `pnpm version:bump`. Rules are in `AGENTS.md`, "Versioning (KEP-48)".                                                                                                      |
| Tags                      | `pX.Y.Z` (the `p` keeps ours apart from upstream `vX.Y.Z`), created only after the deploy succeeded.                                                                                                          |
| Required checks on `main` | `check:format`, `check:lint`, `check:types`, `Build packages`.                                                                                                                                                |
| Known red, not a gate     | `Lint API` (about 140 ruff errors already on `main`) and `React Doctor` errors about hydration or browser globals. `check:sync` (i18n) is not required but must pass: every new key goes into all 19 locales. |

### What is automatic

`rilis.sh <sha>` already does the following. Do not repeat any of it by hand.

| Step                                                                                                                                              | Done by                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| Refuse if `apps/api/plane/release_notes/<ver>.json` or the `### Version <ver>` heading in `CHANGELOG.md` is missing (`### Versi` is accepted too) | `rilis.sh` pre-flight               |
| Wait until the GHCR `latest` digest equals the commit's build                                                                                     | `tunggu-latest.sh`                  |
| `git pull` on the server, database backup, detached deploy                                                                                        | `rilis.sh` over `ssh space`         |
| `migrate` through `plane-migrator`, exit code checked                                                                                             | `deploy.sh`                         |
| `showmigrations --plan` inside the new `api`, migrate again if any `[ ]`                                                                          | `deploy.sh`                         |
| Post the release notes to every workspace's Changelog channel, fail loudly                                                                        | `deploy.sh` (`terbitkan_changelog`) |
| Health check, and the served `current_version` must equal the commit's version                                                                    | `deploy.sh` and `rilis.sh`          |

Never run `migrate` or `terbitkan_changelog` on the server by hand, and never
watch CI yourself with `gh run watch` or by polling `api.github.com`, `ssh space`
or GHCR during a deploy. Anonymous GitHub API limits are shared with the whole
office IP, and a false "CI failed" has cancelled a deploy before.

### Where you run it from

Two machines have shipped releases. The steps are the same, the setup is not.

**Windows laptop (Git Bash).** `rilis.sh` runs in Git Bash. The API test
environment lives in WSL (`~/plane-testenv`). Keep `~/plane-testenv` inside
single quotes when you call `wsl -d Ubuntu -- bash -c '...'`, otherwise Git Bash
expands `~` to the Windows home.

**Linux dev box (Oracle).**

- Create the `space` alias in `~/.ssh/config` (host, user and key above).
- `space` runs Tailscale SSH in check mode. A new connection prints a
  `https://login.tailscale.com/a/...` URL and hangs until the user approves it
  in a browser. Start one `ssh space 'echo APPROVED'` in the background, give
  the URL to the user, and wait for it to exit. Later connections then work.
  The approval expires between sessions, so expect to ask again.
- `tunggu-latest.sh` calls `docker manifest inspect`, and docker needs sudo on
  this box. Put a wrapper first on `PATH` when you run `rilis.sh`:

  ```bash
  mkdir -p /tmp/dockerwrap
  printf '#!/bin/sh\nexec sudo -n docker "$@"\n' > /tmp/dockerwrap/docker
  chmod +x /tmp/dockerwrap/docker
  PATH=/tmp/dockerwrap:$PATH bash paradise/bin/rilis.sh "$sha"
  ```

- The local user has no permission on the docker socket, so the API pytest suite
  cannot run here. Say so in the PR instead of claiming it passed. CI does not
  run pytest either.
- Work from a fresh worktree off `origin/main`, never from a long-lived
  checkout. An old checkout drifts for weeks, and the files you read in it are
  not what `main` has. `scripts/` is gitignored, so `scripts/bump-version.mjs`
  exists only in the main checkout: copy it into the worktree before bumping.
- Run `pnpm install --offline --frozen-lockfile` once in a new worktree (about
  15 seconds from the store). Pushes from a worktree with a fresh install are
  fast. A push from a stale checkout has hung in `.husky/pre-push`.

### 1. Release gate (before any commit)

1. Pick the bump level from `git log --oneline <last p-tag>..HEAD` plus the
   working diff, using `AGENTS.md`. A branch that already bumped at that level
   or higher does not bump again.
2. `pnpm version:bump <level>`, then `pnpm version:bump` shows no `!`.
3. `CHANGELOG.md` has `### Version <ver>` at the top, dated, with the reason for
   the level and any operator step.
4. `apps/api/plane/release_notes/<ver>.json` exists, with user-facing English
   entries typed `Added`, `Changed` or `Fixed`. No file means no Changelog post.
   If it is missing, draft it from the diff and the CHANGELOG entry in the voice
   of the existing files.
5. `ssh space "grep -c '^GHCR_OWNER=.' ~/paradise-app/.env"` prints `1`. A `0`
   means `rilis.sh` cannot find the images: stop and ask.

### 2. Checks

The repo hooks run part of this on their own (`paradise/bin/cek-lokal.sh`):
pre-commit compares ruff errors per file against `HEAD` and runs
`makemigrations --check` when models are staged, pre-push runs the turbo format,
lint and types checks plus the release-notes check. A hook failure is a red gate.
Fix it. Never use `--no-verify` or `PARADISE_LEWATI_CEK=1`.

Run these yourself before committing, in parallel:

| Check                   | Command                                                                                                            | Red means                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| Format, lint, types     | `pnpm check`                                                                                                       | Fix it. CI runs `check:format`, and oxfmt misses have broken releases. |
| i18n                    | `pnpm --filter @plane/i18n check:sync`                                                                             | A key is missing in some locale. Other locales hold English copies.    |
| Missing migration files | `manage.py makemigrations --check --dry-run --settings=plane.settings.test` through `~/plane-testenv/run.sh` (WSL) | A model changed without a migration. Write it.                         |
| API lint                | `uvx ruff check apps/api --statistics`                                                                             | Compare counts with `main`. Only new errors are yours.                 |
| API tests               | `~/plane-testenv/run.sh -m pytest plane/tests -q -p no:cacheprovider --create-db` (WSL)                            | Compare the failure list against `main`, not against zero.             |

`manage.py` without `--settings` loads production settings and dies on the
`file` log handler. `--create-db` is mandatory after any migration.

A red check: fix it and re-run that check. Only when something is red, get the
baseline with `git worktree add ../_base origin/main`, run the same command
there, and remove the worktree. A failure present on both is baseline: list it
in the PR and move on. Stop only when the fix lies outside the branch's scope.

### 3. Commit, PR, merge

1. Group commits by logical change, with explicit paths and never `git add -A`.
   Subjects are `type: imperative summary` (Conventional Commits), at most 72
   characters. Tests ship with the code they cover, the version bump and the
   changelog each get their own commit (`chore(release): bump version to X.Y.Z`,
   `docs(release): add X.Y.Z changelog and release notes`). Commits carry no
   `Co-Authored-By` or "generated by" lines.
2. Before the first commit, snapshot the tree:
   `git update-ref refs/backup/<ver> $(git stash create)` plus a tar of
   `git ls-files -o --exclude-standard`. lint-staged stashes the unstaged tree on
   every commit, and a failed restore once wiped 689 files. Its
   `oxlint --deny-warnings` also rejects warnings that `main` already has in any
   staged file, so fix those first. Do not run `pnpm check` while committing: the
   stash removes your changes from under it.
3. `git push -u origin <branch>`.
4. `gh pr create -R CMMhero/paradise-plane --base main ...`. Write the body to a
   file and pass `--body-file`. A quoted heredoc keeps backslashes, so
   `\`` ends up literally in the PR text.
5. Wait for the required checks. In T3 Code call `watch_pull_request` and end the
   turn: it wakes the thread when they pass. Elsewhere run
   `gh pr checks <n> -R CMMhero/paradise-plane --watch --required`.
6. `gh pr merge <n> -R CMMhero/paradise-plane --merge`. Always a merge commit.
   Squash erases the grouped commits.
7. `git fetch origin main`, then `sha=$(git rev-parse origin/main)`.

On every wake, run `gh pr checks <n> -R CMMhero/paradise-plane --required` and
decide:

| State                           | Action                                                                                                              |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| The user already merged the PR  | Go to step 7 and deploy. Do not wait for another prompt.                                                            |
| All four required checks pass   | Merge, then deploy in the same turn.                                                                                |
| A required check failed         | Fix, push, end the turn. The watch stays on.                                                                        |
| Only non-required checks failed | Act on real findings (for example CodeQL alerts in files this PR touches), ignore the known-red ones, end the turn. |
| Required checks still pending   | End the turn.                                                                                                       |

The go-ahead for a major or data-reshaping deploy is asked once, before the first
commit. A wake never asks again.

The image build ignores pushes that touch only `paradise/**` or `*.md`. Such a
merge builds no image, so `rilis.sh` would wait until it times out. Deploy the
scripts alone instead: `ssh space 'cd ~/paradise-app && git pull --ff-only'`.

### 4. Deploy

```bash
bash paradise/bin/rilis.sh "$sha"
```

Run it in the background and wait for it to exit (T3 Code: `t3_background_wait`
with the task id). It takes 25 to 60 minutes: about 12 for the build and 10 to
14 for `compose pull`. `== SELESAI: <ver> live di space ==` is the success line.
Anything else is a failure: read the server log path it printed.

### 5. Prove and record

On `space` the shell is fish. Anything with `$`, double quotes or `&&` goes
through bash: `ssh space 'bash -s' <<'EOF' ... EOF`.

1. `ssh space 'cd ~/paradise-app && ./paradise/bin/status.sh'`. "minio tidak
   menjawab" is a known false alarm (the minio image has no `curl`).
2. `ssh space 'docker ps --format "{{.Names}} {{.Status}}"'`. The `api` and `web`
   containers must be minutes old. Hours old means the deploy pulled nothing.
3. The deploy log shows `Migrasi lengkap` and a `changelog:` line. `0 post(s)` is
   fine when the new `api` already posted on start. Confirm the card exists with
   `PesanLangsung.objects.filter(jenis="changelog")` in
   `docker exec api python manage.py shell`.
4. Only now: `git tag p<ver> "$sha" && git push origin p<ver>`. A tag marks what
   is live.
5. Record the release in the project vault (`05-Task/Papan Task.md`, plus any new
   trap in `04-Operasional/Jebakan & Pelajaran.md`). The vault is a Windows path
   and is not reachable from the Linux box: say what still needs writing.

Report: PR URL, version, merge sha, the deploy result line, the changelog post
count, and the browser note that an old UI after the deploy is the service
worker (`Ctrl+Shift+R`).

To go back to an earlier version, see [Rollback](#cicd).

### Do not

| Thought                                     | Reality                                                                 |
| ------------------------------------------- | ----------------------------------------------------------------------- |
| "The user is in a hurry, skip `pnpm check`" | CI fails on format and the deploy waits on a build that never ships.    |
| "Lint API is red, so I cannot merge"        | It is red on `main` too. Merge on the four required checks.             |
| "Squash keeps `main` tidy"                  | History is the grouped commits. Merge commit.                           |
| "Tag right after the merge"                 | Tag after `SELESAI` only.                                               |
| "A failure woke me, end the turn"           | Read all checks first. If the required ones pass, merge and deploy now. |
| "The user merged, so they will deploy"      | A merge by the user still means you deploy.                             |
| "`SEHAT` means it worked"                   | Only `SELESAI` plus fresh container ages does.                          |
| "38 tests fail, ship anyway"                | Ship only if the same 38 fail on `main`.                                |
| "`GHCR_OWNER` is empty, I will hardcode it" | Ask the user. The empty default is on purpose.                          |

### Stop and ask

- A migration reshapes or deletes existing data (major bump, operator step).
- A gate is red and the fix lies outside the branch's scope.
- `GHCR_OWNER` is empty in `~/paradise-app/.env` on `space`.

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
