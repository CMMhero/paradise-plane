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

paradise/bin/healthcheck.sh

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
