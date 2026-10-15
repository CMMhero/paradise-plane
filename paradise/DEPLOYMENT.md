# Deployment Produksi, Paradise Task Tracker

Target: satu server kantor (Linux) melayani ~100 user. **Tidak butuh Kubernetes**,
Docker Compose sudah cukup. K8s hanya perlu kalau butuh HA/autoscale + tim ops.

## Prasyarat server

- Docker Engine + Compose plugin
- 4 vCPU / 8 GB RAM minimum (naik kalau editor kolaboratif ramai)
- Disk cukup untuk Postgres + upload MinIO + backup
- Domain atau IP LAN statis untuk `APP_DOMAIN`

## Langkah

1. **Clone repo ini** ke server, checkout branch `main`.
2. **Konfigurasi env:** `cp paradise/.env.example .env` lalu isi semua `<GANTI>`.
   Jalankan [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md), jangan skip.
3. **Pilih compose:**
   - **Disarankan, image hasil CI:** `./paradise/bin/deploy.sh`. Workflow
     `paradise-build` sudah build 6 image dari kode kustom kantor tiap push ke
     `main` dan push ke GHCR; server tinggal tarik. Server tidak perlu build
     (hemat CPU/RAM dan tidak ada downtime lama). Lihat [CI/CD](#cicd) di bawah.
   - Build dari source (kalau CI mati / server airgapped):
     `docker compose -f docker-compose.yml up -d --build`
   - Atau image prebuilt upstream (lihat `deployments/cli/community/`, punya knob `*_REPLICAS`).
4. **Migrasi & verifikasi:** container `api` menjalankan migrasi saat start.
   Cek dengan `paradise/bin/healthcheck.sh`.
5. **HTTPS:** set `SITE_ADDRESS=domain-kamu` + `CERT_EMAIL` → Caddy urus sertifikat
   otomatis. Untuk LAN tanpa domain, tetap HTTP di port 80.

## CI/CD

Alurnya sengaja **push image, tarik manual**, server LAN tidak perlu membuka SSH
ke internet, dan tidak ada restart mendadak di jam kerja.

| Tahap  | Di mana                           | Apa yang terjadi                                                                                          |
| ------ | --------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Build  | GitHub Actions (`paradise-build`) | Tiap push ke `main`: build 6 image, push ke `ghcr.io/<pemilik-repo>/plane-*`, tag = commit SHA + `latest` |
| Deploy | Server, manual                    | `./paradise/bin/deploy.sh` → `git pull` + `compose pull` + `up -d` + healthcheck                          |

**Namespace GHCR mengikuti pemilik repo.** Workflow menurunkannya dari
`GITHUB_REPOSITORY_OWNER` dan mengecilkan hurufnya, jadi tidak ada yang perlu
disunting saat repo dipindahkan atau di-fork. Di sisi server, nilainya diambil
dari `GHCR_OWNER` di `.env`, dan variabel itu wajib diisi, tanpa nilai bawaan.

⚠️ **Paket GHCR TIDAK ikut pindah saat repo dipindah.** Paket dimiliki oleh
namespace akun, bukan oleh repo. Urutan pemindahan yang benar: pindahkan repo,
biarkan CI membangun ulang seluruh image di namespace baru, pastikan tag
`latest` sudah ada di sana, `docker login ghcr.io` di server dengan token yang
berhak membacanya, **baru** isi `GHCR_OWNER` di `.env` server. Terbalik berarti
`docker compose pull` gagal dan rilisnya batal. Aplikasi yang sedang berjalan
tidak ikut mati, `deploy.sh` memakai `set -e` sehingga ia berhenti sebelum
menyentuh container yang sedang melayani.

**Setup sekali saja, setelah run pertama workflow:** package GHCR default-nya
private walaupun repo public. Buka halaman `/pkgs` milik repo → tiap package →
_Package settings_ → _Change visibility_ → **Public**. Tanpa ini `docker pull`
di server akan gagal 401. (Alternatif: `docker login ghcr.io` di server pakai
PAT ber-scope `read:packages`.)

**Rollback.** Tiap build punya tag commit SHA, jadi kembali ke versi lama tidak
perlu build ulang:

```bash
APP_RELEASE=<git-sha-lama> ./paradise/bin/deploy.sh
```

Simpan `APP_RELEASE` di `.env` kalau mau pin permanen. Kosongkan untuk kembali
mengikuti `latest`.

**Kalau nanti mau otomatis penuh**, `deploy.sh` sudah exit != 0 saat healthcheck
gagal, jadi tinggal dipasang di cron (mis. `0 2 * * *`) tanpa perubahan kode.

## Scaling ~100 user

Naikkan replika worker/web sesuai beban (env `*_REPLICAS` pada compose community),
dan pindahkan Postgres ke volume/disk cepat. Aktifkan read-replica hanya kalau
query berat mulai terasa.

## Backup & pemulihan

Jadwalkan `paradise/bin/backup-db.sh` via cron harian. Simpan juga isi bucket
MinIO. Uji restore secara berkala, backup yang tak pernah diuji = bukan backup.
