# Runbook SaaS: menerima pelanggan, menaikkan kelas, menangguhkan

Dokumen operasional. Bukan rencana, bukan rancangan. Yang ada di sini adalah
langkah yang benar-benar bisa dijalankan hari ini, berikut yang **belum** ada dan
harus dikerjakan tangan.

Arsitekturnya ada di `plane/db/models/plan.py`, `plane/utils/plan_limits.py`,
`plane/control/models.py`, dan `plane/utils/workspace_transfer.py`. Kepala tiap
berkas itu menjelaskan alasannya.

---

## Peta singkat

```
deployment PEMILIK      ENABLE_CONTROL_PLANE=1
                        tabel perusahaan, langganan, instance, pemakaian
                        rute /control/

kolam GRATIS            satu deployment, banyak workspace
                        tiap akun gratis dapat satu workspace
                        empat rem menyala

instance BERBAYAR       satu deployment + satu database per perusahaan
                        ENABLE_CONTROL_PLANE=0
                        berdenyut ke pemilik tiap jam

pasang SENDIRI          milik pelanggan Enterprise, tanpa denyut sama sekali
```

Tingkatan menempel di **workspace**, bukan di instance. Workspace tanpa baris
`WorkspacePlan` dianggap gratis, jadi tidak ada backfill yang wajib di mana pun.

---

## 0. Sekali seumur host: nyalakan tumpukan bersama

Harus lebih dulu dari apa pun. Ia yang membuat jaringan `nomaden_saas` dan
container proxy, dan `tenant-up.sh` menolak jalan kalau keduanya belum ada.

```bash
# Paket GHCR repo ini PRIVAT. Tanpa langkah ini `up -d` gagal dengan `denied`,
# dan pesannya menunjuk ke image, bukan ke kredensial yang belum ada.
echo "$GHCR_TOKEN" | docker login ghcr.io -u <akun> --password-stdin

mkdir -p /srv/caddy/tenants
docker compose -p nomaden -f docker-compose-shared.yml up -d
```

Tokennya cukup ber-scope `read:packages`. Alternatifnya membuat keenam paket
jadi publik, tapi repo ini sengaja privat dan paket publik membatalkan sebagian
alasan itu.

Nama proyeknya `nomaden`, dan itu bukan pilihan bebas: `tenant-up.sh` mencari
container bernama `nomaden-proxy-1`. Menggantinya berarti ikut mengganti
`PROXY_CONTAINER` di skrip itu.

Isinya delapan layanan yang tidak memegang data penyewa mana pun: proxy, tiga
frontend statis, MinIO, Gotenberg, LiveKit, dan coturn.

**Panel pemilik disiapkan seperti penyewa biasa**, bukan lewat jalur khusus.
Bedanya cuma satu baris di berkas envnya:

```bash
python manage.py provision_tenant "NomaX Panel" --subdomain panel \
    --email ops@nomaden.id --tier ENTERPRISE --out /srv/tenants/panel.env
# lalu SUNTING /srv/tenants/panel.env: ubah ENABLE_CONTROL_PLANE jadi 1
sudo ./paradise/bin/tenant-up.sh panel /srv/tenants/panel.env
```

Satu jalur untuk semua mengalahkan satu jalur plus satu pengecualian yang cuma
dijalankan sekali seumur hidup lalu dilupakan.

⚠️ Bidang kendali baru bisa dipakai sesudah panel ini hidup. Sebelum itu,
`provision_tenant` di atas harus dijalankan dari deployment lain yang sudah
punya bidang kendali, atau untuk yang paling pertama, langsung lewat
`manage.py shell` di dalam container panel sesudah ia menyala.

---

## 1. Menerima pelanggan baru

Dijalankan di deployment **pemilik**.

```bash
python manage.py provision_tenant "PT Acme" \
    --subdomain acme \
    --email admin@acme.co.id \
    --tier PRO \
    --control-url https://panel.nomaden.id \
    --out /srv/tenants/acme.env
```

Yang terjadi: perusahaan, langganan, dan catatan instance dibuat; rahasia denyut
diterbitkan; berkas env berisi `SECRET_KEY`, kredensial database, alamat, dan
rahasia denyut ditulis dengan izin 600.

⚠️ **Rahasia denyut hanya ada di berkas itu.** Yang tersimpan di database cuma
sidik SHA-256-nya. Kalau berkasnya hilang sebelum sempat dipasang, terbitkan
instance baru; tidak ada yang bisa memulihkannya.

Perintah ini **menolak** menulis ke dalam pohon kerja git mana pun. Itu penjaga
yang berjalan, bukan sekadar baris di `.gitignore`.

### Yang masih tangan

Satu langkah tersisa yang benar-benar butuh manusia: **buat rekaman DNS**
`acme.nomaden.id` menunjuk ke host. Itu ada di penyedia domain, di luar
jangkauan mesin mana pun.

Sesudah DNS-nya jadi, sisanya satu perintah:

```bash
sudo ./paradise/bin/tenant-up.sh acme /srv/tenants/acme.env
```

Ia menyalakan 8 layanan milik pelanggan itu, menunggu migrasinya benar-benar
selesai (bukan menebak dengan sleep), menulis blok situs Caddy, memuat ulang
proxy DAN memeriksa hasilnya, lalu menguji apakah subdomainnya menjawab.

Mematikan tanpa menghapus data: `sudo ./paradise/bin/tenant-down.sh acme`.

🔶 **Ketiga berkas itu belum pernah dijalankan sungguhan**, karena VPS SaaS
belum ada. Jalankan sekali dengan pelanggan uji dan baca keluarannya sebelum
memakainya untuk pelanggan yang membayar. Rinciannya di kepala tiap berkas.

Sesudah instance hidup, denyut pertamanya akan muncul di `/control/companies/`
dalam waktu satu jam. Kalau tidak muncul, `CONTROL_PLANE_URL` atau rahasianya
salah, dan instance akan tetap berjalan di tingkatan terakhir yang diketahuinya.

---

## 2. Melihat keadaan seluruh pelanggan

```bash
curl -H "Cookie: <sesi god-mode>" https://panel.nomaden.id/control/companies/
```

Satu permintaan sudah membawa tingkatan, jejak hidup, dan pemakaian terakhir tiap
instance. Izinnya `InstanceAdminPermission`, yaitu admin God Mode di deployment
pemilik. Tidak ada pintu login kedua.

Ini endpoint yang akan dipanggil Owner Panel. Halamannya sendiri milik tim
frontend dan arah desainnya milik Design Leads.

---

## 3. Menaikkan atau menurunkan tingkatan

```bash
curl -X PATCH https://panel.nomaden.id/control/companies/acme/ \
     -H "Content-Type: application/json" \
     -d '{"tier": "EXPERT"}'
```

Langganan lama **diakhiri**, yang baru dimulai. Riwayatnya disimpan sebagai baris
karena penagihan pasti menanyakan sejak kapan seseorang berada di tingkatan mana.

Instance pelanggan menerapkannya pada denyut berikutnya, paling lama satu jam.
Kalau perlu segera, di instance itu:

```bash
python manage.py set_workspace_plan <slug-workspace> --tier EXPERT
```

---

## 4. Menangguhkan yang menunggak

```bash
curl -X PATCH https://panel.nomaden.id/control/companies/acme/ \
     -d '{"status": "SUSPENDED"}'
```

Instance **diturunkan ke gratis, bukan dimatikan.** Orang yang tidak bisa masuk
tidak akan menyelesaikan tagihannya. Batas gratis akan mulai menolak unggahan
baru begitu kuotanya terlampaui, dan itu tekanan yang cukup tanpa menyandera
datanya.

---

## 4b. Menagih pelanggan

Sekali di awal, di dashboard Xendit: salin secret key ke `XENDIT_SECRET_KEY`,
salin callback verification token ke `XENDIT_CALLBACK_TOKEN`, dan daftarkan
alamat webhook `https://<panel>/control/payments/xendit/`.

⚠️ `XENDIT_CALLBACK_TOKEN` kosong berarti **semua webhook ditolak**, bukan semua
diterima. Itu disengaja: instance yang belum disetel lebih baik kehilangan
webhook daripada menerima perintah "tandai lunas" dari siapa pun yang menemukan
alamatnya.

Menerbitkan tagihan satu periode:

```bash
curl -X POST https://panel.nomaden.id/control/companies/acme/invoices/      -H "Content-Type: application/json" -d '{"tier": "PRO"}'
```

Jawabannya memuat `invoice_url`, halaman bayar Xendit yang sudah menawarkan
virtual account, QRIS, dan e-wallet. Kirimkan tautannya ke pelanggan.

Sesudah dibayar, webhook Xendit melunasi tagihannya, menyesuaikan langganan, dan
menyetel perusahaannya jadi `ACTIVE`. Semuanya otomatis; tidak ada yang perlu
diklik.

**Yang otomatis tiap hari pukul 04:00:** tagihan lewat tempo ditandai
kedaluwarsa dan perusahaannya jadi `PAST_DUE`. Sesudah `BILLING_GRACE_DAYS`
lewat tanpa pembayaran, ia jadi `SUSPENDED`, dan instance-nya turun ke gratis
pada denyut berikutnya.

Tenggangnya bukan nol karena transfer antar bank bisa butuh satu hari kerja untuk
terbaca, dan menangguhkan pelanggan yang uangnya sedang di jalan adalah cara
kehilangan pelanggan yang justru sudah membayar.

### Yang belum diverifikasi

Logika penagihan diuji lengkap, tapi **bentuk muatan Xendit sungguhan belum
pernah diadu ke sandbox**, karena itu butuh akun merchant. Sebelum menagih
pelanggan pertama: buat satu tagihan uji di mode sandbox, bayar, dan pastikan
webhooknya benar-benar melunasi barisnya. Kalau bentuk muatannya ternyata beda,
yang perlu disesuaikan cuma `plane/control/xendit.py`.

FREE tidak ditagih. ENTERPRISE juga tidak punya harga daftar dan memang tidak
boleh punya: rencana produk menyebutnya khusus, jadi ia ditagih lewat kesepakatan
dan statusnya disetel tangan.

---

## 5. Menaikkan kelas pelanggan gratis ke instance sendiri

Ini pemindahan data antar database, bukan pengubahan satu kolom.

```bash
# 1. di kolam gratis. Objeknya IKUT, tidak perlu saklar apa pun.
python manage.py export_workspace acme-gratis --out /srv/pindah/acme.json.gz
#    menghasilkan  acme.json.gz         barisnya
#                  acme-assets.tar.gz   objek penyimpanannya

# 2. pindahkan KEDUA berkas ke instance baru (scp, rsync, apa pun)

# 3. di instance baru, LIHAT DULU
python manage.py import_workspace /srv/pindah/acme.json.gz

# 4. kalau masuk akal
python manage.py import_workspace /srv/pindah/acme.json.gz --terapkan

# 5. tingkatannya
python manage.py set_workspace_plan acme-gratis --tier PRO
```

Uji kering adalah bawaan langkah 3, dan memang begitu seharusnya.

Objek penyimpanan ikut secara **bawaan**, tidak lewat saklar opsional. Ekspor
yang secara bawaan menghasilkan setengah pemindahan adalah ekspor yang
setengahnya akan terlupa, dan yang terlupa itu justru bagian yang baru ketahuan
oleh pemakai akhir.

Tiap sisi memakai penyimpanannya **sendiri**: ekspor mengunduh dari MinIO
instance asal, impor mengunggah ke MinIO instance tujuan, keduanya dengan
kredensial yang memang sudah ada di sana. Tidak ada kredensial yang pernah
berpindah mesin, dan tidak ada konfigurasi baru yang perlu disiapkan.

Impor **menolak jalan** kalau berkas barisnya menyebut objek tapi tar objeknya
tidak ada di sebelahnya. Menyalin satu berkas lalu lupa satunya adalah kejadian
yang sudah pasti terjadi. Kalau memang sengaja tidak ikut, sebutkan dengan
`--no-assets`.

Urutan di dalam impor: objek diunggah **dulu**, baris ditulis belakangan. Kalau
unggahan gagal di tengah, tidak ada satu baris pun yang tertulis dan instance
tujuan tetap bersih. Objek tanpa baris tidak berbahaya karena tidak terlihat di
mana pun; baris tanpa objek terlihat utuh padahal berkasnya tidak akan pernah
terbuka.

Impor **menolak** dua keadaan sebelum menulis sebaris pun: slug sudah ada di
tujuan, dan surel pengguna sudah ada dengan UUID berbeda. Yang kedua penting:
meneruskannya membuat rujukan ribuan baris menunjuk ke orang yang salah.

⚠️ Kalau ekspor melaporkan ada objek yang **hilang di penyimpanan asal**, barisnya
tetap ikut sedangkan berkasnya tidak. Di instance tujuan ia akan muncul di daftar
tanpa bisa dibuka. Periksa laporannya sebelum menyerahkan instance.

Sesudah pelanggan mengonfirmasi instance barunya benar, baru hapus workspace-nya
dari kolam gratis. Jangan sebelum itu.

---

## 6. Menyetel rem kolam gratis

Semuanya variabel lingkungan, tidak perlu rilis. Rinciannya di
`apps/api/.env.example` bagian tingkatan.

```
FREE_MAX_MEMBERS=1     # perorangan, undangan ditolak sejak dikirim
FREE_MAX_STORAGE_BYTES=1073741824
FREE_MAX_WORKSPACES=1
REQUIRE_EMAIL_VERIFICATION_FOR_WORKSPACE=1     # nyalakan DI KOLAM GRATIS
DORMANT_WARN_AFTER_DAYS=60
DORMANT_FREEZE_AFTER_DAYS=90
DORMANT_MARK_DELETION_AFTER_DAYS=180
```

Rem yang paling berpengaruh adalah penyimpanan. Angka dari produksi Paradise:
79 orang, dua bulan pemakaian nyata, database 598 KB ter-gzip tapi unggahan
95 MB. Barisnya nyaris gratis, berkasnya tidak.

`REQUIRE_EMAIL_VERIFICATION_FOR_WORKSPACE` sebaiknya tetap `0` di instance
pasang-sendiri: instance tanpa SMTP tidak akan pernah bisa memverifikasi siapa
pun, dan menyalakannya di sana berarti tidak ada yang bisa membuat workspace.

### Workspace yang tertidur

Tiga tahap: peringatan lewat surel, unggahan dibekukan, lalu **ditandai** calon
hapus. Tahap keempat tidak ada, dan itu disengaja. Penghapusan data pelanggan
lewat timer tidak bisa dibatalkan.

Yang ditandai bisa dilihat lewat `WorkspacePlan.pending_deletion_at`, dan
keputusan menghapusnya milik manusia.

Workspace yang dipakai lagi dibangunkan **saat itu juga** pada percobaan unggah
berikutnya, bukan menunggu sapuan harian. Membangunkan manual:

```bash
python manage.py set_workspace_plan <slug> --tier FREE --bangunkan
```

---

## Yang BELUM ada

Ditulis di sini supaya tidak ada yang mengira sudah ada:

- **Verifikasi Xendit ke sandbox sungguhan.** Kodenya lengkap dan teruji, tapi
  butuh akun merchant untuk membuktikan bentuk muatannya benar. Lihat bagian 4b.
- **Melihat halaman Owner Panel di peramban.** Halamannya sudah dibangun di
  God Mode (`/god-mode/companies`), rutenya terdaftar, dan seluruh backendnya
  sudah diuji lewat sesi sungguhan. Yang belum: rupa akhirnya belum pernah
  dilihat manusia.
- **Menjalankan tumpukan SaaS sekali sungguhan.** `docker-compose-shared.yml`,
  `docker-compose-tenant.yml`, `Caddyfile.saas`, `tenant-up.sh`, dan
  `tenant-down.sh` sudah lengkap dan saling merujuk dengan benar, tapi belum
  pernah dijalankan satu kali pun. Menunggu VPS.
- **Mengisi kerangka dokumen hukum** di `DOKUMEN-HUKUM/`, dan menjawab empat
  keputusan di `PENGAWASAN-DAN-PRIVASI.md`. Keduanya harus beres sebelum
  pelanggan BERBAYAR pertama, bukan sebelum pelanggan gratis pertama.
  Penyalinan objek penyimpanan sudah otomatis sejak 28 Agt dan tidak lagi ada di
  daftar ini.
