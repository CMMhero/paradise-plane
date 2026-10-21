#!/usr/bin/env bash
# Kustomisasi Paradise Task Tracker: menghidupkan server
#
#   sudo hidupkan            # naikkan semuanya, berlapis, lalu buktikan sehat
#   sudo hidupkan --cepat    # lewati penantian kesiapan (jangan dipakai rutin)
#
# Kenapa tidak `docker compose up -d` saja. Perintah itu memang menyalakan semua
# container, dan itulah masalahnya: ia selesai begitu container DIBUAT, bukan
# begitu layanannya SIAP. Yang terjadi berikutnya selalu sama. `api` mencoba
# menyambung ke Postgres yang belum menerima sambungan, mati, dinyalakan lagi
# oleh `restart: always`, mati lagi. Dari luar itu terlihat seperti "sedang
# naik", dan orang menunggu sepuluh menit sebelum sadar tidak ada yang naik.
#
# Skrip ini menyalakan berlapis dari dalam ke luar, dan tiap lapis MENUNGGU
# lapis sebelumnya benar-benar menjawab sebelum lanjut.

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

CEPAT=0
for a in "$@"; do
  case "$a" in
    --cepat) CEPAT=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Pilihan tidak dikenal: $a" >&2; exit 2 ;;
  esac
done

wajib_root

mulai=$(date +%s)
printf '%sMenghidupkan Paradise Task Tracker%s\n' "$TEBAL" "$NOL"
printf 'Project : %s\n' "$AKAR_PARADISE"
printf 'Alamat  : %s\n' "$WEB_URL"

# --------------------------------------------------------------- daemon ------
langkah "Daemon Docker"
if docker_hidup; then
  ok "sudah jalan"
else
  info "belum jalan, menyalakan lewat systemd"
  systemctl start docker || { gagal "docker gagal dinyalakan, tidak ada gunanya melanjutkan"; exit 1; }
  tunggu "daemon docker" 60 docker_hidup || exit 1
fi

# Docker sendiri harus ikut nyala saat mesin di-boot. Kalau tidak, satu kali
# listrik padam berarti kantor menunggu seseorang datang dan mengetik perintah.
if ! systemctl is-enabled docker >/dev/null 2>&1; then
  warn "docker TIDAK otomatis nyala saat boot; jalankan: sudo systemctl enable docker"
fi

# ------------------------------------------------------------- volume --------
# Diperiksa SEBELUM apa pun dinyalakan. Volume yang hilang berarti container
# akan membuat volume kosong baru dengan nama yang sama, lalu aplikasi naik
# dengan gembira di atas database kosong. Lebih baik berhenti di sini dan
# bertanya, daripada naik sempurna tanpa isi.
langkah "Volume data"
proyek="$(basename "$AKAR_PARADISE")"
hilang=()
for v in "${VOLUME_PENTING[@]}"; do
  if docker volume inspect "${proyek}_${v}" >/dev/null 2>&1; then
    info "ada  ${proyek}_${v}"
  else
    hilang+=("${proyek}_${v}")
  fi
done
if [ "${#hilang[@]}" -gt 0 ]; then
  gagal "volume berikut TIDAK ADA: ${hilang[*]}"
  info "Kalau ini server yang baru dipasang, itu wajar dan akan dibuat sendiri."
  info "Kalau BUKAN, berhenti di sini: melanjutkan berarti menyalakan aplikasi"
  info "di atas penyimpanan kosong. Pulihkan dari backup dulu."
  printf '  Lanjutkan? ketik %sYA%s: ' "$TEBAL" "$NOL"
  read -r jawab
  [ "$jawab" = "YA" ] || { echo "Dibatalkan."; exit 1; }
fi

# --------------------------------------------------------------- data --------
langkah "Lapis 1/4: penyimpan (database, redis, antrean, berkas)"
"${C[@]}" up -d --no-deps "${LAPIS_DATA[@]}" || { gagal "gagal menyalakan lapis data"; exit 1; }

if [ "$CEPAT" = "0" ]; then
  # Postgres yang paling lama dan paling menentukan. 120 detik itu lebar dengan
  # sengaja: sesudah mati mendadak (listrik padam), Postgres memutar ulang WAL
  # sebelum menerima sambungan, dan itu bisa memakan waktu.
  tunggu "postgres"  120 probe_db    || { gagal "database tidak siap"; exit 1; }
  tunggu "redis"      60 probe_redis || warn "redis belum menjawab, dilanjutkan"
  tunggu "rabbitmq"  120 probe_mq    || warn "rabbitmq belum menjawab, dilanjutkan"
  tunggu "minio"      60 probe_minio || warn "minio belum menjawab, dilanjutkan"
fi

# ------------------------------------------------------------ migrasi --------
# Dijalankan sebagai LANGKAH TERSENDIRI yang ditunggu sampai selesai, bukan
# dibiarkan berjalan bersama yang lain.
#
# Kenapa penting: `api` tidak menunggu migrator. Kalau keduanya naik bersamaan
# sesudah deploy yang membawa migrasi, ada jendela waktu ketika aplikasi sudah
# melayani orang di atas skema database yang belum lengkap. Yang terlihat oleh
# pemakai bukan pesan galat yang jelas, melainkan kolom yang hilang di tengah
# halaman.
# 🔴 `run --rm`, BUKAN `up --exit-code-from migrator`. Yang kedua terlihat lebih
# tepat tapi membawa `--abort-on-container-exit`: begitu migrator selesai, ia
# menghentikan container lain dalam project ini. Artinya database yang baru saja
# susah payah dinaikkan ikut dimatikan, di tengah proses menyalakan. `run`
# menjalankan satu container sekali pakai, mengembalikan kode keluarnya, dan
# tidak menyentuh apa pun yang lain.
#
# `-T` dan `</dev/null` dengan alasan yang sama seperti probe di lib-server.sh:
# `run` menempelkan stdin, dan stdin yang berupa terminal membuatnya menunggu
# aliran yang tidak akan pernah ditutup. Keluarannya tetap terlihat, yang hilang
# cuma kemampuan mengetik ke dalamnya, dan migrasi memang tidak menanyakan
# apa-apa.
langkah "Lapis 2/4: migrasi database"
if "${C[@]}" run --rm -T --no-deps migrator </dev/null; then
  ok "migrasi selesai"
else
  gagal "MIGRASI GAGAL. Aplikasi TIDAK dinaikkan."
  info "Lihat sebabnya:  docker compose logs migrator | tail -50"
  info "Menaikkan aplikasi di atas skema yang setengah jadi jauh lebih buruk"
  info "daripada kantor yang menunggu sepuluh menit lagi."
  exit 1
fi

# ------------------------------------------------------- aplikasi ------------
langkah "Lapis 3/4: aplikasi, pekerja, dan pendukung"
"${C[@]}" up -d --no-deps "${LAPIS_PENDUKUNG[@]}" "${LAPIS_PEKERJA[@]}" "${LAPIS_APLIKASI[@]}" ||
  { gagal "gagal menyalakan lapis aplikasi"; exit 1; }

# --------------------------------------------------------- gerbang -----------
langkah "Lapis 4/4: gerbang (proxy)"
"${C[@]}" up -d "${LAPIS_GERBANG[@]}" || { gagal "gagal menyalakan proxy"; exit 1; }

# ------------------------------------------------------- pembuktian ----------
# Yang dilaporkan bukan "perintah sudah dijalankan" melainkan "aplikasinya
# menjawab". Keduanya berbeda, dan yang kedua yang ditanyakan orang.
langkah "Membuktikan aplikasinya benar-benar melayani"
if [ "$CEPAT" = "1" ]; then
  warn "dilewati karena --cepat; jalankan 'sudo status' untuk memastikan"
else
  # Batas 180 detik: gunicorn perlu memuat Django, dan sesudah mesin baru boot
  # semuanya lebih lambat karena disk dan CPU diperebutkan banyak container.
  tunggu "api menjawab" 180 probe_api || {
    gagal "aplikasi belum menjawab di $WEB_URL/api/instances/"
    info "Container mungkin sudah naik tapi ada yang salah di dalamnya."
    info "Periksa:  sudo status"
    exit 1
  }
fi

# ---------------------------------------------------------- ringkasan --------
bar "HASIL"
"${C[@]}" ps --format "table {{.Service}}\t{{.State}}\t{{.Status}}" 2>/dev/null

# `migrator` yang keluar dengan kode 0 itu BENAR, bukan kegagalan. Tanpa
# pengecualian ini, tiap kali skrip ini jalan ia akan mengeluh soal satu-satunya
# container yang memang seharusnya berhenti.
belum="$("${C[@]}" ps -a --format '{{.Service}} {{.State}}' 2>/dev/null |
         grep -v '^migrator ' | grep -viE 'running|up' || true)"

detik=$(( $(date +%s) - mulai ))
if [ -n "$belum" ]; then
  printf '\n'; gagal "ada yang belum jalan setelah ${detik}s:"
  echo "$belum" | sed 's/^/    /'
  info "Rinciannya:  sudo status"
  exit 1
fi

printf '\n'
ok "semua layanan hidup dalam ${detik} detik"
info "Buka: $WEB_URL"
info "Periksa kapan saja:  sudo status"
