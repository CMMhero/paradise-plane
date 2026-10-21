#!/usr/bin/env bash
# Memasang aturan repositori GitHub: main tidak bisa didorong langsung, semua
# lewat Pull Request, dan wajib disetujui pemilik kode sebelum boleh di-merge.
#
#   paradise/bin/atur-github.sh [owner/repo]
#
# Tanpa argumen ia menyasar NomaX-Studio-Indonesia/Nomaden.
#
# Butuh `gh` yang sudah login DAN akses admin ke repo. Skrip ini tidak menyimpan
# atau meminta kredensial apa pun; seluruh autentikasi diserahkan ke `gh`.
#
# Aman dijalankan berulang kali. Ruleset dengan nama yang sama diperbarui, bukan
# digandakan.
set -euo pipefail

REPO="${1:-NomaX-Studio-Indonesia/Nomaden}"
NAMA_RULESET="main terlindungi"

merah=$'\033[0;31m'; hijau=$'\033[0;32m'; kuning=$'\033[1;33m'; tebal=$'\033[1m'; nc=$'\033[0m'
info()  { printf '%s\n' "$*"; }
ok()    { printf '%s\n' "${hijau}OK${nc} $*"; }
gagal() { printf '%s\n' "${merah}GAGAL${nc} $*" >&2; exit 1; }

# ── Pemeriksaan awal ────────────────────────────────────────────────────────
command -v gh >/dev/null 2>&1 || gagal \
  "\`gh\` tidak ada. Pasang dari https://cli.github.com/ lalu jalankan: gh auth login"

gh auth status >/dev/null 2>&1 || gagal \
  "\`gh\` belum login. Jalankan dulu: gh auth login"

info "${tebal}Repo   :${nc} $REPO"
info "${tebal}Ruleset:${nc} $NAMA_RULESET"
info ""

admin=$(gh api "repos/$REPO" --jq '.permissions.admin // false' 2>/dev/null) || gagal \
  "Tidak bisa membaca $REPO. Cek nama reponya, dan cek akun \`gh\` punya akses ke sana."

if [ "$admin" != "true" ]; then
  gagal "Akun \`gh\` yang aktif bukan admin di $REPO. Aturan repo hanya bisa dipasang oleh admin."
fi
ok "akses admin terkonfirmasi"

privat=$(gh api "repos/$REPO" --jq '.private')
cabang_utama=$(gh api "repos/$REPO" --jq '.default_branch')
ok "branch utama: $cabang_utama, repo privat: $privat"
info ""

# ── 1. Setelan repo ─────────────────────────────────────────────────────────
# Squash-only. Riwayat main jadi satu commit per PR, gampang dibaca dan
# gampang di-revert. Merge commit dan rebase dimatikan supaya tidak ada tiga
# bentuk riwayat yang bercampur di repo yang sama.
info "${tebal}1. Setelan repo${nc}"
gh api -X PATCH "repos/$REPO" \
  -F has_issues=true \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F allow_auto_merge=true \
  -F delete_branch_on_merge=true \
  -f squash_merge_commit_title=PR_TITLE \
  -f squash_merge_commit_message=PR_BODY \
  >/dev/null
ok "squash-only, branch dihapus otomatis sesudah merge, issue aktif"
info ""

# ── 2. Ruleset branch utama ─────────────────────────────────────────────────
# Status check yang diwajibkan SENGAJA hanya empat, semuanya dari
# pull-request-build-lint-web-apps.yml, satu-satunya workflow PR yang berjalan
# untuk SETIAP perubahan.
#
# `Lint API` dan `check:sync` TIDAK diwajibkan walaupun ada, karena keduanya
# memakai filter `paths`. Check wajib yang tidak pernah terpicu tidak dihitung
# gagal, ia menggantung di status pending selamanya, dan PR-nya tidak akan
# pernah bisa di-merge. Ini jebakan klasik, jangan tambahkan keduanya ke sini.
info "${tebal}2. Ruleset $cabang_utama${nc}"

muatan=$(cat <<JSON
{
  "name": "$NAMA_RULESET",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "required_linear_history" },
    {
      "type": "pull_request",
      "parameters": {
        "required_approving_review_count": 1,
        "require_code_owner_review": true,
        "dismiss_stale_reviews_on_push": true,
        "require_last_push_approval": true,
        "required_review_thread_resolution": true
      }
    },
    {
      "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": true,
        "required_status_checks": [
          { "context": "check:format" },
          { "context": "check:lint" },
          { "context": "check:types" },
          { "context": "Build packages" }
        ]
      }
    }
  ]
}
JSON
)

# Daftar ruleset dibaca lebih dulu SEBAGAI PEMERIKSAAN, bukan cuma untuk mencari
# id. Di paket Free dengan repo privat, endpoint ini menjawab 403 berisi JSON.
# Versi sebelumnya menyerap JSON galat itu sebagai "id", lalu menyusun URL PUT
# yang isinya pesan error ter-encode, dan gagal dengan "unsupported protocol
# scheme" yang tidak menunjuk sebab sebenarnya sama sekali.
if ! daftar=$(gh api "repos/$REPO/rulesets" 2>/tmp/atur-github.err); then
  info ""
  info "${merah}Tidak bisa membaca daftar ruleset.${nc} Pesan mentah dari GitHub:"
  sed 's/^/    /' /tmp/atur-github.err >&2
  info ""
  if [ "$privat" = "true" ]; then
    info "${kuning}Sebabnya paket akun, bukan salah konfigurasi.${nc}"
    info "Ruleset dan branch protection untuk repo PRIVAT hanya tersedia di"
    info "GitHub Team atau Enterprise. Di paket Free, repo privat tidak bisa"
    info "dilindungi sama sekali."
    info ""
    info "Tiga jalan keluarnya:"
    info "  1. Naikkan organisasi ke GitHub Team."
    info "  2. Jadikan repo publik. JANGAN sebelum seluruh berkas .env dicabut"
    info "     dari riwayat, repo ini memuat kredensial produksi."
    info "  3. Sementara ini jalankan disiplinnya secara manual: semua lewat PR,"
    info "     tidak ada yang merge PR sendiri."
    info ""
    info "Setelan repo di langkah 1 SUDAH terpasang dan tetap berlaku."
  fi
  exit 1
fi

# Endpoint-nya sudah terbukti hidup di atas, jadi di sini aman memakai --jq
# untuk mencari ruleset dengan NAMA yang sama, bukan sekadar id pertama yang
# ditemukan. Repo boleh punya beberapa ruleset sekaligus.
id_lama=$(gh api "repos/$REPO/rulesets" --jq "map(select(.name == \"$NAMA_RULESET\")) | .[0].id // empty")
# Jaga-jaga: apa pun yang bukan angka diperlakukan sebagai "belum ada".
case "${id_lama:-}" in
  '' | *[!0-9]*) id_lama="" ;;
esac

if [ -n "$id_lama" ]; then
  info "ruleset sudah ada (id $id_lama), diperbarui"
  jalur="repos/$REPO/rulesets/$id_lama"
  metode="PUT"
else
  info "ruleset belum ada, dibuat baru"
  jalur="repos/$REPO/rulesets"
  metode="POST"
fi

if ! printf '%s' "$muatan" | gh api -X "$metode" "$jalur" --input - >/dev/null 2>/tmp/atur-github.err; then
  info ""
  info "${merah}Ruleset gagal dipasang.${nc} Pesan mentah dari GitHub:"
  sed 's/^/    /' /tmp/atur-github.err >&2
  info ""
  if [ "$privat" = "true" ]; then
    info "${kuning}Kemungkinan terbesar: paket akunnya.${nc}"
    info "Ruleset dan branch protection untuk repo PRIVAT hanya tersedia di"
    info "GitHub Team atau Enterprise. Di paket Free, repo privat tidak bisa"
    info "dilindungi sama sekali."
    info ""
    info "Tiga jalan keluarnya:"
    info "  1. Naikkan organisasi ke GitHub Team."
    info "  2. Jadikan repo publik. JANGAN sebelum seluruh berkas .env dicabut"
    info "     dari riwayat, repo ini memuat kredensial produksi."
    info "  3. Sementara ini jalankan disiplinnya secara manual: semua lewat PR,"
    info "     tidak ada yang merge PR sendiri."
  fi
  exit 1
fi

ok "ruleset aktif"
info ""

# ── Ringkasan ───────────────────────────────────────────────────────────────
info "${tebal}Yang sekarang berlaku di $cabang_utama:${nc}"
info "  - Push langsung DITOLAK, semua perubahan wajib lewat Pull Request"
info "  - Wajib 1 persetujuan, dan harus dari Code Owner di berkas CODEOWNERS"
info "  - Persetujuan hangus otomatis kalau ada commit baru sesudah disetujui"
info "  - Orang yang push terakhir tidak bisa menyetujui PR-nya sendiri"
info "  - Semua komentar review wajib diselesaikan sebelum merge"
info "  - Empat status check wajib hijau: check:format, check:lint, check:types, Build packages"
info "  - Branch wajib sudah sinkron dengan $cabang_utama sebelum merge"
info "  - Force-push dan penghapusan branch DITOLAK, untuk semua orang termasuk admin"
info ""
info "Tidak ada bypass_actors. Kamu sendiri juga tidak bisa menembusnya."
info "Kalau suatu saat butuh, hapus rulesetnya lewat Settings, jangan tambahkan"
info "pengecualian diam-diam."
