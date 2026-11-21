# Security policy, Paradise Task Tracker

This system stores PT Paradise Perkasa's internal work data: work items, time
logs, company documentation, and the employee list with their roles.

## Reporting a vulnerability

Report security findings **directly to PT Paradise Perkasa's IT team**, not
through a public GitHub issue and not to anyone else.

> The IT contact address isn't filled in yet. Add it once there is an official
> one. No made-up address is listed on purpose. A security report sent to an
> address nobody reads is worse than having no address at all.

Include in your report:

- Repeatable steps that trigger the problem
- The URL or part of the system affected
- The impact you estimate
- The account and role you were using when you found it (Admin / Member / Guest)

## What we ask of reporters

- **Don't disclose it** until it's fixed.
- **Don't run automated scans** against the instance people use for work. This
  system is used by 79 people every day.
- **Don't exploit** a finding to access or change other people's data. Proving
  the hole exists is enough.
- Don't do social engineering, DDoS, or physical attacks.

## Scope

**In scope:** the web app, public pages (space), the admin panel / God Mode, the
API, the collaboration server, and the deployment configuration in `paradise/`.

**Out of scope:** vulnerabilities that need physical access to a user's device or
a man-in-the-middle position, email spoofing, and missing DNS headers
(DNSSEC/CAA) while the system still runs on the internal network.

## Vulnerabilities in the upstream codebase

This system is built on Plane Community Edition (see [NOTICE.md](NOTICE.md)).
A vulnerability that comes from upstream code rather than from our modifications
should **also** be reported to the upstream project so other users are
protected too, after the internal IT team has been told first.

## Current state

The system is still in development and **is not yet running on a production
server**. The known issues that must be fixed before production are documented
in `paradise/`, among them default credentials on internal infrastructure
services. Don't treat the development setup as a picture of the production
configuration.
