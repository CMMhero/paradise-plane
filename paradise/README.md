# Paradise Task Tracker

Deployment internal kantor berbasis [Plane CE](https://github.com/makeplane/plane).
Alat manajemen proyek/issue untuk tim (~100 anggota lintas divisi).

> Ini fork operasional, bukan tulis-ulang. Kode aplikasi = karya tim Plane
> (AGPL-3.0). Lihat [`../NOTICE.md`](../NOTICE.md).

## Dua fase

| Fase                  | Tujuan                                         | Cara                                                      |
| --------------------- | ---------------------------------------------- | --------------------------------------------------------- |
| **1, Dev (sekarang)** | Ngoprek & sesuaikan source ke kebutuhan kantor | Build dari source via `docker-compose-local.yml`          |
| **2, Prod (nanti)**   | Layani ~100 user, update via CI/CD             | Build image sendiri → registry → deploy compose di server |

## Mulai cepat (Dev)

```bash
cp paradise/.env.example .env      # lalu isi nilainya
paradise/bin/dev.sh up             # Linux/macOS
paradise\bin\dev.ps1 up            # Windows PowerShell
```

Web default: http://localhost (proxy Caddy). God-mode admin: `/god-mode`.

## Peta dokumen

- [`.env.example`](.env.example), semua variabel wajib + catatan.
- [`DEPLOYMENT.md`](DEPLOYMENT.md), deploy produksi di server kantor.
- [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md), **wajib** sebelum prod.
- [`UPGRADE.md`](UPGRADE.md), cara ambil update dari upstream Plane.
- [`ATURAN-GITHUB.md`](ATURAN-GITHUB.md), aturan repo GitHub: wajib PR, wajib
  review, dan cara memasangnya.
- [`../CODEBASE_INVENTORY.md`](../CODEBASE_INVENTORY.md), audit arsitektur.

## Layanan (compose)

`web` · `space` · `admin` · `live` (collab) · `api` (Django) · `worker`/`beat`
(Celery) · `proxy` (Caddy) · Postgres · Redis · RabbitMQ · MinIO.

## Teks antarmuka (i18n)

Semua teks yang dibaca pengguna di `apps/web` lewat `useTranslation()` dari
`@plane/i18n`, bukan string Indonesia yang ditulis langsung di komponen.

- Teks kustom Paradise ada di namespace `paradise`
  (`packages/i18n/src/locales/<bahasa>/paradise.json`). Kuncinya dikelompokkan
  per fitur dengan akhiran `_ui` (`wiki_ui`, `chat_ui`, `cross_division_ui`,
  `notification_ui`, dst). Jangan memberi kunci teratas yang sama dengan nama
  berkas namespace (`paradise`, `wiki`, ...), `sync:check` menolaknya.
- Semua 19 locale wajib punya kunci yang sama. `id` berisi teks Indonesia,
  `en` bahasa Inggris, sisanya sementara menyalin `en` sampai ada terjemahannya.
- Tombol umum (Simpan, Batal, Hapus, Tutup, Cari) memakai kunci `common`
  (`t("save")`, `t("cancel")`), jangan ditulis ulang.
- Modul murni yang diuji lewat `*.check.ts` (`galat-media`, `baris`, `teks`)
  tidak memanggil hook. Mereka menerima `t` sebagai argumen, dan berkas
  `*.check.ts` meminjam kamus `id/paradise.json`. Jalankan dari `packages/i18n`.
- God Mode (`apps/admin`) memang tidak memakai `@plane/i18n`; kamusnya sendiri di
  `apps/admin/app/i18n/godmode.tsx`.

Pemeriksaan: `pnpm --filter @plane/i18n sync:check`, lalu `pnpm --filter @plane/i18n generate:types`.
