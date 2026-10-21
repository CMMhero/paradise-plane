#!/usr/bin/env bash
# Tunggu sampai tag `latest` di GHCR menunjuk build dari commit tertentu.
#
# KENAPA SKRIP INI ADA
# CI mendorong tag SHA LEBIH DULU, lalu menggeser `latest` di langkah terpisah
# (`imagetools create`). `deploy.sh` menarik `latest`. Jadi memakai kemunculan
# tag SHA sebagai tanda "siap deploy" akan menarik image LAMA, dan deploy
# melaporkan SEHAT tanpa membawa perubahan apa pun. Sudah terjadi 2026-08-11.
#
# Skrip ini sengaja hidup di server, bukan dirangkai dari sisi laptop: dua
# percobaan sebelumnya rusak karena kutipan hancur saat melewati PowerShell dan
# SSH, dan yang paling berbahaya, rusaknya SENYAP. Pembandingnya gagal parse,
# hasilnya dianggap "belum cocok", lalu deploy dibatalkan tanpa alasan benar.
#
# Pakai:
#   ./paradise/bin/tunggu-latest.sh <sha-penuh> [menit-maks]
# Keluar 0 = latest sudah menunjuk build itu, aman deploy.

set -uo pipefail

SHA="${1:?sha penuh wajib diisi}"
MAKS="${2:-25}"
# Namespace GHCR, wajib huruf kecil, dan wajib diisi. Sengaja tanpa nilai
# bawaan, sama seperti docker-compose.ghcr.yml, supaya keduanya tidak pernah
# menunjuk tempat berbeda dan tidak ada yang menunggui image milik akun lain.
IMG="ghcr.io/${GHCR_OWNER:?wajib diisi di .env, tidak ada nilai bawaan}/plane-backend"

# Ambil digest manifest teratas dan bersihkan tanda baca JSON-nya.
digest() {
  docker manifest inspect "$1" 2>/dev/null | grep -m1 digest | tr -d ' ",' | cut -d: -f2-
}

for i in $(seq 1 "$MAKS"); do
  sha_digest=$(digest "$IMG:$SHA")

  if [ -z "$sha_digest" ]; then
    echo "menit $i: membangun"
  else
    latest_digest=$(digest "$IMG:latest")
    if [ "$latest_digest" = "$sha_digest" ]; then
      echo "menit $i: COCOK, latest sudah menunjuk $SHA"
      exit 0
    fi
    echo "menit $i: tag SHA ada, latest belum digeser"
  fi

  sleep 60
done

echo "TIMEOUT setelah $MAKS menit: latest tidak pernah menunjuk $SHA"
exit 1
