# Aturan Repositori GitHub

Repo target: **`NomaX-Studio-Indonesia/Nomaden`**.

Tujuannya satu kalimat: tidak ada perubahan yang masuk ke `main` tanpa dibaca
orang lain lebih dulu.

## Status per 26 Agustus 2026: gerbangnya BELUM aktif

Jangan membaca dokumen ini dan mengira `main` sudah terlindungi. **Belum.**
Saat ini **9 kolaborator, 7 di antaranya berakses write, masih bisa `git push`
langsung ke `main`** tanpa dibaca siapa pun.

Sebabnya paket akun, bukan konfigurasi yang salah. Percobaan pemasangannya
dijawab GitHub apa adanya:

```
Upgrade to GitHub Pro or make this repository public
to enable this feature. (HTTP 403)
```

Ruleset dan branch protection untuk repo **privat** hanya tersedia di GitHub
Team atau Enterprise. Keputusan yang diambil: **tunda dulu, jalankan disiplinnya
secara manual.**

### Yang sudah benar-benar aktif sekarang

| Hal                                                           | Status          |
| ------------------------------------------------------------- | --------------- |
| Merge hanya squash, merge commit dan rebase dimatikan         | aktif           |
| Branch dihapus otomatis sesudah merge                         | aktif           |
| Judul commit squash mengikuti judul PR                        | aktif           |
| Issue aktif, issue kosong dimatikan, semua lewat templat      | aktif           |
| Templat Pull Request                                          | aktif           |
| `CODEOWNERS` menunjuk `@ptnomaxstudio-blip`, dan akun itu admin di repo | aktif           |
| **Wajib PR, wajib review, force-push ditolak**                | **TIDAK aktif** |

### Kesepakatan sementara, karena tidak ada yang menegakkannya

1. Semua perubahan lewat branch dan Pull Request, tidak ada yang push ke `main`.
2. Tidak ada yang me-merge PR miliknya sendiri.
3. Minta review ke `@ptnomaxstudio-blip` sebelum merge.
4. Jangan pernah force-push ke `main`.

Empat baris itu tidak dijaga mesin. Kalau ada yang lupa, tidak akan ada
penolakan, tidak akan ada peringatan, dan ketahuannya belakangan.

## Cara mengaktifkannya nanti

Sesudah organisasi naik ke GitHub Team, cukup satu perintah:

```bash
gh auth login                          # sekali saja per mesin
paradise/bin/atur-github.sh            # menyasar NomaX-Studio-Indonesia/Nomaden
paradise/bin/atur-github.sh owner/repo # atau repo lain
```

Aman dijalankan berulang kali. Ruleset dengan nama sama diperbarui, bukan
digandakan. Skripnya berhenti dengan pesan yang jelas kalau paketnya masih
belum mendukung.

## Yang akan berlaku begitu gerbangnya aktif

| Aturan                                    | Akibat nyata                                                     |
| ----------------------------------------- | ---------------------------------------------------------------- |
| Wajib Pull Request                        | `git push` langsung ke `main` ditolak, untuk semua orang         |
| Wajib 1 persetujuan Code Owner            | Hanya `@ptnomaxstudio-blip`, sesuai berkas `CODEOWNERS` di akar repo       |
| Persetujuan hangus saat ada commit baru   | Reviewer tidak bisa "menyetujui lalu ditambahi diam-diam"        |
| Yang push terakhir tidak boleh menyetujui | Tidak bisa menyetujui PR sendiri                                 |
| Semua komentar review wajib diselesaikan  | Tidak ada catatan yang tertinggal terbuka                        |
| 4 status check wajib hijau                | `check:format`, `check:lint`, `check:types`, `Build packages`    |
| Branch wajib sinkron dengan `main`        | Menghindari merge yang lolos uji tapi rusak setelah digabung     |
| Force-push ditolak                        | Untuk semua orang, **termasuk admin**                            |
| Hapus branch `main` ditolak               | Sama                                                             |
| Riwayat linear                            | Tidak ada merge commit bercabang                                 |
| Merge hanya squash                        | Satu PR jadi satu commit di `main`, gampang dibaca dan di-revert |
| Branch dihapus otomatis sesudah merge     | Daftar branch tidak menumpuk                                     |

**Tidak ada `bypass_actors`.** Ini pilihan sadar. Pemilik repo pun tidak bisa
menembusnya. Kalau suatu saat benar-benar buntu, hapus rulesetnya lewat
Settings, jangan menambahkan pengecualian diam-diam yang lalu terlupakan.

## Alur kerja sehari-hari sesudah ini

```bash
git switch -c fix/nama-singkat
# ... kerjakan ...
git push -u origin fix/nama-singkat
gh pr create            # atau lewat tautan yang muncul setelah push
```

Lalu minta review, tunggu hijau, baru merge dengan squash.

**Ini juga berlaku untuk pembaruan Nomaden dari repo Paradise.** Alur lama yang
membuat commit akar baru lalu force-push sudah tidak bisa dipakai, dan memang
sengaja dihentikan: tiap force-push memaksa semua orang menjalankan
`git reset --hard` dan berisiko menghapus kerja lokal mereka. Sekarang
pembaruan Nomaden adalah commit biasa lewat PR, dan tim cukup `git pull`.

## Kenapa hanya empat status check yang diwajibkan

`Lint API` dan `check:sync` sengaja **tidak** diwajibkan meski keduanya ada.
Alasannya teknis, bukan selera: kedua workflow itu memakai filter `paths`, jadi
mereka tidak berjalan untuk PR yang tidak menyentuh `apps/api/**` atau
`packages/i18n/**`.

Status check wajib yang tidak pernah terpicu **tidak dihitung gagal**, ia
menggantung di status pending selamanya, dan PR-nya tidak akan pernah bisa
di-merge. Keduanya tetap berjalan dan tetap terlihat di halaman PR, hanya saja
tidak memblokir.

Kalau suatu saat ingin mewajibkan keduanya, buang dulu filter `paths`-nya.

## Kalau skripnya gagal

**Repo privat di paket Free.** Ini yang sedang terjadi, sudah dikonfirmasi
langsung oleh GitHub, bukan dugaan. Ruleset dan branch protection untuk repo
privat hanya tersedia di GitHub Team atau Enterprise. Tiga jalan keluar:

1. Naikkan organisasi ke GitHub Team. Ini satu-satunya cara mendapat gerbang
   review tanpa membuka kode ke publik.
2. Jadikan repo publik. **Jangan** sebelum seluruh berkas `.env` dicabut dari
   riwayat git dan setiap rahasianya dirotasi. Repo ini memuat kredensial
   produksi yang sedang dipakai: `SECRET_KEY` Django, kata sandi Postgres,
   RabbitMQ, MinIO, LiveKit, TURN, dan SMTP. Mencabutnya dari riwayat adalah
   pekerjaan tersendiri, bukan satu klik. Lihat
   [`SECURITY-CHECKLIST.md`](SECURITY-CHECKLIST.md).
3. Jalankan disiplinnya secara manual. **Ini yang dipilih untuk sekarang**,
   lihat bagian status di bagian atas dokumen ini.

**Bukan admin.** Ruleset hanya bisa dipasang oleh admin repo. Skripnya berhenti
lebih dulu dan menyebutkannya.

## Berkas yang menopang aturan ini

| Berkas                                                   | Perannya                                                                                                                                                                                             |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CODEOWNERS`                                             | Menentukan siapa yang wajib menyetujui. Sebelumnya masih berisi tujuh maintainer upstream Plane yang tidak punya akses ke repo ini; kalau daftar itu dibiarkan, tidak akan ada PR yang bisa di-merge |
| `.github/pull_request_template.md`                       | Kerangka PR, termasuk daftar periksa sebelum minta review                                                                                                                                            |
| `.github/ISSUE_TEMPLATE/bug-report.yaml`                 | Laporan bug, memaksa langkah untuk mengulang terisi                                                                                                                                                  |
| `.github/ISSUE_TEMPLATE/feature-request.yaml`            | Permintaan fitur, menanyakan masalahnya lebih dulu, bukan solusinya                                                                                                                                  |
| `.github/ISSUE_TEMPLATE/config.yaml`                     | Mematikan issue kosong supaya semua lewat template                                                                                                                                                   |
| `.github/workflows/pull-request-build-lint-web-apps.yml` | Sumber keempat status check wajib                                                                                                                                                                    |
