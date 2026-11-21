# NOTICE, Paradise Task Tracker

**Paradise Task Tracker** is an internal office deployment based on **Plane
Community Edition**.

- **Upstream:** https://github.com/makeplane/plane
- **License:** GNU AGPL-3.0 (see `LICENSE.txt`, unmodified)
- **Copyright of the application code:** © Plane (makeplane) and its contributors.

## What this fork adds

This fork **does not rewrite the Plane application**. The core of the app (work
items, cycles, modules, views, projects, the collaborative editor) remains
upstream's.

On top of it, this fork adds **eight capabilities that don't exist upstream**,
built from scratch: database models, migrations, API endpoints, permission
rules, and the interface.

| #   | Capability                                                                                                                 | Main traces                                                                                                        |
| --- | -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | **Time Tracking**, worklog per work item, edit-own permission                                                              | `IssueWorkLog`, `/work-logs/`                                                                                      |
| 2   | **Work Item Types & Custom Properties**, 6 field types, typed validation on the server                                     | `IssueType`, `IssueProperty`, `IssuePropertyOption`, `IssuePropertyValue`                                          |
| 3   | **Templates & Recurring Issues**, recurring scheduling via Celery beat                                                     | `IssueTemplate`, `RecurringIssue`, `plane/bgtasks/recurring_issue_task.py`                                         |
| 4   | **Workspace Wiki Phase A**, every attachment type up to 100 MB + file nodes in the editor with previews                    | `asset/v2.py`, `packages/editor/.../custom-file/`                                                                  |
| 5   | **Wiki Phase B, per-folder ACL**, top-level folders owned by a division; enforced in REST **and** the collaboration server | `WikiGovernedProject`, `WikiFolderAccess`, `utils/wiki_access.py`, `page/can_edit.py`, `apps/live/src/lib/auth.ts` |
| 6   | **Wiki Phase C, nested page tree**                                                                                         | `page/base.py` (opt-in `?sub_pages=true`)                                                                          |
| 7   | **Division Dashboard + time report CSV export**                                                                            | `workspace/paradise_dashboard.py`                                                                                  |
| 8   | **Initiatives**, cross-division workspace goals with progress rollup                                                       | `Initiative`, `InitiativeProject`                                                                                  |

Plus **Audit Logs**: actor recording on access and content models, with an
admin-only read API (`workspace/audit_log.py`), using `django-auditlog`. See the
library table below.

Plus an office operations layer:

- Configuration and environment templates for the office deployment (`paradise/`)
- Documentation for deploy, security, and upgrades
- Helper scripts (dev up, DB backup, healthcheck, scheduled task registration) in
  `paradise/bin/`
- A CI/CD pipeline to GHCR + deploy and rollback scripts per commit SHA
- A rebrand of the app name to "Paradise Task Tracker"

> **Rebrand ≠ removing attribution.** What was removed from the interface is
> upstream's **product brand** (name, logo, promotional links, calls to
> subscribe to a paid tier). AGPL-3.0 grants no trademark rights, and a modified
> fork that keeps calling itself "Plane" is actually riskier. What **is kept**
> is the legal attribution: the copyright headers in source files,
> `LICENSE.txt`, and this file.

## AGPL-3.0 obligations

Because of AGPL-3.0, when this service is accessed over a network by users, the
source code (including modifications) **must remain available** to them. Don't
delete `LICENSE.txt` or this file.

## Third-party libraries added by this fork

The office's extra features use the open-source libraries below. Copyright and
license belong to their respective authors. The license text is distributed with
the package (`pip`) and must not be removed.

| Library                                                        | Feature                        | License |
| -------------------------------------------------------------- | ------------------------------ | ------- |
| [django-auditlog](https://github.com/jazzband/django-auditlog) | Audit trail (who changed what) | MIT     |
