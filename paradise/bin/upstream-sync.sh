#!/usr/bin/env bash
# Sinkronisasi dengan upstream (makeplane/plane).
#
# Repo ini di-VENDOR, bukan di-fork: berkasnya disalin, jadi tidak ada leluhur
# bersama dengan upstream. `git merge` menolak bekerja. Jalan satu-satunya
# adalah patch tiga arah per commit, yang juga memberi granularitas: satu
# commit bermasalah tidak menggagalkan 24 lainnya.
#
#   ./paradise/bin/upstream-sync.sh check              apa yang baru sejak baseline
#   ./paradise/bin/upstream-sync.sh apply [tag]        terapkan (default: tag rilis terbaru)
#   ./paradise/bin/upstream-sync.sh verify             kustomisasi kita masih utuh?
#
# Status tersimpan di paradise/upstream-sync.json. Baca itu dulu sebelum apa pun.

set -uo pipefail
cd "$(dirname "$0")/../.."

STATE=paradise/upstream-sync.json
# tr -d '\r' wajib: python di Windows menulis CRLF, dan `read` menyimpan \r itu
# di ujung nilainya, path jadi "apps/web/ce\r" dan setiap tes keberadaan berkas
# meleset, melaporkan kustomisasi HILANG padahal ada. Ditambal di sini, satu
# tempat, supaya semua pemanggil aman.
j() { python -c "import json,sys;d=json.load(open('$STATE',encoding='utf-8'));print($1)" | tr -d '\r'; }

BASELINE=$(j "d['baseline']['commit']")
REMOTE_BRANCH=$(j "d['upstream']['branch_rilis']")

# ── check ────────────────────────────────────────────────────────────────────
cmd_check() {
  git fetch upstream --tags --quiet || { echo "gagal fetch upstream"; exit 1; }

  # Tag rilis, bukan ujung preview. preview berisi kerjaan setengah jadi;
  # tag sudah lewat QA mereka. Sync ke preview = jadi penguji beta orang lain.
  local target
  target=$(git tag -l 'v*' --sort=-v:refname | head -1)

  echo "baseline kita : $BASELINE ($(git log -1 --format=%cs "$BASELINE^{commit}"))"
  echo "tag terbaru   : $target ($(git log -1 --format=%cs "$target^{commit}"))"
  echo

  local n
  n=$(git rev-list --count "$BASELINE..$target" 2>/dev/null) || { echo "baseline tidak dikenal, sudah fetch --tags?"; exit 1; }
  if [ "$n" = 0 ]; then echo "sudah paling baru."; return; fi

  echo "$n commit baru:"
  git log --reverse --format='  %h  %s' "$BASELINE..$target"
  echo
  echo "yang akan dilewati (dari daftar 'lewati'):"
  j "'\n'.join('  %s  %s' % (x['commit'], x['judul']) for x in d['lewati']) or '  (kosong)'"
  echo
  echo "dugaan perbaikan keamanan: $(git log --format=%s "$BASELINE..$target" | grep -ciE 'security|xss|injection|takeover|auth|csrf|leak|scope|permission')"
  echo
  echo "$target" > /tmp/.upstream-target
}

# ── apply ────────────────────────────────────────────────────────────────────
cmd_apply() {
  local target="${1:-$(git tag -l 'v*' --sort=-v:refname | head -1)}"
  [ -n "$(git status --porcelain)" ] && { echo "working tree kotor, commit atau stash dulu."; exit 1; }

  local skip
  skip=$(j "' '.join(x['commit'] for x in d['lewati'])")

  local ok=0 gagal=0 lewat=0
  : > /tmp/.upstream-gagal

  # --reverse: urutan kronologis. Patch commit belakangan sering bergantung
  # pada yang duluan; kebalik = konflik yang sebenarnya tidak ada.
  for c in $(git log --reverse --format=%h "$BASELINE..$target"); do
    local judul; judul=$(git log -1 --format=%s "$c")

    if echo "$skip" | grep -q "$c"; then
      printf '  LEWAT  %s  %s\n' "$c" "${judul:0:60}"; lewat=$((lewat+1)); continue
    fi

    if git show "$c" | git apply -3 - 2>/dev/null; then
      printf '  ok     %s  %s\n' "$c" "${judul:0:60}"; ok=$((ok+1))
    else
      printf '  GAGAL  %s  %s\n' "$c" "${judul:0:60}"; gagal=$((gagal+1))
      echo "$c $judul" >> /tmp/.upstream-gagal
    fi
  done

  echo
  echo "berhasil $ok · dilewati $lewat · gagal $gagal"
  if [ "$gagal" -gt 0 ]; then
    echo
    echo "Yang gagal harus dikerjakan TANGAN, satu per satu:"
    cat /tmp/.upstream-gagal
    echo
    echo "  git show <commit> -- <berkas>     lihat maunya apa"
    echo "  git diff                          lihat konflik yang tertinggal"
    echo
    echo "Aturan saat memutuskan: kalau baris yang bentrok itu KUSTOMISASI kita"
    echo "(debranding, gate Wiki, Super Admin tersembunyi), pertahankan punya kita."
    echo "Kalau itu perbaikan keamanan mereka, ambil punya mereka, lalu pasang"
    echo "ulang kustomisasi kita di atasnya. Jangan pilih salah satu buta-buta."
  fi
  echo
  echo "Selanjutnya: ./paradise/bin/upstream-sync.sh verify"
}

# ── verify ───────────────────────────────────────────────────────────────────
cmd_verify() {
  local rusak=0
  # Branch tujuan merge. Di branch sync, ini yang benar. Kalau kebetulan sudah
  # di main, bandingkan working tree dengan HEAD.
  local BASE="${1:-main}"
  [ "$(git rev-parse --abbrev-ref HEAD)" = "$BASE" ] && BASE=HEAD
  echo "pembanding: $BASE"
  echo

  echo "berkas kustomisasi yang harus ada:"
  while read -r f; do
    [ -z "$f" ] && continue
    if [ -e "$f" ]; then printf '  ada     %s\n' "$f"
    else printf '  HILANG  %s\n' "$f"; rusak=1; fi
  done < <(j "'\n'.join(d['harus_selamat']['berkas'])")

  echo
  echo "folder yang tidak boleh kehilangan berkas:"
  while read -r dir; do
    [ -z "$dir" ] && continue
    # Jebakan aslinya: refactor konsolidasi upstream MENGHAPUS 162 berkas di
    # apps/web/ce/. Yang berbahaya penghapusan, bukan perubahan isi, berkas
    # yang lenyap membuat fitur hilang diam-diam, tanpa error.
    #
    # Dibandingkan dengan BASE (default main), bukan HEAD: sekali hasil sync
    # di-commit, `git diff HEAD` selalu kosong dan pemeriksaan ini lolos palsu
    # justru saat paling dibutuhkan, sesaat sebelum merge.
    local hapus
    hapus=$(git diff --diff-filter=D --name-only "$BASE" -- "$dir" | wc -l)
    if [ "$hapus" = 0 ]; then printf '  utuh    %s (%s berkas)\n' "$dir" "$(find "$dir" -type f | wc -l)"
    else printf '  %s BERKAS TERHAPUS di %s\n' "$hapus" "$dir"; rusak=1; fi
  done < <(j "'\n'.join(d['harus_selamat']['folder_tanpa_penghapusan'])")

  echo
  echo "typecheck:"
  for p in apps/web apps/admin apps/space packages/constants packages/services packages/i18n; do
    if (cd "$p" && npx tsc --noEmit -p tsconfig.json >/dev/null 2>&1); then printf '  ok      %s\n' "$p"
    else printf '  GAGAL   %s\n' "$p"; rusak=1; fi
  done

  echo
  [ "$rusak" = 0 ] && echo "SEMUA AMAN." || echo "ADA YANG RUSAK, jangan merge ke main sebelum beres."
  return "$rusak"
}

case "${1:-check}" in
  check)  cmd_check ;;
  apply)  cmd_apply "${2:-}" ;;
  verify) cmd_verify "${2:-main}" ;;
  *) echo "pakai: $0 {check|apply [tag]|verify [branch-pembanding]}"; exit 1 ;;
esac
