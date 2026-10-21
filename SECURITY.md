# Kebijakan Keamanan, Paradise Task Tracker

Sistem ini menyimpan data kerja internal PT Paradise Perkasa: work item, catatan
waktu kerja, dokumentasi perusahaan, dan daftar karyawan beserta perannya.

## Melaporkan kerentanan

Laporkan temuan keamanan **langsung ke bagian IT PT Paradise Perkasa**, bukan
lewat GitHub issue publik dan bukan ke pihak lain.

> Alamat kontak IT belum diisi di berkas ini. Isi begitu ada alamat resminya.
> Sengaja tidak dicantumkan alamat karangan, laporan keamanan yang dikirim ke
> alamat yang tidak dibaca lebih buruk daripada tidak ada alamat sama sekali.

Sertakan dalam laporan:

- Langkah yang bisa diulang untuk memunculkan masalahnya
- URL atau bagian sistem yang terpengaruh
- Dampak yang kamu perkirakan
- Akun/peran yang dipakai saat menemukannya (Admin / Member / Guest)

## Yang diminta dari pelapor

- **Jangan sebarkan dulu** sebelum diperbaiki.
- **Jangan menjalankan pemindaian otomatis** ke instance yang dipakai kerja,
  sistem ini dipakai 79 orang setiap hari.
- **Jangan mengeksploitasi** temuan untuk mengakses atau mengubah data orang
  lain. Cukup buktikan bahwa celahnya ada.
- Jangan melakukan rekayasa sosial, DDoS, atau serangan fisik.

## Cakupan

**Termasuk:** aplikasi web, halaman publik (space), panel admin/God Mode, API,
server kolaborasi, dan konfigurasi deployment di `paradise/`.

**Di luar cakupan:** kerentanan yang butuh akses fisik ke perangkat pengguna
atau posisi man-in-the-middle, spoofing email, dan ketiadaan header DNS
(DNSSEC/CAA) selama sistem masih berjalan di jaringan internal.

## Kerentanan pada basis kode upstream

Sistem ini dibangun di atas Plane Community Edition (lihat [NOTICE.md](NOTICE.md)).
Kerentanan yang berasal dari kode upstream, bukan dari modifikasi kami,
sebaiknya **juga** dilaporkan ke proyek upstream supaya pengguna lain ikut
terlindungi, setelah IT internal diberi tahu lebih dulu.

## Catatan keadaan saat ini

Sistem masih tahap pengembangan dan **belum berjalan di server produksi**.
Hal-hal yang sudah diketahui dan wajib dibereskan sebelum produksi
terdokumentasi di `paradise/`, antara lain kredensial default pada layanan
infrastruktur internal. Jangan anggap keadaan development sebagai gambaran
konfigurasi produksi.
