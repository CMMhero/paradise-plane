# Rencana Wiki, Paradise Task Tracker

Status: **RENCANA** (belum dieksekusi). Disusun 2026-07-24.

Target: satu Wiki perusahaan, folder per-divisi, **divisi pemilik boleh edit +
yang lain hanya view**, upload hampir semua tipe file sampai **100 MB**.

---

## Konsep yang diminta

Dua lapis dokumentasi:

| Lapis                  | Siapa lihat                             | Siapa edit                  | Isi               |
| ---------------------- | --------------------------------------- | --------------------------- | ----------------- |
| **Private per-divisi** | hanya divisi itu (atau yg diberi akses) | divisi itu                  | rahasia divisi    |
| **Public**             | semua karyawan                          | hanya divisi pemilik folder | panduan umum, SOP |

Di dalam Public ada "folder" per divisi. Contoh folder HR: **HR upload/edit/hapus,
yang lain view**. File yang boleh: jpg, png, mp4, mp3, docx, xlsx, pdf, ppt, dll.

Keputusan user: **1 Wiki besar dengan folder per-divisi** (bukan 1 project per
divisi), dan **semua tipe file termasuk video, batas 100 MB**.

---

## Temuan investigasi (kode nyata)

- **Private per-divisi = SUDAH BISA tanpa kode.** Project private Plane (`network=0`
  "Secret") hanya bisa dilihat anggotanya. 16 project divisi sudah private → Pages
  di dalamnya = wiki rahasia divisi. Tidak perlu dibangun.
- **Izin halaman melekat se-project, bukan per-folder.** `ProjectPagePermission`
  (`apps/api/plane/app/permissions/page.py`): harus anggota project untuk akses;
  peran Guest=view, Member=edit, Admin=hapus. Dalam satu project, semua member punya
  hak edit sama → "folder HR cuma HR yang edit" TIDAK didukung native.
- **Editor tidak punya node file non-gambar.** `packages/editor` cuma punya
  `image`/`custom-image`; slash-command cuma "Image". Upload pdf/docx/mp4 ke halaman
  = harus BANGUN node editor baru.
- **Upload halaman = image-only (hardcoded).** `apps/api/.../asset/v2.py` baris ~342
  (`WorkspaceFileAssetEndpoint`) & ~544 (`ProjectAssetEndpoint`): `allowed_types`
  cuma 5 tipe gambar. Daftar lengkap `ATTACHMENT_MIME_TYPES` ADA di
  `settings/common.py` (pdf/docx/xlsx/ppt/mp4/mp3/zip) TAPI cuma dipakai lampiran
  Issue (`issue/attachment.py:105`), bukan halaman.
- **Batas ukuran 5 MB.** `FILE_SIZE_LIMIT=5242880`. Proxy Caddy pakai env yang sama
  (`apps/proxy/Caddyfile.ce`: `max_size {$FILE_SIZE_LIMIT}`) → satu tombol ikut
  mengatur Caddy + Django `DATA_UPLOAD_MAX_MEMORY_SIZE`.
- **Sub-halaman disembunyikan di UI.** List memfilter `parent__isnull=True`
  (`apps/api/plane/app/views/page/base.py:97`) → pohon folder bertingkat tidak
  tampil tanpa kerja frontend.
- **Ada hook untuk override izin.** `page.py` menyediakan
  `_check_access_and_get_role` & `_has_private_page_action_access` ("Override for
  feature flag logic"), titik ekstensi resmi (dipakai edisi EE).

---

## Fase A, Upload file (semua tipe, 100 MB)

Dibutuhkan apa pun struktur wiki-nya. Berdiri sendiri.

| #   | Kerja                            | File                                                                                                                         | Ukuran       | Risiko |
| --- | -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------ | ------ |
| A1  | Buka tipe non-gambar utk halaman | `asset/v2.py` ~342 & ~544 → pakai `ATTACHMENT_MIME_TYPES` saat `entity_type=PAGE_DESCRIPTION` (jgn sentuh avatar/cover ~128) | kecil        | rendah |
| A2  | Batas 100 MB                     | `.env`: `FILE_SIZE_LIMIT=104857600` (ikut Caddy + Django)                                                                    | sepele       | rendah |
| A3  | **Node "File" baru di editor**   | `packages/editor/.../extensions/custom-file/` (baru) + slash-command "File"                                                  | sedang–besar | sedang |

A3 = komponen upload, kartu file (ikon+nama+download), pemutar inline mp4/mp3,
sinkron Yjs. Editor dipakai bersama Issue/Page/Comment → jangan rusak yang lain.
**Versi malas:** kartu file + download saja dulu; preview/inline player menyusul.

## Fase B, Izin per-folder (SENSITIF KEAMANAN)

| #   | Kerja                 | Cara                                                                                                                                                 | Risiko     |
| --- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| B1  | Tandai pemilik folder | Model kecil baru `page → project divisi pemilik` (pinjam 16 project divisi, bukan konsep grup baru) + migrasi                                        | rendah     |
| B2  | Tegakkan izin         | Override `ProjectPagePermission` via hook. Edit/hapus: telusuri naik ke folder induk → cek user anggota project divisi pemilik. View = semua anggota | **tinggi** |
| B3  | Set pemilik folder    | Endpoint kecil, admin only                                                                                                                           | rendah     |

Uji wajib: non-pemilik tak bisa edit/hapus folder lain; sub-halaman mewarisi
pemilik induk; pindah halaman antar-folder hitung ulang pemilik; buat halaman di
bawah folder X cek pemilik folder X (bukan sekadar peran project).

## Fase C, Pohon folder di UI

| #   | Kerja                               | Cara                                                                      | Risiko |
| --- | ----------------------------------- | ------------------------------------------------------------------------- | ------ |
| C1  | Tampilkan halaman bertingkat        | Bangun endpoint anak + sidebar pohon (atasi filter `parent__isnull=True`) | sedang |
| C2  | Edit/hapus nonaktif utk non-pemilik | Backend sudah tolak; UI tinggal tak menawarkan aksi                       | kecil  |
| C3  | UI set pemilik folder               | admin only (pasangan B3)                                                  | kecil  |

---

## Catatan penting

- **Ini fork.** Fase B & C menyimpang dari kode Plane asli → tiap upgrade Plane
  diterapkan & diuji ulang. Dokumentasikan.
- **Semua lewat pipeline CI** (`paradise-build` → GHCR → `deploy.sh`): tiap
  perubahan = commit → build ~7 menit → deploy. Bukan instan.
- **Disk:** 100 MB × banyak orang = GB cepat. Server produksi (belum ada) wajib SSD
  lega + monitoring disk.
- **Urutan disarankan:** Fase A dulu (berguna langsung, risiko rendah, tetap perlu
  walau struktur berubah), baru B lalu C.

## Penghematan yang layak ditimbang

Sebelum bangun node editor (A3) & ACL (B) dari nol, cek dulu apakah Plane edisi
berbayar (EE) sudah punya keduanya untuk di-port, lebih murah & lebih teruji.
Repo `upstream` yang ada cuma community; perlu lihat referensi EE.
