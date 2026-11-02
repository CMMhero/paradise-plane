# Agent Development Guide

## Read this first, the project brain

This repository is a fork of `makeplane/plane`. The reasoning behind every
custom change lives outside the code, in an Obsidian vault:

```
D:\4. SOURCE CODE (DGM)\Brain\Projects\Paradise Task Tracker\
```

Plain Markdown, readable without Obsidian. Before planning any change, read:

| File                                             | Why                                                                  |
| ------------------------------------------------ | -------------------------------------------------------------------- |
| `04-Operasional/Jebakan & Pelajaran.md`          | Failures already paid for. Do not rediscover them.                   |
| `01-Proyek/Keputusan & Kebijakan.md`             | Decisions and their rationale (KEP-nn). Do not silently reverse one. |
| `04-Operasional/Bug Diketahui.md`                | Open bugs and risks (BUG-nn, RISK-nn).                               |
| `02-Teknis/Kode Kustom Kita.md`                  | Which files diverge from upstream Plane.                             |
| `05-Task/Papan Task.md`                          | What is actually being worked on, in priority order.                 |
| `02-Teknis/Celah Fitur & Referensi Eksternal.md` | **License limits.** Read before planning any large feature.          |

Two rules:

- **Record what you change.** New decision, bug, or trap discovered → write it
  into the vault in the same session. An unrecorded finding is a finding lost.
- **The vault wins.** If this file and the vault disagree, the vault is newer.

## Versioning (KEP-48)

Every change that reaches the app gets a version bump in the same branch. The
Paradise version is our own line. It does not follow upstream Plane tags
(`v1.4.x`).

**One version, everywhere.** The root `package.json` and every workspace under
`apps/` and `packages/` carry the same number (`packages/decorators` is the
only exception). The sidebar's "Versi" label reads `instance.current_version`,
which `register_instance` takes from `apps/api/package.json`. If the workspaces
drift from the root, production shows the wrong number. Never edit the numbers
by hand:

```
pnpm version:bump              # list versions, "!" marks drift
pnpm version:bump patch        # 2.0.0 -> 2.0.1
pnpm version:bump minor        # 2.0.0 -> 2.1.0
pnpm version:bump major        # 2.0.0 -> 3.0.0
pnpm version:bump 2.3.0        # exact
```

**Which part to bump.** Compare against the last released version (the last
`chore(release)` / `rilis x.y.z` commit or `CHANGELOG.md` entry), not against
the last commit. Take the highest level that applies:

| Bump      | When                                                                                                                                                                                                                                            | Commit signal                                |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| **MAJOR** | The deploy needs an operator step, or users lose something: a data migration that reshapes existing records, a removed page/menu/endpoint, a renamed or newly required env var, changed permissions semantics, a reorganised org/project model. | `feat!:` / `fix!:` / `BREAKING CHANGE:` body |
| **MINOR** | A new user-visible feature, setting, page, endpoint, notification, or an additive migration (new table/column with a default). Old data and config keep working.                                                                                | `feat:`                                      |
| **PATCH** | A bug fix, copy/i18n/style tweak, performance work, or refactor with no behaviour change.                                                                                                                                                       | `fix:` / `perf:` / `refactor:` / `style:`    |
| none      | Only docs, tests, CI, or agent files. Nothing in the built images changes.                                                                                                                                                                      | `docs:` / `test:` / `ci:` / `chore:`         |

Rules:

- **Bump once per release, not once per commit.** Several `feat:` commits on one
  branch add up to a single minor bump. Unreleased work only escalates: if the
  branch already bumped minor and a breaking change lands, move to the next
  major. Never bump twice at the same level.
- **A patch only follows a release.** `x.y.1` means `x.y.0` shipped and this
  fixes it. The first version after a big change is always `x.0.0` or `x.y.0`.
- **Same pass:** bump, add a dated `### Versi x.y.z` entry at the top of
  `CHANGELOG.md` explaining why that level was chosen, and call out operator
  steps for a major. After merge, tag `pX.Y.Z` (the `p` prefix keeps our tags
  apart from upstream `vX.Y.Z`).
- Mark breaking commits with `!` (`feat(api)!: ...`) so the next bump can be read
  straight off `git log --oneline <last-release>..HEAD`.

## Commands

- `pnpm dev` - Start all dev servers (web:3000, admin:3001)
- `pnpm build` - Build all packages and apps
- `pnpm check` - Run all checks (format, lint, types)
- `pnpm check:lint` - OxLint across all packages, including the `@shadcn/lint`
  design-system plugin (`jsPlugins` in the root `.oxlintrc.json`)
- `pnpm check:types` - TypeScript type checking
- `pnpm fix` - Auto-fix format and lint issues
- `pnpm turbo run <command> --filter=<package>` - Target specific package/app
- `pnpm --filter=@plane/ui storybook` - Start Storybook on port 6006

After making changes, run `pnpm check:lint` and fix all errors. Each package
has a `--max-warnings` budget equal to its current warning count; new code must
not raise it.

`@shadcn/lint` (Oxlint 1.80+ required, we pin 1.90) is registered with no
`shadcn/*` rules enabled yet. Rules go in the `rules` block of the root
`.oxlintrc.json`; components from `@plane/propel` and `@plane/ui` are
recognised through `settings.shadcn.componentImports`. Rule list:
https://github.com/shadcn-ui/lint/blob/main/README.md#rules

## Code Style

- **Imports**: Use `workspace:*` for internal packages, `catalog:` for external deps
- **TypeScript**: Strict mode enabled, all files must be typed
- **Formatting**: oxfmt, run `pnpm fix:format`
- **Linting**: OxLint with shared `.oxlintrc.json` config
- **Naming**: camelCase for variables/functions, PascalCase for components/types
- **Error Handling**: Use try-catch with proper error types, log errors appropriately
- **State Management**: MobX stores in `packages/shared-state`, reactive patterns
- **Testing**: All features require unit tests, use existing test framework per package
- **Components**: Build in `@plane/ui` with Storybook for isolated development

## Backend tests (Docker)

The Django/pytest suite for `apps/api` runs in an isolated stack defined by `docker-compose-test.yml` at the repo root.

Prereq (once): `./setup.sh`, generates `apps/api/.env` from `.env.example`.

- Full suite: `docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests`
- Subset: `docker compose -f docker-compose-test.yml run --rm api-tests pytest -m unit`
- Teardown: `docker compose -f docker-compose-test.yml down -v`

See `apps/api/tests/RUNNING_TESTS.md` for the full walkthrough and troubleshooting; see `apps/api/tests/TESTING_GUIDE.md` for test conventions and fixtures.
