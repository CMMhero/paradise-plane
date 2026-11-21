# Review of monitoring features before selling to many companies

Answers section 9.3 of the work plan, which says this system's monitoring
capabilities carry "serious privacy and legal implications" once it is sold to
many companies and the owner panel sits on top of all of them.

This is an **audit of the code**, not an outline. What is written below is in
the repo and can be checked line by line. What is still undecided is marked as a
decision waiting on the product owner, not dressed up as a recommendation.

Warning: this is not legal advice. Law 27/2022 on Personal Data Protection
applies to this system as soon as it processes another company's employee data,
and a legal expert needs to review how it applies.

---

## 1. What is actually recorded

| Capability                       | Where                              | What it holds                                                                                     |
| -------------------------------- | ---------------------------------- | ------------------------------------------------------------------------------------------------- |
| Login and logout history         | `db/models/login_activity.py`      | One row per event, per user                                                                       |
| Live sessions and devices        | `db/models/device.py`              | Registered devices and their sessions                                                             |
| "Currently using"                | `middleware/last_active.py`        | `User.last_active` is stamped from ordinary traffic, at most once every 60 seconds                |
| Cutting someone's session (kick) | `license/api/views/activity.py:99` | An instance admin can cut all of a person's sessions, and `?nonaktifkan=1` also locks the account |
| Audit trail of changes           | `license/api/views/audit_log.py`   | Who changed what, via django-auditlog                                                             |
| Super Admin project oversight    | `db/superadmin.py`                 | Super Admin holds a role 20 `ProjectMember` in ALL projects                                       |

What does **not** exist, and it is worth saying so nobody assumes otherwise:
there is no recording of chat content for monitoring, no screen time counter, no
screenshots, and no location tracking.

Chat monitoring was once designed and then **removed** before release.

---

## 2. Why this is different once it is SaaS

In Paradise, all of the capabilities above are used by one company on its own
employees. The working relationship is clear, and whoever monitors is
accountable for whoever is monitored.

In SaaS there is a third party: **NomaX**. And three of the capabilities above
cross that line.

**An instance admin can cut sessions and lock accounts.** On a customer
instance, the instance admin is the customer's own person, so this stays an
internal matter. But on the **free pool**, the instance admin is NomaX, and free
users from hundreds of different companies share the same instance. That means
NomaX can technically cut anyone's session in the free pool.

**The free pool's audit trail and login history are in NomaX's database.** Not
because anyone wanted it that way, but because the free pool is a single
deployment.

**The control plane receives each instance's usage.** Only three numbers leave a
customer instance, and that is limited on purpose. But the existence of the
heartbeat path itself has to be disclosed to customers, not just its contents.

---

## 3. What is already right and should not change

**Login history retention is capped and HARD deleted.** `RETENSI_HARI` in
`db/models/login_activity.py`, swept by `bgtasks/login_activity_retention.py`,
with a warning that appears several days ahead. A trail kept forever is a trail
that leaks someday.

**The heartbeat to the control plane carries only three numbers.** Workspace
count, member count, bytes used, plus the version. No names, no work item
titles, no file contents. This is enforced by `kumpulkan_pemakaian` in
`bgtasks/control_plane_heartbeat.py` and is tested.

**The instance pushes, the center does not pull.** If the center pulled, it
would need read credentials to every customer database, and the whole reason for
separating databases would be gone.

**Instance secrets are stored as fingerprints, not as they are.** A leak of the
control plane database does not automatically become a key to every customer
instance.

**The audit trail does NOT travel with a workspace when it is moved.** Decided in
`utils/workspace_transfer.py`. The consequence is real and intended.

---

## 4. Decisions waiting on the product owner

Four, and none of them is mine to make, because they are all about promises to
customers, not about code.

### 4.1 Who may cut sessions in the free pool

Today: the instance admin, which is NomaX. Options:

- **Leave it, and say so.** State in the Terms of Service that free accounts can
  have their sessions ended by the operator. The most honest, the cheapest.
- **Limit it to abuse only**, with a required reason on record. This needs a
  reason field on the kick endpoint.
- **Remove it entirely in the free pool**, and handle abuse through company
  suspension, not by cutting individual sessions.

My recommendation is the first, because the second and third add code for a
problem that has never happened.

### 4.2 Whether paying customers are told about the heartbeat path

Today: nowhere tells the customer. It is honest in the code and invisible to the
people whose data is sent.

Stating it in the Terms of Service is better than having a customer's IT team
find it by reading outbound traffic, because something found independently
always reads worse than something announced.

### 4.3 How long usage is kept in the control plane

Today: **forever**. `UsageSnapshot` has no retention at all, and the heartbeat is
hourly. One customer produces about 8,760 rows a year.

That is not a size problem but a promise problem: a customer who leaves still
leaves a usage trail in our system with no time limit. The number needs to be
decided, then a sweep built like the existing login history retention.

### 4.4 What happens to the data of a customer who leaves

Today: `CHURNED` is only a status. The stack stays alive until someone shuts it
down, and `tenant-down.sh` deliberately never deletes volumes.

To decide: how long data is kept after a customer leaves, and who may request an
export. `export_workspace` can already produce the package, so only the policy is
missing.

---

## 5. What must exist before the first paying customer

Not before the first free customer, because the legal relationship is different.

- [ ] Terms of Service that cover items 4.1 and 4.2
- [ ] Privacy Policy that covers items 4.3 and 4.4
- [ ] Data processing agreement, because the customer is the controller of their
      employees' data and NomaX is the processor
- [ ] `UsageSnapshot` retention decided and running
- [ ] Reviewed by a legal expert, not just written

Drafts of the three documents are in `paradise/DOKUMEN-HUKUM/` (Indonesian).
