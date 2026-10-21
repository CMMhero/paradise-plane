# Perjanjian Pemrosesan Data (KERANGKA)

🔴 Bukan dokumen hukum. Paling sering diminta pelanggan korporat dan paling
sering dilupakan penjual.

## 1. Kedudukan para pihak

Pelanggan adalah **pengendali** data karyawannya. NomaX adalah **pemroses**.
Ini bukan formalitas: UU 27/2022 membebani keduanya kewajiban yang berbeda, dan
menyamakannya membuat salah satu pihak memikul yang bukan bagiannya.

## 2. Ruang lingkup pemrosesan

- Objek: data pribadi karyawan pelanggan di dalam Layanan
- Jenis: identitas, surel, isi pekerjaan, jejak aktivitas
- Tujuan: menjalankan Layanan sesuai instruksi pelanggan
- Jangka waktu: selama langganan berjalan, ditambah masa penyimpanan
  [ISI: mengacu ke keputusan 4.4]

## 3. Kewajiban NomaX sebagai pemroses

- Memproses hanya sesuai instruksi pelanggan
- Menjaga kerahasiaan
- Menerapkan pengamanan yang wajar
- [ISI: berapa jam pemberitahuan kalau terjadi kebocoran]
- Membantu pelanggan menjawab permintaan pemilik data
- Menghapus atau mengembalikan data saat perjanjian berakhir

## 4. Sub-pemroses

Daftar yang harus disebutkan berikut apa yang mereka terima:

- [ISI: penyedia VPS, wilayah pusat data]
- Xendit, pembayaran
- [ISI: penyedia SMTP]
- [ISI: penyedia AI, kalau nanti relevan]

[ISI: berapa hari sebelumnya pelanggan diberi tahu kalau ada sub-pemroses baru,
dan apakah mereka boleh keberatan]

## 5. Lokasi pemrosesan

[ISI: negara tempat data disimpan]
Kalau ada bagian yang diproses di luar Indonesia, itu harus disebut eksplisit
beserta dasar pemindahannya.

## 6. Keamanan teknis

Boleh disalin dari kode karena sudah terverifikasi:

- Database terpisah per perusahaan berbayar
- Objek penyimpanan terpisah per bucket
- Sandi di-hash, rahasia instance disimpan sebagai sidik
- Akses lewat HTTPS
- Riwayat login punya retensi terbatas yang berjalan otomatis

## 7. Audit

[ISI: apakah pelanggan boleh mengaudit, dalam bentuk apa, seberapa sering]

## 8. Setelah perjanjian berakhir

NomaX menyediakan ekspor lengkap berisi baris dan berkasnya, lalu menghapus
sesuai jangka waktu yang disepakati.
[ISI: berapa hari pelanggan punya waktu mengambil ekspornya]
