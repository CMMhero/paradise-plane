# GitHub repository rules

Target repo: **`NomaX-Studio-Indonesia/Nomaden`**.

The goal fits in one sentence: no change reaches `main` without someone else
reading it first.

## Status as of 26 August 2026: the gate is NOT active

Don't read this document and assume `main` is protected. It isn't. Right now
**9 collaborators, 7 of them with write access, can still `git push` straight to
`main`** without anyone reading it.

The cause is the account plan, not a wrong configuration. When we tried to set it
up, GitHub answered plainly:

```
Upgrade to GitHub Pro or make this repository public
to enable this feature. (HTTP 403)
```

Rulesets and branch protection for **private** repos are only available on
GitHub Team or Enterprise. The decision taken: **put it off for now and follow
the discipline by hand.**

### What is actually active right now

| Item                                                                                   | Status         |
| -------------------------------------------------------------------------------------- | -------------- |
| Squash merge only, merge commits and rebase turned off                                 | active         |
| Branches deleted automatically after merge                                             | active         |
| Squash commit title follows the PR title                                               | active         |
| Issues on, blank issues off, everything goes through templates                         | active         |
| Pull Request template                                                                  | active         |
| `CODEOWNERS` points to `@ptnomaxstudio-blip`, and that account is an admin on the repo | active         |
| **PR required, review required, force-push blocked**                                   | **NOT active** |

### Interim agreement, since nothing enforces it

1. Every change goes through a branch and a Pull Request. Nobody pushes to `main`.
2. Nobody merges their own PR.
3. Ask `@ptnomaxstudio-blip` for review before merging.
4. Never force-push to `main`.

Those four lines are not guarded by a machine. If someone forgets, nothing will
reject it, nothing will warn, and it will be noticed later.

## How to turn it on later

Once the organization moves up to GitHub Team, one command is enough:

```bash
gh auth login                          # once per machine
paradise/bin/atur-github.sh            # targets NomaX-Studio-Indonesia/Nomaden
paradise/bin/atur-github.sh owner/repo # or another repo
```

It is safe to run repeatedly. A ruleset with the same name is updated, not
duplicated. The script stops with a clear message if the plan still doesn't
support it.

## What applies once the gate is active

| Rule                                       | Practical effect                                                       |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| Pull Request required                      | A direct `git push` to `main` is rejected, for everyone                |
| 1 Code Owner approval required             | Only `@ptnomaxstudio-blip`, per the `CODEOWNERS` file at the repo root |
| Approval dismissed on new commits          | A reviewer can't "approve, then have things added quietly"             |
| Last pusher can't approve                  | You can't approve your own PR                                          |
| All review comments must be resolved       | No note is left hanging open                                           |
| 4 status checks must be green              | `check:format`, `check:lint`, `check:types`, `Build packages`          |
| Branch must be up to date with `main`      | Avoids a merge that passes tests but breaks once combined              |
| Force-push blocked                         | For everyone, **including admins**                                     |
| Deleting the `main` branch blocked         | Same                                                                   |
| Linear history                             | No branching merge commits                                             |
| Squash merge only                          | One PR becomes one commit on `main`, easy to read and revert           |
| Branches deleted automatically after merge | The branch list doesn't pile up                                        |

**There are no `bypass_actors`.** This is a deliberate choice. Even the repo
owner can't get around it. If you ever end up truly stuck, delete the ruleset
through Settings. Don't add a quiet exception that then gets forgotten.

## Day-to-day workflow after this

```bash
git switch -c fix/short-name
# ... do the work ...
git push -u origin fix/short-name
gh pr create            # or use the link that appears after the push
```

Then ask for review, wait for green, and merge with squash.

**This also applies to Nomaden updates from the Paradise repo.** The old flow,
which created a fresh root commit and then force-pushed, can no longer be used,
and that is on purpose: every force-push forces everyone to run
`git reset --hard` and risks wiping their local work. Nomaden updates are now
ordinary commits through a PR, and the team just runs `git pull`.

## Why only four status checks are required

`Lint API` and `check:sync` are deliberately **not** required even though both
exist. The reason is technical, not a matter of taste: both workflows use a
`paths` filter, so they don't run for a PR that doesn't touch `apps/api/**` or
`packages/i18n/**`.

A required status check that never triggers **is not counted as failed**. It
hangs in pending forever, and the PR can never be merged. Both still run and
still show on the PR page, they just don't block.

If you ever want to require both, remove the `paths` filter first.

## If the script fails

**Private repo on the Free plan.** This is what is happening now, confirmed
directly by GitHub, not a guess. Rulesets and branch protection for private
repos are only available on GitHub Team or Enterprise. Three ways out:

1. Move the organization up to GitHub Team. This is the only way to get a review
   gate without opening the code to the public.
2. Make the repo public. **Not** before every `.env` file is removed from git
   history and every secret in them is rotated. This repo holds production
   credentials that are in use right now: Django `SECRET_KEY`, the Postgres
   password, RabbitMQ, MinIO, LiveKit, TURN, and SMTP. Removing them from history
   is a job of its own, not one click. See
   [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md).
3. Follow the discipline by hand. **This is the one chosen for now**, see the
   status section at the top of this document.

**Not an admin.** A ruleset can only be set by a repo admin. The script stops
early and says so.

## Files that support these rules

| File                                                     | Role                                                                                                                                                                        |
| -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CODEOWNERS`                                             | Decides who must approve. It used to list seven upstream Plane maintainers who have no access to this repo; if that list had been left in place, no PR could ever be merged |
| `.github/pull_request_template.md`                       | PR skeleton, including a checklist to go through before asking for review                                                                                                   |
| `.github/ISSUE_TEMPLATE/bug-report.yaml`                 | Bug report, forces the steps to reproduce to be filled in                                                                                                                   |
| `.github/ISSUE_TEMPLATE/feature-request.yaml`            | Feature request, asks about the problem first, not the solution                                                                                                             |
| `.github/ISSUE_TEMPLATE/config.yaml`                     | Turns off blank issues so everything goes through a template                                                                                                                |
| `.github/workflows/pull-request-build-lint-web-apps.yml` | Source of the four required status checks                                                                                                                                   |
