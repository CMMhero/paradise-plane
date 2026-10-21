#!/usr/bin/env bash
# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
#
# Matikan tumpukan satu pelanggan SaaS dan cabut subdomainnya dari proxy.
#
#   sudo ./paradise/bin/tenant-down.sh acme
#
# 🔶 BELUM PERNAH DIJALANKAN SUNGGUHAN.
#
# ============================================================================
# TIDAK PERNAH MENGHAPUS VOLUME, DAN ITU BUKAN KELALAIAN
# ============================================================================
#
# `docker compose down` tanpa `-v` menghentikan container dan MEMBIARKAN
# volumenya. Itu memang yang diinginkan: database dan berkas pelanggan hidup di
# volume, dan menghapusnya adalah tindakan yang tidak bisa dibatalkan.
#
# Skrip ini sengaja TIDAK punya opsi `--hapus-data`. Menghapus data pelanggan
# harus terasa seperti keputusan, bukan seperti tanda hubung yang salah ketik.
# Perintahnya ditulis di keluaran, dan yang mau menjalankannya harus
# menyalinnya sendiri.
#
# Menghidupkan lagi cukup `tenant-up.sh` dengan berkas env yang sama; volumenya
# masih di tempatnya dan datanya utuh.

set -euo pipefail

SLUG="${1:-}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose-tenant.yml}"
CADDY_TENANT_DIR="${CADDY_TENANT_DIR:-/srv/caddy/tenants}"
PROXY_CONTAINER="${PROXY_CONTAINER:-nomaden-proxy-1}"

merah() { printf '\033[0;31m%s\033[0m\n' "$*"; }
hijau() { printf '\033[0;32m%s\033[0m\n' "$*"; }
kuning() { printf '\033[1;33m%s\033[0m\n' "$*"; }

[ -n "$SLUG" ] || { merah "Pemakaian: $0 <slug>"; exit 1; }
[ -f "$COMPOSE_FILE" ] || { merah "'$COMPOSE_FILE' tidak ada. Jalankan dari akar repo."; exit 1; }

# --- 1. Cabut dari proxy DULU, baru matikan ---------------------------------
#
# Urutannya disengaja. Kalau containernya dimatikan lebih dulu, Caddy masih
# mengarahkan ke hulu yang sudah mati dan pengunjung dapat 502 selama beberapa
# detik. Mencabut rutenya lebih dulu membuat mereka dapat jawaban proxy yang
# jelas, bukan galat yang tampak seperti kerusakan.

SITUS="${CADDY_TENANT_DIR}/${SLUG}.caddy"
if [ -f "$SITUS" ]; then
  rm -f "$SITUS"
  echo "Blok situs dibuang: $SITUS"
  if docker ps --format '{{.Names}}' | grep -qx "$PROXY_CONTAINER"; then
    if docker exec "$PROXY_CONTAINER" caddy reload --config /etc/caddy/Caddyfile 2>&1; then
      hijau "Caddy dimuat ulang."
    else
      kuning "Caddy menolak memuat ulang. Rutenya mungkin masih aktif; periksa: docker logs $PROXY_CONTAINER"
    fi
  else
    kuning "Container proxy tidak berjalan, muat ulang dilewati."
  fi
else
  kuning "Blok situs '$SITUS' tidak ada, dilewati."
fi

# --- 2. Matikan containernya ------------------------------------------------

echo
echo "Mematikan tumpukan '$SLUG' ..."
docker compose -p "$SLUG" -f "$COMPOSE_FILE" down

echo
hijau "SELESAI. Tumpukan '$SLUG' mati, VOLUMENYA UTUH."
echo
echo "Menghidupkan lagi:"
echo "  sudo ./paradise/bin/tenant-up.sh ${SLUG} /srv/tenants/${SLUG}.env"
echo
kuning "Menghapus datanya PERMANEN (tidak bisa dibatalkan, salin sendiri kalau memang mau):"
echo "  docker compose -p ${SLUG} -f ${COMPOSE_FILE} down -v"
