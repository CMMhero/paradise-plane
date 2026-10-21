#!/usr/bin/env bash
# Kustomisasi Paradise Task Tracker: mematikan server dengan tertib
#
#   sudo matikan             # tanya dulu, lalu turunkan berlapis
#   sudo matikan -y          # tanpa bertanya (untuk skrip, mis. sebelum reboot)
#   sudo matikan --hapus     # sekalian hapus containernya (volume TETAP aman)
#
# 🔴 TIDAK ADA satu pun perintah di berkas ini yang menyentuh volume.
#    Tidak `down -v`, tidak `volume prune`, tidak `system prune --volumes`.
#    Kalau suatu saat ada yang menambahkannya "biar bersih", yang terhapus
#    adalah seluruh isi aplikasi, semua lampiran, dan sertifikat TLS yang cuma
#    boleh diterbitkan lima kali seminggu. Jangan.
#
# Kenapa tidak `docker compose stop` saja. Perintah itu mengirim SIGTERM ke
# semua container SEKALIGUS, lalu membunuh yang belum mati dalam 10 detik.
# Untuk tumpukan ini itu berarti dua hal buruk sekaligus: Postgres bisa terbunuh
# saat sedang menulis, dan Celery kehilangan tugas yang sedang dikerjakan di
# tengah jalan. Skrip ini menutup dari luar ke dalam, dan memberi tiap lapis
# waktu yang pantas.

set -uo pipefail
# Pustakanya dicari di sebelah skrip ini dulu (saat dijalankan langsung dari
# repo), baru di tempat pasangnya (saat dipanggil sebagai perintah sistem).
_diri="$(dirname "$(readlink -f "$0")")"
_lib=""
for _kandidat in "$_diri/lib-server.sh" /usr/local/lib/paradise/lib-server.sh; do
  [ -f "$_kandidat" ] && { _lib="$_kandidat"; break; }
done
[ -n "$_lib" ] || { echo "lib-server.sh tidak ditemukan" >&2; exit 1; }
# shellcheck source=lib-server.sh
. "$_lib"

TANYA=1
HAPUS=0
for a in "$@"; do
  case "$a" in
    -y|--ya) TANYA=0 ;;
    --hapus) HAPUS=1 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "Pilihan tidak dikenal: $a" >&2; exit 2 ;;
  esac
done

wajib_root

if ! docker_hidup; then
  warn "daemon Docker tidak jalan, berarti tidak ada yang perlu dimatikan"
  exit 0
fi

printf '%sMematikan Paradise Task Tracker%s\n' "$TEBAL" "$NOL"
printf 'Project : %s\n' "$AKAR_PARADISE"

bar "YANG SEDANG JALAN"
"${C[@]}" ps --format "table {{.Service}}\t{{.State}}\t{{.Status}}" 2>/dev/null

jumlah="$("${C[@]}" ps -q 2>/dev/null | wc -l | tr -d ' ')"
if [ "$jumlah" = "0" ]; then
  printf '\n'; ok "tidak ada container yang jalan, tidak ada yang perlu dilakukan"
  exit 0
fi

# Orang yang sedang memakai aplikasi TIDAK tahu ini akan terjadi. Menyebut
# angkanya membuat "matikan server" berhenti terasa seperti perintah tanpa
# akibat, dan itu memang bukan.
# Dibatasi waktu. Ini kueri BASA-BASI, cuma untuk memberi tahu berapa orang yang
# akan terputus. Kalau databasenya sendiri sedang bermasalah, ia tidak boleh
# menahan perintah yang justru dipanggil untuk mengatasi masalah itu.
sesi="$(batas_waktu 10 "${C[@]}" exec -T plane-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc \
        "SELECT count(*) FROM sessions WHERE expire_date > now();" 2>/dev/null | tr -d ' ')"
[ -n "${sesi:-}" ] && printf '\n  %sAda %s sesi login yang masih hidup.%s\n' "$KUNING" "$sesi" "$NOL"

if [ "$TANYA" = "1" ]; then
  printf '\n  Ini akan menghentikan %s container dan membuat aplikasi\n' "$jumlah"
  printf '  TIDAK BISA DIAKSES sampai "sudo hidupkan" dijalankan.\n'
  printf '  Data TIDAK dihapus.\n\n'
  printf '  Lanjutkan? ketik %sMATIKAN%s: ' "$TEBAL" "$NOL"
  read -r jawab
  [ "$jawab" = "MATIKAN" ] || { echo "Dibatalkan, tidak ada yang disentuh."; exit 1; }
fi

mulai=$(date +%s)

# `stop` per lapis, bukan sekaligus. `-t` diberikan per lapis karena yang
# pantas untuk gerbang (cepat) berbeda jauh dari yang pantas untuk Celery
# (selesaikan dulu) dan Postgres (tutup buku dengan rapi).
turunkan() {
  local judul="$1" batas="$2"; shift 2
  local ada=()
  for s in "$@"; do
    [ -n "$("${C[@]}" ps -q "$s" 2>/dev/null)" ] && ada+=("$s")
  done
  if [ "${#ada[@]}" -eq 0 ]; then
    printf '\n%s-> %s: sudah berhenti%s\n' "$BIRU" "$judul" "$NOL"
    return 0
  fi
  langkah "$judul (maks ${batas}s): ${ada[*]}"
  "${C[@]}" stop -t "$batas" "${ada[@]}" 2>&1 | sed 's/^/     /'
}

# 1. Pintu ditutup lebih dulu. Selama lapis di bawah masih dibongkar, permintaan
#    baru tidak boleh masuk dan menemui aplikasi separuh mati.
turunkan "Lapis 1/5: gerbang" 20 "${LAPIS_GERBANG[@]}"

# 2. Yang dilihat orang. Sudah tidak ada yang bisa mencapainya.
turunkan "Lapis 2/5: aplikasi" 30 "${LAPIS_APLIKASI[@]}"

# 3. Pekerja belakang. 120 detik: SIGTERM ke Celery artinya "habiskan dulu tugas
#    yang sedang dipegang". Memotongnya berarti email terkirim separuh, atau
#    tugas berulang yang sudah tercatat dibuat padahal barisnya belum ditulis.
turunkan "Lapis 3/5: pekerja latar" 120 "${LAPIS_PEKERJA[@]}"

# 4. Pendukung. Tidak menyimpan apa pun yang tidak bisa dibuat lagi.
turunkan "Lapis 4/5: pendukung" 30 "${LAPIS_PENDUKUNG[@]}"

# 5. Penyimpan, paling akhir. Postgres diberi 120 detik supaya sempat menuntaskan
#    checkpoint; dibunuh di tengah checkpoint berarti pemulihan WAL yang panjang
#    saat dinyalakan lagi, dan pada kasus terburuk kerusakan yang butuh backup.
turunkan "Lapis 5/5: penyimpan" 120 "${LAPIS_DATA[@]}"

# Termasuk `migrator` yang mungkin masih menggantung dari deploy yang gagal.
sisa="$("${C[@]}" ps -q 2>/dev/null | wc -l | tr -d ' ')"
if [ "$sisa" != "0" ]; then
  langkah "Sisa container yang belum disebut lapis mana pun"
  "${C[@]}" stop -t 30 2>&1 | sed 's/^/     /'
fi

if [ "$HAPUS" = "1" ]; then
  # `down` TANPA -v. Container dan jaringannya dibuang, volume tidak disentuh.
  # Ditulis eksplisit begini supaya siapa pun yang membacanya melihat sendiri
  # bahwa tidak ada bendera volume di sini.
  langkah "Menghapus container dan jaringan (volume TIDAK disentuh)"
  "${C[@]}" down --remove-orphans 2>&1 | sed 's/^/     /'
fi

bar "HASIL"
tersisa="$(docker ps --filter "label=com.docker.compose.project=$(basename "$AKAR_PARADISE")" \
           --format '{{.Names}}' 2>/dev/null)"
detik=$(( $(date +%s) - mulai ))

if [ -n "$tersisa" ]; then
  gagal "masih ada yang jalan setelah ${detik}s:"
  echo "$tersisa" | sed 's/^/    /'
  exit 1
fi

ok "semua container berhenti dengan tertib dalam ${detik} detik"

# Bukti bahwa yang penting memang tidak ikut hilang. Ditampilkan justru pada
# saat orang paling cemas, yaitu tepat sesudah mematikan segalanya.
printf '\n  Volume data AMAN dan tetap ada:\n'
proyek="$(basename "$AKAR_PARADISE")"
for v in "${VOLUME_PENTING[@]}"; do
  if docker volume inspect "${proyek}_${v}" >/dev/null 2>&1; then
    printf '    ada     %s\n' "${proyek}_${v}"
  else
    printf '    %sTIDAK ADA %s%s\n' "$MERAH" "${proyek}_${v}" "$NOL"
  fi
done

printf '\n  Menyalakan lagi:  %ssudo hidupkan%s\n' "$TEBAL" "$NOL"
