# Security Checklist, WAJIB sebelum produksi

Plane CE punya kesadaran keamanan bagus (mitigasi SSRF webhook, guard SECRET_KEY,
fix TOCTOU sign-up). Tapi **default dev tidak aman untuk prod**. Tuntaskan ini:

## Secrets, ganti SEMUA nilai default

- [ ] `SECRET_KEY`, generate baru: `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] `LIVE_SERVER_SECRET_KEY`, generate baru (cara sama)
- [ ] `POSTGRES_PASSWORD`, bukan `plane`, minimal 20 karakter acak
- [ ] `RABBITMQ_PASSWORD`, bukan `plane`
- [ ] `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (MinIO), bukan `access-key`/`secret-key`
- [ ] Pastikan `.env` **tidak** ter-commit (`git status` harus bersih)

## Jaringan & host

- [ ] `ALLOWED_HOSTS` **jangan** `*` di prod, set ke `APP_DOMAIN` kantor
- [ ] `CORS_ALLOWED_ORIGINS` = hanya origin kantor, bukan `localhost`
- [ ] `WEB_URL` / `ADMIN_BASE_URL` / `SPACE_BASE_URL` pakai domain/IP asli
- [ ] Kalau publik: aktifkan HTTPS (`SITE_ADDRESS`=domain + `CERT_EMAIL`)

## Akses & operasional

- [ ] Batasi god-mode admin (`/god-mode`), akun kuat, jangan diumbar
- [ ] `API_KEY_RATE_LIMIT` sesuai kebutuhan (default `60/minute`)
- [ ] Postgres & MinIO **tidak** expose port ke publik, hanya via jaringan internal compose
- [ ] Backup terenkripsi & diuji restore ([`DEPLOYMENT.md`](DEPLOYMENT.md))
- [ ] Rotasi secret bila ada indikasi bocor

## Verifikasi cepat

```bash
grep -R "GANTI\|=plane\"\|access-key" .env   # harus TIDAK ada hasil
```
