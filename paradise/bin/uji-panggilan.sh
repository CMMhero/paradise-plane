#!/usr/bin/env bash
# Uji jalur panggilan dari ujung ke ujung, TANPA peramban.
#
# KENAPA SKRIP INI ADA
# Panggilan gagal berulang kali sementara semua pemeriksaan sisi server hijau:
# LiveKit hidup, token diterima, port terbuka. Yang gagal ada di jalur yang
# hanya dilalui peramban, dan tiap kali penyebabnya baru ketahuan setelah
# meminta orang menyalin konsol peramban. Itu lambat dan tidak bisa diulang.
#
# Skrip ini menirukan persis yang dilakukan klien LiveKit:
#   1. minta token ke API seperti peramban
#   2. buka WebSocket ke jalur sinyal lewat HTTPS publik
#   3. laporkan jalur mana yang hidup
#
# Pakai:
#   ./paradise/bin/uji-panggilan.sh [host]
# Contoh:
#   ./paradise/bin/uji-panggilan.sh space.paradiseperkasa.com
set -uo pipefail

HOST="${1:-space.paradiseperkasa.com}"
echo "== Uji jalur panggilan lewat https://$HOST =="
echo

# --- 1. Token, diterbitkan seperti untuk peramban -------------------------
echo "[1/4] Menerbitkan token dari API..."
TOKEN=$(docker exec -i api python manage.py shell 2>/dev/null <<'PY' | tr -d '\r'
from rest_framework.test import APIClient
from plane.db.models import Langganan
l = Langganan.objects.select_related("user", "ruang").first()
if l is None:
    print("TOKEN=")
else:
    c = APIClient(HTTP_HOST="space.paradiseperkasa.com")
    c.force_authenticate(user=l.user)
    r = c.post("/api/workspaces/pt-paradise-perkasa/chat/ruang/%s/panggilan/" % l.ruang_id)
    print("TOKEN=" + (r.data.get("token", "") if r.status_code == 200 else ""))
    print("URL=" + (r.data.get("url", "") if r.status_code == 200 else ""))
    print("STATUS=%s" % r.status_code)
PY
)
LK_TOKEN=$(echo "$TOKEN" | grep "^TOKEN=" | cut -d= -f2-)
LK_URL=$(echo "$TOKEN" | grep "^URL=" | cut -d= -f2-)
LK_STATUS=$(echo "$TOKEN" | grep "^STATUS=" | cut -d= -f2-)

if [ -z "$LK_TOKEN" ]; then
  echo "  GAGAL: API tidak menerbitkan token (status ${LK_STATUS:-?})."
  echo "  Periksa LIVEKIT_API_KEY / LIVEKIT_API_SECRET / LIVEKIT_URL di apps/api/.env."
  exit 1
fi
echo "  OK. url=$LK_URL"

# --- 2. Jalur validasi lewat HTTPS ---------------------------------------
echo "[2/4] Memeriksa jalur sinyal lewat HTTPS..."
for jalur in "/rtc/validate" "/rtc/v1/validate"; do
  kode=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "https://$HOST$jalur?access_token=$LK_TOKEN")
  printf "  %-18s %s%s\n" "$jalur" "$kode" \
    "$([ "$kode" = "200" ] && echo "  <- hidup" || { [ "$kode" = "404" ] && echo "  <- tidak ada di versi server ini" || echo ""; })"
done

# --- 3. Token palsu WAJIB ditolak ----------------------------------------
echo "[3/4] Token palsu harus ditolak..."
kode=$(curl -s -o /dev/null -w "%{http_code}" -m 15 "https://$HOST/rtc/validate?access_token=palsu")
if [ "$kode" = "401" ]; then
  echo "  OK, ditolak 401."
else
  echo "  MENCURIGAKAN: token palsu dijawab $kode, harusnya 401."
fi

# --- 4. Jabat tangan WebSocket sungguhan ---------------------------------
# Inilah yang tidak bisa ditiru curl: peramban membuka WebSocket, bukan HTTP.
echo "[4/4] Membuka WebSocket sinyal seperti yang dilakukan peramban..."
docker exec -i -e H="$HOST" -e T="$LK_TOKEN" plane-live node -e '
const host = process.env.H, token = process.env.T;
const jalur = ["/rtc/v1", "/rtc"];
const coba = (p) => new Promise((res) => {
  const url = `wss://${host}${p}?access_token=${token}&auto_subscribe=1&sdk=js&version=2.22.0&protocol=17`;
  const ws = new WebSocket(url);
  const t = setTimeout(() => { try { ws.close(); } catch {} res(`${p}  TIMEOUT`); }, 10000);
  ws.onopen = () => { clearTimeout(t); ws.close(); res(`${p}  TERBUKA  <- jalur sinyal hidup`); };
  ws.onerror = () => {};
  ws.onclose = (e) => { clearTimeout(t); res(`${p}  DITUTUP kode=${e.code} ${e.reason || ""}`); };
});
(async () => { for (const p of jalur) console.log("  " + await coba(p)); })();
' 2>&1 | grep -vE "^$"

echo
echo "Kesimpulan: kalau salah satu jalur di langkah 4 TERBUKA, sinyal panggilan sehat."
echo "Kalau dua-duanya gagal, panggilan tidak akan pernah tersambung dari peramban."
