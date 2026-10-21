# Syarat Layanan (KERANGKA)

🔴 Bukan dokumen hukum. Isi tiap `[ISI: ...]`, lalu serahkan ke ahli hukum.

## 1. Para pihak dan definisi

[ISI: nama badan hukum NomaX, alamat, nomor pendaftaran]
Definisi yang perlu dikunci: Layanan, Pelanggan, Pengguna Akhir, Instance,
Kolam Gratis, Tingkatan.

## 2. Tingkatan dan batasnya

Fakta terverifikasi dari kode, tinggal disalin:

- Gratis: 1 workspace per akun, 1 anggota (perorangan), 1 GiB penyimpanan
- Pro: 3 workspace, 30 anggota, 20 GiB
- Expert: workspace tanpa batas, anggota tanpa batas, 200 GiB
- Enterprise: dinegosiasikan, dipasang di server pelanggan sendiri

Angka-angka itu bisa diubah lewat variabel lingkungan tanpa rilis. Perlu klausul
yang mengatur pemberitahuan sebelum batas diturunkan.
[ISI: berapa hari sebelumnya pelanggan diberi tahu kalau batas berubah]

## 3. Pembayaran

[ISI: harga tiap tingkatan]
Fakta dari kode: periode 30 hari, jatuh tempo 7 hari, tenggang 7 hari sebelum
ditangguhkan. Pembayaran lewat Xendit.
Penangguhan MENURUNKAN ke tingkatan gratis, tidak menghapus data dan tidak
memutus akses masuk.

## 4. Akun gratis

🔴 Butir yang menunggu keputusan 4.1 di `../PENGAWASAN-DAN-PRIVASI.md`:
operator dapat memutus sesi akun gratis.
[ISI: dipertahankan, dibatasi, atau dicabut]

Fakta dari kode yang harus disebutkan:

- Workspace gratis yang tidak dipakai 60 hari mendapat peringatan
- 90 hari: unggahan baru dibekukan, isinya tetap bisa dibaca
- 180 hari: ditandai calon hapus, TIDAK dihapus otomatis
  [ISI: apakah dan kapan yang ditandai benar-benar dihapus]

## 5. Kode sumber dan lisensi

Layanan ini turunan Plane Community Edition di bawah AGPL-3.0. Pengguna yang
mengakses lewat jaringan berhak atas Corresponding Source, disediakan di
`/source/` pada tiap instance.

## 6. Ketersediaan

[ISI: ada SLA atau tidak. Kalau ada, angkanya. Kalau tidak, katakan tidak ada]
Jangan menjanjikan angka yang belum pernah diukur.

## 7. Penghentian dan data setelahnya

🔴 Menunggu keputusan 4.4 di `../PENGAWASAN-DAN-PRIVASI.md`.
[ISI: berapa lama data disimpan setelah berhenti]
[ISI: bagaimana pelanggan meminta ekspor datanya]
Fakta dari kode: `export_workspace` menghasilkan paket lengkap berisi baris dan
berkasnya, jadi kemampuannya sudah ada dan yang kurang kebijakannya.

## 8. Perubahan syarat

[ISI: cara memberi tahu, dan berapa lama sebelum berlaku]

## 9. Hukum yang berlaku dan penyelesaian sengketa

[ISI: yurisdiksi]
