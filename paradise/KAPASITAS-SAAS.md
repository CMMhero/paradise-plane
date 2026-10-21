# Rencana kapasitas SaaS

Ditulis 28 Agt 2026, saat VPS dan domain SaaS belum ada. Tujuannya satu: menjawab
"berapa besar mesin yang perlu disewa, dan muat berapa pelanggan" dengan angka
yang diukur, bukan ditebak.

**Yang diukur ditandai jelas, yang diperkirakan juga.** Membaca perkiraan sebagai
pengukuran adalah cara memesan mesin yang salah ukuran.

---

## 1. Angka yang BENAR-BENAR diukur

Sumbernya produksi Paradise Task Tracker, 79 pengguna, dua bulan pemakaian nyata.

| Besaran                       | Nilai                       | Cara diukur           |
| ----------------------------- | --------------------------- | --------------------- |
| Layanan dalam satu tumpukan   | 16                          | `docker-compose.yml`  |
| RAM terpakai seluruh tumpukan | **2,2 GB**                  | `status.sh` di server |
| Mesinnya                      | 4 vCPU / 30 GB / 98 GB disk | spesifikasi VPS       |
| Disk terpakai                 | 19% dari 98 GB              | `status.sh`           |
| Database aplikasi             | **598 KB** ter-gzip         | dump 27 Agt           |
| Unggahan (MinIO)              | **95 MB**                   | arsip volume 27 Agt   |

Dua angka terakhir yang paling penting, dan hubungannya mengejutkan: **barisnya
598 KB, berkasnya 95 MB.** Perbandingannya sekitar 1 banding 160. Artinya
perencanaan kapasitas SaaS ini pada dasarnya perencanaan PENYIMPANAN OBJEK,
bukan perencanaan database.

⚠️ Jangan pakai angka 35 MB yang tercatat di `paradise/backup.log`. Itu database
LOKAL yang kembung karena 20.000 work item uji volume, bukan produksi.

---

## 2. Mana yang wajib per pelanggan, mana yang boleh dibagi

Dari 16 layanan, yang benar-benar harus terpisah hanyalah yang memegang datanya.

| Layanan                        | Per pelanggan?    | Alasan                                                        |
| ------------------------------ | ----------------- | ------------------------------------------------------------- |
| `plane-db`                     | **wajib**         | Inti keputusan isolasi. Ini yang dijanjikan ke pelanggan      |
| `api`, `worker`, `beat-worker` | **wajib**         | Memegang koneksi ke database itu                              |
| `live`                         | **wajib**         | Membaca dokumen dari database itu                             |
| `plane-redis`                  | wajib, tapi kecil | Sesi dan cache milik satu penyewa                             |
| `plane-mq`                     | wajib, tapi kecil | Antrean Celery milik satu penyewa                             |
| `web`, `admin`, `space`        | **boleh dibagi**  | Frontend statis. Alamat API diturunkan dari hostname peramban |
| `proxy` (Caddy)                | **boleh dibagi**  | Satu Caddy melayani semua subdomain, itu memang tugasnya      |
| `plane-minio`                  | **boleh dibagi**  | Satu klaster, satu bucket per pelanggan                       |
| `livekit`, `coturn`            | **boleh dibagi**  | Media relay tidak menyentuh database siapa pun                |
| `gotenberg`                    | **boleh dibagi**  | Konversi Office ke PDF, tanpa keadaan                         |

**16 layanan turun jadi 7 per pelanggan.** Sisanya sembilan, dibagi bersama.

---

## 3. Perkiraan jejak per pelanggan

🔶 **Ini PERKIRAAN, bukan pengukuran.** Tumpukan terpisah 7 layanan belum pernah
dijalankan; yang pernah diukur cuma tumpukan penuh 16 layanan sebesar 2,2 GB.

Pembagian kasar dari tumpukan penuh itu:

```
per pelanggan (7 layanan)      ~1,2 - 1,5 GB
dibagi bersama (9 layanan)     ~0,7 - 1,0 GB, TIDAK bertambah per pelanggan
```

Angka per pelanggan itu untuk keadaan diam. Pelanggan yang sedang sibuk menaikkan
pemakaian `api` dan `worker`, dan rapat daring menaikkan `livekit` yang dibagi.

**Langkah pertama yang harus dilakukan sebelum memesan mesin apa pun:** jalankan
SATU tumpukan pelanggan dengan pembagian 7/9 di atas, biarkan sehari, lalu ukur.
Satu pengukuran mengalahkan seluruh bagian ini.

---

## 4. Muat berapa pelanggan

Dengan perkiraan 1,5 GB per pelanggan, ditambah 1 GB bersama, dan menyisakan
20 persen untuk lonjakan:

| RAM mesin | Perkiraan pelanggan | Catatan                                                    |
| --------- | ------------------- | ---------------------------------------------------------- |
| 8 GB      | 3 - 4               | Cukup untuk pelanggan pertama sampai ketiga                |
| 16 GB     | 7 - 8               |                                                            |
| 32 GB     | 16 - 17             |                                                            |
| 64 GB     | 33 - 34             | Di titik ini, satu mesin jadi satu titik kegagalan tunggal |

Disk lebih longgar: 95 MB unggahan untuk 79 orang selama dua bulan berarti
pelanggan biasa tumbuh sekitar 50 MB per bulan. Seratus pelanggan selama setahun
sekitar 60 GB. Disk bukan kendala yang mengikat, RAM yang mengikat.

**Rekomendasi awal: satu VPS 16 GB.** Ia memuat tujuh pelanggan berbayar, dan
tujuh pelanggan berbayar sudah cukup untuk membiayai mesin berikutnya. Memulai
dari 64 GB berarti membayar kapasitas kosong berbulan-bulan.

---

## 5. Kolam gratis dihitung terpisah

Kolam gratis bukan sekumpulan tumpukan, melainkan SATU tumpukan berisi banyak
workspace. Jadi ongkosnya tidak tumbuh per pengguna gratis, tapi tumbuh per
BERKAS yang mereka unggah, dan itulah kenapa rem yang paling berpengaruh adalah
kuota penyimpanan.

Dengan bawaan sekarang, `FREE_MAX_STORAGE_BYTES=1 GiB` dan gratis perorangan:

```
1.000 akun gratis, rata-rata memakai 5% kuotanya   ~50 GB
1.000 akun gratis, rata-rata memakai 50% kuotanya  ~500 GB
```

Selisih sepuluh kali lipat itu bukan ketidakpastian teknis melainkan
ketidakpastian perilaku, dan tidak ada yang bisa menjawabnya sebelum ada pemakai
sungguhan. Karena itu tiga hal berikut ada dan harus dipantau sejak akun gratis
pertama:

- `FREE_MAX_STORAGE_BYTES`, bisa diturunkan tanpa rilis
- rem tidur, yang membekukan unggahan workspace yang menganggur
- `UsageSnapshot` di bidang kendali, yang mencatat kecenderungannya

🔴 **Kolam gratis adalah satu-satunya bagian arsitektur ini yang tabelnya dipakai
bersama ribuan penyewa.** Uji volume lokal dulu menemukan `.distinct()` membuat
COUNT 88 kali lebih lambat pada 20.000 work item, dan kesimpulan waktu itu "baru
terasa dua tahun lagi" berlaku untuk SATU perusahaan. Di kolam gratis, ongkos
kueri semacam itu datang jauh lebih cepat.

---

## 6. Kapan harus memecah

Pemicu yang bisa diukur, bukan perasaan:

| Pemicu                                           | Tindakan                                                              |
| ------------------------------------------------ | --------------------------------------------------------------------- |
| RAM terpakai lewat 75% selama seminggu           | Sewa mesin kedua, pindahkan pelanggan terbaru ke sana                 |
| Satu pelanggan konsisten memakai lebih dari 3 GB | Pindahkan dia ke mesinnya sendiri                                     |
| Kolam gratis lewat 60% disk penyimpanan objek    | Turunkan kuota gratis, atau percepat rem tidur                        |
| Rapat daring mulai patah-patah                   | `livekit` keluar ke mesin sendiri lebih dulu, ia yang paling sensitif |

Pemindahan pelanggan antar mesin memakai jalur yang sudah ada:
`export_workspace` lalu `import_workspace`, objek penyimpanannya ikut sendiri.
Lihat `SAAS-RUNBOOK.md` bagian 5.

---

## 7. Yang belum bisa dijawab dokumen ini

- **Harga sewa.** Bergantung penyedia dan wilayah, dan menuliskan angka yang
  tidak diverifikasi di sini akan dibaca orang sebagai anggaran.
- **Kebutuhan bandwidth rapat daring.** LiveKit adalah komponen paling haus, dan
  belum pernah diukur dengan lebih dari beberapa peserta.
- **Beban puncak.** Seluruh angka di sini keadaan diam. Pola puncak baru
  terbentuk setelah ada pelanggan sungguhan dengan jam kerja yang bertumpuk.

Ketiganya butuh pengukuran, bukan pemikiran lebih lanjut.
