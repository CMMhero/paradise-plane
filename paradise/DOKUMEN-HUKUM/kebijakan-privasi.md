# Kebijakan Privasi (KERANGKA)

🔴 Bukan dokumen hukum. Isi tiap `[ISI: ...]`, lalu serahkan ke ahli hukum.

Audit lengkap apa yang direkam sistem ada di `../PENGAWASAN-DAN-PRIVASI.md`.
Serahkan dokumen itu bersama kerangka ini.

## 1. Siapa yang bertanggung jawab

[ISI: nama badan hukum, kontak petugas pelindungan data]

Perlu dibedakan tegas, karena kewajibannya berbeda:

- Untuk data AKUN GRATIS, NomaX adalah pengendali
- Untuk data KARYAWAN PELANGGAN BERBAYAR, pelanggan pengendali dan NomaX
  pemroses. Diatur terpisah di `perjanjian-pemrosesan-data.md`

## 2. Data yang dikumpulkan

Terverifikasi dari kode, bukan diperkirakan:

- Identitas: surel, nama tampilan, sandi (ter-hash)
- Isi kerja: work item, halaman, berkas, pesan
- Riwayat login dan logout, dengan retensi terbatas yang sudah berjalan
- Sesi dan perangkat yang dipakai masuk
- Stempel "terakhir aktif", diperbarui dari lalu lintas biasa
- Jejak audit perubahan pada objek tertentu

Yang TIDAK dikumpulkan, dan sebaiknya ditulis eksplisit karena orang
mengasumsikan sebaliknya: tidak ada tangkapan layar, tidak ada penghitung waktu
layar, tidak ada pelacakan lokasi, tidak ada perekaman isi percakapan untuk
diawasi.

## 3. Data yang keluar dari instance pelanggan

🔴 Menunggu keputusan 4.2 di `../PENGAWASAN-DAN-PRIVASI.md`.

Fakta dari kode: tiap instance berbayar mengirim EMPAT hal ke NomaX tiap jam,
yaitu jumlah workspace, jumlah anggota, total byte terpakai, dan versi
aplikasinya. Tidak ada nama orang, judul pekerjaan, atau isi berkas.

## 4. Berapa lama disimpan

- Riwayat login: sudah dibatasi dan dihapus keras oleh sapuan harian
- Tempat sampah: 30 hari lalu dihapus permanen
- 🔴 Pemakaian di bidang kendali: SEKARANG SELAMANYA. Menunggu keputusan 4.3
  [ISI: berapa lama]
- 🔴 Data setelah berhenti berlangganan. Menunggu keputusan 4.4
  [ISI: berapa lama]

## 5. Pihak ketiga yang menerima data

- Xendit, untuk pembayaran. Menerima surel kontak dan jumlah tagihan
- [ISI: penyedia VPS dan wilayah pusat datanya]
- [ISI: penyedia SMTP]
- [ISI: penyedia AI, kalau nanti fitur AI menyala. Catatan: rancangannya
  memakai API milik tiap perusahaan sendiri, jadi biayanya dan datanya milik
  mereka, dan ini perlu ditulis jelas]

## 6. Hak pemilik data

UU 27/2022 memberi hak akses, perbaikan, penghapusan, dan penarikan persetujuan.
[ISI: cara mengajukannya, dan berapa lama dijawab]

## 7. Keamanan

Fakta dari kode yang boleh disebutkan: sandi di-hash, lalu lintas lewat HTTPS,
tiap perusahaan berbayar mendapat database terpisah, dan rahasia instance
disimpan sebagai sidik bukan dalam bentuk terbaca.
Jangan menjanjikan sertifikasi yang belum dimiliki.

## 8. Perubahan kebijakan

[ISI: cara memberi tahu]
