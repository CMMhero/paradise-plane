#!/usr/bin/env bash
# Kustomisasi Paradise Task Tracker: bagian bersama perintah server
#
# Disumber (`source`) oleh hidupkan.sh, matikan.sh, dan status.sh. Bukan untuk
# dijalankan sendiri.
#
# Kenapa ada berkas ini: ketiga perintah itu harus sepakat soal hal-hal yang
# kalau berbeda akan berbahaya, terutama URUTAN LAYANAN. Urutan mematikan yang
# tidak cermin dari urutan menghidupkan adalah cara paling halus kehilangan data:
# proses yang dimatikan sebelum yang bergantung padanya akan ditinggalkan
# separuh jalan. Satu daftar, dipakai bersama.

# ---------------------------------------------------------------------------
# Letak project. TIDAK PERNAH diambil dari direktori kerja: perintah ini
# dipanggil dari mana saja lewat /usr/local/bin, dan `docker compose` yang
# dijalankan di direktori yang salah akan membuat PROJECT BARU yang kosong
# alih-alih menyentuh yang sedang jalan. Yang terlihat: "semua container mati"
# padahal semuanya baik-baik saja beberapa direktori di sebelah.
#
# Tiga sumber, diperiksa berurutan:
#   1. env AKAR_PARADISE          untuk menguji, atau kalau ada lebih dari satu
#   2. dua tingkat di atas lib    saat dijalankan langsung dari dalam repo
#   3. /usr/local/lib/paradise/akar   saat dipanggil sebagai perintah sistem
#
# Nomor 2 hanya dipakai kalau di sana MEMANG ada docker-compose.yml. Salinan
# terpasang tinggal di /usr/local/lib/paradise, dan dua tingkat di atasnya
# adalah /usr/local yang jelas bukan project; tanpa pemeriksaan itu, perintah
# terpasang akan menunjuk ke tempat yang salah tanpa mengeluh.
# ---------------------------------------------------------------------------
_dari_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)"
if [ -z "${AKAR_PARADISE:-}" ] && [ -n "$_dari_repo" ] && [ -f "$_dari_repo/docker-compose.yml" ]; then
  AKAR_PARADISE="$_dari_repo"
fi
if [ -z "${AKAR_PARADISE:-}" ] && [ -f /usr/local/lib/paradise/akar ]; then
  AKAR_PARADISE="$(cat /usr/local/lib/paradise/akar)"
fi
if [ -z "${AKAR_PARADISE:-}" ] || [ ! -f "$AKAR_PARADISE/docker-compose.yml" ]; then
  echo "Direktori project tidak ditemukan: ${AKAR_PARADISE:-<kosong>}" >&2
  echo "Pasang ulang dengan: sudo <repo>/paradise/bin/pasang-perintah.sh" >&2
  exit 1
fi
cd "$AKAR_PARADISE" || exit 1

C=(docker compose -f docker-compose.yml -f docker-compose.ghcr.yml)
[ -f docker-compose.ghcr.yml ] || C=(docker compose -f docker-compose-local.yml)

# ---------------------------------------------------------------------------
# URUTAN LAYANAN, dari paling luar ke paling dalam.
#
# Menghidupkan berjalan dari BAWAH ke ATAS daftar ini, mematikan dari ATAS ke
# BAWAH. Jadi database selalu yang pertama siap dan yang terakhir berhenti, dan
# proxy selalu yang terakhir menerima tamu dan yang pertama menutup pintu.
#
# `migrator` sengaja TIDAK ada di sini. Ia sekali jalan lalu keluar (restart:
# no), jadi ia bukan sesuatu yang "dinyalakan" atau "dimatikan"; hidupkan.sh
# menanganinya sendiri sebagai satu langkah tersendiri.
# ---------------------------------------------------------------------------

# Lapis 1, pintu masuk. Berhenti duluan supaya tidak ada permintaan baru masuk
# ke aplikasi yang sedang dibongkar.
LAPIS_GERBANG=(proxy)

# Lapis 2, yang dilihat orang.
LAPIS_APLIKASI=(web admin space live api)

# Lapis 3, yang bekerja di belakang. Diberi waktu berhenti paling lama: SIGTERM
# ke Celery berarti "selesaikan dulu tugas yang sedang dikerjakan", dan memotong
# di tengah berarti kirim email separuh atau tugas berulang yang tercatat sudah
# dibuat padahal belum.
LAPIS_PEKERJA=(worker beat-worker)

# Lapis 4, pelayan tambahan. Tidak menyimpan apa pun yang tidak bisa dibuat lagi.
LAPIS_PENDUKUNG=(livekit coturn gotenberg)

# Lapis 5, penyimpan. Paling akhir berhenti, paling awal hidup.
LAPIS_DATA=(plane-minio plane-mq plane-redis plane-db)

# ---------------------------------------------------------------------------
# Volume yang isinya TIDAK BISA dibuat ulang. Dipakai sebagai daftar periksa,
# dan sebagai pengingat kenapa tidak satu pun perintah di sini boleh menyentuh
# `docker compose down -v`, `docker volume prune`, atau `docker system prune
# --volumes`.
#
#   pgdata       seluruh isi aplikasi. Hilang berarti selesai.
#   uploads      semua lampiran dan materi Wiki.
#   caddy_data   sertifikat TLS. Let's Encrypt cuma memberi LIMA per minggu,
#                jadi menghapusnya bisa berarti kantor tanpa HTTPS berhari-hari.
# ---------------------------------------------------------------------------
VOLUME_PENTING=(pgdata uploads caddy_data rabbitmq_data redisdata caddy_config)

# ---------------------------------------------------------------------------
# Tampilan
# ---------------------------------------------------------------------------
if [ -t 1 ] && [ "${NO_COLOR:-}" = "" ]; then
  TEBAL=$'\033[1m'; MERAH=$'\033[31m'; HIJAU=$'\033[32m'; KUNING=$'\033[33m'; BIRU=$'\033[36m'; NOL=$'\033[0m'
else
  TEBAL=""; MERAH=""; HIJAU=""; KUNING=""; BIRU=""; NOL=""
fi

bar()   { printf '\n%s== %s ==%s\n' "$TEBAL" "$1" "$NOL"; }
ok()    { printf '  %sOK%s   %s\n'    "$HIJAU"  "$NOL" "$1"; }
warn()  { printf '  %sHATI%s %s\n'    "$KUNING" "$NOL" "$1"; }
gagal() { printf '  %sMASALAH%s %s\n' "$MERAH"  "$NOL" "$1"; }
info()  { printf '  %s\n' "$1"; }
langkah() { printf '\n%s-> %s%s\n' "$BIRU" "$1" "$NOL"; }

# ---------------------------------------------------------------------------
# Alamat yang dipakai orang, diambil dari .env.
#
# Bawaan `http://localhost` memeriksa hal yang keliru sejak HTTPS menyala: Caddy
# mengalihkannya ke `https://localhost`, nama host yang tidak punya sertifikat,
# sehingga jabat tangan TLS ditolak dan hasilnya tidak pernah 200 sekalipun
# aplikasinya sehat sempurna.
# ---------------------------------------------------------------------------
dari_env() { [ -f .env ] && grep -m1 "^$1=" .env 2>/dev/null | cut -d= -f2- | tr -d '"' | tr -d "'"; }

WEB_URL="${WEB_URL:-$(dari_env WEB_URL)}"
WEB_URL="${WEB_URL:-http://localhost}"

# Nama pengguna database dan vhost antrean DIBACA dari .env, bukan ditebak.
# Sebelumnya keduanya cuma punya nilai bawaan "plane" yang kebetulan benar di
# server ini. Kebetulan bukan alasan: begitu ada instance kedua dengan nama lain,
# `sudo status` akan melaporkan "postgres tidak menjawab" pada server yang
# sehat sempurna, dan itu jenis peringatan palsu yang membuat orang berhenti
# mempercayai seluruh layar ini.
POSTGRES_USER="${POSTGRES_USER:-$(dari_env POSTGRES_USER)}"
POSTGRES_USER="${POSTGRES_USER:-plane}"
POSTGRES_DB="${POSTGRES_DB:-$(dari_env POSTGRES_DB)}"
POSTGRES_DB="${POSTGRES_DB:-plane}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-$(dari_env RABBITMQ_VHOST)}"
RABBITMQ_VHOST="${RABBITMQ_VHOST:-plane}"

# ---------------------------------------------------------------------------
# Pemeriksa dasar
# ---------------------------------------------------------------------------

# Daemon Docker hidup? Semua yang lain tidak ada artinya kalau jawabannya tidak.
docker_hidup() { docker info >/dev/null 2>&1; }

# Nama container yang benar-benar ada, per service compose.
container_dari() { "${C[@]}" ps -a --format '{{.Service}} {{.Name}}' 2>/dev/null | awk -v s="$1" '$1==s{print $2; exit}'; }

# Menunggu sebuah syarat sampai terpenuhi atau waktunya habis.
# Dipakai untuk kesiapan yang SUNGGUHAN (pg_isready, redis PONG), bukan sekadar
# "containernya sudah dibuat". Container yang sudah berjalan tapi belum siap
# menerima sambungan adalah persis keadaan yang membuat `api` gagal start lalu
# masuk restart-loop, dan restart-loop itu terlihat seperti "sedang naik".
tunggu() {
  local nama="$1" batas="$2"; shift 2
  local i=0
  printf '     menunggu %s ' "$nama"
  while [ "$i" -lt "$batas" ]; do
    if "$@" >/dev/null 2>&1; then printf ' %ssiap%s (%sd)\n' "$HIJAU" "$NOL" "$i"; return 0; fi
    printf '.'; sleep 1; i=$((i + 1))
  done
  printf ' %sTIDAK SIAP setelah %sd%s\n' "$MERAH" "$batas" "$NOL"
  return 1
}

# 🔴 Tiap probe yang masuk ke dalam container DIBATASI WAKTU dan DIPUTUS dari
#    papan ketik.
#
# Dua hal berbeda, dan yang kedua ditemukan justru saat perintah ini pertama kali
# dijalankan manusia di terminal sungguhan.
#
# SATU, batas waktu. `docker compose exec` pada container yang menggantung akan
# menunggu selamanya, dan `sudo status` justru paling dibutuhkan ketika ada yang
# menggantung. `-k 5` menyusulkan KILL lima detik sesudah TERM, karena klien
# docker yang sedang menempel pada aliran data tidak selalu mau pergi hanya
# karena diminta baik-baik.
#
# DUA, `</dev/null`, dan ini yang sebenarnya menyelamatkan. `docker compose exec`
# MENEMPELKAN stdin, dan kalau stdin itu terminal sungguhan, ia menunggu aliran
# itu ditutup, yaitu tidak pernah. Perintahnya membeku, dan Ctrl-C pun ikut
# tertelan karena papan ketiknya sudah dipegang docker.
#
# ⚠️ Ini TIDAK terlihat kalau diuji lewat `ssh perintah` tanpa TTY, dan begitulah
# skrip ini sempat lolos uji: tanpa terminal, stdin sudah kosong sejak awal.
# Terbukti dengan `ssh -tt`: tanpa `</dev/null` menggantung sampai sambungannya
# diputus paksa, dengan `</dev/null` selesai dalam 1 detik.
batas_waktu() { timeout -k 5 "${1:-15}" "${@:2}" </dev/null; }

probe_db()    { batas_waktu 15 "${C[@]}" exec -T plane-db pg_isready -U "$POSTGRES_USER" -q; }
probe_redis() { batas_waktu 15 "${C[@]}" exec -T plane-redis redis-cli ping 2>/dev/null | grep -q PONG; }
probe_mq()    { batas_waktu 20 "${C[@]}" exec -T plane-mq rabbitmq-diagnostics -q ping; }
probe_minio() { batas_waktu 15 "${C[@]}" exec -T plane-minio curl -sf -o /dev/null http://localhost:9000/minio/health/live; }
probe_api()   { curl -fsSL --max-time 20 -o /dev/null "$WEB_URL/api/instances/"; }

# Git dijalankan sebagai root di repo milik pengguna `it`, dan git modern
# MENOLAK itu ("detected dubious ownership") lalu mengembalikan kosong. Akibatnya
# baris "commit repo" di layar status diam-diam berisi tanda hubung, dan orang
# menyimpulkan reponya rusak. Diberikan per pemanggilan, bukan disetel global:
# mengubah konfigurasi git milik root demi sebuah layar status adalah harga yang
# tidak sepadan.
gitp() { git -c safe.directory="$AKAR_PARADISE" "$@"; }

# Harus root? hidupkan dan matikan menyentuh daemon dan seluruh layanan kantor,
# jadi keduanya minta sudo. status baca-saja, jadi tidak.
wajib_root() {
  [ "$(id -u)" = "0" ] && return 0
  echo "Perintah ini harus dijalankan dengan sudo:  sudo $(basename "$0")" >&2
  exit 1
}
