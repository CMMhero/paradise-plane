# Upgrade, sinkron dengan upstream Plane

Jalankan:

```bash
./paradise/bin/upstream-sync.sh check     # apa yang baru sejak baseline
./paradise/bin/upstream-sync.sh apply     # terapkan
./paradise/bin/upstream-sync.sh verify    # kustomisasi kita masih utuh?
```

Baseline, daftar commit yang sengaja ditolak, dan daftar berkas yang harus
selamat ada di [`upstream-sync.json`](upstream-sync.json). Baca itu dulu.

Sisanya di halaman ini adalah hal-hal yang tidak bisa dikerjakan skrip.

## Kenapa tidak bisa `git merge`

Repo ini **di-vendor, bukan di-fork**: berkasnya disalin. Tidak ada leluhur
bersama dengan `makeplane/plane`, jadi `git merge upstream/preview` menolak
bekerja, dan kalau dipaksa dengan `--allow-unrelated-histories`, hasilnya
konflik di hampir setiap berkas. Yang dipakai: patch tiga arah per commit.

Versi lama halaman ini menyuruh `git merge upstream/main`. Itu keliru.

## Sync ke tag rilis, bukan ke `preview`

`preview` adalah branch kerja mereka, berisi hal setengah jadi. Tag `v*` sudah
lewat QA mereka. Sync ke `preview` = jadi penguji beta orang lain, di server
yang dipakai 79 orang.

## Kustomisasi kita TIDAK terisolasi di `paradise/`

Anggapan itu benar saat vendoring, sekarang tidak lagi. Yang tersebar di kode
upstream:

| Di mana                                                         | Apa                                                                                                                                    |
| --------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web/ce/` (246 berkas)                                     | Lapisan ekstensi, Time Tracking, Custom Properties, perbaikan sidebar. Mengisi stub yang upstream sediakan lewat alias `@/plane-web/*` |
| `apps/api/plane/db/superadmin.py`                               | Super Admin tersembunyi                                                                                                                |
| `apps/api/plane/utils/trash.py` + `app/views/paradise_trash.py` | Trashbin & TPA                                                                                                                         |
| `apps/api/plane/license/api/views/`                             | Log audit, pemulihan, kelola member (God Mode)                                                                                         |
| `apps/api/plane/app/views/asset/v2.py`                          | Gate lampiran Wiki, **upstream berkala mau membuang `import Page` yang jadi sandarannya**                                              |
| `packages/i18n/src/locales/`                                    | Debranding, ~1.700 baris di 19 locale                                                                                                  |
| `apps/web/core/components/instance/edition-badge.tsx`           | Modal ajakan upgrade dibuang (KEP-14), **upstream berkala memasangnya lagi**                                                           |
| `apps/api/plane/authentication/utils/login.py`                  | Satu panggilan `LoginActivity.catat()` sesudah `session.save()`                                                                        |
| `apps/api/plane/authentication/views/{app,space}/signout.py`    | Satu panggilan `LoginActivity.catat()` **sebelum** `logout()`                                                                          |
| `apps/api/plane/settings/common.py`                             | `LastActiveMiddleware` di `MIDDLEWARE` + `login_activity_retention` di `CELERY_IMPORTS`                                                |
| `apps/api/plane/celery.py`                                      | Jadwal `bersihkan-login-activity` (17:00 UTC = 00:00 WIB)                                                                              |
| `apps/admin/app/routes.ts` + `hooks/use-sidebar-menu/`          | Rute & menu God Mode: Jejak audit, TPA, Member, Aktivitas                                                                              |

### Jebakan pemantauan aktivitas (2026-08-07)

Empat titik sambung di atas masing-masing cuma satu-dua baris, dan itu justru
bahayanya: patch yang gagal di sana **tidak menimbulkan error apa pun**, hanya
membuat angka di dashboard diam-diam jadi nol. Sesudah tiap sync, periksa:

- `LoginActivity.catat()` masih terpanggil di jalur login **dan** ketiga logout.
  Hilang di logout saja → sesi menggantung selamanya, durasi tak terhitung.
- `session_key` diambil **sesudah** `request.session.save()`. Django membuat ulang
  kunci saat login; membaca lebih awal memasangkan logout ke login yang salah.
- `LastActiveMiddleware` masih **setelah** `AuthenticationMiddleware`. Kalau
  urutannya berubah, `request.user` belum ada dan middleware diam seribu bahasa.
- Task retensi terdaftar di **worker**, bukan cuma beat:
  `docker compose exec worker celery -A plane inspect registered | grep login_activity`.
  Beat saja = task dikirim, worker menjawab "unregistered", pesannya dibuang.

Selebihnya berkas milik kita sendiri (`db/models/login_activity.py`,
`middleware/last_active.py`, `bgtasks/login_activity_retention.py`,
`license/api/views/activity.py`, `apps/admin/.../activity/`), tidak akan pernah
bentrok dengan upstream.

## Saat patch gagal

Skrip melaporkan yang gagal satu per satu, tidak menggugurkan sisanya.
Kerjakan tangan, dan aturannya:

- Baris bentrok itu **kustomisasi kita** → pertahankan punya kita.
- Baris bentrok itu **perbaikan keamanan mereka** → ambil punya mereka, lalu
  pasang ulang kustomisasi kita di atasnya.

Jangan pilih salah satu sisi buta-buta. Dua patch keamanan aset (Juli 2026)
sama-sama mau membuang `import Page`, kalau diambil mentah, gate Wiki jebol
tanpa satu pun error.

## Yang harus ditolak selamanya

`8ef78bf0c1` "store and components consolidation to core" menghapus seluruh
`apps/web/ce/` (249 berkas jadi nol). Tiga fitur kita kehilangan antarmuka
sementara backend-nya tetap jalan, dan pemanggilnya ikut hilang, **tidak ada
yang gagal dengan berisik**. Pindah ke struktur `core/` itu porting, kerjakan
terpisah, jangan dibarengkan dengan patch keamanan.

## Setelah sync

1. `./paradise/bin/upstream-sync.sh verify`, wajib hijau sebelum merge ke `main`.
2. Cek migrasi baru: `git show <commit> --stat | grep migrations/`. Kalau ada,
   **dump DB dulu** (`paradise/bin/backup-db.sh`) sebelum merge.
3. `paradise/bin/healthcheck.sh`.
4. Ulangi [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md) bila upstream menambah env baru.

> Container `api`, `worker`, dan `beat-worker` bind-mount `apps/api` ke `/code`.
> **Branch yang ter-checkout itulah yang dijalankan backend.** Selama hasil sync
> masih nangkring di branch sendiri, `git checkout main` diam-diam mencabut
> semua patch keamanannya.
