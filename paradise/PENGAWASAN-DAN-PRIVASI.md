# Peninjauan fitur pengawasan sebelum dijual ke banyak perusahaan

Menjawab pasal 9.3 rencana kerja, yang menyebut kemampuan pengawasan sistem ini
"berimplikasi privasi dan hukum serius" begitu dijual ke banyak perusahaan dan
panel pemilik berdiri di atas semuanya.

Ini **audit isi kode**, bukan kerangka. Yang tertulis di bawah ada di repo dan
bisa dicek barisnya. Yang belum diputuskan ditandai sebagai keputusan yang
menunggu pemilik produk, bukan disamarkan jadi rekomendasi.

⚠️ Ini bukan nasihat hukum. UU 27/2022 tentang Pelindungan Data Pribadi berlaku
untuk sistem ini begitu ia memproses data karyawan perusahaan lain, dan
penerapannya perlu ditinjau ahli hukum.

---

## 1. Apa yang sebenarnya direkam

| Kemampuan                      | Di mana                            | Isinya                                                                                           |
| ------------------------------ | ---------------------------------- | ------------------------------------------------------------------------------------------------ |
| Riwayat login dan logout       | `db/models/login_activity.py`      | Satu baris per peristiwa, per pengguna                                                           |
| Sesi hidup dan perangkat       | `db/models/device.py`              | Perangkat terdaftar dan sesinya                                                                  |
| "Sedang memakai"               | `middleware/last_active.py`        | `User.last_active` distempel dari lalu lintas biasa, dibatasi 60 detik sekali                    |
| Memutus sesi orang (kick)      | `license/api/views/activity.py:99` | Admin instance bisa memutus semua sesi seseorang, dan `?nonaktifkan=1` sekalian mengunci akunnya |
| Jejak audit perubahan          | `license/api/views/audit_log.py`   | Siapa mengubah apa, lewat django-auditlog                                                        |
| Pengawasan project Super Admin | `db/superadmin.py`                 | Super Admin punya `ProjectMember` role 20 di SEMUA project                                       |

Yang **tidak** ada, dan ini penting disebut supaya tidak ada yang mengira ada:
tidak ada perekaman isi percakapan untuk diawasi, tidak ada penghitung waktu
layar, tidak ada tangkapan layar, dan tidak ada pelacakan lokasi.

Pengawasan percakapan pernah dirancang lalu **dicabut** sebelum dirilis.

---

## 2. Kenapa ini berbeda begitu jadi SaaS

Di Paradise, seluruh kemampuan di atas dipakai satu perusahaan terhadap
karyawannya sendiri. Hubungan kerjanya jelas, dan yang mengawasi bertanggung
jawab atas yang diawasi.

Di SaaS, ada pihak ketiga: **NomaX**. Dan tiga kemampuan di atas menyeberangi
batas itu:

**Admin instance bisa memutus sesi dan mengunci akun.** Di instance pelanggan,
admin instance adalah orang pelanggan, jadi ini tetap urusan internal mereka.
Tapi di **kolam gratis**, admin instance adalah NomaX, dan pemakai gratis dari
ratusan perusahaan berbeda ada di instance yang sama. Artinya NomaX secara
teknis bisa memutus sesi siapa pun di kolam gratis.

**Jejak audit dan riwayat login kolam gratis ada di database NomaX.** Bukan
karena ada yang menghendaki, melainkan karena kolam gratis memang satu
deployment.

**Bidang kendali menerima pemakaian tiap instance.** Yang keluar dari instance
pelanggan cuma tiga angka, dan itu memang sengaja dibatasi. Tapi keberadaan
jalur denyut itu sendiri harus disebutkan ke pelanggan, bukan hanya isinya.

---

## 3. Yang sudah benar dan jangan diubah

**Retensi riwayat login sudah dibatasi dan dihapus KERAS.** `RETENSI_HARI` di
`db/models/login_activity.py`, disapu `bgtasks/login_activity_retention.py`,
dengan peringatan yang muncul beberapa hari di depan. Jejak yang disimpan
selamanya adalah jejak yang suatu hari bocor.

**Denyut ke bidang kendali cuma membawa tiga angka.** Jumlah workspace, jumlah
anggota, byte terpakai, plus versi. Tidak ada nama orang, judul pekerjaan, atau
isi berkas. Ini ditegakkan `kumpulkan_pemakaian` di
`bgtasks/control_plane_heartbeat.py` dan diuji.

**Instance yang mendorong, bukan pusat yang menarik.** Kalau pusat yang menarik,
ia butuh kredensial baca ke tiap database pelanggan, dan seluruh alasan
memisahkan database jadi hilang.

**Rahasia instance disimpan sebagai sidik, bukan apa adanya.** Kebocoran
database bidang kendali tidak otomatis jadi kunci ke semua instance pelanggan.

**Jejak audit TIDAK ikut saat workspace dipindahkan.** Diputuskan di
`utils/workspace_transfer.py`. Konsekuensinya nyata dan disengaja.

---

## 4. Keputusan yang menunggu pemilik produk

Empat, dan tidak satu pun bisa saya putuskan sendiri karena semuanya soal
janji ke pelanggan, bukan soal kode.

### 4.1 Siapa boleh memutus sesi di kolam gratis

Sekarang: admin instance, yaitu NomaX. Pilihan:

- **Biarkan, dan katakan.** Sebutkan di Syarat Layanan bahwa akun gratis dapat
  dihentikan sesinya oleh operator. Paling jujur, paling murah.
- **Batasi ke penyalahgunaan saja**, dengan pencatatan alasan yang wajib diisi.
  Butuh kolom alasan pada endpoint kick.
- **Cabut sama sekali di kolam gratis**, dan tangani penyalahgunaan lewat
  penangguhan perusahaan, bukan pemutusan sesi orang.

Rekomendasi saya yang pertama, karena yang kedua dan ketiga menambah kode untuk
masalah yang belum pernah terjadi.

### 4.2 Apakah pelanggan berbayar diberi tahu soal jalur denyut

Sekarang: tidak ada tempat yang menyebutkannya kepada pelanggan. Ia jujur di
kode dan tidak terlihat oleh yang datanya dikirim.

Menyebutkannya di Syarat Layanan lebih baik daripada ditemukan sendiri oleh tim
IT pelanggan yang membaca lalu lintas keluar, karena yang ditemukan sendiri
selalu terbaca lebih buruk daripada yang diumumkan.

### 4.3 Berapa lama pemakaian disimpan di bidang kendali

Sekarang: **selamanya**. `UsageSnapshot` tidak punya retensi sama sekali, dan
denyutnya per jam. Satu pelanggan menghasilkan sekitar 8.760 baris per tahun.

Itu bukan masalah ukuran melainkan masalah janji: pelanggan yang berhenti tetap
meninggalkan jejak pemakaian di sistem kita tanpa batas waktu. Perlu diputuskan
angkanya, lalu dibuatkan sapuan seperti retensi riwayat login yang sudah ada.

### 4.4 Apa yang terjadi pada data pelanggan yang berhenti

Sekarang: `CHURNED` cuma status. Tumpukannya tetap hidup sampai ada yang
mematikannya, dan `tenant-down.sh` sengaja tidak pernah menghapus volume.

Yang perlu diputuskan: berapa lama data disimpan setelah berhenti, dan siapa
yang boleh memintanya diekspor. `export_workspace` sudah bisa menghasilkan
paketnya, jadi yang kurang cuma kebijakannya.

---

## 5. Yang harus ada sebelum pelanggan berbayar pertama

Bukan sebelum pelanggan gratis pertama, karena hubungan hukumnya berbeda.

- [ ] Syarat Layanan yang menyebut butir 4.1 dan 4.2
- [ ] Kebijakan Privasi yang menyebut butir 4.3 dan 4.4
- [ ] Perjanjian pemrosesan data, karena pelanggan adalah pengendali data
      karyawannya dan NomaX pemrosesnya
- [ ] Retensi `UsageSnapshot` diputuskan dan dijalankan
- [ ] Ditinjau ahli hukum, bukan hanya ditulis

Kerangka ketiga dokumen itu ada di `paradise/DOKUMEN-HUKUM/`.
