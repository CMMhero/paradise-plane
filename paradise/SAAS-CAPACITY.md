# SaaS capacity plan

Written 28 Aug 2026, before the SaaS VPS and domain existed. It has one goal:
answer "how big a machine should we rent, and how many customers fit on it" with
measured numbers, not guesses.

**What was measured is marked clearly, and so is what was estimated.** Reading an
estimate as a measurement is how you order a machine of the wrong size.

---

## 1. Numbers that were ACTUALLY measured

The source is Paradise Task Tracker production, 79 users, two months of real use.

| Quantity                    | Value                       | How it was measured    |
| --------------------------- | --------------------------- | ---------------------- |
| Services in one stack       | 16                          | `docker-compose.yml`   |
| RAM used by the whole stack | **2.2 GB**                  | `status.sh` on server  |
| The machine                 | 4 vCPU / 30 GB / 98 GB disk | VPS spec               |
| Disk used                   | 19% of 98 GB                | `status.sh`            |
| App database                | **598 KB** gzipped          | dump from 27 Aug       |
| Uploads (MinIO)             | **95 MB**                   | volume archive, 27 Aug |

The last two numbers matter most, and their relationship is surprising: **the
rows are 598 KB, the files are 95 MB.** That is roughly 1 to 160. So capacity
planning for this SaaS is really OBJECT STORAGE planning, not database planning.

Warning: do not use the 35 MB figure recorded in `paradise/backup.log`. That is a
LOCAL database bloated by 20,000 volume-test work items, not production.

---

## 2. What is required per customer, and what can be shared

Of the 16 services, only the ones that hold the data have to be separate.

| Service                        | Per customer?       | Reason                                                                 |
| ------------------------------ | ------------------- | ---------------------------------------------------------------------- |
| `plane-db`                     | **required**        | The core of the isolation decision. This is what we promise customers  |
| `api`, `worker`, `beat-worker` | **required**        | They hold the connections to that database                             |
| `live`                         | **required**        | Reads documents from that database                                     |
| `plane-redis`                  | required, but small | Sessions and cache belonging to one tenant                             |
| `plane-mq`                     | required, but small | Celery queue belonging to one tenant                                   |
| `web`, `admin`, `space`        | **can be shared**   | Static frontends. The API address is derived from the browser hostname |
| `proxy` (Caddy)                | **can be shared**   | One Caddy serves every subdomain, which is its job                     |
| `plane-minio`                  | **can be shared**   | One cluster, one bucket per customer                                   |
| `livekit`, `coturn`            | **can be shared**   | The media relay touches nobody's database                              |
| `gotenberg`                    | **can be shared**   | Office-to-PDF conversion, stateless                                    |

**16 services drop to 7 per customer.** The other nine are shared.

---

## 3. Estimated footprint per customer

Warning: **this is an ESTIMATE, not a measurement.** The separate 7-service stack
has never been run. The only thing ever measured is the full 16-service stack at
2.2 GB.

A rough split of that full stack:

```
per customer (7 services)      ~1.2 - 1.5 GB
shared (9 services)            ~0.7 - 1.0 GB, does NOT grow per customer
```

The per-customer figure is for an idle state. A busy customer raises usage in
`api` and `worker`, and online meetings raise usage in the shared `livekit`.

**The first thing to do before renting any machine:** run ONE customer stack with
the 7/9 split above, leave it for a day, then measure. One measurement beats this
whole section.

---

## 4. How many customers fit

Assuming 1.5 GB per customer plus 1 GB shared, and leaving 20 percent headroom
for spikes:

| Machine RAM | Estimated customers | Notes                                                       |
| ----------- | ------------------- | ----------------------------------------------------------- |
| 8 GB        | 3 - 4               | Enough for the first to third customer                      |
| 16 GB       | 7 - 8               |                                                             |
| 32 GB       | 16 - 17             |                                                             |
| 64 GB       | 33 - 34             | At this point a single machine is a single point of failure |

Disk is looser: 95 MB of uploads for 79 people over two months means a typical
customer grows about 50 MB per month. A hundred customers over a year comes to
about 60 GB. Disk is not the binding constraint, RAM is.

**Starting recommendation: one 16 GB VPS.** It fits seven paying customers, and
seven paying customers are enough to pay for the next machine. Starting at 64 GB
means paying for empty capacity for months.

---

## 5. The free pool is counted separately

The free pool is not a set of stacks but ONE stack holding many workspaces. So
its cost does not grow per free user. It grows per FILE they upload, which is why
the limit with the most effect is the storage quota.

With the current defaults, `FREE_MAX_STORAGE_BYTES=1 GiB` and individual-only
free accounts:

```
1,000 free accounts, using 5% of quota on average   ~50 GB
1,000 free accounts, using 50% of quota on average  ~500 GB
```

That tenfold gap is not technical uncertainty but behavioral uncertainty, and
nobody can answer it before there are real users. That is why the following three
things exist and must be watched from the first free account:

- `FREE_MAX_STORAGE_BYTES`, which can be lowered without a release
- the dormancy limit, which freezes uploads for idle workspaces
- `UsageSnapshot` in the control plane, which records the trend

Warning: **the free pool is the only part of this architecture whose tables are
shared by thousands of tenants.** The local volume test once found that
`.distinct()` made COUNT 88 times slower at 20,000 work items, and the conclusion
at the time, "won't be felt for two more years", applied to ONE company. In the
free pool, the cost of a query like that arrives much sooner.

---

## 6. When to split

Measurable triggers, not feelings:

| Trigger                                        | Action                                                             |
| ---------------------------------------------- | ------------------------------------------------------------------ |
| RAM use above 75% for a week                   | Rent a second machine, move the newest customers to it             |
| One customer consistently using more than 3 GB | Move them to their own machine                                     |
| Free pool above 60% of object storage disk     | Lower the free quota, or speed up the dormancy limit               |
| Online meetings start to stutter               | `livekit` moves to its own machine first, it is the most sensitive |

Moving a customer between machines uses the existing path: `export_workspace`
then `import_workspace`, and the storage objects come along on their own. See
`SAAS-RUNBOOK.md` section 5.

---

## 7. What this document cannot answer yet

- **Rental price.** It depends on the provider and region, and writing down an
  unverified number here would get read as a budget.
- **Bandwidth needed for online meetings.** LiveKit is the hungriest component,
  and it has never been measured with more than a few participants.
- **Peak load.** Every number here is for an idle state. Peak patterns only form
  once there are real customers with overlapping working hours.

All three need measurement, not more thinking.
