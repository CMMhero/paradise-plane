#!/usr/bin/env bash
# Kustomisasi Paradise Task Tracker: keadaan server, menyeluruh
#
#   sudo status              # potret lengkap sekali jalan (sekitar 30 detik)
#   sudo status --ringkas    # hanya bagian yang cepat (sekitar 10 detik)
#   sudo status --pantau     # ulangi bagian cepat terus-menerus, jeda 5 detik
#   sudo status --pantau 30  # ganti jedanya
#
# Potret lengkap lebih lama karena ia memuat Django di dalam container untuk
# memeriksa migrasi dan task terjadwal. Itu wajar, dan itulah sebabnya --pantau
# tidak ikut melakukannya.
#
# Baca-saja. Tidak menyentuh, menyalakan, atau mematikan apa pun, jadi aman
# dijalankan kapan saja termasuk saat sedang ada masalah.
#
# Kode keluar: 0 kalau semuanya sehat, 1 kalau ada yang perlu dilihat. Jadi bisa
# dipakai cron atau pemantauan tanpa perlu membaca teksnya.

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

PANTAU=0
SELANG=5
RINGKAS=0
sisa_arg=("$@")
i=0
while [ "$i" -lt "${#sisa_arg[@]}" ]; do
  case "${sisa_arg[$i]}" in
    --pantau|-w)
      PANTAU=1
      berikut="${sisa_arg[$((i + 1))]:-}"
      if [ -n "$berikut" ] && [ "$berikut" -eq "$berikut" ] 2>/dev/null; then SELANG="$berikut"; i=$((i + 1)); fi
      ;;
    --ringkas) RINGKAS=1 ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "Pilihan tidak dikenal: ${sisa_arg[$i]}" >&2; exit 2 ;;
  esac
  i=$((i + 1))
done

# Semua yang perlu dilihat manusia dikumpulkan di sini lalu dicetak sekali di
# bawah. Peringatan yang berserak di tengah keluaran sepanjang tiga layar sama
# saja dengan peringatan yang tidak pernah dibaca.
MASALAH=()
catat() { MASALAH+=("$1"); }

# ===========================================================================
# BAGIAN CEPAT: yang berubah dari detik ke detik. Ini yang diputar --pantau.
# ===========================================================================
bagian_cepat() {
  bar "MESIN"
  printf '  Waktu    : %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  printf '  Nyala    : %s\n' "$(uptime -p 2>/dev/null || echo '-')"
  printf '  Beban    : %s  (%s vCPU)\n' \
    "$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || echo '-')" "$(nproc 2>/dev/null || echo '?')"
  if command -v free >/dev/null 2>&1; then
    free -h | awk 'NR==2{printf "  Memori   : %s dipakai dari %s, tersedia %s\n",$3,$2,$7}
                   NR==3{printf "  Swap     : %s dipakai dari %s\n",$3,$2}'
  fi
  df -h / 2>/dev/null | awk 'NR==2 && $2 ~ /[0-9]/{printf "  Disk /   : %s dipakai dari %s (%s), sisa %s\n",$3,$2,$5,$4}'

  # Disk penuh adalah cara paling sering sebuah server yang "sehat" berhenti
  # bekerja: Postgres berhenti menerima tulisan jauh sebelum disknya betul-betul
  # habis. Diperiksa di sini, bukan diserahkan pada mata yang membaca sekilas.
  pakai="$(df -P / 2>/dev/null | awk 'NR==2{gsub(/%/,"",$5); print $5}')"
  if [ -n "${pakai:-}" ]; then
    [ "${pakai:-0}" -ge 90 ] 2>/dev/null && catat "disk root $pakai% penuh"
    { [ "${pakai:-0}" -ge 80 ] && [ "${pakai:-0}" -lt 90 ]; } 2>/dev/null && catat "disk root $pakai% terpakai, mulai perlu diperhatikan"
  fi

  bar "DAEMON DOCKER"
  if docker_hidup; then
    ok "jalan  ($(docker version --format '{{.Server.Version}}' 2>/dev/null))"
    systemctl is-enabled docker >/dev/null 2>&1 ||
      { warn "TIDAK otomatis nyala saat boot"; catat "docker tidak enabled di systemd"; }
  else
    gagal "TIDAK JALAN. Semua di bawah ini tidak bisa diperiksa."
    catat "daemon Docker mati"
    return 1
  fi

  bar "CONTAINER"
  printf '  %-14s %-10s %-9s %-8s %s\n' LAYANAN KEADAAN SEHAT ULANG SEJAK
  "${C[@]}" ps -a --format '{{.Service}}\t{{.Name}}' 2>/dev/null | sort | while IFS=$'\t' read -r svc nama; do
    [ -n "$nama" ] || continue
    keadaan="$(docker inspect -f '{{.State.Status}}' "$nama" 2>/dev/null || echo '?')"
    sehat="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' "$nama" 2>/dev/null || echo '-')"
    ulang="$(docker inspect -f '{{.RestartCount}}' "$nama" 2>/dev/null || echo '?')"
    sejak="$(docker inspect -f '{{.State.StartedAt}}' "$nama" 2>/dev/null | cut -c1-19 | tr 'T' ' ')"
    printf '  %-14s %-10s %-9s %-8s %s\n' "$svc" "$keadaan" "$sehat" "$ulang" "$sejak"
  done

  # migrator memang berhenti sesudah selesai; itu bukan kegagalan.
  while IFS=$'\t' read -r svc nama; do
    [ -n "$nama" ] || continue
    keadaan="$(docker inspect -f '{{.State.Status}}' "$nama" 2>/dev/null || echo '?')"
    sehat="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}-{{end}}' "$nama" 2>/dev/null || echo '-')"
    ulang="$(docker inspect -f '{{.RestartCount}}' "$nama" 2>/dev/null || echo 0)"
    kode="$(docker inspect -f '{{.State.ExitCode}}' "$nama" 2>/dev/null || echo 0)"
    case "$svc" in
      migrator)
        [ "$keadaan" = "exited" ] && [ "$kode" != "0" ] && catat "migrator keluar dengan kode $kode"
        ;;
      *)
        [ "$keadaan" = "running" ] || catat "$svc tidak jalan (keadaan: $keadaan)"
        [ "$sehat" = "unhealthy" ] && catat "$svc dilaporkan unhealthy"
        # Restart yang menumpuk berarti container mati lalu dinyalakan lagi
        # berulang-ulang. Dari luar itu terlihat "running", dan itulah yang
        # membuatnya mudah terlewat.
        [ "$ulang" -gt 3 ] 2>/dev/null && catat "$svc sudah restart $ulang kali"
        ;;
    esac
  done < <("${C[@]}" ps -a --format '{{.Service}}\t{{.Name}}' 2>/dev/null)

  bar "PEMAKAIAN PER CONTAINER"
  docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" 2>/dev/null | sed 's/^/  /' | head -20

  bar "LAYANAN DALAM"
  cek() {
    if "$2" >/dev/null 2>&1; then ok "$1"; else gagal "$1 tidak menjawab"; catat "$1 tidak menjawab"; fi
  }
  cek "postgres  " probe_db
  cek "redis     " probe_redis
  cek "rabbitmq  " probe_mq
  cek "minio     " probe_minio

  # Gotenberg dipakai Wiki untuk mengubah Word/Excel/PowerPoint jadi PDF. Kalau
  # ia diam, Wiki tetap terlihat normal sampai ada yang membuka berkas Office.
  if batas_waktu 15 "${C[@]}" exec -T proxy sh -c 'wget -qO- --timeout=5 http://gotenberg:3000/health' 2>/dev/null | grep -q '"up"'; then
    ok "gotenberg "
  else
    warn "gotenberg tidak menjawab (Wiki tidak bisa menampilkan berkas Office)"
    catat "gotenberg tidak menjawab"
  fi

  # Antrean yang menumpuk = pekerja tidak menghabiskan pekerjaannya. Email,
  # pemberitahuan, dan penugasan-ke-DM semuanya lewat sini.
  antre="$(batas_waktu 20 "${C[@]}" exec -T plane-mq rabbitmqctl list_queues -p "$RABBITMQ_VHOST" name messages --quiet 2>/dev/null |
           awk '$1=="celery"{print $2}')"
  if [ -n "${antre:-}" ]; then
    printf '  antrean celery : %s pesan menunggu\n' "$antre"
    [ "${antre:-0}" -gt 100 ] 2>/dev/null && catat "antrean celery menumpuk ($antre pesan)"
  fi

  bar "HTTP  ($WEB_URL)"
  for p in / /api/instances/ /god-mode/ /spaces/ /live/health; do
    kode="$(curl -sL -o /dev/null -w '%{http_code}' --max-time 15 "${WEB_URL}${p}" 2>/dev/null)"
    # 308 sengaja TIDAK dianggap OK: artinya pengalihan http->https tidak sampai
    # tujuan. Caddy menjawab 308 bahkan saat aplikasinya mati, jadi menerimanya
    # membuat pemeriksaan ini lulus justru ketika rantai HTTPS-nya patah.
    case "$kode" in
      200|302) printf '  %sOK%s   %-18s %s\n' "$HIJAU" "$NOL" "$p" "$kode" ;;
      *) printf '  %sMASALAH%s %-18s %s\n' "$MERAH" "$NOL" "$p" "$kode"; catat "endpoint $p menjawab $kode" ;;
    esac
  done
}

# ===========================================================================
# BAGIAN LENGKAP: yang berubah lambat, dan mahal untuk diperiksa.
# ===========================================================================
bagian_lengkap() {
  bar "SERTIFIKAT TLS"
  host="$(printf '%s' "$WEB_URL" | sed -e 's#^https\?://##' -e 's#/.*##')"
  akhir="$(echo | openssl s_client -connect "$host:443" -servername "$host" 2>/dev/null |
           openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)"
  if [ -n "${akhir:-}" ]; then
    sisa=$(( ( $(date -d "$akhir" +%s 2>/dev/null || echo 0) - $(date +%s) ) / 86400 ))
    printf '  %-22s berlaku sampai %s (%s hari lagi)\n' "$host" "$akhir" "$sisa"
    # Caddy memperbarui sendiri di 30 hari terakhir. Kalau sisanya sudah di
    # bawah 21 hari, pembaruan otomatisnya berarti sudah gagal beberapa kali.
    [ "${sisa:-999}" -lt 21 ] 2>/dev/null && catat "sertifikat tinggal $sisa hari, pembaruan otomatis mungkin gagal"
  else
    warn "tidak bisa membaca sertifikat dari $host"
  fi

  bar "VOLUME DATA"
  proyek="$(basename "$AKAR_PARADISE")"
  for v in "${VOLUME_PENTING[@]}"; do
    if titik="$(docker volume inspect -f '{{.Mountpoint}}' "${proyek}_${v}" 2>/dev/null)"; then
      # Ukurannya hanya terbaca sebagai root: isi volume ada di dalam
      # /var/lib/docker yang tertutup untuk pengguna biasa. Dikatakan apa
      # adanya, bukan dibiarkan jadi tanda tanya yang terbaca seperti kerusakan.
      besar="$(du -sh "$titik" 2>/dev/null | cut -f1)"
      printf '  ada     %-28s %s\n' "${proyek}_${v}" "${besar:-(ukuran butuh sudo)}"
    else
      printf '  %sTIDAK ADA %s%s\n' "$MERAH" "${proyek}_${v}" "$NOL"
      catat "volume ${proyek}_${v} hilang"
    fi
  done
  docker system df 2>/dev/null | sed 's/^/  /'

  bar "VERSI TERPASANG"
  docker ps --format '{{.Names}}\t{{.Image}}' 2>/dev/null | grep -E 'ghcr\.io' | sort | sed 's/^/  /'
  printf '  commit repo   : %s  %s\n' \
    "$(gitp rev-parse --short HEAD 2>/dev/null || echo '-')" \
    "$(gitp log -1 --format=%s 2>/dev/null | cut -c1-60)"
  if gitp rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
    gitp fetch -q origin 2>/dev/null || true
    belakang="$(gitp rev-list --count HEAD..@{u} 2>/dev/null || echo '?')"
    if [ "$belakang" = "0" ]; then
      printf '  tertinggal    : tidak, sudah rilis terbaru\n'
    else
      printf '  tertinggal    : %s commit dari origin  <-- jalankan deploy.sh\n' "$belakang"
      catat "repo tertinggal $belakang commit dari origin"
    fi
  fi

  # Dibatasi waktu seperti probe lainnya: database yang menggantung, misalnya
  # karena satu transaksi menahan kunci, tidak boleh membuat layar status ikut
  # membeku justru pada saat orang membukanya untuk mencari tahu kenapa
  # aplikasinya berhenti merespons.
  psql_t() { batas_waktu 20 "${C[@]}" exec -T plane-db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A "$@" 2>/dev/null; }

  # Semua di bawah butuh database hidup. Kalau mati, lewati dengan tenang
  # daripada memuntahkan galat psql beruntun yang menutupi bagian di atasnya.
  if psql_t -c "SELECT 1" >/dev/null 2>&1; then
    bar "DATABASE"
    printf '  ukuran       : %s\n' "$(psql_t -c "SELECT pg_size_pretty(pg_database_size(current_database()));")"
    sambung="$(psql_t -c "SELECT count(*) FROM pg_stat_activity;")"
    batas="$(psql_t -c "SHOW max_connections;")"
    printf '  sambungan    : %s dari %s\n' "$sambung" "$batas"
    printf '  transaksi terlama : %s\n' \
      "$(psql_t -c "SELECT COALESCE(max(now()-xact_start)::text,'-') FROM pg_stat_activity WHERE state<>'idle';")"

    bar "MIGRASI"
    printf '  terakhir  : %s\n' "$(psql_t -c "SELECT app||' '||name FROM django_migrations ORDER BY id DESC LIMIT 1;")"
    tertinggal="$(batas_waktu 30 "${C[@]}" exec -T api python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]')"
    if [ "${tertinggal:-0}" = "0" ]; then
      printf '  belum jalan: 0\n'
    else
      printf '  belum jalan: %s  <-- ada migrasi tertunda\n' "$tertinggal"
      catat "$tertinggal migrasi belum dijalankan"
    fi

    bar "ISI SISTEM"
    psql_t -F' : ' -c "
      SELECT 'user aktif', count(*) FROM users WHERE is_active AND NOT is_bot
      UNION ALL SELECT 'project', count(*) FROM projects WHERE deleted_at IS NULL
      UNION ALL SELECT 'work item', count(*) FROM issues WHERE deleted_at IS NULL
      UNION ALL SELECT 'halaman wiki', count(*) FROM pages WHERE deleted_at IS NULL
      UNION ALL SELECT 'lampiran', count(*) FROM file_assets WHERE is_uploaded
      UNION ALL SELECT 'instance admin', count(*) FROM instance_admins WHERE deleted_at IS NULL;" | sed 's/^/  /'

    bar "SESI & AKTIVITAS"
    printf '  sesi hidup     : %s\n' "$(psql_t -c "SELECT count(*) FROM sessions WHERE expire_date > now();")"
    printf '  login 24 jam   : %s\n' \
      "$(psql_t -c "SELECT count(*) FROM login_activities WHERE jenis='LOGIN' AND terjadi_pada > now() - interval '24 hours';")"
    printf '  pesan obrolan  : %s (%s belum dibaca)\n' \
      "$(psql_t -c "SELECT count(*) FROM direct_messages;")" \
      "$(psql_t -c "SELECT count(*) FROM direct_messages WHERE dibaca_pada IS NULL;")"

    bar "EMAIL"
    psql_t -F' : ' -c "
      SELECT key, CASE WHEN is_encrypted THEN '<terenkripsi>'
                       WHEN value IS NULL OR value='' THEN '<kosong>'
                       ELSE value END
      FROM instance_configurations
      WHERE key IN ('ENABLE_SMTP','EMAIL_HOST','EMAIL_PORT','EMAIL_HOST_USER','EMAIL_FROM')
      ORDER BY key;" | sed 's/^/  /'
  else
    bar "DATABASE"
    gagal "tidak bisa dihubungi, seluruh bagian yang bersandar padanya dilewati"
  fi

  bar "CELERY"
  # SATU panggilan untuk tiga jawaban, dan itu bukan kerapian melainkan waktu.
  # Tiap `exec` ke container worker memuat Django dari nol, dan itu sepuluh detik
  # sekali jalan; versi sebelumnya memanggilnya TIGA KALI (ping, registered,
  # beat_schedule) sehingga tiga puluh detik dari lima puluh satu detik seluruh
  # layar ini dihabiskan memuat Django yang sama berulang-ulang.
  #
  # Daftar task DIAMBIL dari beat_schedule yang sedang jalan, tidak ditulis
  # tangan. Daftar tulis tangan pasti ketinggalan begitu ada task baru, padahal
  # justru task barulah yang paling mungkin belum terdaftar.
  celery_out="$(batas_waktu 45 "${C[@]}" exec -T worker python -c '
from plane.celery import app
i = app.control.inspect(timeout=6)
print("PEKERJA", len(i.ping() or {}))
terdaftar = {t for v in (i.registered() or {}).values() for t in v}
for t in sorted({e["task"] for e in app.conf.beat_schedule.values()}):
    print("TASK", "ya" if t in terdaftar else "tidak", t)
' 2>/dev/null)"

  hidup="$(printf '%s\n' "$celery_out" | awk '$1=="PEKERJA"{print $2; exit}')"
  if [ "${hidup:-0}" -gt 0 ] 2>/dev/null; then
    ok "$hidup pekerja menjawab"
  else
    gagal "tidak ada pekerja yang menjawab"
    catat "tidak ada pekerja Celery yang menjawab"
  fi

  if ! printf '%s\n' "$celery_out" | grep -q '^TASK '; then
    info "(beat_schedule tidak terbaca dari worker)"
  else
    printf '  Task terjadwal:\n'
    while read -r penanda status tugas; do
      [ "$penanda" = "TASK" ] || continue
      if [ "$status" = "ya" ]; then
        printf '    %-58s terdaftar\n' "$tugas"
      else
        printf '    %-58s %sTIDAK TERDAFTAR%s\n' "$tugas" "$MERAH" "$NOL"
        catat "task terjadwal $tugas tidak terdaftar di worker"
      fi
    done <<< "$celery_out"
    info "(beat saja tidak cukup - task tak terdaftar dibuang diam-diam)"
  fi

  bar "BACKUP"
  if [ -d backups ] && [ -n "$(ls -A backups 2>/dev/null)" ]; then
    printf '  Jumlah   : %s berkas, total %s\n' "$(ls backups | wc -l)" "$(du -sh backups | cut -f1)"
    terbaru="$(ls -t backups | head -1)"
    umur=$(( ( $(date +%s) - $(stat -c %Y "backups/$terbaru" 2>/dev/null || echo 0) ) / 86400 ))
    printf '  Terbaru  : %s (%s hari lalu)\n' "$terbaru" "$umur"
    [ "${umur:-0}" -gt 7 ] 2>/dev/null && catat "backup terbaru sudah $umur hari"
  else
    gagal "BELUM ADA BACKUP di ./backups"
    catat "tidak ada backup sama sekali"
  fi

  bar "PEMERIKSAAN CEPAT"
  for f in .env apps/api/.env; do
    if [ ! -f "$f" ]; then
      printf '  %-16s TIDAK ADA\n' "$f"; catat "berkas $f tidak ada"; continue
    fi
    lemah="$(grep -cE '^(POSTGRES_PASSWORD|RABBITMQ_PASSWORD|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)="?(plane|access-key|secret-key)"?$' "$f")"
    if [ "$lemah" = "0" ]; then
      printf '  %-16s secret bukan nilai contoh\n' "$f"
    else
      printf '  %-16s %s SECRET MASIH NILAI CONTOH\n' "$f" "$lemah"
      catat "$f masih memakai $lemah secret contoh"
    fi
  done
  printf '  port terekspos  : %s\n' \
    "$(docker ps --format '{{.Ports}}' 2>/dev/null | grep -oE '0\.0\.0\.0:[0-9]+' | sort -u | tr '\n' ' ')"
  if [ -f /var/run/reboot-required ]; then
    printf '  reboot          : TERTUNDA (kernel baru terpasang)\n'
    catat "reboot tertunda karena kernel baru"
  else
    printf '  reboot          : tidak perlu\n'
  fi
}

# ===========================================================================
vonis() {
  bar "KESIMPULAN"
  # 🔴 Vonis yang tidak menyebutkan apa yang TIDAK diperiksa adalah vonis yang
  # menyesatkan. `--ringkas` dan `--pantau` melewati migrasi, sertifikat, backup,
  # dan reboot tertunda; tanpa baris ini, keduanya bisa mencetak "SEMUA SEHAT"
  # pada server yang sertifikatnya tinggal tiga hari.
  local sebagian=""
  [ "$RINGKAS" = "1" ] || [ "$PANTAU" = "1" ] &&
    sebagian="  (hanya bagian cepat; migrasi, sertifikat, backup, dan reboot TIDAK diperiksa)"

  if [ "${#MASALAH[@]}" -eq 0 ]; then
    printf '  %sSEMUA SEHAT.%s Tidak ada yang perlu dikerjakan.\n' "$HIJAU$TEBAL" "$NOL"
    [ -n "$sebagian" ] && printf '%s\n' "$sebagian"
    printf '\n'
    return 0
  fi
  [ -n "$sebagian" ] && printf '%s\n' "$sebagian"
  printf '  %s%s hal perlu dilihat:%s\n' "$MERAH$TEBAL" "${#MASALAH[@]}" "$NOL"
  for m in "${MASALAH[@]}"; do printf '    - %s\n' "$m"; done
  printf '\n'
  return 1
}

if [ "$PANTAU" = "1" ]; then
  # Yang diputar hanya bagian cepat. Kueri database, celery inspect, dan `du`
  # ke seluruh volume butuh beberapa detik dan isinya tidak berubah dari detik
  # ke detik; memutarnya tiap 5 detik cuma membebani server yang mungkin sedang
  # bermasalah, persis saat ia paling tidak boleh dibebani.
  trap 'printf "\n"; exit 0' INT
  lalu=""
  while true; do
    awal=$(date +%s)
    keluaran="$(MASALAH=(); bagian_cepat; vonis)"
    # Digambar ke layar SESUDAH semuanya terkumpul, bukan sambil dikerjakan.
    # Satu putaran butuh sekitar sepuluh detik, dan menggambar sedikit demi
    # sedikit selama itu membuat layarnya terlihat seperti sedang tersendat.
    clear
    printf '%sPANTAU LANGSUNG%s   %s   putaran sebelumnya %s   jeda %sd   Ctrl-C berhenti\n' \
      "$TEBAL" "$NOL" "$(date '+%H:%M:%S')" "${lalu:-?}" "$SELANG"
    printf '%s\n' "$keluaran"
    lalu="$(( $(date +%s) - awal ))d"
    sleep "$SELANG"
  done
fi

printf '%sKEADAAN SERVER PARADISE TASK TRACKER%s\n' "$TEBAL" "$NOL"
printf 'Project : %s\n' "$AKAR_PARADISE"

# Nilai kembalian bagian_cepat DIPAKAI. Kalau daemon Docker mati, bagian lengkap
# hanya akan memuntahkan galat berlembar-lembar dari tiap perintah docker, dan
# galat itu mengubur satu-satunya kalimat yang penting di layar ini.
if bagian_cepat; then
  [ "$RINGKAS" = "1" ] || bagian_lengkap
else
  info "(bagian lengkap dilewati karena Docker tidak bisa dihubungi)"
fi
vonis
