#!/usr/bin/env bash
# Jalankan deploy TERLEPAS dari sesi SSH yang memicunya.
#
# KENAPA SKRIP INI ADA
# 13 Agt 2026 produksi sempat 502 beberapa menit. Sebabnya bukan kodenya:
# deploy dipanggil lewat satu perintah SSH panjang, lalu koneksinya putus tepat
# saat container sedang dibuat ulang. `docker compose up -d` mati di tengah
# jalan, dan `api`, `web`, serta `live` tinggal berhenti tanpa pengganti.
#
# Deploy tidak boleh punya nasib yang sama dengan koneksi yang memicunya.
# setsid + nohup melepasnya dari terminal pemanggil, jadi SSH boleh putus,
# laptop boleh mati, deploy tetap sampai selesai.
#
# Pakai:
#   ./paradise/bin/deploy-lepas.sh          # mulai, langsung kembali
#   tail -f ~/paradise-app/logs/deploy-*.log  # ikuti jalannya
#
# Keluaran lengkapnya ditulis ke berkas log, BUKAN ke stdout: yang memanggil
# sudah pergi, dan keluaran yang tidak ada pembacanya akan hilang.
set -euo pipefail

cd "$(dirname "$0")/../.."
mkdir -p logs
log="logs/deploy-$(date +%Y%m%d-%H%M%S).log"

# Berkas penanda supaya dua deploy tidak berjalan bersamaan. Dua `compose up`
# yang bertabrakan bisa meninggalkan container setengah jadi, persis keadaan
# yang sedang dicegah skrip ini.
kunci="logs/deploy.lock"
if [ -e "$kunci" ]; then
  pid=$(cat "$kunci" 2>/dev/null || echo "")
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    echo "Deploy lain masih jalan (pid $pid). Batal."
    exit 1
  fi
  echo "Penanda basi ditemukan, dibersihkan."
  rm -f "$kunci"
fi

setsid nohup bash -c '
  echo $$ > logs/deploy.lock
  trap "rm -f logs/deploy.lock" EXIT
  ./paradise/bin/deploy.sh
' >"$log" 2>&1 < /dev/null &

echo "Deploy dilepas. Log: $log"
echo "Ikuti dengan: tail -f $log"
