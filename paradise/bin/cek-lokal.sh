#!/usr/bin/env bash
# Gerbang lokal otomatis, dipanggil husky. Tidak perlu dijalankan tangan.
#
#   bash paradise/bin/cek-lokal.sh pre-commit   # cepat: berkas yang di-stage
#   bash paradise/bin/cek-lokal.sh pre-push     # seperti CI: format, lint, types
#
# pre-commit
#   - ruff pada .py yang di-stage. Gagal HANYA kalau galat sebuah berkas
#     bertambah dibanding versinya di HEAD. Main sudah punya ~150 galat ruff
#     (kebanyakan pola fixture pytest), jadi "nol galat" akan memblokir hampir
#     tiap commit dan akhirnya dilewati dengan --no-verify.
#   - `makemigrations --check` kalau model atau migrasi ikut di-stage: model
#     yang berubah tanpa berkas migrasi tertangkap di sini, bukan di produksi.
# pre-push
#   - `turbo check:format check:lint check:types --affected`, sama dengan CI.
#   - versi di apps/api/package.json wajib punya release_notes/<versi>.json dan
#     `### Versi <versi>` di CHANGELOG.md, persis yang ditolak rilis.sh.
#
# Lewati sekali (darurat): PARADISE_LEWATI_CEK=1 git commit ...
set -uo pipefail
cd "$(dirname "$0")/../.."

[ "${PARADISE_LEWATI_CEK:-0}" = "1" ] && { echo "cek-lokal: dilewati (PARADISE_LEWATI_CEK=1)"; exit 0; }

gagal=0
merah() { echo "cek-lokal: $*" >&2; gagal=1; }

hitung_ruff() { # <nama-berkas>; isi dari stdin
  uvx --quiet ruff check --quiet --output-format concise --stdin-filename "$1" - 2>/dev/null | grep -c ':[0-9]*:[0-9]*: ' || true
}

cek_ruff() {
  command -v uvx >/dev/null || { echo "cek-lokal: uvx tidak ada, ruff dilewati"; return; }
  mapfile -t py < <(git diff --cached --name-only --diff-filter=ACM -- 'apps/api/*.py')
  for f in "${py[@]}"; do
    baru=$(git show ":$f" | hitung_ruff "$f")
    lama=0
    git cat-file -e "HEAD:$f" 2>/dev/null && lama=$(git show "HEAD:$f" | hitung_ruff "$f")
    if [ "$baru" -gt "$lama" ]; then
      merah "ruff: $f punya $baru galat (HEAD: $lama). Lihat: uvx ruff check $f"
    fi
  done
}

jalankan_manage() { # perintah manage.py di container lokal, atau WSL
  local id
  id=$(docker compose -f docker-compose-local.yml ps -q api 2>/dev/null | head -1)
  if [ -n "$id" ]; then
    docker exec "$id" python manage.py "$@" --settings=plane.settings.local
  elif command -v wsl >/dev/null; then
    MSYS_NO_PATHCONV=1 wsl -d Ubuntu -- bash -c "~/plane-testenv/run.sh manage.py $* --settings=plane.settings.test"
  else
    return 127
  fi
}

cek_migrasi() {
  git diff --cached --name-only -- 'apps/api/plane/*/models/*' 'apps/api/plane/*/models.py' 'apps/api/plane/*/migrations/*' | grep -q . || return
  keluaran=$(jalankan_manage makemigrations --check --dry-run 2>&1)
  case $? in
    0) ;;
    127) echo "cek-lokal: tidak ada stack lokal maupun WSL, makemigrations --check dilewati" ;;
    *) merah "migrasi hilang: model berubah tanpa berkas migrasi"; echo "$keluaran" | tail -8 >&2 ;;
  esac
}

cek_catatan_rilis() {
  versi=$(grep -m1 '"version"' apps/api/package.json | sed 's/.*"version": *"\([^"]*\)".*/\1/')
  [ -f "apps/api/plane/release_notes/$versi.json" ] ||
    merah "apps/api/plane/release_notes/$versi.json tidak ada (kanal Changelog butuh ini)"
  grep -q "^### Versi $versi\b" CHANGELOG.md ||
    merah "CHANGELOG.md tidak punya '### Versi $versi'"
}

case "${1:-}" in
  pre-commit) cek_ruff; cek_migrasi ;;
  pre-push)
    cek_catatan_rilis
    # Klon ini dangkal dan origin/main tidak berbagi riwayat, jadi turbo tidak
    # menemukan basisnya sendiri lalu memeriksa SEMUA paket (4 menit).
    TURBO_SCM_BASE="$(git merge-base HEAD main 2>/dev/null || git rev-parse HEAD~1)" \
      pnpm turbo run check:format check:lint check:types --affected --continue --output-logs=errors-only || merah "turbo check gagal"
    ;;
  *) echo "pakai: cek-lokal.sh pre-commit|pre-push" >&2; exit 2 ;;
esac

[ "$gagal" = 0 ] || echo "cek-lokal: perbaiki dulu, atau darurat: PARADISE_LEWATI_CEK=1" >&2
exit "$gagal"
