#!/usr/bin/env bash
# Satu perintah rilis dari LAPTOP: tunggu image commit ini siap di GHCR, backup
# database di server, deploy terlepas, ikuti sampai selesai, lalu cocokkan versi.
#
#   ./paradise/bin/rilis.sh              # commit terbaru di origin/main
#   ./paradise/bin/rilis.sh <sha-penuh>  # commit tertentu
#   RILIS_HOST=space ./paradise/bin/rilis.sh   # alias SSH server (bawaan: space)
#
# Butuh: alias SSH `space` di ~/.ssh/config, dan Docker di laptop (hanya untuk
# `docker manifest inspect`; paket GHCR-nya publik, jadi tanpa login).
#
# Kenapa lewat skrip, bukan dirangkai tangan: rangkaian SSH dari PowerShell
# pernah rusak SENYAP karena kutipan hancur, lalu deploy dibatalkan atau, lebih
# buruk, berjalan dengan image lama. Langkah yang rawan itu semua ada di sini.
set -euo pipefail

HOST="${RILIS_HOST:-space}"
cd "$(dirname "$0")/../.."

git fetch -q origin main
SHA="${1:-$(git rev-parse origin/main)}"
SHA="$(git rev-parse "$SHA")" # sha pendek jadi penuh; tag GHCR memakai sha penuh
VERSI="$(git show "$SHA:apps/api/package.json" | grep -m1 '"version"' | sed 's/.*"version": *"\([^"]*\)".*/\1/')"
echo "== Rilis $VERSI ($SHA) ke $HOST =="

# 0. Catatan rilis wajib ada di commit ini. Kanal Changelog hanya menerbitkan
#    versi yang punya `release_notes/<versi>.json`; tanpanya rilis naik tanpa
#    pengumuman apa pun dan tidak ada yang menyadarinya. CHANGELOG.md wajib
#    memuat entri versinya (KEP-48). Dicek sebelum menunggu CI 45 menit.
git cat-file -e "$SHA:apps/api/plane/release_notes/$VERSI.json" 2>/dev/null ||
  { echo "BATAL: apps/api/plane/release_notes/$VERSI.json tidak ada di $SHA."; exit 1; }
git show "$SHA:CHANGELOG.md" | grep -q "^### Versi $VERSI\b" ||
  { echo "BATAL: CHANGELOG.md di $SHA tidak punya '### Versi $VERSI'."; exit 1; }

# Namespace GHCR dibaca dari .env server supaya laptop dan server tidak pernah
# menunggui namespace yang berbeda.
GHCR_OWNER="${GHCR_OWNER:-$(ssh "$HOST" "grep -m1 '^GHCR_OWNER=' ~/paradise-app/.env | cut -d= -f2")}"
export GHCR_OWNER

# 1. CI harus sudah menggeser `latest` ke commit ini. Tag SHA saja belum cukup:
#    deploy.sh menarik `latest`. Lihat tunggu-latest.sh.
paradise/bin/tunggu-latest.sh "$SHA" "${RILIS_TUNGGU_MENIT:-45}"

# 2. Tarik skrip terbaru di server LEBIH DULU. deploy.sh menarik git sendiri,
#    tapi saat itu ia sudah berjalan: bash membaca skrip sambil jalan, jadi
#    berkas yang berubah di tengah eksekusi bisa menjalankan potongan acak, dan
#    deploy-lepas.sh yang dipanggil masih versi lama.
# 3. Backup dulu; kalau gagal, deploy tidak boleh jalan (karena itu `&&`).
# 4. Deploy dilepas dari sesi SSH, jadi koneksi yang putus tidak meninggalkan
#    container setengah jadi.
log="$(ssh "$HOST" 'cd ~/paradise-app && git pull -q --ff-only && ./paradise/bin/backup-db.sh >/dev/null && ./paradise/bin/deploy-lepas.sh' |
  sed -n 's/^Deploy dilepas. Log: //p')" || true
[ -n "$log" ] || { echo "Deploy tidak dimulai (backup gagal atau deploy lain masih jalan)."; exit 1; }
echo "Log server: ~/paradise-app/$log"

# 5. Ikuti sampai baris DEPLOY_EXIT muncul. `compose pull` bisa 10-14 menit;
#    jaraknya 30 detik supaya SSH tidak disodok terus selama unduhan.
for _ in $(seq 1 80); do
  sleep 30
  akhir="$(ssh "$HOST" "grep -m1 '^DEPLOY_EXIT=' ~/paradise-app/$log" 2>/dev/null || true)"
  [ -n "$akhir" ] && break
  echo "  $(ssh "$HOST" "tail -1 ~/paradise-app/$log" 2>/dev/null | cut -c1-120)"
done
ssh "$HOST" "grep -E 'Migrasi|MIGRASI|changelog:|CHANGELOG|SEHAT|MASALAH|Versi berjalan|DEPLOY_EXIT' ~/paradise-app/$log" || true

[ "${akhir:-}" = "DEPLOY_EXIT=0" ] || { echo "== DEPLOY GAGAL: ${akhir:-tidak selesai dalam 40 menit} =="; exit 1; }

# 6. Versi yang dilayani harus sama dengan versi commit ini.
berjalan="$(ssh "$HOST" "grep -m1 'Versi berjalan' ~/paradise-app/$log" | sed 's/.*Versi berjalan: \([^ ]*\).*/\1/')"
if [ "$berjalan" != "$VERSI" ]; then
  echo "== PERINGATAN: server melayani '$berjalan', commit ini $VERSI =="
  exit 1
fi
echo "== SELESAI: $VERSI live di $HOST =="
