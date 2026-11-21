# SaaS runbook: onboarding customers, changing tiers, suspending

An operations document. Not a plan, not a design. It covers the steps you can
actually run today, plus what does **not** exist yet and has to be done by hand.

The architecture lives in `plane/db/models/plan.py`, `plane/utils/plan_limits.py`,
`plane/control/models.py`, and `plane/utils/workspace_transfer.py`. The header of
each file explains the reasoning.

---

## Quick map

```
OWNER deployment        ENABLE_CONTROL_PLANE=1
                        company, subscription, instance and usage tables
                        /control/ routes

FREE pool               one deployment, many workspaces
                        every free account gets one workspace
                        four limits active

PAID instance           one deployment + one database per company
                        ENABLE_CONTROL_PLANE=0
                        sends a heartbeat to the owner every hour

SELF-hosted             owned by Enterprise customers, no heartbeat at all
```

The tier attaches to the **workspace**, not the instance. A workspace with no
`WorkspacePlan` row counts as free, so no backfill is required anywhere.

---

## 0. Once per host: bring up the shared stack

This comes before everything else. It creates the `nomaden_saas` network and the
proxy container, and `tenant-up.sh` refuses to run if either is missing.

```bash
# This repo's GHCR packages are PRIVATE. Without this step `up -d` fails with
# `denied`, and the message points at the image, not at the missing credentials.
echo "$GHCR_TOKEN" | docker login ghcr.io -u <account> --password-stdin

mkdir -p /srv/caddy/tenants
docker compose -p nomaden -f docker-compose-shared.yml up -d
```

The token only needs the `read:packages` scope. The alternative is making all six
packages public, but this repo is private on purpose and public packages undo
part of that reasoning.

The project name is `nomaden`, and it is not a free choice: `tenant-up.sh` looks
for a container named `nomaden-proxy-1`. Renaming it means changing
`PROXY_CONTAINER` in that script too.

It contains eight services that hold no tenant data: the proxy, three static
frontends, MinIO, Gotenberg, LiveKit, and coturn.

**The owner panel is set up like any other tenant**, not through a special path.
The only difference is one line in its env file:

```bash
python manage.py provision_tenant "NomaX Panel" --subdomain panel \
    --email ops@nomaden.id --tier ENTERPRISE --out /srv/tenants/panel.env
# then EDIT /srv/tenants/panel.env: change ENABLE_CONTROL_PLANE to 1
sudo ./paradise/bin/tenant-up.sh panel /srv/tenants/panel.env
```

One path for everyone beats one path plus an exception that runs once in the
life of the host and then gets forgotten.

Warning: the control plane is only usable once this panel is up. Until then, the
`provision_tenant` call above has to run from another deployment that already
has a control plane, or, for the very first one, directly through
`manage.py shell` inside the panel container after it starts.

---

## 1. Onboarding a new customer

Run this on the **owner** deployment.

```bash
python manage.py provision_tenant "PT Acme" \
    --subdomain acme \
    --email admin@acme.co.id \
    --tier PRO \
    --control-url https://panel.nomaden.id \
    --out /srv/tenants/acme.env
```

What happens: the company, subscription, and instance records are created; the
heartbeat secret is issued; an env file holding `SECRET_KEY`, the database
credentials, the addresses, and the heartbeat secret is written with 600
permissions.

Warning: **the heartbeat secret exists only in that file.** The database stores
just its SHA-256 hash. If the file is lost before it gets deployed, issue a new
instance. There is no way to recover the secret.

The command **refuses** to write inside any git working tree. That is a guard
that runs, not just a line in `.gitignore`.

### What is still manual

One step is left that genuinely needs a human: **create the DNS record** that
points `acme.nomaden.id` at the host. It lives at the domain provider, out of
reach of any machine here.

Once DNS is in place, the rest is one command:

```bash
sudo ./paradise/bin/tenant-up.sh acme /srv/tenants/acme.env
```

It starts that customer's 8 services, waits for the migrations to actually
finish (it does not guess with a sleep), writes the Caddy site block, reloads the
proxy AND checks the result, then tests whether the subdomain answers.

To shut a tenant down without deleting its data: `sudo ./paradise/bin/tenant-down.sh acme`.

Warning: **none of these three files has ever been run for real**, because the
SaaS VPS does not exist yet. Run them once with a test customer and read the
output before using them for a paying one. Details are in the header of each
file.

Once the instance is up, its first heartbeat shows up at `/control/companies/`
within an hour. If it does not, `CONTROL_PLANE_URL` or the secret is wrong, and
the instance keeps running on the last tier it knew.

---

## 2. Checking the state of all customers

```bash
curl -H "Cookie: <god-mode session>" https://panel.nomaden.id/control/companies/
```

One request returns each instance's tier, liveness trail, and latest usage. The
permission is `InstanceAdminPermission`, meaning a God Mode admin on the owner
deployment. There is no second login door.

This is the endpoint the Owner Panel will call. The page itself belongs to the
frontend team and its design direction belongs to the Design Leads.

---

## 3. Raising or lowering a tier

```bash
curl -X PATCH https://panel.nomaden.id/control/companies/acme/ \
     -H "Content-Type: application/json" \
     -d '{"tier": "EXPERT"}'
```

The old subscription is **ended** and a new one starts. The history is kept as
rows because billing will always ask since when someone has been on which tier.

The customer's instance applies the change on its next heartbeat, at most an
hour later. If it is needed right away, run this on that instance:

```bash
python manage.py set_workspace_plan <workspace-slug> --tier EXPERT
```

---

## 4. Suspending an overdue customer

```bash
curl -X PATCH https://panel.nomaden.id/control/companies/acme/ \
     -d '{"status": "SUSPENDED"}'
```

The instance is **dropped to free, not switched off.** People who cannot log in
will not settle their invoice. The free limits start rejecting new uploads once
the quota is exceeded, which is enough pressure without holding their data
hostage.

---

## 4b. Billing a customer

Once, at the start, in the Xendit dashboard: copy the secret key into
`XENDIT_SECRET_KEY`, copy the callback verification token into
`XENDIT_CALLBACK_TOKEN`, and register the webhook address
`https://<panel>/control/payments/xendit/`.

Warning: an empty `XENDIT_CALLBACK_TOKEN` means **every webhook is rejected**, not
every webhook accepted. This is deliberate. An instance that has not been
configured should lose webhooks rather than accept a "mark as paid" command from
anyone who finds the address.

Issuing an invoice for one period:

```bash
curl -X POST https://panel.nomaden.id/control/companies/acme/invoices/      -H "Content-Type: application/json" -d '{"tier": "PRO"}'
```

The response includes `invoice_url`, the Xendit payment page, which already
offers virtual account, QRIS, and e-wallet. Send that link to the customer.

After payment, the Xendit webhook settles the invoice, adjusts the subscription,
and sets the company to `ACTIVE`. All of it is automatic. Nothing needs to be
clicked.

**What runs automatically every day at 04:00:** overdue invoices are marked
expired and the company becomes `PAST_DUE`. After `BILLING_GRACE_DAYS` pass
without payment, it becomes `SUSPENDED`, and its instance drops to free on the
next heartbeat.

The grace period is not zero because an interbank transfer can take a business
day to show up, and suspending a customer whose money is in transit is a good way
to lose a customer who has in fact paid.

### Not yet verified

The billing logic is fully tested, but **the real Xendit payload shape has never
been run against the sandbox**, because that needs a merchant account. Before
billing the first customer, create one test invoice in sandbox mode, pay it, and
confirm the webhook really settles the row. If the payload shape turns out to
differ, only `plane/control/xendit.py` needs adjusting.

FREE is not billed. ENTERPRISE has no list price either, and is not supposed to:
the product plan calls it custom, so it is billed through a negotiated deal and
its status is set by hand.

---

## 5. Moving a free customer up to their own instance

This is a data move between databases, not a one-column change.

```bash
# 1. on the free pool. The objects COME ALONG, no switch needed.
python manage.py export_workspace acme-gratis --out /srv/pindah/acme.json.gz
#    produces      acme.json.gz         the rows
#                  acme-assets.tar.gz   the storage objects

# 2. move BOTH files to the new instance (scp, rsync, anything)

# 3. on the new instance, LOOK FIRST (dry run)
python manage.py import_workspace /srv/pindah/acme.json.gz

# 4. if it looks right
python manage.py import_workspace /srv/pindah/acme.json.gz --terapkan

# 5. the tier
python manage.py set_workspace_plan acme-gratis --tier PRO
```

The dry run is the default for step 3, and that is how it should be.

Storage objects come along **by default**, with no optional switch. An export
that produces half a move by default is an export where the half gets forgotten,
and the forgotten half is the part end users notice last.

Each side uses its **own** storage: the export downloads from the source
instance's MinIO, the import uploads to the target instance's MinIO, both with
credentials that already exist there. No credential ever moves between machines,
and no new configuration is needed.

The import **refuses to run** if the rows file mentions objects but the objects
tar is not next to it. Copying one file and forgetting the other is certain to
happen sooner or later. If leaving them out is intentional, say so with
`--no-assets`.

Order inside the import: objects are uploaded **first**, rows written afterward.
If the upload fails midway, no row has been written and the target instance stays
clean. An object without a row is harmless because it is not visible anywhere. A
row without an object looks intact, but its file will never open.

The import **refuses** two situations before writing a single row: the slug
already exists on the target, and a user's email already exists with a different
UUID. The second one matters: pushing ahead would leave thousands of rows
referencing the wrong person.

Warning: if the export reports objects that are **missing in the source storage**,
their rows still come along while the files do not. On the target instance they
will appear in lists but cannot be opened. Check the report before handing over
the instance.

Only after the customer confirms the new instance is correct, delete their
workspace from the free pool. Not before.

---

## 6. Tuning the free pool limits

All of these are environment variables, no release needed. Details are in
`apps/api/.env.example` under the tiers section.

```
FREE_MAX_MEMBERS=1     # individual, invites are rejected from the moment they are sent
FREE_MAX_STORAGE_BYTES=1073741824
FREE_MAX_WORKSPACES=1
REQUIRE_EMAIL_VERIFICATION_FOR_WORKSPACE=1     # turn on ON THE FREE POOL
DORMANT_WARN_AFTER_DAYS=60
DORMANT_FREEZE_AFTER_DAYS=90
DORMANT_MARK_DELETION_AFTER_DAYS=180
```

The limit with the most effect is storage. Numbers from Paradise production: 79
people, two months of real use, a 598 KB gzipped database but 95 MB of uploads.
The rows are nearly free, the files are not.

`REQUIRE_EMAIL_VERIFICATION_FOR_WORKSPACE` should stay `0` on self-hosted
instances: an instance without SMTP can never verify anyone, and turning it on
there means nobody can create a workspace.

### Dormant workspaces

Three stages: an email warning, uploads frozen, then **marked** as a deletion
candidate. There is no fourth stage, and that is deliberate. Deleting customer
data on a timer cannot be undone.

What has been marked can be seen through `WorkspacePlan.pending_deletion_at`, and
the decision to delete belongs to a human.

A workspace that gets used again is woken up **immediately** on the next upload
attempt, without waiting for the daily sweep. To wake one manually:

```bash
python manage.py set_workspace_plan <slug> --tier FREE --bangunkan
```

---

## What does NOT exist yet

Written here so nobody assumes it does:

- **Xendit verification against a real sandbox.** The code is complete and
  tested, but a merchant account is needed to prove the payload shape is right.
  See section 4b.
- **Viewing the Owner Panel page in a browser.** The page is built in God Mode
  (`/god-mode/companies`), the route is registered, and the whole backend has
  been tested through real sessions. What is missing: no human has seen how it
  finally looks.
- **Running the SaaS stack once for real.** `docker-compose-shared.yml`,
  `docker-compose-tenant.yml`, `Caddyfile.saas`, `tenant-up.sh`, and
  `tenant-down.sh` are complete and reference each other correctly, but none has
  been run even once. Waiting on the VPS.
- **Filling in the legal document skeletons** in `DOKUMEN-HUKUM/` (Indonesian),
  and answering the four decisions in `MONITORING-AND-PRIVACY.md`. Both must be
  done before the first PAID customer, not before the first free one. Copying of
  storage objects has been automatic since 28 Aug and is no longer on this list.
