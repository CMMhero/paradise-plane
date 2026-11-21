# Security checklist, REQUIRED before production

Plane CE has good security awareness (webhook SSRF mitigation, a SECRET_KEY
guard, a sign-up TOCTOU fix). But **the dev defaults are not safe for prod**.
Work through this:

## Secrets, replace ALL default values

- [ ] `SECRET_KEY`, generate a new one: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] `LIVE_SERVER_SECRET_KEY`, generate a new one (same way)
- [ ] `POSTGRES_PASSWORD`, not `plane`, at least 20 random characters
- [ ] `RABBITMQ_PASSWORD`, not `plane`
- [ ] `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (MinIO), not `access-key`/`secret-key`
- [ ] Make sure `.env` is **not** committed (`git status` must be clean)

## Network and host

- [ ] `ALLOWED_HOSTS` must **not** be `*` in prod, set it to the office `APP_DOMAIN`
- [ ] `CORS_ALLOWED_ORIGINS` = office origins only, not `localhost`
- [ ] `WEB_URL` / `ADMIN_BASE_URL` / `SPACE_BASE_URL` use the real domain/IP
- [ ] If public: enable HTTPS (`SITE_ADDRESS`=domain + `CERT_EMAIL`)

## Access and operations

- [ ] Restrict God Mode admin (`/god-mode`), strong accounts, don't hand it out freely
- [ ] `API_KEY_RATE_LIMIT` set as needed (default `60/minute`)
- [ ] Postgres and MinIO do **not** expose ports publicly, internal compose network only
- [ ] Encrypted backups with a tested restore ([`DEPLOYMENT.md`](DEPLOYMENT.md))
- [ ] Rotate secrets if there is any sign of a leak

## Quick verification

```bash
grep -R "GANTI\|=plane\"\|access-key" .env   # must return NO results
```
