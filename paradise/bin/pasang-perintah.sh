#!/usr/bin/env bash
# Kustomisasi Paradise Task Tracker: memasang perintah server
#
#   sudo ./paradise/bin/pasang-perintah.sh
#
# Sesudah ini tersedia dari mana saja di server:
#
#   sudo hidupkan     menyalakan seluruh tumpukan dengan tertib
#   sudo matikan      mematikannya dengan tertib
#   sudo status       melihat keadaannya (juga bisa tanpa sudo)
#
# Jalankan ulang tiap kali skripnya berubah di repo (mis. sesudah `git pull`).

set -euo pipefail

ASAL="$(cd "$(dirname "$0")" && pwd)"
TUJUAN=/usr/local/bin
PUSTAKA=/usr/local/lib/paradise

[ "$(id -u)" = "0" ] || { echo "Jalankan dengan sudo." >&2; exit 1; }

# ---------------------------------------------------------------------------
# DISALIN, bukan disambung dengan symlink ke /home/it.
#
# Symlink akan lebih praktis: `git pull` langsung memperbarui perintahnya. Tapi
# itu berarti root menjalankan berkas yang berada di direktori milik pengguna
# biasa. Siapa pun yang bisa menulis ke sana bisa menentukan apa yang dijalankan
# root, dan itu bukan kenyamanan yang pantas ditukar. Salinan ini milik root,
# dan diperbarui dengan menjalankan ulang pemasang ini secara sadar.
# ---------------------------------------------------------------------------
AKAR="$(cd "$ASAL/../.." && pwd)"
[ -f "$AKAR/docker-compose.yml" ] || { echo "Bukan direktori project: $AKAR" >&2; exit 1; }

install -d -m 755 "$PUSTAKA"
install -m 644 "$ASAL/lib-server.sh" "$PUSTAKA/lib-server.sh"

# Letak project dicatat sebagai berkas biasa, bukan disuntikkan ke dalam skrip.
# Skrip yang isinya ditulis ulang saat dipasang tidak lagi sama dengan yang ada
# di repo, dan begitu ada yang membacanya untuk mencari sebab sebuah masalah, ia
# membaca berkas yang berbeda dari yang dijalankan.
printf '%s\n' "$AKAR" > "$PUSTAKA/akar"
chmod 644 "$PUSTAKA/akar"

pasang() {
  local sumber="$1" nama="$2"
  install -m 755 "$sumber" "$TUJUAN/$nama"
  printf '  terpasang  %-12s -> %s\n' "$nama" "$TUJUAN/$nama"
}

pasang "$ASAL/hidupkan.sh" hidupkan
pasang "$ASAL/matikan.sh"  matikan
pasang "$ASAL/status.sh"   status
printf '  project    %s\n' "$AKAR"

echo
echo "Selesai. Coba:"
echo "  sudo status"
echo "  sudo status --pantau"
echo "  sudo hidupkan --help"
echo "  sudo matikan --help"
