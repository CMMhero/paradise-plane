# Changelog, Paradise Task Tracker

Urutan pembangunan sistem, disusun dari riwayat commit. Entri terbaru di atas.

Format tanggal: YYYY-MM-DD. Referensi commit menunjuk repositori ini.

---

## 2026-07-31

### Branding

- **Penuntasan penghapusan merek upstream** (`07a6fe2`), pass sebelumnya
  membuang tautan, komponen, dan route, tapi **tidak menyentuh teks locale**.
  1.712 baris di 19 locale diperbaiki. Dua permukaan yang paling sering dilihat
  masih menulis nama vendor sampai hari ini: command palette `Ctrl+K` dan layar
  masuk.
- `SUPPORT_EMAIL` dan `WEBSITE_URL` kehilangan default vendor. Yang pertama
  paling berdampak: nilainya disisipkan ke pesan nyata _"User account
  deactivated. Please contact …"_ di web, space, **dan** admin, karyawan yang
  akunnya dinonaktifkan diarahkan ke inbox vendor.
- Tiga permukaan ajakan upgrade yang sebelumnya terlewat dibereskan: spanduk
  yang muncul saat menyeleksi beberapa work item, seluruh halaman
  `/active-cycles`, dan "Powered by …" di halaman publik.

## 2026-07-30

### Navigasi

- **Wiki masuk sidebar workspace** (`9ea16c2`). Sekaligus memperbaiki bug lama:
  `Dashboards` dan `Initiatives` **tidak pernah terlihat di sidebar siapa pun
  sejak dibuat**, item nav dinamis disembunyikan kalau tidak di-pin, dan
  default-nya tidak di-pin.
- Penghapusan merek produk upstream dari antarmuka (`a407ce0`): tombol promosi,
  badge tier, menu bantuan vendor, command palette, tab Billing beserta
  route-nya, dan tautan syarat layanan di layar masuk.

### Operasional

- Backup menunggu Postgres siap alih-alih gagal seketika saat Docker belum naik
  (`8468112`).
- Healthcheck berhenti mencatat `HTTP 000000` (`0134346`), dan schedule-nya
  didaftarkan nonaktif sampai server produksi benar-benar ada (`cef2a20`).

### Wiki

- Seed berhenti menulis judul ganda di badan halaman (`ecbc4e8`).

## 2026-07-29

- **Node berkas di editor dengan pratinjau di tempat** (`84e6638`), melengkapi
  Fase A: backend sudah menerima pdf/docx/mp4/zip, tapi editor hanya menawarkan
  gambar.
- **Pohon halaman bertingkat** (`8e6e2fc`), Fase C. Sub-halaman sebelumnya
  bukan sekadar tak terlihat, tapi **404 saat dibuka**: filter berada di
  `get_queryset()` yang juga dipakai `retrieve`/`update`/`destroy`.
- Skrip registrasi scheduled task diperbaiki hingga benar-benar bisa jalan
  (`d03ef68`).

## 2026-07-28

### Wiki, Fase B lengkap (kontrol akses per folder)

- Lampiran semua tipe berkas, batas unggah 100 MB (`7a85899`).
- **Penegakan izin edit di server kolaborasi real-time** (`e9e73ea`), tanpa
  ini, anggota di luar divisi pemilik folder melihat halaman bisa diedit,
  mengetik, lalu tulisannya hilang saat memuat ulang.
- API admin untuk mengelola kepemilikan folder (`3685b5e`).
- UI setelan akses folder, dan editor menghormati keadaan baca-saja (`4149011`).

### Perbaikan

- **Recurring issue akhirnya benar-benar jalan** (`5f1cb37`), task terdaftar di
  penjadwal tapi tidak di daftar impor worker, jadi setiap 15 menit pesannya
  dikirim lalu dibuang diam-diam.

## 2026-07-24

- **Audit Logs**, perekaman aktor pada model akses & konten (`cc2888b`), lalu
  API baca khusus admin dengan filter dan pagination (`352422c`).
- **ACL per folder Wiki, backend** (`886303d`): model, resolver, dan penegakan
  izin. Dibangun tanpa dependency baru; keanggotaan divisi bersifat dinamis,
  jadi grant statis rawan melenceng dari keadaan sebenarnya.
- **CI/CD ke GHCR** (`1a681fb`), build image per push, deploy dengan menarik
  image di server. Dua perbaikan menyusul: berkas env dibuat sebelum validasi
  compose (`1c36246`) dan bake memakai compose root (`f2f5736`).
- Endpoint MinIO yang dilihat browser bisa di-override (`15ff66e`).

## 2026-07-13

### Delapan hari pertama membangun fitur

- **Time Tracking**, model & API dengan izin per-user (`cc82b12`), lalu UI
  sidebar untuk mencatat, melihat total, dan menghapus worklog sendiri
  (`0b24b07`).
- **Work Item Types**, tipe work item per project, khusus admin (`cdeb15e`).
- **Custom Properties**, model properti/opsi/nilai dengan 6 jenis field
  (`9354fe7`), pembersihan berjenjang saat penghapusan tipe + validasi nilai
  bertipe (`461ce37`), dan frontend selector tipe + field dinamis (`8205b9b`).
- **Templates & Recurring**, template work item + pengulangan otomatis via
  Celery beat (`7364fc7`), dan halaman setelan untuk mengelolanya (`ee54c30`).
- **Workspace Wiki**, seed project Wiki perusahaan dengan halaman akar per
  divisi (`09b925f`).
- **Dashboard Divisi**, rekap per divisi dengan total worklog dan ekspor CSV
  laporan waktu (`0b68e8a`).
- **Initiatives**, sasaran workspace lintas divisi dengan rollup progres
  (`0e0f417`).

### Identitas & lingkungan

- Logo dan spinner pemuatan diganti identitas Paradise Perkasa (`f3aa2d2`).
- Atribusi pembuat tertanam beserta pemeriksaan tamper-evident (`a03a842`).
- Dev server terikat ke semua antarmuka untuk akses LAN (`f36753f`).
- Junction `packages/i18n/locales` dipulihkan sebagai symlink di index git
  (`ebf0314`), masalah yang berulang di Windows.

## 2026-07-10, fondasi

- Vendoring **Plane Community Edition v0.24.0 (AGPL-3.0)** sebagai basis
  (`1d503d3`), dan NOTICE atribusi upstream (`7d8ac1f`).
- Audit arsitektur baca-saja atas basis kode (`2433208`).
- Lapisan operasional kantor: template environment (`1d62838`), panduan
  self-host (`20fd63b`), panduan deploy produksi (`c4b29d3`), checklist keamanan
  pra-produksi (`81253c8`), panduan sinkronisasi upstream (`0429966`).
- Skrip: helper dev (`0c81898`), backup PostgreSQL dengan retensi & pemeriksaan
  integritas (`b215cb2`), healthcheck layanan (`7da2b7a`), registrasi scheduled
  task (`f10842a`).
- Kerangka workflow build & deploy (`180c6cc`), Makefile operasional
  (`1cdaec2`), `.gitignore` diperketat untuk secrets & backup (`248fe06`).
- Identitas paket dan judul aplikasi diganti menjadi Paradise Task Tracker
  (`a5763d7`, `0330de0`).
