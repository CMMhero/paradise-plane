# Kerangka dokumen hukum

🔴 **Berkas di folder ini KERANGKA, bukan dokumen hukum.** Tidak satu pun boleh
diterbitkan apa adanya.

Yang ada di sini adalah daftar bagian yang harus ada, keputusan yang harus
diambil, dan fakta teknis yang sudah terverifikasi dari kode. Kalimat hukumnya
ditulis ahli hukum, bukan di sini.

Saya menulisnya karena satu alasan praktis: ahli hukum yang menerima "tolong
buatkan syarat layanan" akan menagih waktu untuk menanyakan hal yang jawabannya
sudah ada di repo ini. Kerangka yang membawa jawaban itu memotong bagian
termahalnya.

## Cara memakai

1. Isi setiap `[ISI: ...]`. Itu keputusan bisnis, dan tidak ada yang bisa
   mengisinya selain pemilik produk.
2. Serahkan ke ahli hukum **beserta** `paradise/PENGAWASAN-DAN-PRIVASI.md`.
   Dokumen itu berisi audit apa yang benar-benar direkam sistem, dan itu yang
   biasanya paling sulit didapat ahli hukum dari klien.
3. Jangan terbitkan sebelum ditinjau.

## Kenapa ketiganya, bukan satu

| Dokumen                         | Antara siapa                            | Menjawab                                           |
| ------------------------------- | --------------------------------------- | -------------------------------------------------- |
| `syarat-layanan.md`             | NomaX dan perusahaan pelanggan          | Aturan pemakaian, pembayaran, penghentian          |
| `kebijakan-privasi.md`          | NomaX dan orang yang datanya diproses   | Data apa, untuk apa, berapa lama                   |
| `perjanjian-pemrosesan-data.md` | NomaX dan pelanggan, soal data karyawan | Siapa pengendali, siapa pemroses, apa kewajibannya |

Yang ketiga paling sering dilupakan dan paling sering diminta pelanggan
korporat. Perusahaan pelanggan adalah **pengendali** data karyawannya, NomaX
adalah **pemroses**, dan UU 27/2022 membebani keduanya dengan kewajiban yang
berbeda.

## Dasar hukum yang relevan

- **UU 27/2022 tentang Pelindungan Data Pribadi.** Berlaku untuk sistem ini
  begitu ia memproses data karyawan perusahaan lain.
- **AGPL-3.0.** Sudah dipenuhi lewat `/source/`, tapi Syarat Layanan sebaiknya
  menyebutkannya supaya penerima tahu haknya.

⚠️ Ini informasi umum, bukan nasihat hukum.
