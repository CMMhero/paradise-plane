# Changelog, Paradise Task Tracker

Urutan pembangunan sistem, disusun dari riwayat commit. Entri terbaru di atas.

Format tanggal: YYYY-MM-DD. Referensi commit menunjuk repositori ini.

---

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
