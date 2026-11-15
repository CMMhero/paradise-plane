# Audit UI: sebelum dan sesudah

Tangkapan layar dan metrik dari audit tampilan, tata letak, aksesibilitas, dan
kinerja (versi 2.7.1). Tangkapan diambil di 31 halaman, 3 ukuran layar, tema
terang dan gelap: 186 PNG per folder, plus `metrics.json`.

| Folder                                     | Isi                                                                                           |
| ------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `before/`                                  | Kondisi sebelum audit (basis 2.6.1)                                                           |
| `final/`                                   | Kondisi sesudah semua perbaikan                                                               |
| `a11y-before/`, `a11y-after/`              | Hasil axe-core per halaman (tanpa PNG)                                                        |
| `perf-before/`, `perf-after/`, `perf-opt/` | Kinerja build produksi: basis, perbaikan tampilan saja, perbaikan tampilan plus ukuran bundle |

Nama berkas: `<halaman>-<mobile|tablet|desktop>-<light|dark>.png`.
Ukuran layar: mobile 390x844, tablet 820x1180, desktop 1440x900.

Tangkapan `before/` dan `final/` diambil sebelum cabang ini digabung dengan
2.7.0 (jenjang Sekretaris, balasan chat, dan seterusnya). Halaman chat di
`final/` belum menampilkan fitur itu. Metrik axe dan kinerja juga diukur di
basis lama.

## Hasil

| Pengukuran                                                   | Sebelum      | Sesudah                  |
| ------------------------------------------------------------ | ------------ | ------------------------ |
| Pelanggaran axe serius atau kritis (muatan halaman dari 155) | 151          | 0                        |
| Pelanggaran axe di semua tingkat (186 tangkapan akhir)       | tidak diukur | 0                        |
| Halaman (rute x ukuran) dengan CLS di atas 0,1               | 28           | 1 (0,1045, tablet gelap) |
| CLS median tablet                                            | 0,20         | 0                        |
| Galat `pageerror: undefined`                                 | 42           | 0                        |
| Galat console                                                | 54           | 0                        |
| Peringatan React (mode dev, sebagian dari pustaka)           | 316          | 288                      |
| Halaman gagal render atau terlempar ke login                 | 0            | 0                        |

### Kinerja build produksi

Diukur pada build produksi, CPU diperlambat 4x, jaringan Fast 4G, median 3
muatan dingin, tema terang. Server dev Vite tidak dipakai untuk angka ini.

| Rute (mobile)    | JS pertama (KB, gzip), sebelum / sesudah | LCP (detik) | TBT (detik) | CLS           |
| ---------------- | ---------------------------------------- | ----------- | ----------- | ------------- |
| workspace-home   | 2104 / 1526                              | 15,2 / 11,9 | 4,1 / 3,6   | 0,535 / 0     |
| issues-list      | 2136 / 1550                              | 19,6 / 18,4 | 8,1 / 7,7   | 0,557 / 0     |
| chat             | 2021 / 1439                              | 11,8 / 11,3 | 4,1 / 3,4   | 0,285 / 0     |
| approvals        | 1999 / 1415                              | 16,0 / 14,8 | 4,7 / 4,2   | 0 / 0         |
| dashboard-divisi | 1997 / 1410                              | 13,9 / 12,4 | 3,6 / 3,0   | 0,001 / 0,001 |

JS yang dimuat pertama kali turun sekitar 28 persen di semua rute ruang kerja.
Tabel lengkap: `node scripts/ui-audit/perf-compare.mjs perf-before perf-after
perf-opt --md` dari folder ini.

Catatan jujur tentang angka:

- LCP absolut tinggi karena throttling agresif dan server statis HTTP/1.1
  buatan sendiri (`serve-static.mjs`). Banding antar-build adil, nilai
  mutlaknya tidak mewakili produksi di belakang Caddy.
- `issues-kanban` mobile LCP naik dari 13,3 ke 18,3 detik, konsisten di tiga
  run, sementara TBT dan waktu dinding tidak berubah. Dugaan: perbaikan CLS
  mengubah elemen mana yang dihitung sebagai LCP. Belum diverifikasi.
- Halaman login sedikit lebih lambat (sekitar 0,3 detik LCP, 4 permintaan
  lebih banyak) karena bundler memecah beberapa chunk kecil bersama.

## Yang belum beres

- `workspace-views` tablet gelap CLS 0,1045, tepat di atas batas.
- `page-detail` menampilkan kerangka terus karena server kolaborasi (`:3100`)
  tidak ikut tumpukan lokal. Itu artefak lingkungan. Elemen yang tercatat
  "terpotong" di notifikasi adalah panel detail kosong yang sengaja diparkir
  di luar layar pada layar sempit.
- Tidak dikerjakan karena mengubah perilaku: satu permintaan per pesan chat
  untuk rujukan tugas dan pratinjau tautan, polling chat yang bisa diganti
  peristiwa socket, virtualisasi daftar pesan, tabel lintas divisi dan sampah
  sebagai kartu di HP, ilustrasi keadaan kosong (202 KB gzip di setiap
  halaman) yang bisa dimuat malas, dan pemecahan `@plane/utils` dan
  `@plane/ui`.
- Belum diuji manual: seret kartu kanban di layar sentuh, klik dan keyboard
  pada breadcrumb, chip anggota, dan pemilih reaksi yang strukturnya diubah,
  dan editor kaya yang kini dimuat malas (referensinya kosong sampai kodenya
  tiba; pemanggil sudah memakai `ref.current?.`).

## Mengulang

```bash
scripts/ui-audit/stack.sh up        # docker + server dev
set -a; . <berkas-env-berisi-UI_AUDIT_EMAIL-dan-PASSWORD>; set +a
cd scripts/ui-audit
node shoot.mjs <label>                     # tangkapan layar + metrik
node shoot.mjs <label> --a11y --no-shots   # axe dan sasaran sentuh
node shoot.mjs <label> --throttle --runs 3 --no-shots   # kinerja (build produksi)
```

Kata sandi tidak disimpan di repo; skrip membacanya dari variabel lingkungan.

## Aksesibilitas (axe dan sasaran sentuh)

Aturan, jumlah halaman terdampak sebelum audit, dan hasil akhir 0 untuk semuanya:

| Aturan                      | Tingkat | Halaman terdampak sebelum |
| --------------------------- | ------- | ------------------------- |
| button-name                 | kritis  | 146                       |
| aria-required-attr          | kritis  | 116                       |
| label                       | kritis  | 16                        |
| nested-interactive          | serius  | 141                       |
| label-content-name-mismatch | serius  | 141                       |
| color-contrast              | serius  | 109                       |
| aria-command-name           | serius  | 64                        |
| target-size                 | serius  | 53                        |
| link-name                   | serius  | 8                         |
| scrollable-region-focusable | serius  | 5                         |
| svg-img-alt                 | serius  | 5                         |
| aria-input-field-name       | serius  | 2                         |
| document-title              | serius  | 1                         |

Tidak ada aturan yang dimatikan dan tidak ada elemen yang disembunyikan dengan
`aria-hidden`. Sasaran sentuh di mobile (minimal 24x24 piksel, WCAG 2.2 AA
2.5.8) turun dari 1.561 elemen menjadi 460 pada run perantara; angka itu masih
menghitung tombol nonaktif, dan filter `:disabled` ditambahkan sesudahnya.
Satu tombol kirim di `settings-projects` kadang terdeteksi kontras saat sedang
bertransisi dan lolos di run berikutnya.
