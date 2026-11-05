#!/usr/bin/env bash
# Deploy manual di server: tarik image hasil CI dari GHCR lalu restart.
# Server tidak pernah build sendiri, image dibangun oleh workflow paradise-build.
#
#   ./paradise/bin/deploy.sh                       # rilis terbaru (tag latest)
#   APP_RELEASE=<git-sha> ./paradise/bin/deploy.sh # pin / rollback ke commit tertentu
#   DEPLOY_RECREATE_PROXY=1 ./paradise/bin/deploy.sh   # paksa buat ulang proxy
#   DEPLOY_SKIP_PRUNE=1 ./paradise/bin/deploy.sh       # simpan image lama
#
# Exit != 0 kalau healthcheck gagal, jadi aman dipanggil dari cron kalau nanti
# mau diotomatiskan.
set -euo pipefail

cd "$(dirname "$0")/../.."
compose=(docker compose -f docker-compose.yml -f docker-compose.ghcr.yml)

git pull --ff-only
"${compose[@]}" pull

# ---------------------------------------------------------------------------
# JANGAN buat ulang `proxy` kalau konfigurasinya tidak berubah.
#
# KENAPA. Caddy sudah diberi `lb_try_duration`, jadi saat `api` atau `web`
# dibuat ulang, permintaan DITAHAN lalu dilayani, bukan dijawab 502. Terbukti
# lewat uji terkendali: 123 permintaan selama `api` restart penuh, 123-nya 200,
# satu di antaranya ditahan 12 detik.
#
# Tapi trik itu punya satu celah yang tidak bisa ditutup dari sisi Caddy:
# saat container `proxy` SENDIRI yang dibuat ulang, tidak ada yang bisa menahan
# apa pun, dan pemakai mendapat sambungan ditolak. Terukur 26 kali dengan durasi
# ~2 milidetik pada deploy 19 Agt 2026.
#
# Jalan keluarnya bukan menambah proxy kedua (itu cuma memindahkan masalahnya
# satu lapis ke atas), melainkan BERHENTI membuat ulang proxy tanpa alasan.
# Hampir semua deploy hanya mengubah aplikasi, bukan konfigurasi proxy.
#
# Yang dibandingkan ISI Caddyfile, bukan digest image. Digest tidak bisa
# dipakai: CI membangun tanpa cache layer, jadi digest-nya selalu berbeda walau
# isinya sama persis.
#
# Kalau perbandingannya gagal karena alasan apa pun, kita JATUH KE PERILAKU
# LAMA (buat ulang semuanya). Deploy yang selamat tapi sedikit mengganggu jauh
# lebih baik daripada deploy yang melewatkan perubahan proxy diam-diam.
#
# ⚠️ Ini juga berarti pembaruan image dasar Caddy (mis. tambalan keamanan) TIDAK
# ikut terpasang selama Caddyfile-nya tidak berubah. Kalau perlu, paksa dengan
# `DEPLOY_RECREATE_PROXY=1`.
# ---------------------------------------------------------------------------
proxy_image=$("${compose[@]}" config --images 2>/dev/null | grep "plane-proxy" | head -1 || true)
caddy_lama=$(docker exec proxy sha256sum /etc/caddy/Caddyfile 2>/dev/null | cut -d' ' -f1 || true)
caddy_baru=""
if [ -n "$proxy_image" ]; then
  caddy_baru=$(docker run --rm --entrypoint sha256sum "$proxy_image" /etc/caddy/Caddyfile 2>/dev/null | cut -d' ' -f1 || true)
fi

if [ "${DEPLOY_RECREATE_PROXY:-0}" != "1" ] &&
   [ -n "$caddy_lama" ] && [ -n "$caddy_baru" ] &&
   [ "$caddy_lama" = "$caddy_baru" ]; then
  echo "Caddyfile tidak berubah, proxy TIDAK dibuat ulang (pemakai tidak kehilangan sambungan)."
  # Seluruh service disebut eksplisit KECUALI proxy. `--no-deps` supaya compose
  # tidak diam-diam ikut membuat ulang proxy sebagai dependensi service lain.
  mapfile -t layanan < <("${compose[@]}" config --services | grep -v '^proxy$')
  "${compose[@]}" up -d --no-deps "${layanan[@]}"
else
  echo "Konfigurasi proxy berubah (atau tidak bisa dibandingkan): membuat ulang SEMUA service."
  "${compose[@]}" up -d
fi

# ---------------------------------------------------------------------------
# Migrasi WAJIB diperiksa, bukan diandaikan.
#
# `migrator` menjalankan `manage.py migrate` lalu keluar, dan tidak ada service
# yang menunggunya. Dulu tidak ada yang membaca kode keluarnya, jadi migrasi
# yang gagal tetap diakhiri "SEHAT": `docker compose ps` tidak menampilkan
# container yang sudah berhenti, dan `api` tetap menjawab 200 di atas skema
# lama. `docker wait` mengembalikan kode keluar container itu; kalau sudah
# berhenti sebelumnya, ia langsung menjawab kode yang lama.
# ---------------------------------------------------------------------------
if docker inspect plane-migrator >/dev/null 2>&1; then
  echo "== Menunggu migrasi =="
  kode_migrasi=$(docker wait plane-migrator)
  docker logs --tail 15 plane-migrator 2>&1 | sed 's/^/  migrator: /'
  if [ "$kode_migrasi" != "0" ]; then
    echo "MIGRASI GAGAL (exit $kode_migrasi). Lihat: docker logs plane-migrator"
    exit 1
  fi
  echo "Migrasi selesai."
fi

paradise/bin/healthcheck.sh

# ---------------------------------------------------------------------------
# Migrasi dan changelog DIBUKTIKAN dari dalam `api`, bukan diandaikan.
#
# Exit 0 dari migrator belum berarti skema sama dengan kode yang sekarang
# jalan: migrator bisa saja memakai image lain, atau container lama yang sudah
# berhenti lebih dulu dan `docker wait` menjawab kode lamanya. `showmigrations`
# dijalankan di image `api` yang BARU, jadi `[ ]` di sana berarti ada migrasi
# yang belum diterapkan. Kalau begitu, diterapkan di sini, lalu dicek ulang.
#
# Changelog diterbitkan entrypoint `api` saat start, tapi galatnya DITELAN di
# sana supaya gunicorn tidak tertahan. Akibatnya changelog yang gagal terbit
# tidak pernah terlihat. Di sini perintahnya dijalankan sekali lagi
# (idempoten, dijaga advisory lock), dan galatnya menggagalkan deploy.
# ---------------------------------------------------------------------------
echo "== Memeriksa migrasi dari dalam api =="
belum=$(docker exec api python manage.py showmigrations --plan 2>&1 | grep -c '^\[ \]' || true)
if [ "$belum" != "0" ]; then
  echo "Ada $belum migrasi belum diterapkan, menjalankan migrate"
  docker exec api python manage.py migrate --noinput 2>&1 | tail -15 | sed 's/^/  migrate: /'
  belum=$(docker exec api python manage.py showmigrations --plan 2>&1 | grep -c '^\[ \]' || true)
  if [ "$belum" != "0" ]; then
    echo "MIGRASI GAGAL: masih $belum belum diterapkan"
    exit 1
  fi
fi
echo "Migrasi lengkap (0 tertunda)."

echo "== Menerbitkan changelog =="
if ! docker exec api python manage.py terbitkan_changelog 2>&1 | sed 's/^/  /'; then
  echo "CHANGELOG GAGAL. Lihat: docker exec api python manage.py terbitkan_changelog"
  exit 1
fi

# Versi yang benar-benar dilayani, dibaca dari API (register_instance mengambilnya
# dari apps/api/package.json saat api start). Ini bukti perubahan sudah naik,
# bukan sekadar container hidup.
web_url="$(grep -m1 '^WEB_URL=' .env | cut -d= -f2- | tr -d "\"'")"
versi=$(curl -fsSL --max-time 15 "${web_url:-http://localhost}/api/instances/" 2>/dev/null |
  grep -o '"current_version": *"[^"]*"' | head -1 | sed 's/.*"\([^"]*\)"$/\1/' || true)
echo "== Versi berjalan: ${versi:-tidak terbaca} =="

# ---------------------------------------------------------------------------
# Buang image versi lama yang tertinggal di mesin.
#
# Tiap `docker compose pull` melepas tag dari image versi sebelumnya, dan tidak
# ada satu pun langkah yang pernah mengambilnya kembali. Terukur 20 Agt 2026:
# 96 image tanpa tag menahan 55,89 GB, dan disk naik 36% -> 73% dalam satu hari
# berisi 13 deploy. Disk penuh menghentikan PostgreSQL menulis, jadi ini bukan
# soal kerapian.
#
# 🔴 Baris ringkasan `docker system df` menyebut angka yang sama "1.925GB (3%)"
# dan itu MENYESATKAN. Yang benar ada di rincian `docker system df -v`, kolom
# UNIQUE SIZE, yaitu data yang tidak dipakai bersama image lain. Jangan
# menyimpulkan "tidak ada masalah" dari baris ringkasannya.
#
# Yang dibuang HANYA image dangling (tanpa tag). Image bertag tidak disentuh,
# dan image yang masih dirujuk container mana pun dilewati docker sendiri,
# termasuk container yang tagnya sudah bergeser karena pull.
#
# ⚠️ ADA HARGANYA, DAN BUKAN NOL. Rollback tetap BISA: `APP_RELEASE=<sha>`
# menarik tag SHA dari GHCR, dan GHCR menyimpannya. Tapi versi sebelumnya di
# mesin ini tidak bertag (server hanya pernah menarik `latest`), jadi ia ikut
# terbuang, dan bersamanya hilang pula lapisan yang tadinya membuat penarikan
# ulang hampir seketika. Rollback sesudah prune berarti mengunduh penuh sekitar
# 600 MB, 10 sampai 14 menit, persis saat orang paling butuh cepat.
#
# Tetap dipilih karena bandingannya berat sebelah: rollback jarang dan masih
# mungkin, sedangkan disk penuh menghentikan PostgreSQL menulis dan mematikan
# aplikasi untuk 90 orang. Kalau sedang deploy yang berisiko dan ingin jalan
# pulang tetap hangat, lewati sekali dengan `DEPLOY_SKIP_PRUNE=1`.
#
# Dijalankan SESUDAH healthcheck lulus. `set -e` di atas menghentikan skrip
# kalau healthcheck gagal, jadi deploy yang gagal tetap meninggalkan lapisan
# lamanya utuh di mesin.
#
# Kegagalan pembersihan TIDAK boleh menggagalkan deploy yang aplikasinya sudah
# sehat, jadi galatnya dilaporkan lalu ditelan di sini saja.
# ---------------------------------------------------------------------------
if [ "${DEPLOY_SKIP_PRUNE:-0}" = "1" ]; then
  echo "== DEPLOY_SKIP_PRUNE=1: image lama DIBIARKAN, jalan pulang tetap hangat =="
else
  echo "== Membersihkan image lama =="
  docker image prune -f | tail -1 ||
    echo "peringatan: pembersihan image gagal; deploy TETAP dianggap berhasil"
fi
