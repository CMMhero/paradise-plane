# Changelog, Paradise Task Tracker

Urutan pembangunan sistem, disusun dari riwayat commit. Entri terbaru di atas.

Format tanggal: YYYY-MM-DD. Referensi commit menunjuk repositori ini.

---

## 2026-11-13

### Versi 2.7.0

- **Naik 2.6.1 ke 2.7.0, minor.** Fitur baru yang kelihatan pengguna (layar
  hidup, balasan komentar, jenjang Sekretaris) dan satu migrasi aditif
  (`0175_tingkat_sekretaris`, hanya mengubah pilihan kolom, data lama tidak
  tersentuh). Langkah operator: tidak ada. `apps/live` ikut dibangun ulang
  karena meneruskan sinyal baru, dan Redis yang sudah ada dipakai apa adanya.
- **Layar hidup tanpa F5 (KEP-102).** Daftar, papan, kalender, detail tugas,
  pemberitahuan, dan keanggotaan project menyegarkan diri saat orang lain
  mengubahnya. Django menerbitkan petunjuk kecil (hanya id) ke Redis,
  `apps/live` meneruskannya cuma ke orang yang boleh melihat, dan peramban
  menarik ulang lewat API biasa. Ada tombol segarkan di bilah atas yang
  menyegarkan isi layar tanpa memuat ulang halaman. Saat soket putus,
  penyegaran berjalan tiap 45 detik.
- **Balasan komentar (KEP-103).** Komentar bisa dibalas, balasan tersusun di
  bawah komentar induk, penulis induk diberi tahu satu kali (tidak ganda bila
  juga disebut), dan menghapus induk ikut menghapus balasannya.
- **Jenjang Sekretaris (KEP-101).** Jenjang 35 antara Manager dan Direktur:
  jangkauan seluruh organisasi seperti Direktur, tapi tidak bisa menugaskan
  Direktur. Kartu profil kini menampilkan jenjang walau orangnya tidak
  ditempatkan di departemen.
- **Lampiran lebih andal (KEP-104).** Tipe berkas tidak lagi bergantung pada
  registri OS komputer pengguna, kegagalan unggah tampil sebagai toast
  terjemahan alih-alih diam, kegagalan sementara diulang, unggahan yang
  dibatalkan tidak dianggap berhasil, dan memilih berkas yang sama dua kali
  bekerja lagi.
- **Onboarding sepenuhnya i18n (KEP-105).** Semua langkah onboarding, tur,
  sapaan, dan kolom kata sandi memakai kunci terjemahan di 19 bahasa;
  workspace baru diisi contoh project dalam bahasa pemiliknya. Skrip penjaga
  `check:onboarding` gagal bila ada teks onboarding yang ditulis langsung.

## 2026-11-12

### Versi 2.6.1

- **Naik 2.6.0 ke 2.6.1, patch.** Perbaikan dan penyempurnaan kecil, tanpa
  migrasi dan tanpa variabel env baru. Langkah operator: tidak ada. Bersamaan
  dengan ini skema versi diganti (lihat poin berikutnya), jadi nomor rilis
  lama dinomori ulang.
- **Skema versi diperbaiki dan riwayat dinomori ulang.** Patch (x.y.Z) untuk
  perubahan kecil, minor (x.Y.0) untuk perubahan besar, major (X.0.0) hanya
  untuk perombakan besar. Rilis yang dulu bernomor 3.0.0, 4.0.0, 4.1.0, dan
  4.2.0 kini 2.3.0, 2.4.0, 2.5.0, dan 2.6.0 (2.3.0 lama tidak pernah dirilis
  sendiri dan menyatu ke 3.0.0). Kartu Changelog yang sudah terbit di tiap
  workspace ikut dinomori ulang oleh `catatan_rilis.terbitkan` saat API
  menyala, tanpa kartu ganda. Tag git `p3.0.0`..`p4.2.0` diganti
  `p2.4.0`..`p2.6.0`. Aturan baru ada di AGENTS.md > Versioning.
- **Persetujuan tidak lagi meninggalkan baris status ganda.** Saat atasan
  menyetujui, log aktivitas hanya mencatat "approved". Baris "set state to
  Done", kartu chat "updated your work item", dan notifikasi inbox yang
  mengulang hal yang sama tidak dibuat lagi. Penolakan tetap mencatat
  perpindahan statusnya.
- **Keputusan persetujuan sampai ke semua assignee.** Dulu hanya pemohon yang
  menerima email dan kartu "approved"/"rejected"; rekan sesama assignee tidak.
  Kini pemohon dan semua assignee tugas itu (kecuali yang memutuskan).
- **Pemilih @ menampilkan orang di luar departemen.** Muncul abu-abu di bagian
  "Outside this department" dan tidak bisa dipilih, jadi nama rekan yang tidak
  sedepartemen tidak lagi terkesan hilang. Hanya muncul setelah mengetik.
- **Pemilih induk mengutamakan work item yang sudah punya sub-item.** Berlaku
  di form buat work item dan di detail work item.
- **Super Admin bisa mengatur assignee di tugas mana pun** tanpa ditolak
  "Staf hanya boleh mengajak rekan", dan toast gagal-ubah menampilkan alasan
  dari server.

### Versi 2.6.0

- **Naik 2.5.0 ke 2.6.0, minor (dulu bernomor 4.2.0).** Fitur dan aturan baru yang kelihatan
  pengguna, plus satu migrasi data (0174, tanpa skema). Tidak ada data yang
  dibentuk ulang, tidak ada variabel env baru, jadi bukan major. Langkah
  operator: tidak wajib. Satu hal perlu dicek: bawaan visibilitas project di
  God Mode (Defaults > Project) yang SUDAH pernah disimpan tetap menang atas
  bawaan pabrik baru. Kalau tersimpan "Public", ubah ke "Private" sekali.
- **Assignee anak naik ke induk dan module (KEP-98).** Orang yang ditugaskan
  di sub-work item otomatis jadi assignee induknya (berantai ke kakek) dan
  anggota module tempat tugas-tugas itu berada, termasuk module milik induk.
  Hanya menambah: melepas assignee dari anak tidak mencabutnya dari induk.
  Dipanggil dari serializer buat/ubah tugas (web dan API v1), tambah sub-work
  item, dan tambah tugas ke module. Tidak melewati gerbang penugasan karena
  ini turunan dari penugasan anak yang sudah lolos. Kode:
  `plane/utils/naik_assignee.py`. Data lama tidak diisi ulang.
- **Menambah sub-work item di induk milik orang lain.** Staf yang pembuat atau
  assignee salah satu anak sebuah tugas kini boleh menambah sub-work item di
  induknya. Sebelumnya `POST .../sub-issues/` ditolak 403 karena induknya
  bukan buatan atau tugasnya, sehingga orang harus membuat tugas baru lalu
  mengisi induknya lewat formulir. Hanya menambah anak: judul, deskripsi, dan
  assignee induk tetap hanya-lihat, dan tugas yang dijadikan anak tetap harus
  milik sendiri. Server: `terlibat_di_anak` di `utils/task_access.py`; web:
  `useTerlibatDiAnak` dan prop `subIssueDisabled` di widget work item.
- **Project dan departemen baru privat.** Bawaan pabrik visibilitas project
  jadi Private, dan project yang dibuat dari departemen (God Mode) ikut
  bawaan itu, tidak lagi Public karena default kolom.
- **Direktur hanya untuk tugas buatan manager ke atas.** Pengajuan
  persetujuan selesai untuk tugas biasa (dibuat supervisor, staf, atau tanpa
  pembuat) tidak lagi muncul di direktur: tidak di antrean, widget Needs
  attention, Dashboard Divisi, notifikasi, maupun pengingat tenggat, dan POST
  setuju/tolak dari direktur ditolak 403. Pembuat TUGAS yang dihitung, bukan
  pemohon. Satu aturan di `saring_penyetuju` dan `pengajuan_boleh_diputuskan`
  (kunci pengajuan kini `(project, pemohon, pembuat)`). Divisi tanpa atasan
  sama sekali tetap jatuh ke Super Admin, bukan ke direktur.
- **Departemen, project, dan folder Wiki satu kesatuan.** Mengganti nama
  departemen di God Mode kini mengganti nama project-nya, dan folder Wiki
  departemen membawa ikon project-nya (ikon pilihan tangan di folder itu tidak
  disimpan lagi). Nama yang sudah dipakai project lain ditolak 400 sebelum
  disimpan. Identifier project (kode di nomor tugas) sengaja tidak ikut kode
  departemen. Migrasi 0174 menyamakan data yang sudah ada; nama yang bentrok
  dilewati.

## 2026-11-09

### Versi 2.5.0

- **Naik 2.4.0 ke 2.5.0, minor (dulu bernomor 4.1.0).** Ada fitur baru yang kelihatan pengguna
  (halaman departemen dan pencarian isi di Wiki, pratinjau berkas, halaman
  Views workspace, kolom persetujuan) dan satu migrasi tambahan (0172, dua
  kolom berisi nilai bawaan, ekstensi `pg_trgm`, dua indeks). Tidak ada data
  yang dibentuk ulang dan tidak ada variabel env baru, jadi bukan major.
  Langkah operator: tidak wajib. Materi Wiki lama baru ikut pencarian isi
  setelah `docker exec api python manage.py wiki_indeks_ulang` dijalankan
  sekali; unggahan baru terindeks sendiri.
- **Susulan di versi yang sama (9 Nov).** Menyusul rilis awal 4.1.0, perubahan
  berikut ikut 4.1.0 atas keputusan user (versi tidak dinaikkan). Tanpa
  migrasi, tanpa variabel env baru, tanpa langkah operator.
- **Tombol segarkan.** Ada di header semua halaman. Satu klik menjalankan
  ulang semua data SWR yang sedang dipakai layar (daftar work item, antrean
  persetujuan, lencana) tanpa memuat ulang halaman. Komponen:
  `core/components/common/refresh-button.tsx`.
- **Email peringatan retensi tidak lagi harian, dan jedanya diatur Super
  Admin.** Sesudah bulan ketiga selalu ada baris di jendela 7 hari, jadi
  peringatan menyala tiap hari selamanya. Kini jedanya setelan God Mode
  `ADMIN_RETENTION_EMAIL_INTERVAL_DAYS` (Notifications > Sending, bawaan 7
  hari, 1 sampai 365; **0 = ikut masa retensi riwayat login**, jadi retensi 90
  hari berarti satu email per 90 hari). Jumlah yang melonjak dua kali lipat
  atau lebih (misalnya retensi dipersingkat) dikirim lebih cepat, tapi tidak
  dua kali sehari. Penanda terakhir kirim ada di cache dan hanya ditulis kalau
  email benar terkirim, jadi SMTP mati tidak menahan percobaan besok. Retensi
  Trash tidak punya email peringatan, jadi setelan ini hanya menyangkut riwayat
  login.
- **Label ditolak.** "Rejected - needs revision" jadi "Rejected" (Indonesia:
  "Ditolak") di 19 locale.
- **Tinggi pilihan Modul di detail work item** sama dengan pilihan State.
- **Induk work item bisa diklik** dari properti Parent, juga untuk tugas
  orang lain yang hanya-lihat (tautannya sebelumnya di dalam tombol yang
  nonaktif, jadi mati). Membuka di tab yang sama.

- **Django 4.2 ke 5.2 dan DRF 3.18.** Dukungan 4.2 sudah habis. Migrasi 0173
  hanya mengubah status (`through_fields` pada tiga M2M), tanpa SQL. Butuh
  PostgreSQL 14 ke atas; server produksi 15.7. Kode ini tidak bisa lagi jalan
  di Django 4.2, jadi mundur berarti memasang ulang image lama.
- **Pindah ke Vite+.** Skrip paket kini memanggil `vp lint`, `vp fmt`,
  `vp pack`, `vp test`; Turbo, Dockerfile, dan CI tetap.
- **Tujuh perbaikan dari Plane hulu.** Saringan rentang tanggal created_at
  dan updated_at, pemulihan galat aset basi, zona jatuh hapus di Kanban,
  batas galat per layout, perbaikan layanan notifikasi, dan hook klik-luar
  serta dropdown.
- **Wiki.** Folder departemen menampilkan halaman project departemen
  (baca saja, izin dijaga di server). Pencarian memaafkan salah ketik dan
  mencari isi berkas serta halaman. Berkas teks, Markdown, CSV, Excel, dan
  Word dipratinjau di aplikasi tanpa konversi PDF, sebagai blok JSON
  terstruktur (tidak pernah HTML).
- **Views.** Halaman Views workspace memuat view departemen yang boleh dibuka
  orang itu; penyaringan di server. Formulir view dan daftar view dirombak.
- **Obrolan.** Daftar percakapan diurut: belum dibaca, lalu sedang online,
  lalu sisanya. Kartu tugas memakai judul tugas.

---

## 2026-11-05

### Versi 2.4.0

- **Naik 2.3.0 ke 2.4.0, minor (dulu bernomor 4.0.0).** 3.1.0 tidak pernah
  dirilis; peran per tempat (KEP-93) jadi rilis sendiri karena migrasi 0169 membentuk ulang
  baris penempatan yang sudah ada dan arti izin berubah. Langkah operator:
  tidak ada yang manual (deploy.sh menjalankan 0169), tapi setelah deploy cek
  papan Organization: manager yang dulu duduk di departemen divisi lain kini
  tercatat Supervisor di sana, dan barisnya di departemen divisinya sendiri
  dicabut. Data `PengawasanDivisi` dan keanggotaan project eksplisit TIDAK
  dihapus.
- **Peran per tempat (KEP-93).** Baris departemen membawa peran orang itu di
  departemen tersebut (Staf/Supervisor, tidak pernah Manager). Semua keputusan
  wewenang di satu project memakai peran di tempat yang menjangkau project itu
  (`tingkat_anggota(..., project_id)`, `peta_tingkat(..., project_id)`), jadi
  manager divisi A yang duduk sebagai Staf di departemen divisi B hanya staf di
  B. Jenjang orangnya = peran tertinggi; manager tanpa divisi menyimpan
  jenjangnya di baris tanpa tempat.
- **Tidak ada manager departemen.** Menambah manager ke departemen di divisi
  yang ia pimpin ditolak (400 `sudah-memimpin-divisi`); memimpin divisi melepas
  departemen di dalamnya (`departemen_dilepas`). Ke departemen divisi lain:
  papan menanyakan perannya (Staf/Supervisor) lewat dialog.
- **Papan Organization.** Lajur Levels menampilkan anggotanya (kotak tetap,
  bisa digulir) dan bisa diseret. Hanya lajur Director yang menerima lepasan;
  Staf/Supervisor diatur di lajur departemen, Manager lewat divisi. Lajur
  "Managers" di kartu departemen dibuang. Seret dari People = tambah, dari
  struktur = pindah (kini juga lintas jenis); manager diseret DARI STRUKTUR ke
  departemen divisinya sendiri = diturunkan (lepas divisi, `pertahankan_peran`),
  dari People tetap dikunci. Direktur diseret ke People = turun ke Staf. People
  panel lengket mulai md, zona Managers bergaya lajur, kartu departemen tanpa
  bingkai, tombol New division di ujung daftar.
- **Dibuang: Other project access dan Supervised divisions** di editor
  member. Penempatan tampil hanya-baca; diubah di papan. Resolver tidak lagi
  membaca `PengawasanDivisi`, dan POST `pengawasan` ditolak 400.
- **Sebelumnya disiapkan sebagai 3.1.0 (minor):** fitur baru di chat plus
  satu migrasi aditif (0167, kolom baru yang boleh kosong, jalan sendiri saat
  deploy).
- **Migrasi dan changelog tidak lagi dijalankan tangan.** Produksi:
  `deploy.sh` memastikan nol migrasi tertunda dari dalam `api` baru dan
  menerbitkan changelog dengan galat yang menggagalkan deploy; `rilis.sh`
  menolak commit tanpa `release_notes/<versi>.json` atau entri CHANGELOG.
  Lokal: `api` menerapkan migrasi sendiri saat start (tidak lagi macet
  menunggu migrator), lalu `plane/db/sinkron_lokal.py` menerapkan migrasi
  baru dan changelog beberapa detik sesudah berkasnya disimpan. Migrasi 0168
  menyelaraskan pilihan `user_timezone` dengan pytz terpatok (SQL no-op),
  supaya `makemigrations --check` bersih dan bisa jadi gerbang.
- **Catatan rilis 3.0.0 bertanggal 2026-11-04**, bukan 05 (berkasnya ditulis
  sehari sesudah rilis). Kartu Changelog yang sudah terbit kini mengikuti
  berkasnya kalau berkas itu dikoreksi (`selaraskan()`), tanpa kartu baru
  dan tanpa lencana belum-dibaca; produksi terkoreksi sendiri saat deploy.
- **Gerbang lokal otomatis.** pre-commit: ruff menolak galat baru di `.py`
  yang di-stage (dibanding HEAD) dan `makemigrations --check` saat model
  berubah. pre-push: `turbo check:format check:lint check:types --affected`
  seperti CI, plus catatan rilis. Darurat: `PARADISE_LEWATI_CEK=1`.
- **Sebutan @all, diri sendiri, #kanal, dan #work item (KEP-91).** Di chat,
  deskripsi, dan komentar: `@` menawarkan orang, diri sendiri, dan `@all`;
  `#` menawarkan kanal dan work item. Server menyaring ke yang boleh dilihat
  pengirim (kanal privat: anggotanya saja; work item: project yang ia ikuti),
  lalu menyamarkan nama kanal privat jadi `#private-channel` bagi pembaca
  yang bukan anggota, di gelembung, kutipan, sematan, pencarian, kartu, inbox,
  dan email. `@all` di kanal mengirim kartu sebutan ke semua anggota; di
  deskripsi/komentar mengirim notifikasi sebutan ke semua anggota project
  tanpa menjadikan mereka subscriber. Endpoint baru `chat/rujukan/` dan
  `chat/rujukan/info/`. Petunjuk `@ mention · # channel or work item` tampil di
  placeholder kotak tulis chat, komentar, dan deskripsi selama masih kosong.
  Arahkan pointer ke sebutan untuk kartu pratinjau: orang = kartu profil yang
  sudah ada (kini terbuka saat hover), kanal = nama, publik/privat, topik, jumlah
  anggota, work item = nomor, project, judul, state, prioritas, tenggat,
  penanggung jawab. `chat/rujukan/info/` ikut membawa bahan kartunya
  (komponen `HoverCard` baru di `@plane/propel/popover`, Base UI PreviewCard).
  Kartu profil tidak lagi mencetak label "Division"/"Department" di tiap unit;
  ikon gedung sudah menandai penempatan.
  Tanpa migrasi. Ikut diperbaiki: email sebutan deskripsi dulu
  dialamatkan ke variabel sisa loop (`subscriber`), bukan orang yang disebut.
- **Sematkan, salin, dan reaksi cepat di chat (KEP-87).** Anggota yang boleh
  menulis di ruang bisa menyematkan pesan siapa pun (Pengumuman: admin saja,
  Changelog: tidak bisa), maksimal 20 per ruang, tampil di bilah atas
  percakapan. Kolom `disematkan_pada`/`disematkan_oleh` di `PesanLangsung`
  (migrasi 0167), endpoint `chat/pesan/<id>/sematkan/` dan
  `chat/ruang/<id>/sematan/`, siaran WebSocket `sematan`. Menu pesan dapat
  Salin, dan baris reaksi cepat plus pemilih emoji lengkap; di
  layar sentuh lewat tekan lama.
- **Gelembung chat lebih rapat.** Jarak lebar antarpesan ternyata dari bilah
  aksi tak terlihat (`opacity-0`) yang tetap memakan ~30px di bawah tiap
  pesan. Bilah itu dibuang: aksi (reaksi cepat, Balas, Salin, Sematkan,
  Sunting, Hapus) pindah ke menu klik kanan / tekan lama / Shift+F10, plus
  tombol emoji dan "..." yang melayang di samping gelembung saat diarahkan.
  Semua gelembung, termasuk kartu panggilan/tugas/rilis, memakai satu radius
  kecil (`rounded-item`). Reaksi menumpang tepi bawah gelembung.
- **Kartu aktivitas masuk DM pelaku (KEP-90).** Persetujuan, komentar,
  sebutan, dan pembaruan work item kini dikirim ke DM antara orang yang
  bertindak dan tiap orang yang terdampak (penerima notifikasi: assignee,
  penyetuju, pembuat), dengan pelaku sebagai pengirim. Aksi sistem, bot, dan
  aksi atas tugas sendiri tetap ke ruang "Paradise". Saklar yang sama dengan
  penugasan ke DM (`ENABLE_TUGAS_KE_DM`); dimatikan, semua kartu kembali ke
  ruang "Paradise". Tidak ada migrasi; kartu lama tetap di tempatnya.
- **Kartu milik sendiri berwarna gelembung sendiri.** Kartu panggilan, tugas,
  dan persetujuan yang saya picu tampil di warna aksen seperti pesan keluar;
  tombol Approve/Reject tidak muncul di kartu pengajuan saya sendiri.
- **Perbaikan chat 5 Nov sore.** Tombol emoji/"..." di samping gelembung
  tidak lagi hilang saat diarahkan (celah 4px di luar area hover), kini rata
  bawah dan menempel (sticky) untuk pesan panjang. Reaksi ganda/tak bisa
  ditambah: klik menu konteks Base UI terpicu dua kali di Windows (disaring
  `chat/reaksi.ts`), toggle reaksi di server kini atomik (kunci baris pesan,
  duplikat lama ikut bersih), dan reaksi pada riwayat lama kini tampil. Menu
  klik kanan tidak lagi tertutup chip reaksi (`z-50` dipindah ke Positioner
  di propel). Pratinjau tautan diberi jarak bawah 12px.
- **Mengetik terasa lebih ringan.** Kotak tulis chat jadi komponen sendiri
  (`chat/kotak-tulis.tsx`), jadi ketikan tidak lagi merender ulang seluruh
  daftar pesan. Deskripsi work item dan komentar baru tidak lagi merender
  ulang editor Tiptap tiap ketukan (Controller react-hook-form diganti
  `setValue`).
- **Kartu profil anggota.** Divisi dan departemen di baris terpisah, peran
  jadi lencana sendiri; penempatan ganda tampil per blok (3 pertama, sisanya
  "+N lagi").
- **Ilustrasi empty state di tengah.** `EmptyStateDetailed` di propel kini
  bawaannya `align="center"`; semua halaman kosong/tidak ditemukan ikut.
- **Folder favorit dicabut.** Tombol buat folder di sidebar Favorites
  dihapus dan folder tidak lagi ditampilkan. Favorit yang dulu di dalam folder
  naik ke daftar utama, jadi tidak ada yang hilang; baris folder lama tetap di
  database, tanpa migrasi.
- **Tombol "ke pesan terbaru" di chat.** Muncul saat menggulir ke atas, diberi
  titik kalau ada pesan masuk. Pesan masuk tidak lagi menarik layar ke bawah
  selagi membaca riwayat; percakapan yang baru dibuka dan pesan kiriman
  sendiri tetap langsung ke bawah.
- **Your Work tidak lagi menampilkan baris kosong.** `ActivityMessage` hanya
  kenal sebagian `field`; reaction, vote, draft, comment, approval, `intake`
  (web memakai kunci `inbox`) dan `estimate_points` jatuh ke kosong, jadi yang
  tampil cuma "You, 1 day ago". Kini ada pesan untuk semuanya dan field tak
  dikenal dapat kalimat umum. Tidak ada data yang dihapus.
- **Audit log God Mode berlabel lengkap.** Tipe objek kosong karena label di
  web cuma kenal lima model, sementara perubahan setelan tercatat sebagai
  `instanceconfiguration`. Semua endpoint tulis God Mode kini mencatat lewat
  `plane/license/audit_godmode.py` dengan tipe dan nama objek; baris lama yang
  kosong dapat label cadangan.
- **Gambar chat dibuka di penampil work item (KEP-88).** Klik gambar lampiran
  chat membuka lightbox yang sama dengan deskripsi work item (zoom, geser,
  Esc/Back), bukan tab baru. `ImageFullScreenModal` kini diekspor dari
  `@plane/editor`.
- **Tautan & gambar di deskripsi/komentar ikut tampil di Links dan
  Attachments (KEP-88).** Tidak disimpan sebagai baris baru: daftar
  `issue-links/` dan `attachments/` menambahkan turunan dari teks
  (`plane/utils/turunan_konten.py`) berpenanda `sumber`, hanya-baca di web.
  Hapus dari teks = hilang dari daftar. Gambar deskripsi tidak bisa lagi
  dihapus lewat endpoint lampiran. Lencana jumlah di daftar work item masih
  menghitung yang manual saja.
- **Kartu pratinjau tautan (KEP-88).** Endpoint baru
  `workspaces/<slug>/link-preview/?url=` mengambil judul, ringkasan, gambar
  Open Graph lewat `safe_get` (IP dipatok tiap hop), cache 24 jam (gagal: 1
  jam), 120 permintaan/menit per orang. Kartu tampil di bawah deskripsi,
  komentar, pesan chat, dan di atas kotak tulis chat saat mengetik. Tanpa
  migrasi, tanpa setelan baru, masuk ke 3.1.0 yang belum dirilis.
- **Project disebut departemen di mana-mana (KEP-92).** Tiap departemen sudah
  punya tepat satu project (0146), jadi yang berubah cuma sebutannya: 19
  locale, teks hardcode web, dan God Mode. Tombol, modal, perintah palet, dan
  pintasan "buat project" di web dibuang; `ProjectViewSet.create` menjawab 403
  "Departments are created in God Mode." API v1 tidak diubah. Kartu departemen
  di papan Organization tidak lagi mengulang nama project-nya, dan kelas
  `uppercase` dibuang dari semua label teks.
- **Wiki lepas dari project (KEP-94), major.** Migrasi 0170 membuat
  `wiki_folder` dan `wiki_material`; 0171 memindah tiap halaman project WIKI
  jadi folder ber-id sama dan tiap materi jadi `WikiMaterial` ber-id sama
  dengan berkasnya (tautan lama tetap hidup), lalu mem-soft-delete project
  WIKI, keanggotaannya, halaman lamanya, dan baris ACL lamanya dengan satu cap
  waktu. Objek MinIO tidak disentuh. Tiap Divisi dan Departemen otomatis punya
  folder. Hak unggah dibaca dari penempatan organisasi, bukan keanggotaan
  project. Endpoint baru di `/api/workspaces/<slug>/wiki/`, endpoint Wiki lama
  di bawah `projects/` dibuang, Wiki punya tempat sampah sendiri. Langkah
  operator: tidak ada yang manual (deploy menjalankan 0170/0171), tapi
  sesudah deploy buka /wiki dan cek folder lama tetap berisi; migrasi bisa
  dimundurkan (`migrate db 0170`) selama project WIKI belum dihapus permanen
  oleh tugas harian (lihat `TRASH_RETENTION_DAYS`).

## 2026-11-04

### Versi 2.3.0

- **Naik 2.2.0 ke 2.3.0, minor (dulu bernomor 3.0.0).** Gabungan dua nomor
  lama: 2.3.0, yang tidak pernah dirilis sendiri, dan 3.0.0. Semantik izin
  berubah dan orang kehilangan hak yang kemarin mereka punya (KEP-85), ada
  endpoint baru, dan satu migrasi data perapian (0163, jalan sendiri saat
  deploy). Tidak ada langkah operator.

- **Izin per sumber mengikuti kepemilikan dan hierarki (KEP-85).** Module, page,
  view, komentar, dan materi Wiki hanya bisa diubah, diarsipkan, atau dihapus
  pemiliknya (pembuat/owner, ditambah lead dan anggota module), atasannya di
  hierarki, admin workspace, dan Super Admin. Struktur project (detail &
  setelan, state, label, estimate, intake, arsip/hapus project, pulihkan/buang
  trash) jadi wewenang supervisor ke atas di project yang ia awasi. Role "admin
  project" milik Plane tidak lagi memberi hak atas barang orang lain. Semua 18
  aturan bisa diatur di God Mode > Work rules > Permissions (frasa
  `CHANGE RULES`, tercatat di Audit log). Endpoint baru
  `GET workspaces/<slug>/izin-saya/` dipakai web untuk menyembunyikan aksi yang
  pasti ditolak.
- **Celah yang tertutup:** token API bisa mengubah/menghapus komentar siapa pun
  (termasuk guest); setiap member bisa mengubah dan mengarsipkan module orang
  lain, mengarsipkan project, dan mengubah state; guest bisa mengubah state;
  token API bisa mengarsipkan project tanpa jadi admin; siapa pun bisa mengganti
  judul materi Wiki orang lain lewat endpoint aset; admin project bisa membuang
  permanen page, view, module, dan materi orang lain dari Trash.
- **Yang akan terasa:** staf tidak lagi bisa memasukkan work item ke module yang
  bukan miliknya (bukan pembuat, lead, atau anggota). Mengatur state, termasuk
  urutannya, kini butuh wewenang alur kerja.

- **Tampilan HP dirapikan di seluruh aplikasi.** Diuji dengan tangkapan layar
  390/360/768/1280 px. Nama di tabel Members tidak lagi pecah satu huruf per
  baris (juga di desktop). Bilah atas: pencarian jadi ikon yang membuka palet
  perintah, lonceng/bantuan/avatar tidak lagi terdorong keluar layar. Tab
  project bisa digeser, breadcrumb tanpa panah gantung dan tanpa baris ganda di
  Settings, toolbar work item punya tombol Filter dan ikon tata letak. Ribbon
  filter: tombol pindah ke baris sendiri di HP, chip lebih besar di layar
  sentuh, filter tidak lagi hilang di dev (StrictMode). Toolbar Members, padding
  profil, palet perintah, modal, dropdown, laci sidebar, Pages, Views, Dashboard
  Divisi, dan Recents ikut dirapikan. Ikut 2.3.0 yang belum dirilis, tanpa
  naik versi lagi.
- **God Mode ditata ulang, aturan kerja bisa diatur (KEP-83).** Delapan menu
  (General, Sign-in & access, People, Work rules, Notifications, Modules,
  Integrations, Data & logs); URL lama dialihkan. Satu sumber setelan:
  `GET/PATCH /api/instances/settings/`, God Mode tidak lagi menyalin bawaan.
  Baru bisa diatur: jam & hari ringkasan dan pengingat dalam zona waktu kantor,
  titik pengingat, aturan persetujuan, hapus/arsip, ganti tenggat, assign ke
  bawah saja, batas unggah, umur sesi, masa berlaku undangan, batas chat
  (panjang, lampiran, jendela sunting), jendela Needs attention. Semua bawaan =
  perilaku lama; aturan sensitif minta frasa `CHANGE RULES` dan tercatat di
  Audit log. Saklar pribadi yang induknya dimatikan admin tampil terkunci.
  Arsip otomatis instance jadi plafon untuk setelan per project. People >
  Organization jadi satu halaman: bagan struktur di atas, Board seret-lepas
  di bawah (tab Chart & details dan panel project lama dibuang, KEP-86);
  seret orang kembali ke People = cabut dari tempat itu; supervisor/manager
  jatuh ke Staf hanya kalau tidak tersisa departemen atau divisi apa pun; tombol edit member di kolom pertama;
  kolom teknis Audit log selalu tampil. Migrasi 0165 hanya menambah tabel
  penanda jadwal. Tetap minor: tanpa env baru dan tanpa langkah operator.
  Catatan operator: `FILE_SIZE_LIMIT` dan `SESSION_COOKIE_AGE` kini hanya
  benih. Sesudah deploy pertama, menaikkan env tidak lagi menaikkan batas;
  ubah di God Mode (Modules > Files, Sign-in & access > Sessions). Migrasi 0165
  bergantung pada 0163 dan 0164, jadi ketiganya harus ikut commit yang sama.
- **Pencarian setelan God Mode (Ctrl/Cmd + K).** Palet perintah ala Power K
  di header God Mode: cari menu, tab, dan setiap setelan registri secara fuzzy
  lewat judul, teks bantuan, label pilihan, kunci setelan, dan jalur menu
  (salah ketik satu huruf tetap ketemu). Memilih setelan membuka tabnya,
  menggulir ke barisnya, dan menandainya sebentar. Dropdown pilihan
  (`CustomSelect`, `CustomSearchSelect`) kini rata kiri saat labelnya
  terlipat dua baris; sebelumnya baris kedua jadi rata tengah.
- **Bawaan setelan ditinjau ulang + waktu selesai = saat mengajukan (KEP-84).**
  Bawaan baru: gerbang hierarki, email pengingat tenggat, satu utas email per
  work item, dan email hanya ke member aktif HIDUP; undangan kedaluwarsa 7 hari,
  jendela sunting chat 24 jam, Trash 30 hari, member baru zona Asia/Jakarta.
  Tugas yang diajukan staf dihitung selesai saat diajukan, bukan saat atasan
  menyetujui, dan selama menunggu tidak dihitung terlambat; pengingat lewat
  tenggat pindah ke penyetuju. Keduanya setelan God Mode > Work rules.
  Akibat langsung saat deploy (kuncinya baru lahir di rilis ini): orang yang
  30 hari tak membuka aplikasi berhenti menerima email kabar kerja (inbox tetap),
  undangan lebih tua dari 7 hari langsung kedaluwarsa, pesan chat lebih tua dari
  24 jam tak bisa disunting lagi.
- **Panggilan DM berdering di halaman mana pun, video kembali jalan.**
  Undangan panggilan dulu lewat soket PER RUANG, jadi yang ditelepon hanya
  berdering kalau kebetulan sedang membuka percakapan itu, dan yang mengangkat
  masuk ke ruang LiveKit milik percakapan yang terbuka di layarnya, bukan milik
  panggilannya. Sekarang sinyal DM lewat soket kehadiran (satu per tab,
  `tipe: "panggilan"`, diperiksa keanggotaan ruangnya oleh `apps/live`), dan
  panggilan hidup di tingkat workspace (`penyedia-panggilan.tsx`) sehingga tidak
  putus saat pindah halaman. Ada kartu panggilan masuk + nada dering +
  notifikasi peramban, batas dering 45 detik (penelepon: "Tidak dijawab", yang
  ditelepon: "Panggilan tak terjawab"), batal, tolak, sibuk, dan sinkron antar
  tab. Video: `adaptiveStream` dicabut karena kita tidak memakai
  `track.attach()`, sehingga server berhenti meneruskan video (suara jalan,
  video 0 KB); pratinjau sendiri dirakit ulang sesudah kamera dinyalakan lagi,
  dan kamera lawan yang dimatikan tampil sebagai avatar.
- **Staf jadi jenjang bawaan, staf tidak bisa membuat project (KEP-79).**
  Orang tanpa jenjang otomatis Staf; manajer/supervisor yang kehilangan tempat
  terakhirnya turun ke Staf. Membuat project hanya untuk Super Admin, Admin
  workspace, dan Supervisor ke atas. Jenjang bisa diatur langsung di God Mode
  > Members > Organization.
- **Quick link bersama + judul & favicon otomatis (KEP-82).** Super Admin dan
  admin workspace bisa memasang quick link untuk semua orang atau untuk divisi
  dan departemen tertentu. Satu modal untuk semua link: admin memilih
  Visibility Private (hanya dirinya) atau Public (semua orang / unit pilihan);
  member biasa hanya mengelola link Private miliknya. Mengganti visibilitas
  memindah link. Link itu tampil paling atas di Home dan halaman Quick links
  tiap orang yang masuk sasarannya. Judul dan favicon diambil otomatis dari
  situsnya; ikon dipilih dari emoji/ikon bawaan seperti ikon project (bukan
  URL gambar), dan bisa dikembalikan ke favicon situs. Teks quick link yang
  dulu tampil sebagai kunci mentah kini terbaca. Migrasi 0164 menambah tabel;
  migrasi 0166 mengimpor 23 link dari portal one.paradiseperkasa.com sebagai
  quick link global untuk semua orang (idempoten, ikut terpasang saat deploy).
- **Inbox jadi popover di lonceng (KEP-80).** Bisa diperluas ke halaman penuh.
  Halaman penuh dirapikan: header sejajar, kolom daftar lebih lebar, tombol
  suara kini jalan (z-index salah tempat) dan seukuran tombol lain.
- **Chat: pesan terhapus tampil "Pesan dihapus" (KEP-81)**, daftar orang
  diurutkan online/away dulu, lencana status juga di diri sendiri.
- **Ganti tema tanpa memuat ulang halaman.** Tema diterapkan langsung, disimpan
  di latar belakang, dikembalikan kalau gagal.
- **Wiki tidak lagi dihitung** di Dashboard Divisi, Laporan, analytics, dan
  daftar project tanpa departemen.
- **Kartu profil member di seluruh God Mode**, "View work" hanya untuk admin,
  dan nama/email panjang di tabel member tidak lagi meluber.
- **Email yang isinya sama dikirim sekali, semua alamat di To (KEP-78).**
  Peringatan riwayat login akan dihapus (ke semua admin), email penugasan ke
  rekan setugas, dan pengingat tenggat satu tugas dulu dikirim satu per satu;
  sekarang satu email `To: a; b; c`, jadi tiap penerima tahu siapa lagi yang
  menerimanya. Sapaannya menyebut semua nama dan footer menulis semua alamat.
  Dipecah hanya per bahasa penerima dan posisi di utas email, maksimal 50
  alamat per pesan.
- **Stickies dan editor ikut font aplikasi.** Editor (stickies, deskripsi,
  komentar, halaman) dulu memakai Inter yang dipatok; sekarang pilihan
  "Sans serif" mengikuti font antarmuka di Preferensi. Font kode (blok kode,
  `<code>`, `<kbd>`, kelas `font-code`/`font-mono`, pilihan "Mono" di editor)
  selalu Geist Mono, juga saat font antarmuka diganti ke JetBrains Mono. Blok
  kode dulu menunjuk keluarga "JetBrainsMono" yang tidak pernah dimuat, dan
  `font-mono` adalah kelas mati yang diam-diam memakai font antarmuka.
- **"Deleted account" tidak lagi nyangkut di departemen God Mode.** Menghapus
  akun dulu tidak mencabut penempatan organisasinya, jadi akun itu tetap
  tampil (di R&D sebagai Manager) dan tombol cabutnya diam karena daftar member
  menyembunyikan akun terhapus. Sekarang penghapusan akun mencabut
  penempatannya (soft delete), memulihkan dari Trash mengembalikannya, pohon
  organisasi tidak pernah menampilkan akun terhapus, dan migrasi 0163
  merapikan sisa lama. Baris produksi sudah dibersihkan langsung 4 Nov.
- **God Mode > Email > Preview:** bawaan bahasa jadi Inggris, tombol
  "Send to me" mengirim contoh yang sedang dibuka ke email admin yang masuk
  (`POST /api/instances/email-preview/<key>/send/`), dan bingkai iframe tidak
  lagi menambah sudut/garis yang bukan bagian dari email.
- **Pengirim email bernama "Space Paradise Perkasa"** (`pengirim()` di
  `email_merek.py`); alamatnya tetap dari konfigurasi SMTP God Mode.
- **Garis tipis di dalam kartu email (Outlook klasik) hilang.** Bingkai kartu
  dulu berupa sel berlatar warna garis dengan sel putih di dalamnya; Word pada
  skala layar 125/150% menyisakan celah antar blok sehingga warna garis tembus
  jadi garis sepanjang kartu. Sekarang satu bingkai bersama
  (`partials/bingkai_buka.html` / `bingkai_tutup.html`): Outlook klasik memakai
  sel garis 1px di empat sisi, klien lain `border` biasa.
- **Font email = tumpukan sistem berawalan Segoe UI**, tautan Google Fonts
  dibuang, supaya pratinjau God Mode sama dengan yang tampil di Outlook. Tinggi
  tombol HTML disamakan dengan tombol VML Outlook (40px).
- **Email tugas & persetujuan dikumpulkan jadi satu ringkasan per orang.**
  Antrean `EmailNotificationLog` + sapuan 5 menit, jeda bawaan 15 menit;
  permintaan persetujuan di atas. Tiga setelan baru di God Mode `/features`:
  `ENABLE_EMAIL_BATCH` (+ `EMAIL_BATCH_DELAY_MINUTES`), `ENABLE_EMAIL_THREADING`
  (balasan di utas yang sama per work item, bawaan mati karena subjek jadi
  `[PROJ-12] Judul`), `ENABLE_EMAIL_ACTIVE_ONLY` (+ `EMAIL_ACTIVE_DAYS`, 30).
- **Widget "Needs attention" di Home** (`GET .../paradise/attention/`): tugas
  telat, jatuh tempo 7 hari, ditolak, menunggu persetujuan, mention; atasan
  juga dapat antrean keputusan dan tugas telat timnya.
- **Antrean persetujuan hanya untuk yang berhak memutuskan** (predikat sama
  dengan aksi setujui/tolak); ditolak lalu diajukan ulang kini tampil sekali
  sebagai menunggu. Kolom Approval di tampilan tabel punya dropdown filter
  (termasuk "None").
- **Activity:** entri ganda hilang (join keanggotaan project diganti `Exists`,
  store menyaring id ganda); field tak dikenal tidak lagi tampil kosong.
- **Mobile:** sidebar tidak lagi terbuka sendiri dan tidak tertutup header,
  setelan profil pakai navigasi mobile, teks activity membungkus, ID di
  antrean persetujuan tidak terpotong, target sentuh menu dropdown lebih tinggi.
  Dropdown Module di detail work item sejajar tinggi baris lain.

## 2026-11-03

### Versi 2.2.0

- **Naik 2.1.0 ke 2.2.0, minor.** Awalnya 2.1.1 (patch teks email), lalu naik
  ke minor karena rilis yang sama menambah properti tampilan baru. Tetap
  minor sesudah gelombang 3 Nov sore (kanal sistem, kartu chat, profil,
  email bermerek): dua migrasi aditif (`0159_obrolan_kartu_sistem`,
  `0160_profil_kontak`) dengan nilai bawaan, data lama tetap jalan. Filter
  tampilan lama tetap jalan (properti baru bawaannya menyala).
  - **DM penugasan lama ikut jadi kartu.** Migrasi `0161_kartu_tugas_lama`
    mengubah DM "📋 Tugas baru untuk Anda" berbentuk teks dari sebelum 2.2.0
    menjadi kartu tugas bertombol. Hanya `jenis`/`muatan` yang berubah, `isi`
    tetap; tugas yang sudah dihapus dibiarkan teks. Bisa dibalik, tanpa langkah
    operator, jadi tetap minor. Jenis kartu lain (sebutan, komentar, pembaruan,
    persetujuan, project) belum pernah dikirim ke obrolan sebelum 2.2.0.
  - **Penempatan: menambah, bukan memindah (KEP-76).** Satu orang = satu
    jenjang + satu daftar tempat. Staf dan supervisor boleh di banyak
    departemen; manager boleh memimpin banyak divisi dan sekaligus duduk di
    departemen di luar divisinya. Galat "Only supervisors can hold multiple
    departments", "Lowering the level requires a single department first", dan
    "Set a level before placing this person" dihapus: turun di bawah Manager
    melepas divisinya otomatis (editor menampilkannya sebelum Simpan),
    departemennya tetap. Empat jalur tulis yang dulu menimpa baris penempatan
    PERTAMA (editor jenjang, "Jadikan departemen dari project", pilih
    departemen sendiri) sekarang lewat satu penulis, `plane/db/penempatan.py`.
    Editor Member: satu pemilih "Departments & divisions"; "Other project
    access" hanya menampilkan project yang belum otomatis. Halaman Organisasi:
    panel "Multi-department supervisors" dilebur ke Members, label calon
    "moved from" jadi "also in". Tetap minor: tanpa migrasi, data lama tetap
    berlaku. **Cek sebelum deploy:** baris manager yang menempel di departemen
    dulu diabaikan dan sekarang memberi akses ke project departemen itu.
    Hitung dulu di produksi:
    `JabatanOrganisasi.objects.filter(tingkat__gte=30, tingkat__lt=40, departemen__isnull=False).count()`.
  - **Cek sebelum deploy.** Bahasa email sekarang mengikuti
    `Profile.language`, dan bawaannya `en`. Periksa nilai itu di produksi
    dulu, kalau tidak seluruh kantor menerima email berbahasa Inggris.
    Indikator online butuh `apps/live` dan Redis.
  - **Gambar pratinjau tautan ikut tampilan Bara.** `og-image.png` (yang
    muncul saat tautan dibagikan di WhatsApp, Slack, Teams) sekarang memakai
    panel arang hangat layar masuk, Plus Jakarta Sans + Geist Mono, dan
    potongan papan project yang sama dengan `AuthShowcase`. Pembangkitnya
    pindah dari Pillow ke `paradise/bin/buat-og-image.mjs` +
    `og-image.html` (dipotret Chrome headless), jadi font dan warnanya sama
    persis dengan aplikasi. `og:description` ikut jadi "tugas", bukan "issue".
  - **Sebutan @ di obrolan & kanal divisi/departemen (KEP-74).** Ketik `@` di
    kotak tulis untuk menyebut orang di percakapan itu (DM: lawan bicara; kanal:
    anggotanya). Peramban mengirim ID (`sebut`), server menyaringnya ke anggota
    ruang, menyimpannya di `muatan.sebut`, dan untuk kanal mengirim kartu
    "menyebut Anda di #kanal" ke ruang Paradise orang itu (saklar
    `inbox_mention`). Tiap divisi dan departemen otomatis punya kanal privat
    (`kunci_sistem` `divisi:<id>` / `departemen:<id>`); anggotanya mengikuti
    penempatan God Mode lewat `plane/db/jangkauan.py`, tanpa tombol
    undang/keluar. Tanpa migrasi.
    Sebutan ke diri sendiri sekarang ikut tersorot dan bisa diklik seperti
    sebutan yang kita kirim. Dulu nama pencocoknya "Anda", bukan nama tampilan
    asli, jadi `@NamaSaya` di pesan orang lain tetap teks biasa.
  - **Kutipan balasan bisa diklik.** Mengklik kutipan di gelembung melompat ke
    pesan aslinya dan menyorotnya sebentar. Kalau pesan itu belum termuat,
    riwayat lama ditarik sampai 10 halaman; kalau sudah dihapus, muncul kabar
    "pesan aslinya sudah tidak tersedia".
  - **Kartu profil: data kosong cukup "Not set".** Awalan "Job title:" dan
    sejenisnya dibuang; ikon barisnya sudah menunjukkan datanya apa.
  - **Notifikasi peramban untuk obrolan & inbox.** Dulu kartu sistem operasi
    hanya untuk tab tersembunyi, jadi Paradise yang terbuka di belakang aplikasi
    lain cuma berbunyi. Sekarang tiap pesan obrolan dan pemberitahuan inbox
    juga dikirim lewat peramban (kalau diizinkan), di samping kartu dalam
    aplikasi. Saklar + tombol uji di popup suara (Chat & panel Notifications),
    disimpan per peramban (`notif_peramban_nyala`). Gagal di Chrome Android
    (`new Notification` melempar) jatuh ke kartu dalam aplikasi. Peramban yang
    ditutup tetap tidak menerima apa pun (itu butuh Web Push).
  - **Perbaikan: bunyi saat membuka kanal sistem.** Penanda pesan terakhir di
    halaman Obrolan tidak dikunci per percakapan, jadi berpindah ke percakapan
    yang sudah ada di cache SWR terbaca sebagai pesan baru dan berbunyi.
  - **Perbaikan: kartu komentar/sebutan/pembaruan tidak pernah terkirim.**
    `notification_task` membangun Notification di memori dengan id string,
    sedangkan `_muat_tugas` memakai kunci UUID, jadi semua kartu dari jalur
    Celery terlewat diam-diam. Kunci sekarang string, ada uji penjaganya.
  - **Nama orang bisa diklik (KEP-73).** Assignee di sidebar & peek, Created by
    di peek, nama pengirim gelembung chat, kutipan balasan, dan `@sebutan`
    membuka kartu profil. Sebutan chat punya tiga gaya (saya disebut, saya
    menyebut, orang lain). Data profil kosong tampil satu baris "Not set".
    Avatar assignee di tabel (spreadsheet), kartu list/kanban, sub-issue,
    relasi, inbox, dan antrean persetujuan juga membuka kartu profil; sisa sel
    tetap membuka pemilih assignee. Sel baca-saja dirender tanpa tombol
    `disabled`, karena tombol itu menelan klik avatar di dalamnya.
  - **Command palette (Power K) mengikuti fitur yang ada.** Perintah baru:
    Chat (`gc`), Wiki (`gw`), Dashboard Divisi (`gb`), Stickies (`gt`), Quick
    links (`gl`), Approvals project (`gq`), Initiatives, kalender Your Work,
    dan "Open an account setting" (`oa`, tab modal profil termasuk
    Connections). Semuanya ikut saklar modul God Mode dan akses yang sama
    dengan sidebar. Dibuang: semua perintah Cycles (KEP-53; `gc` kini milik
    Chat), Billing di daftar setelan workspace (tak punya halaman), perintah
    "Documentation" (diganti `gw`), dan "Go to account settings" yang
    menunjuk `/settings/account` yang tak ada, kini membuka modal profil.
  - **Batas hapus pesan obrolan.** Pengirim hanya bisa menghapus pesannya
    sendiri dalam 24 jam; sesudahnya server menjawab 403 dan tombol hapus
    hilang. Angkanya setelan baru `CHAT_DELETE_WINDOW_HOURS` di God Mode >
    Features > Chat (0 = tanpa batas), dibenihkan otomatis oleh
    `configure_instance`, tanpa migrasi.
  - **Job title dari daftar departemen.** Profile > General memakai pilihan
    departemen (`GET penempatan-saya/?daftar=1`), bukan kolom bebas. Isian
    lama yang bukan nama departemen tetap terlihat dan tidak terhapus.
  - **Obrolan ala WhatsApp.** Kutipan balasan berlatar tipis dengan garis
    aksen kiri yang ikut sudut kotak, nama pengirim di gelembung masuk, dan
    avatar di kanal kini milik pengirim tiap pesan (sebelumnya selalu lawan
    bicara DM, jadi kosong di kanal).
  - **Ekstensi telepon di kartu profil anggota** selalu tampil berlabel,
    atau "Not set" kalau belum diisi.
  - **Popup suara di Obrolan dan panel Pemberitahuan.** Tombol speaker tidak
    lagi sekadar saklar bisu: klik membuka popup berisi penggeser volume,
    saklar bisu, dan tombol Pratinjau. Logikanya dipakai bersama dengan
    Profile > Preferences (`useVolumeSuara`), jadi keduanya menyimpan ke akun
    yang sama.
  - **Avatar di layar panggilan.** `Avatar` propel mengabaikan ukuran angka,
    jadi avatarnya kempis jadi huruf kecil terpotong. Ukuran angka sekarang
    dipasang inline, dan layar panggilan menampilkan foto profil asli (lawan
    bicara di DM, tiap peserta dari identitas LiveKit).
  - **Layar masuk baru (web dan God Mode).** Satu kartu berbingkai: panel
    kiri memutar empat gambar aplikasi (papan, dashboard divisi, detail
    tugas, chat) dengan keterangan satu baris, panel kanan form masuk.
    Daftar fitur bernomor, slogan, tekstur titik, dan baris hak cipta
    dibuang; merek tampil sebagai "Space Paradise Perkasa", judul form
    berbahasa Inggris ("Sign in"). Pernyataan "Sistem internal PT Paradise
    Perkasa" di bawah form ikut dibuang. Komponennya satu, `AuthShowcase` di
    `@plane/propel/auth-showcase`; warnanya token `--pamer-*` di
    `paradise-tampilan.css`. Kunci i18n `login_ui.*` diganti di 19 bahasa.
  - **Sidebar tanpa label ganda.** Grup project di sidebar hanya memakai nama
    divisi; label departemen di atas tiap project dibuang karena project
    sudah khusus per departemen dan namanya sama.
  - **Departemen selalu punya project (KEP-32 dikuatkan).** Kode yang
    identifier-nya bentrok tidak lagi ditolak: project baru dapat akhiran
    angka (`P1` -> `P3`). Memindahkan project ke departemen lain langsung
    membuatkan project pengganti untuk departemen asalnya, dan `project_ids`
    kosong ditolak. Data lama disusulkan lewat
    `manage.py lengkapi_project_departemen [--dry-run]` (manual, idempoten).
  - **Changelog lama ikut tampil.** `release_notes/` sekarang memuat 1.5.0,
    1.6.0, 2.0.0, dan 2.1.0. Rilis lama yang menyusul diberi tanggal
    rilisnya, jadi kanal tetap urut versi dan tidak menyalakan lencana
    belum-dibaca. Di produksi semuanya terbit otomatis saat container API
    2.2.0 pertama kali start.
  - **Gaya email.** Garis aksen callout dan catatan kartu ikut lengkung
    sudut kartu (sel bertingkat, bukan `border-left`). Tombol tidak lagi
    bergaris bawah di klien yang membuang `!important` inline.
  - **Saklar bulat penuh.** Lintasan dan kenop toggle (`@plane/ui`
    ToggleSwitch, `@plane/propel` Switch, saklar channel Slack) kembali
    `rounded-full`. Pengecualian kedua dari aturan "tidak ada yang bulat penuh
    kecuali avatar" di KEP-64.
  - **Breadcrumb God Mode tanpa huruf kapital semua.** Segmen tanpa label
    dulu tampil `PROJECT-DEFAULTS`; sekarang berlabel ("New project defaults",
    "Preview", "Workspaces") dan cadangannya kalimat biasa, bukan kapital.
  - **Toast tanpa garis aksen.** Pita 2px berwarna per jenis di tepi atas
    toast (`toast-garis`) dibuang. Jenis toast cukup terbaca dari ikonnya.
  - **Kolom Approval di tampilan tabel.** Status persetujuan punya kolom
    sendiri di spreadsheet, bukan lagi chip yang menumpang di sel judul.
    Pemutus tetap melihat tombol Setujui/Tolak di sel itu. Tugas yang tak
    pernah butuh persetujuan menampilkan strip.
  - **Display properties mengikuti apa yang ada.** Properti baru `Approval`
    bisa dimatikan per tampilan dan berlaku di list, kanban, dan tabel. Modul
    Approvals mati di God Mode = chip, kolom, dan warna baris persetujuan
    hilang. Menu Setujui/Tolak di titik-tiga sengaja tetap ada supaya tugas
    yang masih menunggu tidak terkunci selamanya. Estimate tidak ditawarkan di project tanpa
    estimasi. Created on/Updated on sekarang bisa dimatikan, tapi hanya
    ditawarkan di tabel karena list dan kanban memang tak menggambarnya.
  - **Laporan tugas selesai di Dashboard Divisi (KEP-62).** Mode ketiga,
    "Laporan", di samping Ringkas dan Rinci. Pilih periode (7 hari, 30 hari,
    bulan ini, bulan lalu), lalu lihat empat angka (selesai dengan pembanding
    periode sebelumnya, persen tepat waktu, selesai terlambat, work item baru),
    bilah selesai per divisi, dan judul setiap tugas yang selesai per divisi >
    project lengkap dengan penanggung jawab, tanggal selesai, dan label tepat
    waktu/terlambat/tanpa tenggat. Hari dihitung dalam WIB. Daftar di layar
    dibatasi 500 baris terbaru; CSV (`?unduh=csv`) memuat semuanya. Cakupan
    sama dengan dashboard: hanya project yang user anggotai. Endpoint baru
    `GET /api/workspaces/<slug>/divisi-dashboard/laporan/?periode=`, tanpa
    migrasi.
  - **Arsip otomatis work item Done (God Mode > Features > Work items).**
    Super Admin memilih Off / 7 / 14 / 30 / 60 / 90 / 180 / 365 hari; bawaan 90. Task harian 01:00 UTC mengarsipkan work item di grup completed yang
    sudah selesai selama itu, di semua project. Hitungan dari `completed_at`,
    baris lama tanpa `completed_at` memakai `updated_at`. Cancelled tidak
    ikut, intake yang belum diputuskan tidak ikut. Aktivitas dicatat tanpa
    notifikasi. Setelan "Auto-archive" per project milik upstream tetap jalan
    di sampingnya. Kunci baru `AUTO_ARCHIVE_DONE_DAYS`, PATCH menolak nilai di
    luar daftar. Tanpa migrasi. **Catatan deploy:** karena bawaannya 90 hari,
    putaran pertama sesudah deploy langsung mengarsipkan semua tugas Done
    yang selesai lebih dari 90 hari lalu. Setel ke Off di God Mode sebelum
    01:00 UTC kalau itu belum diinginkan. Semuanya bisa dipulihkan dari
    Archives.
- Perbaikan teks email persetujuan (rencana 2.1.1):
  - Email persetujuan tidak lagi tertukar antara atasan dan staf. Subjek untuk
    atasan diawali "Perlu persetujuanmu: Andi menandai ... selesai", subjek
    untuk staf diawali "Pekerjaanmu disetujui/ditolak". Isi, tombol, dan kaki
    email menyebut peran penerima.
  - Teks email masih memakai alur lama KEP-28 ("tidak lagi terkunci",
    "kembali ke draft pribadimu"). Sekarang mengikuti KEP-55: disetujui = Done,
    ditolak = kembali ke In Progress lalu geser ke Done lagi untuk mengajukan
    ulang.
  - Kartu inbox ikut diperjelas ("perlu persetujuan Anda untuk menandai tugas
    ini selesai", "menyetujui pekerjaan Anda"), dan setelan notifikasi
    "Persetujuan penugasan" berganti nama jadi "Persetujuan selesai".
  - Super Admin yang ditempatkan di sebuah departemen atau divisi (God Mode >
    Organization) sekarang muncul di project departemen/divisinya: filter
    Created by, Assignees, Mentions, dropdown assignee, pemilih mention, dan
    daftar anggota. Di project lain ia tetap tersembunyi. Satu perbaikan di
    `plane/db/superadmin.py`, jadi kelima endpoint daftar anggota ikut (KEP-61).
- Performa dan pemakaian di layar sentuh (ikut 2.2.0, tidak menaikkan versi
  lagi; semuanya perbaikan tanpa migrasi dan tanpa langkah operator):
  - **Papan lebih ringan untuk atasan.** `_bawahan_ids` dan `rekan_staf_ids`
    dulu menembak satu kueri keanggotaan per orang (`bisa-ditugaskan/`, tiap
    papan dibuka, dan tiap ubah properti). Sekarang satu kueri. Endpoint
    `bisa-ditugaskan` juga membuang pemeriksaan keanggotaan kedua per bawahan.
  - **Ubah properti tugas tidak lagi memeriksa izin dua kali.** View PATCH
    menandai konteks serializer, jadi `galat_ubah_tugas` cukup jalan sekali.
    Jalur tulis lain (bulk, API token, intake) tetap diperiksa di serializer.
  - **Daftar Initiatives**: dua kueri agregat untuk seluruh daftar, bukan tiga
    kueri per initiative.
  - **Hak akses per kartu tidak diambil ulang terus.** `bisa-ditugaskan` dan
    status Super Admin tidak lagi dimuat ulang tiap kartu digulir kembali ke
    layar atau tiap tab difokus; perubahan jabatan terbaca sesudah muat ulang.
  - **Chat**: SDK panggilan (LiveKit) baru diunduh saat panggilan pertama,
    bukan tiap chat dibuka. Gema soket dari aksi tab sendiri tidak memicu
    tarik ulang kedua. Gambar dan video lampiran punya tinggi tetap, jadi
    percakapan tetap berhenti di pesan terbaru saat gambar selesai dimuat.
  - **Aksi yang dulu cuma muncul saat hover sekarang terjangkau di HP/tablet**
    dan lewat papan ketik: tombol pesan chat, ganti nama/hapus materi Wiki,
    menu Quick Links, tutup pop-up notifikasi, menu bagan organisasi God Mode.
    Varian Tailwind baru `sentuh:` (= `pointer: coarse`, sama dengan
    `isMobile`) di `paradise.css`.
  - **Konfirmasi sebelum menghapus** pesan chat, keluar kanal, dan menghapus
    materi Wiki (hook `useKonfirmasi`). Sebelumnya satu sentuhan meleset
    langsung menghapus.
  - **Persetujuan**: alasan penolakan dan peringatan "belum ada penyetuju"
    tampil di bawah baris antrean, tidak hanya di tooltip yang tak pernah
    muncul di layar sentuh. Tombol Setujui/Tolak di kartu kanban lebih besar
    dan berjarak di layar sentuh.
  - Tata letak HP: nama kanal/DM panjang terpotong rapi alih-alih mendorong
    tombol panggilan keluar layar, URL panjang di gelembung chat dipatahkan,
    kontrol judul sub-topik Wiki jadi ikon saja di bawah `sm`, tabel Trash
    project memberi ruang untuk nama item, saklar matriks notifikasi lebih
    besar di layar sentuh, kepala divisi di sidebar lebih kontras.
  - Halaman Sambungan membedakan "memuat" dari "gagal memuat" dan memberi
    tombol coba lagi. Tiga kelas mati di God Mode (`text-sm`, `text-lg`,
    `text-custom-text-300`) diganti token tema.
  - **Sistem tampilan (KEP-64).** Semua nilai visual jadi token di
    `packages/tailwind-config/paradise-tampilan.css`; komponen hanya memakai
    kelas token dan prop komponen (`variant`, `size`), tidak menulis warna,
    radius, atau padding sendiri.
    - Latar berona per skema warna, bukan putih/hitam polos. Lima skema:
      Ember (bawaan, aksen merah merek), Dusk (ungu), Ink (indigo),
      Forest (hijau), Neutral (abu bawaan Plane, aksen biru). Aksen utama
      dan aksen kedua ikut skema; tangga `--brand-*` dibangun dari tiga
      kenop per skema.
    - Font Plus Jakarta Sans (bawaan) dan Geist Mono untuk kode, dimuat
      lokal dari fontsource.
    - Radius bernama, terdaftar juga di tailwind-merge: `control`,
      `button`, `field`, `item` 0.375 sampai 0.5rem, `card`/`popover`
      0.75rem, `overlay` 1rem. Tidak ada yang bulat penuh kecuali foto
      profil, spinner, dan titik status kecil.
    - Tombol ukuran 24/28/32/36px, tombol ikon setinggi tombol biasa,
      ukuran `chip` (20px, teks 11px) untuk properti di kartu work item.
    - Badge persetujuan memakai `Badge` propel dengan varian per status.
    - Satu kurva gerak untuk semua transisi; tampilan tabel work item
      berselang-seling (`bg-zebra`); garis aksen toast di tepi atas.
    - Efek 3D, kilap, dan glow sempat dicoba lalu dicabut atas permintaan
      user; tampilan kembali datar.
  - **Preferensi tampilan per orang.** Profile > Preferences: skema warna,
    font (Plus Jakarta Sans, Inter, Geist, Figtree, Bricolage Grotesque,
    Archivo, Sora, Shantell Sans, JetBrains Mono, Source Serif 4, font sistem), dan
    animasi (halus/kurangi). Disimpan di `Profile.theme`, tanpa migrasi.
    Mengikuti KEP-57: bawaan akun baru di God Mode > Members > Defaults,
    nilai per orang di panel member.
  - **Komponen standar di seluruh aplikasi.** `<select>` bawaan peramban,
    tombol buatan tangan, dan lencana warna sendiri di halaman Paradise
    dan God Mode diganti `Button`/`IconButton`/`Badge`/`CustomSelect`.
    `CustomSelect` tampil sama dengan `Input`; `CustomMenu.MenuItem` punya
    varian `danger`. Pagination God Mode memakai `Button`. Lencana belum
    dibaca di Chat memakai `CountChip` yang sama dengan Inbox. Nama divisi
    dan departemen di sidebar tidak lagi huruf kapital semua.
  - Tombol Filters/Display kadang berganti ukuran dan kadang tidak
    membuka panel: dua tombol (penuh dan ikon saja) ditukar container query
    di dalam `<div>` yang dijadikan tombol. Sekarang satu tombol nyata.
  - **Kanal sistem Announcements dan Changelog.** Ada di tiap workspace,
    semua anggota otomatis bergabung (migrasi mengisi anggota lama, sinyal
    dan pengecekan saat daftar chat dibuka menangani yang baru). Tidak bisa
    ditinggalkan, diganti nama, atau dihapus. Announcements hanya bisa
    diisi Super Admin dan admin workspace; Changelog hanya-baca.
  - **Changelog otomatis saat deploy.** Catatan rilis per versi di
    `apps/api/plane/release_notes/<versi>.json` (Added/Changed/Fixed).
    `terbitkan_changelog` jalan di entrypoint API sesudah migrasi, tidak
    pernah memposting dua kali, tidak memposting versi di atas
    `apps/api/package.json`, dan gagalnya tidak menahan gunicorn.
  - **Kartu di chat, bukan tautan.** Tiap orang punya ruang pribadi
    "Paradise" berisi kartu dengan tombol: persetujuan (Setujui/Tolak
    langsung, tombol hilang begitu ada keputusan), mention, komentar,
    pembaruan tugas, ditambahkan ke project. Pemicunya baris Notification
    yang sudah ada, jadi aturan dan setelan inbox tetap berlaku. Penugasan
    tetap di DM pemberi tugas, sekarang sebagai kartu.
  - **Log panggilan suara/video** muncul di percakapan (tersambung dengan
    durasi, atau tak terjawab) dengan tombol Telepon balik.
  - **Kelola kanal**: direktori kanal dengan pencarian dan pratinjau,
    panel setelan (ganti nama, topik, anggota, undang, keluarkan, keluar,
    hapus). Undangan ke kanal privat sekarang hanya oleh pengelola.
  - **Indikator online/away/offline** di daftar DM, kepala DM, dan daftar
    anggota kanal, lewat WebSocket `apps/live` (bukan polling).
  - **Tempel atau seret berkas** ke chat jadi lampiran (maks 5 per pesan).
    Di komentar dan deskripsi work item, berkas bukan gambar jadi lampiran
    work item; gambar tetap di dalam teks.
  - **Volume notifikasi**: slider, bisukan, dan tombol Preview di Profile >
    Preferences; bawaan untuk akun baru di God Mode.
  - **Profil anggota.** Klik nama/avatar di mention, aktivitas, komentar,
    daftar anggota, dan chat membuka kartu: jabatan, departemen/divisi,
    email, ekstensi telepon, status online, tombol Kirim pesan. Field baru
    `job_title` dan `phone_extension`, diisi sendiri atau lewat God Mode.
    Guest tidak melihat email dan ekstensi.
  - **Super Admin bisa di-mention dan dipilih di filter** bila ditempatkan
    di departemen (KEP-61). Pencarian mention sekarang menemukan nama
    lengkap (dulu "Budi Santoso" tidak cocok dengan siapa pun). Akun
    terhapus tidak lagi ditawarkan.
  - **Email bermerek.** Ke-26 jenis email memakai satu tata letak: logo
    Paradise Perkasa (disematkan, karena server hanya LAN), warna dan font
    aplikasi, tombol gaya aplikasi, versi teks polos. Foto profil di email
    diperbaiki (`http://hostNone` dan tautan MinIO yang kedaluwarsa),
    dengan cadangan inisial. Bahasa mengikuti profil penerima. Perintah
    `kirim_contoh_email` mengirim semua contoh, hanya ke
    it.ai1@itechmandiri.com. God Mode > Email > Preview menampilkan semua
    template (ID/EN, desktop/ponsel) tanpa mengirim apa pun.
  - **Tanggal dan overdue di God Mode > Features.** Isi otomatis start
    date saat In Progress, isi due date saat Done, perlakuan due date saat
    selesai lebih awal (tetap, atau mundur ke hari selesai; tugas terlambat
    tidak pernah digeser), masa tenggang overdue (hari), dan jendela "tepat
    waktu" Dashboard Divisi. Bawaannya sama dengan perilaku lama.
  - **God Mode**: bilah "Unsaved changes" dengan Save/Discard yang selalu
    terlihat di semua formulir, plus peringatan sebelum meninggalkan
    halaman. Sisa teks Indonesia di God Mode jadi Inggris.
  - **Layar masuk dirombak** (aplikasi dan God Mode): panel merek di kiri
    untuk desktop, satu kolom di ponsel. Alur autentikasi tidak berubah.
  - **Selalu ada jalan kembali.** Penampil gambar punya tombol tutup, Esc,
    klik latar, Back peramban, dan kontrol zoom (termasuk cubit). Back
    menutup peek work item, layar penuh Gantt, dan penampil Wiki, bukan
    meninggalkan halaman.
  - Reaksi di pesan kanal milik orang lain dulu ditolak (dicek ke pengirim
    atau penerima saja), sekarang dicek ke keanggotaan kanal.
  - **Tidak ada lagi kontrol bawaan peramban.** Pilihan bulan/tahun di semua
    kalender (tanggal work item, rentang tanggal, filter, snooze) dulu
    `<select>` asli dengan daftar gambaran OS; sekarang `Combobox` propel.
    Checkbox asli jadi `Checkbox` `@plane/ui`; radio jadi `RadioGroup` propel
    baru (titik, bukan centang; panah berpindah pilihan; seluruh baris bisa
    diklik), contohnya mode navigasi Accordion/Tabbed. Kolom tanggal di filter God Mode jadi `Calendar` di `Popover`,
    dan input/textarea mentah jadi `Input`/`TextArea`. Slider volume tetap
    `<input type="range">` karena belum ada komponen slider.
  - **Build dan deploy lebih cepat.** CI memakai cache layer GitHub Actions
    per image, dan Dockerfile web/admin/space/live memasang dependensi
    sebelum menyalin source, jadi commit yang hanya mengubah kode tidak
    mengunduh ulang paket. Rilis sekarang satu perintah dari laptop,
    `paradise/bin/rilis.sh`. `deploy.sh` gagal kalau migrasi gagal; dulu
    tetap berakhir SEHAT karena container migrator yang berhenti tidak
    terlihat di `compose ps`.
  - **Bahasa email diputuskan: Inggris.** Semua 100 profil produksi
    `language=en`, jadi email ikut Inggris, sama dengan UI. Tidak ada
    perubahan data; siapa pun bisa memilih Indonesia di Profile.

## 2026-11-02

### Versi 2.1.0

- **Naik 2.0.0 ke 2.1.0, minor.** 2.0.0 sudah jalan di produksi. Rilis ini
  menambah tab baru dan memperbaiki persetujuan, tanpa migrasi dan tanpa
  langkah operator.
  - Tab **Approval** muncul di navigasi bertab project, sama dengan menu di
    sidebar. Bisa dimatikan dari God Mode lewat modul `approvals`.
  - Sesudah atasan menyetujui, kartu langsung pindah ke kolom Done tanpa muat
    ulang. Tolak memindahkannya ke In Progress. Balasan keputusan sekarang
    membawa `tugas.state_id`.
  - Status persetujuan memakai satu komponen `ApprovalStatusChip` di halaman
    Approval, kartu kanban/list/spreadsheet, sidebar detail, dan peek.
  - Halaman Approval lambat: tiap baris menghitung ulang daftar penyetuju
    (1.085 kueri untuk 6 baris). Sekarang dihitung sekali per permintaan, 93
    kueri dan 241 ms di data lokal. Riwayat yang sudah diputuskan dibatasi 200
    baris terbaru, yang menunggu tidak dibatasi. Ini juga sebab "manager divisi
    tidak bisa menyetujui": tombol Setujui baru tampil sesudah balasan yang
    bisa melewati batas waktu gunicorn (BUG-11).
  - Papan tidak lagi mengambil ulang antrean persetujuan untuk tiap kartu yang
    baru tampil.

## 2026-10-30

### Versi 2.0.0

- **Naik 1.6.0 → 2.0.0, mayor.** Sejak 1.6.0 (26 Okt) ada perubahan yang
  memaksa langkah operator atau mencabut fitur:
  - KEP-29: divisi & departemen jadi record, project pindah di bawah
    departemen. Data organisasi lama perlu dimigrasi.
  - KEP-46: menu Pelanggan di God Mode dibuang, God Mode jadi English-only,
    menu kustom digabung.
  - KEP-40/46: setelan pindah dari `.env` ke God Mode. Env tinggal jadi benih.
  - Migrasi baru `0150_email_bawaan_jabatan` dan `0151_potret_bawaan_email`
    (bawaan email member baru di God Mode tidak lagi mengubah akun lama), plus perubahan
    `apps/api/.env.example` dan `docker-compose-local.yml`.
  - Tenggat lewat intake: triase intake boleh mengubah tenggat tugas orang lain.
  - KEP-59 (2 Nov): direktur hanya menerima penyebutan, obrolan, dan ringkasan.
    Persetujuan, perubahan properti/status, tugas, dan komentar mati untuk semua
    direktur, termasuk yang dulu menyalakannya sendiri. Bawaan notifikasi di God
    Mode (`/members/defaults`) jadi tiga kolom: Staff, Leaders (supervisor,
    manager), Directors. Kolom Directors berlaku seketika sebagai batas atas.
  - Perbaikan obrolan (2 Nov): lampiran di pesan kanal dulu hanya bisa dibuka
    pengirimnya (aturan lama "pengirim/penerima", sedangkan pesan kanal tidak
    punya penerima). Sekarang aturannya sama dengan isi ruang: anggota ruang
    boleh membuka. Pemilik workspace tetap tidak ikut kecuali anggota.
  - Data demo `manage.py seed_demo_data` (alat lokal, bukan fitur): perusahaan
    rekaan lengkap dengan hierarki, work item, persetujuan, obrolan, lampiran,
    Wiki, dan riwayat login, dengan akun Super Admin ikut di dalamnya. Lokal
    saja: wajib `--settings=plane.settings.local`, ditolak di instance dengan
    lebih dari 5 akun sungguhan, dan berkasnya dikecualikan dari image produksi
    lewat `apps/api/.dockerignore` yang baru. Bukan data migration. Lihat README.
  - KEP-25 dikuatkan (2 Nov): tugas orang lain sekarang benar-benar hanya-lihat.
    Peek overview, kartu kanban/list, sel tabel, dan menu aksi cepat memakai satu
    aturan (`useBolehUbahTugas`): pembuat, assignee, atasan dari SEMUA
    assignee-nya, atau Super Admin. Di server, tautan, lampiran, sub-issue,
    relasi, cycle/module, worklog, versi, dan seret tanggal ikut dijaga
    `KepemilikanTugasMixin`. Komentar tetap terbuka. Tanpa migrasi.
    Susulan: baris sub-issue di detail dinilai per anak (dulu ikut hak
    induknya), dan blok Gantt orang lain tidak bisa diseret/diubah ukurannya.
  - Notifikasi granular (2 Nov): tiap jenis kabar (diberi tugas, disebut,
    komentar, persetujuan, tenggat & terlambat, tugas selesai, status,
    perubahan lain, obrolan) punya saklar INBOX dan EMAIL sendiri di Profil >
    Notifikasi, dan ringkasan harian bisa dipilih per bagian (terlambat, hari
    ini, 7 hari, yang Anda berikan, tim). Matriks yang sama tampil di God Mode
    (preferensi per member dan bawaan jabatan). Baru di inbox: pengingat
    tenggat/terlambat (H-1, H, H+1, H+3, H+7, tanpa menunggu
    `ENABLE_DEADLINE_REMINDER` karena tidak mengirim email) dan DM belum dibaca
    (satu baris per percakapan). Migrasi aditif `0155_notifikasi_granular`,
    semua kolom baru lahir hidup = perilaku lama.
  - KEP-57 (2 Nov): semua setelan pribadi bisa diatur dari God Mode, sebagai
    bawaan akun baru (Members > New member defaults) maupun per orang (panel
    member). Baru tercakup: navigasi sidebar (menu tersemat, gaya daftar
    project, batas project) dan tata letak work item. **Tata letak bawaan kini
    Board** (dulu List) untuk setiap member+project baru; member lama disamakan
    hanya lewat tombol "Apply ... to everyone" yang meminta konfirmasi. Menu
    baru Workspaces > New project defaults: visibilitas, zona waktu, arsip/tutup
    otomatis, dan akses guest untuk project baru (formulir Create project terisi
    nilai ini; API v1 kini menerima `network`). Chat, Wiki, Division dashboard,
    dan Initiatives akhirnya bisa disematkan di Customize navigation. Tanpa
    migrasi.
  - KEP-55 (2 Nov): staf yang menggeser tugasnya ke Done hanya mengajukan
    persetujuan. Statusnya tidak berpindah, toast "Requested for approval"
    muncul, dan tugas baru masuk Done saat atasan menyetujui. Ditolak = tugas
    kembali ke In Progress, lalu staf mengerjakan dan menggeser ke Done lagi
    untuk mengajukan ulang. Properti work item (sidebar penuh dan peek) punya
    baris "Approval" berisi satu chip yang sama dengan badge kartu ("Awaiting
    approval", "Approved by <nama>", "Rejected"; tanpa pengajuan "-"). Log tiap pengajuan/keputusan (dengan alasan
    tolak) ada di Activity (`IssueActivity field="approval"`). Badge persetujuan
    di kartu kini selebar isinya. Mengganti aturan 26 Okt (tugas tetap Done
    selama menunggu). Migrasi data `0157_log_persetujuan_lama` menulis log
    untuk pengajuan lama (idempoten, mundur menghapusnya); pengajuan lama yang
    masih menunggu di status Done tetap bisa diputuskan seperti biasa.
  - Ringkasan akhir hari (2 Nov): selain ringkasan awal hari Senin-Jumat 08.30
    WIB, ada email kedua pukul 17.30 WIB (`kirim_ringkasan_sore`, beat
    `ringkasan-sore`) untuk menutup hari. Isinya: tugas yang selesai hari ini,
    yang tenggatnya hari ini tapi belum selesai, yang terlambat, dan yang jatuh
    tempo hari kerja berikutnya (Jumat = sampai Senin). Untuk supervisor dan
    manager, bagian tim mendapat kolom Selesai. Saklarnya sendiri,
    `daily_digest_sore`, di Profil > Notifikasi dan di God Mode (per member dan
    bawaan jabatan). Bawaannya hidup untuk semua jabatan, sama seperti ringkasan
    pagi. Bagian yang dimuat ikut pilihan bagian yang sama. Subjek ringkasan
    pagi kini berawalan `[Ringkasan pagi]`. "Hari ini" dihitung menurut WIB,
    bukan UTC. Migrasi aditif `0158_ringkasan_sore`: orang yang sudah
    membekukan pilihannya mewarisi saklar ringkasan paginya.
  - KEP-60 (2 Nov): Dashboard Divisi untuk pimpinan. Bawaannya mode
    **Ringkas**: satu kalimat (berapa divisi lancar, mana yang paling
    bermasalah), empat angka dengan pembanding 7 hari sebelumnya (selesai tepat
    waktu, selesai 7 hari, terlambat, menunggu persetujuan Anda), kartu
    kesehatan per divisi (Lancar / Perlu perhatian / Kritis), dan paling banyak
    lima hal yang perlu dilihat dengan tautan langsung. Mode **Rinci** berisi
    tabel per divisi > departemen dan unduhan CSV. Pilihan mode diingat per
    peramban. Ambang status diatur di God Mode > Features > Division dashboard
    (`DASHBOARD_PERHATIAN_PERSEN` 5%, `DASHBOARD_KRITIS_PERSEN` 15%). Endpoint
    `divisi-dashboard` ditulis ulang dengan kueri agregat: dulu ~6 kueri per
    project, sekarang 12 kueri berapa pun jumlah project-nya (93 ms di data
    lokal). Wewenang persetujuan dihitung borongan lewat
    `project_boleh_diputuskan`, setara `boleh_memutuskan` untuk 57 dari 57 akun
    lokal. Field lama tetap ada. Tanpa migrasi.
  - Sub work item di detail tidak lagi berkedip lalu hilang: dua fetch yang
    balapan (StrictMode/pasang ulang) menyaklar visibilitas nyala lalu mati.
    Sekarang disetel, bukan disaklar (`sub-issues/content.tsx`).
  - KEP-56 (2 Nov): navigasi bawaan berubah. Project bertab (bukan
    accordion), semua project tampil di sidebar ("Show limited projects" mati),
    dan semua menu sidebar tersemat. Menu khusus admin (Analytics, Views,
    Archives, Division dashboard) tetap disaring izin, jadi member biasa tidak
    melihatnya. Migrasi `0156_navigasi_bawaan_tab` ikut menyamakan akun lama:
    saklar "Show limited projects" sebelumnya terkesan tidak bisa dimatikan
    (gagal simpan diam-diam dikembalikan store), jadi batas 10 yang tersimpan
    bukan pilihan siapa pun. Gagal simpan di dialog Customize navigation
    sekarang memunculkan toast.
  - Obrolan: catatan untuk diri sendiri. Diri sendiri tampil paling atas di
    daftar orang dengan label "(Kamu)", DM ke diri sendiri tidak lagi ditolak
    400, ruangnya cuma punya satu langganan, pesannya lahir sudah terbaca
    (tidak memicu lencana atau email), dan tombol panggilan disembunyikan.
    Tanpa migrasi.
  - Lead & anggota module: pengguna yang login selalu bisa memilih dirinya
    sendiri. Super Admin disaring dari daftar anggota project
    (`sembunyikan()`), jadi dulu ia tak pernah muncul di pemilih ini; begitu
    juga atasan yang masuk lewat jangkauan hierarki. Prop baru
    `sertakanDiriSendiri` di `MemberDropdown`.
  - Struktur organisasi di God Mode lebih gampang dikelola (2 Nov). Bagan
    ringkasan sekarang kanvas: seret untuk menggeser, Ctrl + scroll atau
    tombol untuk zoom, "pas ke layar", dan mode layar penuh (papan ketik:
    panah, + / -, 0). Panel pohon kiri bisa dilipat jadi rel ikon (diingat
    per peramban), divisinya terlipat secara bawaan dengan tombol buka/lipat
    semua. Tiap kotak bagan dan baris pohon punya menu "..." untuk ubah nama
    & kode, hapus, tambah departemen, tambah manager/anggota, serta pindah
    divisi atau ganti project, tanpa harus membuka panel detail dulu. Semua
    modal kelola disatukan di `organisasi/kelola.tsx`. Tanpa migrasi, tanpa
    endpoint baru.
  - Sidebar tidak lagi menampilkan kode divisi/departemen: sidebar project di
    web dan pohon organisasi di God Mode cukup memakai nama. Kode tetap ada
    di panel detail God Mode dan tetap bisa dicari.
  - Modul yang dimatikan (atau dicabut, KEP-50) tidak lagi bocor ke dalam
    aplikasi. Estimate, Cycle, Module, dan Work item type hilang dari Display
    properties, kolom spreadsheet, chip list/kanban, Group by, dan Order by,
    termasuk filter lama yang tersimpan (group by cycle jadi state, order by
    estimate jadi Last created). Power K ikut: perintah, pintasan kunci, modal
    Keyboard shortcuts, submenu setelan project, dan grup hasil pencarian.
    Juga tombol Analytics di header work item/module, kartu Total cycles/intake
    dan sumbu Cycle/Module/Estimate di Analytics, tawaran "Save to Drafts",
    aksi Archive (work item, module, project, arsip otomatis), Pages di
    Recents Home, Cycle/Module di form intake, pop-up Chat/Inbox, dan menu
    Help > Documentation (Wiki). Peta gerbangnya satu: `paradise-features.ts`
    dan `power-k/core/paradise-gates.ts`. Tanpa migrasi, data tidak disentuh.
  - Wiki lebih datar (2 Nov): sub-topik tidak lagi tampil sebagai kartu yang
    harus diklik dulu. Di halaman folder, tiap sub-topik jadi seksi yang bisa
    dibuka-tutup langsung di Daftar Materi, lengkap dengan materinya, tombol
    unggahnya sendiri, dan sub-topik di bawahnya. Bawaannya terbuka; seksi
    yang ditutup diingat per peramban (`localStorage`) dan tidak mengambil
    materinya. Halaman sub-topik tetap ada lewat tautan "Buka". Angka materi
    di kepala daftar sekarang ikut menghitung sub-topik. Tanpa migrasi.
  - Sisa logo Plane dibuang: ikon "Projects" di app rail (`PlaneNewIcon`)
    jadi glyph rumah Paradise satu warna, dan `apple-touch-icon` web
    (`app/assets/icons/icon-180x180.png`, `icon-512x512.png`, yang juga
    dipakai pratinjau tautan di iOS/WhatsApp/Slack) diganti logo Paradise.
  - Quick links dapat menu sidebar dan halaman sendiri di
    `/:workspace/quick-links`, seperti Stickies. Widgetnya tetap ada di Home;
    keduanya membaca data yang sama. Tidak ada migrasi.
  - KEP-49: semua menu bisa dimatikan dari God Mode > Features. Sidebar utama
    (Inbox, Your work, Stickies, Drafts, Quick links), menu workspace (tambah
    Chat & Wiki), tab project (Work items, Cycles, Modules, Pages, Intake,
    Approvals), dan fitur work item (Time tracking, Estimates, Work item types,
    Templates). Yang terakhir dulu dimatikan di kode lewat `PARADISE_FEATURES`
    dan rutenya dibuang saat build; sekarang rutenya selalu terdaftar dan
    dijaga di runtime. **Perhatikan Cycles:** bawaannya mati, jadi project yang
    sempat menyalakan Cycles tidak melihat tabnya sampai Super Admin
    menyalakannya. Tidak ada migrasi: baris saklar baru dibuat
    `configure_instance` dengan nilai bawaan.
  - Akun terhapus & Trash lengkap (KEP-50). Akun yang dihapus dari God Mode
    hilang dari daftar Accounts, daftar member workspace/project, dan semua
    pemilih (assignee, mention). Rujukan lamanya tetap ada dan tampil sebagai
    "Deleted account" (`is_deleted` di `UserLiteSerializer`). Identitas aslinya
    disimpan di tabel baru `akun_terhapus` (migrasi `0152_akun_terhapus`,
    aditif, plus mengganti nama akun lama "Akun dihapus" jadi "Deleted
    account"), jadi akun bisa dipulihkan dari Logs > Trash; status Super Admin
    sengaja tidak ikut kembali. Trash juga memuat project, materi Wiki, view,
    label, template, dan initiative. Pemulihan yang bentrok (email,
    identifier project, nama label) ditolak 409 sebelum ada yang dipulihkan.
  - KEP-53 (2 Nov): **Cycles, Work item types, dan Templates & Recurring
    dicabut.** Rute, halaman setelan, panel custom properties, saklar God Mode
    (`ENABLE_CYCLES`, `ENABLE_WORK_ITEM_TYPES`, `ENABLE_TEMPLATES`,
    `ENABLE_RECURRING_ISSUES`), endpoint `issue-types`, `properties`,
    `issue-templates`, `recurring-issues`, dan task beat
    `create-recurring-issues` dibuang. Tabel & data lama tidak disentuh.
  - KEP-53: **semua fitur project menyala**, termasuk project departemen dan
    project lama. Migrasi `0154_fitur_project_nyala` mengubah bawaan kolom
    (`module_view`, `issue_views_view`, `intake_view`,
    `is_time_tracking_enabled` jadi `True`) dan menyalakan kelimanya di semua
    project. Nilai per project sebelumnya tidak disimpan.
  - **Trash dirombak** (Logs > Trash di God Mode dan Settings > Trash di
    project): susunan baku halaman daftar God Mode. Cari nama atau penghapus,
    filter jenis yang diturunkan dari isi tong sampah (dengan jumlah), tabel,
    avatar penghapus, aksi ikon, dan modal konfirmasi menggantikan
    `window.confirm`. Label jenis di Trash project kini benar-benar
    diterjemahkan (sebelumnya yang tampil kunci i18n mentah).
  - **Daftar God Mode seperti tampilan work item** (2 Nov): Accounts, Logs >
    Activity (riwayat masuk), Audit log, dan Trash memakai satu kit
    (`apps/admin/components/common/data-view`). Cari, tombol Filters yang
    menambah chip `properti | operator | nilai` (is / is not, rentang tanggal
    dengan preset, teks), menu Display (urutan, kolom yang tampil, baris per
    halaman), dan kepala tabel yang bisa diklik untuk mengurutkan. Pilihan
    disimpan per halaman di browser. Accounts kini bisa disaring menurut
    status, Super Admin, jabatan, departemen, divisi, akses, sesi, tanggal
    aktif/masuk/keluar/dibuat, metode masuk, IP, dan email. Audit log menurut
    aktor (termasuk skrip), aksi, jenis objek, kolom yang berubah, tanggal, dan
    IP. Riwayat masuk menurut orang, peristiwa, sumber, metode, tanggal, dan IP.
    Backend: `/api/instances/audit-logs/` dan `/api/instances/login-history/`
    menerima nilai ganda (`a,b`), negasi (`*_not`), dan `?sort=`; riwayat
    masuk ikut mengirim `pilihan` (sumber & metode yang ada). Tanpa migrasi.
- **Bukan 2.0.1.** Patch hanya untuk memperbaiki versi yang sudah rilis, dan
  2.0.0 belum pernah rilis.
- **Versi diseragamkan.** Sebelumnya root 1.6.0 sementara 19 workspace tertinggal
  di 1.5.0, jadi label "Versi" di sidebar (dibaca dari `apps/api/package.json`)
  menampilkan angka yang salah. Sekarang semuanya diatur lewat
  `pnpm version:bump` (`scripts/bump-version.mjs`). Aturannya ada di
  `AGENTS.md` → Versioning (KEP-48).

### Navigasi: tak ada lagi halaman buntu (2 Nov)

Masuk 2.0.0 tanpa naik versi: 2.0.0 belum rilis. Kalau berdiri sendiri, ini
patch (perbaikan, tanpa migrasi atau setelan).

- **Inbox (Notifications).** Upstream menyembunyikan sidebar utama di Inbox
  karena mengandalkan app rail, padahal app rail di sini mati. Akibatnya Inbox
  tak punya jalan keluar selain tombol Back browser. Sidebar sekarang hanya
  disembunyikan kalau app rail benar tampil, dan header Inbox mendapat tombol
  buka sidebar seperti halaman lain (layar sempit/sidebar diciutkan).
- **Settings akun (`/settings/profile/*`).** Halaman ini di luar layout
  workspace, jadi tanpa sidebar utama dan top bar. Ditambah panah "Back to
  workspace" di atas sidebar setelan, cermin header Workspace settings.
- **Create workspace.** Tombol "Go back" memakai `router.back()` yang diam saja
  kalau halaman dibuka langsung. Sekarang jatuh ke workspace terakhir kalau tak
  ada halaman aplikasi sebelumnya.
- Diaudit dan sudah aman: semua halaman di bawah `(projects)` (sidebar +
  toggle + breadcrumb), Workspace/Project settings (panah kembali), halaman
  modul yang dimatikan, 404/error, undangan, God Mode.

### Persetujuan: filter standar, satu klik, halaman seragam

Masuk 2.0.0 tanpa naik versi lagi: 2.0.0 belum rilis dan sudah mayor. Kalau
berdiri sendiri, ini minor (filter baru, tanpa migrasi atau setelan).

- **Filter "Approval" di filter work item.** Tombol pil "Tunggu persetujuan"
  di sebelah baris filter dibuang. Gantinya properti `approval_status` di
  filter bawaan (Add filter > Approval > Awaiting approval / Approved), jadi
  bisa digabung dengan filter lain, disimpan ke view, dan ikut URL. Disaring
  di server (`IssueFilterSet`, baris persetujuan terbaru per tugas), bukan
  disembunyikan di klien seperti dulu: hitungan grup dan paginasi sekarang
  benar.
- **Setujui satu klik untuk atasan.** Di list, kanban, dan spreadsheet, tugas
  yang menunggu dan boleh saya putuskan membawa tombol Setujui (langsung) dan
  Tolak (dialog alasan) di sebelah badge. Satu request per project, bukan per
  kartu. Sidebar work item dan menu "..." memakai tombol dan dialog yang sama.
- **Halaman Persetujuan seragam dengan Pages.** Header sekunder bertab
  (Needs my decision + jumlah / My requests, tab di `?tab=`), baris
  `ListItem` selebar halaman, `Banner` untuk gerbang mati dan galat muat,
  loader dan empty state bawaan. Kartu, `max-w-3xl`, dan textarea buatan
  sendiri dibuang.

### Wiki: setelan akses dibuang, aturan bawaan (KEP-51, 2 Nov)

Masuk 2.0.0 tanpa naik versi lagi: 2.0.0 belum rilis dan sudah mayor. Isinya
sendiri mayor (halaman setelan dan dua endpoint dicabut, arti izin berubah),
jadi aturan "jangan naik dua kali di level yang sama" berlaku.

- **Halaman Setelan project > Wiki access dibuang**, berikut endpoint
  `wiki-access/` dan `wiki-access/folders/<id>/`. Centang pemilik di panel
  Kelola di dalam Wiki juga dibuang; panelnya tinggal menampilkan siapa yang
  boleh mengisi.
- **Governance selalu aktif** untuk project ber-identifier WIKI, tanpa baris
  `WikiGovernedProject`. Lokal dan produksi kini berperilaku sama.
- **Matriks hak baru:** baca = semua anggota Wiki; unggah = admin atau
  anggota (member/admin, bukan guest) project departemen di bawah divisi
  folder itu; ubah/hapus materi = admin atau pengunggahnya; folder dan
  sub-topik = admin saja. "Admin" = admin workspace atau Super Admin.
- **Bawaan folder:** folder divisi mengikuti struktur organisasi God Mode
  (`pastikan_folder_divisi`). Divisi tanpa departemen = hanya admin yang
  mengunggah. Folder teratas lain tanpa pemilik = General, semua anggota Wiki
  boleh mengunggah. ⚠️ Folder sisa percobaan di produksi yang dulu terkunci
  ikut jadi General; hapus lewat panel Kelola kalau tidak dipakai.
- Tanpa migrasi. Baris `WikiFolderAccess` lama tetap dibaca.

### Tampilan God Mode: Audit log, Accounts, Organization

Masuk 2.0.0 tanpa naik versi: 2.0.0 belum rilis, dan ini perubahan tampilan
tanpa perubahan perilaku (tidak ada endpoint, migrasi, atau setelan baru).

- **Audit log.** Entri dikelompokkan per hari (Today, Yesterday, tanggal),
  aktor tampil dengan avatar, aksi memakai lencana berikon, dan kolom baru
  "Changes" meringkas kolom yang berubah. Baris dibuka jadi tabel
  Field / Before / After dengan nama kolom yang bisa dibaca (`state_id` jadi
  State, `True` jadi Yes, UUID dipendekkan, HTML deskripsi jadi teks). Kolom
  teknis (timestamp, urutan) disembunyikan dulu di balik tombol. Ada tombol
  Clear filters.
- **Accounts.** Kolom dipadatkan: avatar + nama + email, lencana Super Admin /
  You / Deactivated, jenjang + penempatan (nama departemen), akses workspace,
  waktu relatif ("3h ago") dengan waktu persis di tooltip. Editor pindah dari
  baris yang membuka di tempat ke modal bertahap (Account, Organization,
  Preferences, Super Admin, Danger zone) dengan Save/Cancel lengket di bawah.
  Akun baru juga lewat modal.
- **Organization.** Halaman jadi master-detail: pohon organisasi di kiri
  (perusahaan > divisi > departemen, plus Not placed yet dan Projects without
  a department), panel node terpilih di kanan. Ringkasan perusahaan berupa
  bagan atas-ke-bawah (direktur > divisi + manager > departemen). Ubah/hapus
  divisi & departemen lewat modal dan AlertModalCore, orang tampil sebagai
  baris seragam dengan aksi naik/turun jenjang dan keluarkan.
- **Buat divisi/departemen: nama dulu, kode menyusul otomatis.** Kode diisi
  dari nama (Finance jadi FIN, Human Resources jadi HR), diberi angka kalau
  bentrok (FIN2). Kode tetap bisa disunting; mengosongkannya kembali ke kode
  otomatis. Saat mengubah, kode lama tidak ikut berganti.
- **Kolom Object di Audit log.** Teks `__str__` upstream berbentuk `A <B>`
  (mis. `email <New division>` untuk halaman Wiki) dipecah jadi nama tebal +
  konteks redup ("by email", "in Project"). Dirapikan di tampilan karena teks
  itu dibekukan saat entri ditulis.
- **Tab Connections tersembunyi tanpa kredensial Google.** `/api/instances/`
  mengirim `has_google_calendar_configured` (client ID DAN secret terisi, dari
  God Mode atau env). Kalau False, tab Connections hilang dari setelan profil
  (halaman & modal) dan `/settings/profile/connections` dialihkan ke General.
  Server lama tanpa bidang ini: tab tetap tampil.
- **Komponen upstream, bukan buatan sendiri.** Select native diganti
  `CustomSelect`/`CustomSearchSelect`, input `Input`, saklar `ToggleSwitch`,
  centang `Checkbox`, lencana `Badge`, avatar `Avatar`, tombol ikon
  `IconButton`, modal `ModalCore`. Balok bersama yang tersisa ada di
  `apps/admin/components/common/paradise-ui.tsx`.
- **Kelas mati dibereskan:** `font-mono` (tidak ada di tema, diganti
  `font-code`), `bg-placeholder` pada titik status sesi (titik "Signed out"
  dulu tidak terlihat), `border-l-warning-primary`, `shadow-lg`.

## 2026-10-22

### Notifikasi persetujuan (inbox + email)

- **Tiga pemicu baru.** Pengajuan (baru & ulang) → inbox + email ke atasan yang
  boleh memutuskan; keputusan (setujui/tolak, alasan ikut) → inbox + email ke
  pemohon. Penugasan ke saya & status berubah tetap lewat jalur lama (sudah
  jalan — assignee otomatis jadi subscriber + saklar `property_change`).
- **Bahasa email mengikuti penerima** (`Profile.language`, id/en); templat
  `emails/notifications/approval.html` baru.
- **Saklar baru** `approval` di `UserNotificationPreference` (default hidup)
  - toggle di Profil → Notifikasi; inbox selalu ditulis, saklar hanya email.
- Tanpa SMTP, baris ditandai selesai (tidak macet antrean).

### Versi 1.5.0

- **Naik versi 1.4.0 → 1.5.0** di 20 `package.json` workspace (fitur baru sejak
  14 Okt: antrean persetujuan, God Mode member & organisasi, filter tunggu
  persetujuan).
- **i18n untuk semua string fitur baru.** Web memakai kunci `issue.approval.*`
  (52 kunci, 19 locale sinkron); tanggal mengikuti bahasa aktif. God Mode
  memakai kamus bertipe `apps/admin/app/i18n/godmode.ts` + toggle ID/EN.
- **Konfirmasi Super Admin tanpa passphrase.** Pemberian memakai ketik-ulang
  "jadikan superadmin" / "make superadmin" (divalidasi server); env
  `SUPER_ADMIN_GRANT_PASSPHRASE` dihapus.
- **Rapi design system:** token `danger-subtle`/`warning-subtle` ganti hardcode
  `red-500`/`amber-500`, `aria-pressed`/`aria-label` di kontrol approval.

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
