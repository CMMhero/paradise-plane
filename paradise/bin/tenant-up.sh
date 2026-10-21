#!/usr/bin/env bash
# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Nyalakan tumpukan satu pelanggan SaaS, lalu daftarkan subdomainnya ke proxy.
#
#   sudo ./paradise/bin/tenant-up.sh acme /srv/tenants/acme.env
#
# 🔶 BELUM PERNAH DIJALANKAN SUNGGUHAN. Skrip ini ditulis saat VPS SaaS belum
# ada, supaya provisioning tidak dimulai dari layar kosong. Yang bisa dijamin
# hanya bentuknya; angka dan perilaku hostnya belum pernah diuji siapa pun.
#
# Jalankan sekali dengan pelanggan uji dan BACA keluarannya sebelum memakai ini
# untuk pelanggan yang membayar.
#
# ============================================================================
# APA YANG DIKERJAKAN
# ============================================================================
#
#   1. Periksa prasyarat, dan BERHENTI kalau ada yang kurang
#   2. Nyalakan 8 layanan milik pelanggan itu (compose project = slug)
#   3. Tunggu migrasi selesai, bukan tebak dengan sleep
#   4. Tulis blok situs Caddy untuk subdomainnya
#   5. Muat ulang Caddy, dan PERIKSA hasilnya
#   6. Uji asap: apakah subdomainnya benar-benar menjawab
#
# Yang TIDAK dikerjakan: membuat rekaman DNS. Itu ada di penyedia domain, di
# luar jangkauan mesin ini. Skrip berhenti dan mengatakannya kalau namanya
# belum bisa diselesaikan.

set -euo pipefail

SLUG="${1:-}"
ENV_FILE="${2:-}"
BASE_DOMAIN="${BASE_DOMAIN:-nomaden.id}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose-tenant.yml}"
CADDY_TENANT_DIR="${CADDY_TENANT_DIR:-/srv/caddy/tenants}"
PROXY_CONTAINER="${PROXY_CONTAINER:-nomaden-proxy-1}"
BATAS_MIGRASI_DETIK="${BATAS_MIGRASI_DETIK:-600}"

merah() { printf '\033[0;31m%s\033[0m\n' "$*"; }
hijau() { printf '\033[0;32m%s\033[0m\n' "$*"; }
kuning() { printf '\033[1;33m%s\033[0m\n' "$*"; }

berhenti() {
  merah "BERHENTI: $*"
  exit 1
}

# --- 1. Prasyarat -----------------------------------------------------------
#
# Diperiksa SEMUA di depan, bukan satu per satu sambil jalan. Skrip yang gagal
# di langkah keempat meninggalkan tiga langkah pertama setengah jadi, dan
# membereskannya lebih lama daripada mengulang dari awal.

[ -n "$SLUG" ] || berhenti "Pemakaian: $0 <slug> <berkas-env>"
[ -n "$ENV_FILE" ] || berhenti "Pemakaian: $0 <slug> <berkas-env>"
[ -f "$ENV_FILE" ] || berhenti "Berkas env '$ENV_FILE' tidak ada. Buat dulu dengan 'manage.py provision_tenant'."
[ -f "$COMPOSE_FILE" ] || berhenti "'$COMPOSE_FILE' tidak ada. Jalankan dari akar repo."

# Slug jadi nama proyek compose, nama container, DAN subdomain sekaligus.
# Karakter di luar pola ini akan diterima compose lalu ditolak Caddy, atau
# sebaliknya, dan gejalanya muncul jauh dari sebabnya.
echo "$SLUG" | grep -qE '^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$' \
  || berhenti "Slug '$SLUG' tidak sah. Huruf kecil, angka, dan tanda hubung saja."

command -v docker >/dev/null || berhenti "docker tidak ada di PATH."
docker network inspect nomaden_saas >/dev/null 2>&1 \
  || berhenti "Jaringan 'nomaden_saas' belum ada. Nyalakan tumpukan bersama lebih dulu."
docker ps --format '{{.Names}}' | grep -qx "$PROXY_CONTAINER" \
  || berhenti "Container proxy '$PROXY_CONTAINER' tidak berjalan."

if docker compose -p "$SLUG" -f "$COMPOSE_FILE" ps -q 2>/dev/null | grep -q .; then
  berhenti "Pelanggan '$SLUG' SUDAH punya tumpukan yang berjalan. Pakai tenant-down.sh dulu."
fi

# DNS diperiksa SEBELUM apa pun dinyalakan. Caddy akan meminta sertifikat
# begitu blok situsnya masuk, dan permintaan yang gagal karena nama belum
# menunjuk ke mana-mana ikut memakan jatah rate limit Let's Encrypt.
if command -v getent >/dev/null; then
  getent hosts "${SLUG}.${BASE_DOMAIN}" >/dev/null \
    || berhenti "'${SLUG}.${BASE_DOMAIN}' belum bisa diselesaikan. Buat rekaman DNS-nya dulu, lalu ulangi."
else
  kuning "getent tidak ada, pemeriksaan DNS DILEWATI. Pastikan sendiri namanya sudah menunjuk ke host ini."
fi

hijau "Prasyarat lengkap."

# --- 2. Nyalakan tumpukannya ------------------------------------------------

echo
echo "Menyalakan tumpukan '$SLUG' ..."
TENANT_ENV_FILE="$ENV_FILE" docker compose -p "$SLUG" -f "$COMPOSE_FILE" \
  --env-file "$ENV_FILE" up -d

# --- 3. Tunggu migrasi ------------------------------------------------------
#
# Ditunggu sampai containernya BERHENTI, bukan `sleep 60`. Sleep yang kependekan
# membuat langkah berikutnya berjalan di atas skema yang belum jadi, dan sleep
# yang kepanjangan membuang waktu di tiap pelanggan selamanya.

echo
echo "Menunggu migrasi selesai (maks ${BATAS_MIGRASI_DETIK} detik) ..."
MIGRATOR="$(docker compose -p "$SLUG" -f "$COMPOSE_FILE" ps -q migrator)"
[ -n "$MIGRATOR" ] || berhenti "Container migrator tidak ketemu."

habis=0
while [ "$(docker inspect -f '{{.State.Running}}' "$MIGRATOR")" = "true" ]; do
  sleep 5
  habis=$((habis + 5))
  if [ "$habis" -ge "$BATAS_MIGRASI_DETIK" ]; then
    berhenti "Migrasi belum selesai sesudah ${BATAS_MIGRASI_DETIK} detik. Lihat: docker logs $MIGRATOR"
  fi
done

KODE="$(docker inspect -f '{{.State.ExitCode}}' "$MIGRATOR")"
[ "$KODE" = "0" ] || berhenti "Migrasi GAGAL (exit $KODE). Lihat: docker logs $MIGRATOR"
hijau "Migrasi selesai."

# --- 4. Blok situs Caddy ----------------------------------------------------
#
# Ditulis ke berkas sementara lalu dipindahkan, bukan langsung ke tujuan.
# `caddy reload` bisa berjalan bersamaan dengan penulisan ini, dan config yang
# terbaca setengah tertulis akan menjatuhkan reload untuk SELURUH penyewa.

mkdir -p "$CADDY_TENANT_DIR"
SITUS="${CADDY_TENANT_DIR}/${SLUG}.caddy"
SEMENTARA="${SITUS}.tmp.$$"

cat > "$SEMENTARA" <<EOF
# Dibuat tenant-up.sh $(date -u '+%Y-%m-%d %H:%M UTC'). Jangan disunting tangan:
# tenant-down.sh menghapus berkas ini apa adanya.
${SLUG}.${BASE_DOMAIN} {
	import tenant_proxy ${SLUG}-api-1:8000 ${SLUG}-live-1:3000
}
EOF
mv -f "$SEMENTARA" "$SITUS"
hijau "Blok situs ditulis: $SITUS"

# --- 5. Muat ulang Caddy, DAN PERIKSA ---------------------------------------
#
# Hasil reload wajib diperiksa. Caddy memvalidasi seluruh config sebelum
# menerapkannya, jadi satu berkas rusak membuat reload gagal dan Caddy tetap
# menjalankan config LAMA. Tanpa pemeriksaan ini, pelanggan baru diam-diam
# tidak pernah aktif sementara semuanya tampak berhasil.

echo
echo "Memuat ulang Caddy ..."
if ! docker exec "$PROXY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile 2>&1; then
  rm -f "$SITUS"
  berhenti "Caddy MENOLAK config barunya. Blok situs '$SLUG' sudah dibuang lagi, penyewa lain tidak terganggu."
fi
hijau "Caddy dimuat ulang."

# --- 6. Uji asap ------------------------------------------------------------
#
# Menyalakan tanpa memeriksa berarti menyerahkan penemuan kegagalan kepada
# pelanggan.

echo
echo "Uji asap ..."
ALAMAT="https://${SLUG}.${BASE_DOMAIN}"
for i in 1 2 3 4 5 6 7 8 9 10; do
  KODE_HTTP="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${ALAMAT}/api/instances/" || echo 000)"
  [ "$KODE_HTTP" != "000" ] && break
  sleep 5
done

echo "  GET ${ALAMAT}/api/instances/ -> ${KODE_HTTP}"
if [ "$KODE_HTTP" = "000" ]; then
  kuning "  Belum menjawab. Sertifikat bisa butuh waktu; periksa: docker logs $PROXY_CONTAINER"
else
  hijau "  Menjawab."
fi

echo
hijau "SELESAI. Tumpukan '$SLUG' berjalan di ${ALAMAT}"
echo
echo "Yang masih harus dikerjakan manusia:"
echo "  1. Buka ${ALAMAT}/god-mode/ dan daftarkan admin instance pertama pelanggan."
echo "  2. Pastikan CONTROL_PLANE_URL di ${ENV_FILE} terisi, kalau tidak"
echo "     tingkatan pelanggan ini tidak akan pernah diperbarui dari pusat."
echo "  3. Tunggu satu jam, lalu pastikan denyutnya muncul di /control/companies/."
