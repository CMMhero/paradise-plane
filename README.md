# Paradise Task Tracker

Sistem manajemen kerja internal PT Paradise Perkasa. Jalan di server sendiri,
tanpa langganan bulanan ke siapa pun.

Sekarang dipakai 16 divisi, 79 akun.

## Kenapa dibikin

Kantor butuh satu tempat buat ngelacak kerjaan, catat jam kerja, dan naruh
dokumentasi perusahaan. Yang komersial mahal kalau dikali 79 orang, dan datanya
ada di server orang lain.

Jadi saya ambil basis open-source yang bagus (Plane CE, AGPL, lihat bagian
paling bawah), lalu bangun sendiri bagian-bagian yang kantor butuh tapi memang
nggak ada di dalamnya.

## Yang saya bangun sendiri

Delapan ini nggak ada di basis aslinya. Semuanya dari nol, model database,
migrasi, endpoint, aturan izin, sampai tampilannya.

**Time tracking.** Orang catat jam kerja langsung di work item-nya. Tiap orang
cuma bisa hapus catatan miliknya sendiri, admin project bisa lihat semua.

**Work item types + custom properties.** Tiap project bisa punya tipe work item
sendiri, dan properti custom dengan 6 jenis field (teks, angka, boolean,
tanggal, pilihan, anggota). Validasinya di server, opsi harus beneran milik
propertinya, dan kalau field-nya "anggota" ya orangnya harus beneran anggota
project itu.

**Template + recurring.** Bikin template work item, terus jadwalkan berulang.
Yang agak saya pikirin di sini: kalau laptop mati semalam, jadwal yang kelewat
**dilewat**, bukan dirapel. Kalau dirapel, paginya orang bangun dan dapat
tumpukan tugas palsu.

**Wiki perusahaan.** Ini yang paling panjang, dikerjain tiga tahap:

Tahap A, halaman bisa nerima semua tipe file, pdf, docx, mp4, zip, sampai
100 MB, plus node "File" di editor yang bisa nampilin PDF langsung di dalam
halaman.

Tahap B, kontrol edit per folder. Tiap folder tingkat atas dimiliki divisi
tertentu; cuma anggotanya yang boleh nyunting, sisanya baca doang. Ini yang
paling makan waktu, karena harus ditegakkan di **dua tempat**: REST API dan
server kolaborasi real-time. Kalau cuma di REST, orang di luar divisi bakal
lihat halamannya bisa diedit, ngetik panjang-panjang, terus tulisannya hilang
pas reload. Endpoint `can-edit/` sengaja nggak nyalin aturan izinnya, dia
manggil kelas permission yang sama persis, jadi REST sama editor mustahil beda
pendapat.

Tahap C, pohon halaman bertingkat. Sub-halaman dulu bukan cuma nggak keliatan,
tapi **404 kalau dibuka**.

**Dashboard divisi.** Rekap per project yang kamu ikuti: total, yang masih
jalan, yang lewat tenggat, yang selesai, plus total jam kerja. Ada ekspor CSV
juga, langsung bisa dibuka Excel. Staf cuma lihat project yang dia ikuti.

**Initiatives.** Sasaran tingkat workspace yang nyambungin beberapa project
divisi, progresnya dihitung dari semua work item di project yang ketaut.

**Audit logs.** Nyatet siapa ngubah apa di model-model penting. Aktornya
kerekam baik lewat request HTTP biasa maupun lewat editor kolaboratif, yang
kedua ini sempat saya ragukan, ternyata jalan.

**ACL per folder Wiki.** Pemetaan folder ke divisi, sub-halaman mewarisi dari
induknya, admin bisa override. Sengaja nggak nambah dependency: keanggotaan
divisi itu berubah-ubah, jadi grant statis malah gampang melenceng dari
kenyataan.

## Bagian operasionalnya

Ini juga saya urus sendiri, dan jujur bagian ini yang paling sering ngasih
pelajaran:

- **CI/CD**, tiap push ke `main` bikin 6 image ke GHCR. Tag-nya pakai commit
  SHA, terus `latest` digeser pakai `imagetools create` (nyalin manifest, bukan
  build ulang). Deploy di server manual lewat `paradise/bin/deploy.sh`, rollback
  tinggal `APP_RELEASE=<sha>`.
- **Backup**, `pg_dump` terkompresi, ada retensi, hasilnya dicek nggak kosong.
  Dan dia **nunggu** Postgres beneran siap, bukan langsung nyerah pas Docker
  belum naik. Ini hasil dua pagi berturut-turut backup gagal.
- **Healthcheck** buat semua layanan, plus skrip pendaftaran scheduled task yang
  nggak butuh hak admin di Windows.

## Cara jalanin di lokal

Panduan dari nol sampai aplikasinya kebuka. Ditulis buat Windows karena itu yang
dipakai di sini, tapi langkah versi bash-nya sama persis di macOS dan Linux.

Baca sampai habis sebelum ngetik. Tujuh langkah, dan langkah 3 sama 4 itu yang
paling sering dilewat lalu bikin `pnpm dev` kelihatan "rusak".

### Langkah 1, pasang alatnya

| Alat               | Versi minimum | Buat apa                                                                    | Unduh                                             |
| ------------------ | ------------- | --------------------------------------------------------------------------- | ------------------------------------------------- |
| **Docker Desktop** | terbaru       | Postgres, Redis, RabbitMQ, MinIO, dan backend Django semuanya jalan di sini | <https://www.docker.com/products/docker-desktop/> |
| **Node.js**        | **22.18.0**   | frontend dan server kolaborasi                                              | <https://nodejs.org/en/download>                  |
| **pnpm**           | **11.3.0**    | package manager monorepo, lihat catatan di bawah                            | <https://pnpm.io/installation>                    |
| **Git**            | 2.40+         | Git for Windows sekalian ngasih Git Bash                                    | <https://git-scm.com/downloads>                   |
| VS Code (opsional) | terbaru       | ekstensi yang dipakai ada di `.vscode/`                                     | <https://code.visualstudio.com/>                  |

Mesinnya butuh **RAM 12 GB** (8 GB sering gagal pas build container) dan sisa
disk sekitar **15 GB**.

**Node 20 nggak cukup.** `package.json` minta `>=22.18.0`, dan pnpm bakal nolak
install dengan `ERR_PNPM_UNSUPPORTED_ENGINE`. Ini beda dari dokumen lama, jadi
cek beneran versinya, jangan diasumsikan.

**pnpm-nya jangan sembarang versi.** Versinya dikunci di `packageManager`
(`pnpm@11.3.0`). Cara paling aman lewat corepack yang udah bawaan Node:

```powershell
corepack enable pnpm
corepack prepare pnpm@11.3.0 --activate
```

Kalau `corepack` nggak ada di instalasi Node kamu, `npm install -g pnpm@11.3.0`
juga cukup. Yang nggak boleh: pnpm 9 atau 10, lockfile-nya bakal ditolak.

**Khusus Windows**, sekali seumur mesin, biar path `node_modules` yang dalam
nggak kena batas 260 karakter:

```powershell
git config --global core.longpaths true
```

Verifikasi semuanya sebelum lanjut:

```powershell
node --version            # harus v22.18.0 atau lebih baru
pnpm --version            # harus 11.3.0
docker --version
docker compose version
git --version
```

### Langkah 2, ambil kodenya

```powershell
git clone <url-repo>
cd <folder-repo>
```

### Langkah 3, Windows saja: benerin symlink i18n

Repo ini punya **satu** symlink yang di-track git: `packages/i18n/locales`
nunjuk ke `packages/i18n/src/locales`. Git di Windows nggak bikin symlink kecuali
Developer Mode nyala, jadi yang keluar dari `git clone` itu **file teks 11 byte**
berisi tulisan `src/locales`. Akibatnya semua terjemahan gagal dimuat.

Gejalanya: seluruh tampilan jadi kunci mentah kayak `auth.common.email.label`,
bukan teks.

Cek dulu:

```powershell
Get-Item packages\i18n\locales | Select-Object Name, LinkType
```

`LinkType` harus `Junction`. Kalau kosong, benerin:

```powershell
Remove-Item packages\i18n\locales -Force -Recurse -ErrorAction SilentlyContinue
cmd /c mklink /J packages\i18n\locales packages\i18n\src\locales
git update-index --skip-worktree packages/i18n/locales
Add-Content .git\info\exclude "/packages/i18n/locales/"
```

Baris terakhir bikin VS Code nggak nampilin 532 file bayangan. Ini lokal, sengaja
di `.git/info/exclude` dan bukan di `.gitignore`, karena ini masalah mesin
Windows, bukan masalah proyeknya.

Alternatif yang lebih bersih kalau kamu boleh: nyalain **Developer Mode** di
Windows, terus `git config --global core.symlinks true`, lalu klon ulang. Setelah
itu langkah ini nggak perlu selamanya.

Jangan sekali-kali "benerin" dengan nyalin isi `src/locales` ke `locales`.
Salinannya bakal melenceng diam-diam.

### Langkah 4, bikin berkas `.env`, semuanya **ENAM**

Ini penyebab nomor satu "udah pull tapi `pnpm dev` nggak jalan". Panduan lama
cuma nyuruh bikin dua, dan dua itu nggak cukup.

| Berkas            | Dibaca siapa                                           | Kalau nggak ada                               |
| ----------------- | ------------------------------------------------------ | --------------------------------------------- |
| `.env`            | `docker compose` buat Postgres, Redis, RabbitMQ, MinIO | container gagal naik, variabel kosong         |
| `apps/api/.env`   | Django, Celery, migrator                               | API mati atau nolak semua panggilan           |
| `apps/web/.env`   | Vite aplikasi web                                      | **web jalan tapi mati total**, lihat di bawah |
| `apps/admin/.env` | Vite God Mode                                          | sama, God Mode nggak bisa manggil API         |
| `apps/space/.env` | Vite halaman publik                                    | sama                                          |
| `apps/live/.env`  | server kolaborasi                                      | **`live` langsung crash dan restart terus**   |

Dua akibat yang paling bikin bingung, dan dua-duanya nggak nyebut `.env` sama
sekali di pesan errornya:

- **`apps/live/.env` nggak ada.** Perintahnya `node --env-file=.env .`, dan Node
  itu mati kalau file-nya nggak ada. Supervisor-nya nyalain lagi, mati lagi.
  Di output `pnpm dev` kelihatan kayak seluruh dev server-nya yang error.
- **`apps/web/.env` nggak ada.** `VITE_API_BASE_URL` kosong, dan kode jatuh ke
  string kosong (`packages/constants/src/endpoints.ts`). Semua panggilan API jadi
  nyasar ke `localhost:4000` yang nggak punya backend. Halamannya kebuka, tapi
  putih atau muter terus, dan errornya cuma 404 di tab Network.

Cara cepat, lewat **Git Bash** (atau macOS/Linux):

```bash
bash setup.sh
```

Skrip itu nyalin keenamnya dari `.env.example` masing-masing, **nggak nimpa yang
udah ada**, terus ngisiin `SECRET_KEY` Django.

Manual lewat PowerShell:

```powershell
Copy-Item .env.example .env
Copy-Item apps\api\.env.example   apps\api\.env
Copy-Item apps\web\.env.example   apps\web\.env
Copy-Item apps\admin\.env.example apps\admin\.env
Copy-Item apps\space\.env.example apps\space\.env
Copy-Item apps\live\.env.example  apps\live\.env

$chars = (48..57) + (97..122) | ForEach-Object { [char]$_ }
$key = -join (1..50 | ForEach-Object { $chars | Get-Random })
Add-Content apps\api\.env "SECRET_KEY=$key"
```

⚠️ Kalau klon repo-mu **udah bawa `.env`**, lewati langkah ini seluruhnya. Jangan
nimpa, isinya kredensial beneran.

Nilai bawaannya udah bener buat dev lokal. Satu hal yang wajib kamu cocokkan
sendiri kalau ngubah-ubah: **`LIVE_SERVER_SECRET_KEY` di `apps/api/.env` dan
`apps/live/.env` harus sama persis.** Beda dikit, editor kolaboratif nolak semua
sambungan dengan "Tidak berhak", padahal orangnya emang berhak.

### Langkah 5, nyalain layanan pendukungnya (Docker)

Docker Desktop harus **udah jalan** dulu, bukan cuma keinstal.

PowerShell:

```powershell
docker compose -f docker-compose-local.yml up -d --build
```

Git Bash, macOS, Linux:

```bash
COMPOSE_FILE=docker-compose-local.yml docker compose up -d --build
```

⚠️ Bentuk `COMPOSE_FILE=... docker compose ...` itu **sintaks bash**. Ditempel ke
PowerShell hasilnya langsung galat `The term 'COMPOSE_FILE=...' is not recognized`.
Di PowerShell pakai `-f`.

Build pertama makan **5 sampai 15 menit**, image Django-nya dibangun dari source.

Yang naik: `plane-db`, `plane-redis`, `plane-mq`, `plane-minio`, `api`, `worker`,
`beat-worker`, dan `migrator`.

**`migrator` berhenti sendiri dengan status `Exited (0)`, dan itu normal.** Dia
cuma jalan sekali buat migrasi database, bukan container yang mati.

Cek:

```powershell
docker compose -f docker-compose-local.yml ps
curl.exe http://localhost:8000/api/instances/
```

Ada pembungkus tipisnya juga: `.\paradise\bin\dev.ps1 up|down|logs|ps|rebuild`
di Windows, atau `make dev-up` / `make dev-logs svc=api` di bash.

### Langkah 6, pasang dependensi lalu jalanin frontend

```powershell
pnpm install
pnpm dev
```

`pnpm install` pertama 3 sampai 8 menit. `pnpm dev` **nggak langsung ngasih
port**: turbo bangun dulu 12 paket internal (`dev` punya `dependsOn: ["^build"]`
di `turbo.json`), baru nyalain 4 aplikasi. Jadi wajar 1 sampai 3 menit diam
sebelum ada alamat yang bisa dibuka. Jangan keburu di-Ctrl+C.

**Tiap habis `git pull`, jalanin `pnpm install` lagi** kalau `package.json` atau
`pnpm-lock.yaml` ikut berubah. Ini penyebab paling sering "kemarin jalan, habis
pull mati", dan errornya biasanya `Cannot find module`.

### Langkah 7, daftarin admin pertama

1. Buka **<http://localhost:3001/god-mode/>**, daftarkan instance admin pertama.
2. Baru buka **<http://localhost:4000>** buat aplikasinya.

Urutannya nggak bisa dibalik: sebelum ada instance admin, aplikasi utamanya
nggak punya apa-apa buat dilayanin.

### Langkah 8, isi organisasi contoh

Instance yang baru daftar itu **kosong**, dan kosong artinya sebagian besar
fiturnya nggak bisa dicoba sama sekali. Wiki paling kentara: rute `/wiki`
nyari project ber-identifier `WIKI` pas jalan, dan kalau nggak ketemu yang
muncul cuma layar "Wiki belum tersedia" tanpa tombol apa pun.

Satu perintah buat bikin organisasi contoh lengkap:

```bash
# uji kering dulu, nggak nulis apa-apa
docker compose -f docker-compose-local.yml exec -T api     python manage.py shell < paradise/bin/seed-demo.py

# kalau hasilnya masuk akal, baru terapkan
docker compose -f docker-compose-local.yml exec -T api     -e SEED_DEMO_APPLY=1 python manage.py shell < paradise/bin/seed-demo.py
```

Yang dibikin: workspace `nomaden-demo`, lima akun, tiga project divisi (OPS,
SALES, TECH), project `WIKI` lengkap dengan governance-nya, plus tiga folder
Wiki yang sengaja mewakili tiga keadaan izin yang beda (punya divisi pemilik,
General terbuka buat semua, dan satu yang sengaja dibiarkan terkunci).

Sandi semua akunnya `Demo1234!`, masuk pakai `owner@demo.local`. Bisa diganti
lewat variabel lingkungan:

| Variabel              | Bawaan         |
| --------------------- | -------------- |
| `SEED_DEMO_WORKSPACE` | `nomaden-demo` |
| `SEED_DEMO_NAME`      | `Nomaden Demo` |
| `SEED_DEMO_DOMAIN`    | `demo.local`   |
| `SEED_DEMO_PASSWORD`  | `Demo1234!`    |

Aman dijalanin berkali-kali, nggak bakal numpuk. Dan dia nolak jalan kalau
workspace tujuannya ternyata punya orang lain, biar nggak kejadian kesiram ke
data beneran.

**Buat lokal doang.** Sandinya seragam dan ketulis di berkasnya.

### Tabel port

| Layanan                | Port     | Alamat                                 |
| ---------------------- | -------- | -------------------------------------- |
| Web (aplikasi utama)   | **4000** | <http://localhost:4000>                |
| Admin / God Mode       | 3001     | <http://localhost:3001/god-mode/>      |
| Space (halaman publik) | 3002     | <http://localhost:3002/spaces/>        |
| Live (kolaborasi)      | 3100     | <http://localhost:3100/live/health>    |
| API (Django)           | 8000     | <http://localhost:8000/api/instances/> |
| MinIO console          | 9090     | <http://localhost:9090>                |
| PostgreSQL             | 5432     |                                        |
| Redis                  | 6379     |                                        |
| RabbitMQ               | 5672     |                                        |

**Web-nya di 4000, bukan 3000.** Upstream pakai 3000 dan itu masih nempel di
banyak dokumen dan tutorial di luar sana.

### Perintah harian

```powershell
pnpm dev                  # nyalain semua frontend + live
pnpm check:types          # pemeriksaan tipe
pnpm check:lint           # oxlint
pnpm check:format         # oxfmt
pnpm build                # build seluruh aplikasi
pnpm fix                  # rapikan format + lint otomatis

docker compose -f docker-compose-local.yml logs -f api
docker compose -f docker-compose-local.yml restart api
docker compose -f docker-compose-local.yml down
```

Dua hal yang bakal bikin kamu bingung kalau nggak tahu:

- Ubah kode backend? **`docker compose restart api`.** Autoreload-nya nggak
  jalan di sini, bind-mount Windows ke container nggak nerusin event perubahan
  file. Gejalanya endpoint balas 404 padahal kodenya udah bener.
- Ubah `.env`? **`docker compose up -d`, bukan `restart`.** `restart` nggak baca
  ulang `env_file`.

### Kalau nggak jalan

Cari gejalanya di kolom kiri. Hampir semua yang pernah kejadian ada di sini.

| Gejala / pesan error                                                                               | Sebabnya                                                                       | Obatnya                                                                                                |
| -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `ERR_PNPM_UNSUPPORTED_ENGINE`, "Unsupported engine"                                                | Node di bawah 22.18.0                                                          | pasang Node 22.18+, lalu `pnpm install` lagi                                                           |
| `pnpm` nggak dikenal, atau versinya bukan 11.3.0                                                   | pnpm belum aktif atau salah versi                                              | `corepack enable pnpm` lalu `corepack prepare pnpm@11.3.0 --activate`                                  |
| `ERR_PNPM_LOCKFILE_BREAKING_CHANGE` / `ERR_PNPM_OUTDATED_LOCKFILE`                                 | pnpm beda versi, atau lockfile berubah setelah pull                            | pastikan pnpm 11.3.0, lalu `pnpm install` (tanpa `--frozen-lockfile`)                                  |
| Habis `git pull`, muncul `Cannot find module ...`                                                  | dependensi baru belum dipasang                                                 | `pnpm install`                                                                                         |
| `live` mati lalu nyala terus, `apps/live/live-dev.log` bilang `ENOENT ... .env`                    | `apps/live/.env` nggak ada                                                     | bikin dari `apps/live/.env.example`, lihat langkah 4                                                   |
| Halaman 4000 kebuka tapi putih atau muter terus, tab Network penuh 404 ke `localhost:4000/api/...` | `apps/web/.env` nggak ada, `VITE_API_BASE_URL` kosong                          | bikin `apps/web/.env`, lalu **matikan dan nyalain ulang** `pnpm dev` (Vite baca `.env` cuma pas start) |
| Konsol peramban bilang **CORS**                                                                    | `CORS_ALLOWED_ORIGINS` di `apps/api/.env` nggak memuat `http://localhost:4000` | tambahin, lalu `docker compose -f docker-compose-local.yml up -d` (bukan `restart`)                    |
| Semua teks jadi kunci mentah, contoh `auth.common.email.label`                                     | junction i18n pecah atau belum dibikin                                         | langkah 3                                                                                              |
| `git status` tiba-tiba ratusan perubahan `packages/i18n/locales/**`                                | junction dipecah pre-commit hook                                               | **jangan di-commit**, pulihkan dulu, langkahnya di [CONTRIBUTING.md](CONTRIBUTING.md)                  |
| `EPERM` / `ENOENT` waktu `pnpm install`, path kepanjangan                                          | batas 260 karakter Windows                                                     | `git config --global core.longpaths true`, hapus `node_modules`, install ulang                         |
| `error during connect`, `docker daemon is not running`                                             | Docker Desktop belum nyala                                                     | nyalain Docker Desktop, tunggu ikonnya hijau                                                           |
| `The term 'COMPOSE_FILE=...' is not recognized`                                                    | sintaks bash ditempel ke PowerShell                                            | pakai bentuk `docker compose -f docker-compose-local.yml ...`                                          |
| `port is already allocated`, atau `EADDRINUSE` di 4000                                             | port dipakai proses lain                                                       | `netstat -ano \| findstr :4000` lalu `taskkill /PID <pid> /F`                                          |
| `migrator` statusnya `Exited (0)`                                                                  | itu memang seharusnya                                                          | bukan error, abaikan                                                                                   |
| Endpoint backend balas 404 padahal kodenya udah bener                                              | backend nggak autoreload                                                       | `docker compose -f docker-compose-local.yml restart api`                                               |
| Ganti `.env` tapi nggak ngefek                                                                     | `restart` nggak baca ulang `env_file`                                          | `docker compose -f docker-compose-local.yml up -d`                                                     |
| `pnpm dev` diam lama tanpa port                                                                    | turbo lagi build 12 paket internal dulu                                        | tunggu 1 sampai 3 menit                                                                                |
| turbo error aneh yang nggak masuk akal                                                             | daemon turbo nyangkut                                                          | `pnpm exec turbo daemon stop`, ulangi                                                                  |
| Lampiran dan avatar gagal dimuat                                                                   | `MINIO_PUBLIC_ENDPOINT_URL` kosong di `apps/api/.env`                          | isi `http://localhost:9000`, lalu `up -d`                                                              |
| Editor kolaboratif nolak dengan "Tidak berhak"                                                     | `LIVE_SERVER_SECRET_KEY` beda antara api dan live                              | samakan persis, lalu `up -d` dan restart `pnpm dev`                                                    |

Kalau masih mentok, kirim **teks error persisnya** plus keluaran `node --version`,
`pnpm --version`, dan `docker compose -f docker-compose-local.yml ps`. Tiga itu
biasanya cukup buat nunjuk penyebabnya.

Sisanya, deploy produksi, checklist keamanan, cara sync dari upstream, ada di
folder `paradise/`.

## Dibangun pakai

Django REST Framework, PostgreSQL, Redis, RabbitMQ + Celery, MinIO di backend.
React + React Router, TypeScript, MobX, Tailwind di frontend. Hocuspocus (Y.js)
buat editor kolaboratif. Semuanya dibungkus Docker Compose, di depannya Caddy.

## Yang belum beres

Biar jujur aja:

- **SMTP belum jalan.** Kolomnya udah keisi, tapi host-nya masih placeholder yang
  nggak resolve dari dalam container. Jadi undangan user sama reset password
  nggak bakal nyampe. Nunggu IP mail server dari IT.
- **Belum ada server produksi.** Masih jalan lokal semua.
- **Isi Wiki-nya masih kerangka.** Mesinnya udah kelar, dokumennya belum ditulis
  , dan itu kerjaan manusia, bukan kerjaan kode.
- **Belum pernah sync dari upstream.** Berisiko konflik, nanti dikerjain di
  branch sendiri.

## Soal basis kodenya

Ini dibangun di atas **Plane Community Edition v0.24.0**, lisensinya
**GNU AGPL-3.0**. Detail atribusi sama kewajiban lisensinya ada di
[NOTICE.md](NOTICE.md) dan [LICENSE.txt](LICENSE.txt).

Merek produk aslinya udah saya hapus dari tampilan, sistem ini bukan produk
vendor dan nggak dijual, jadi nampilin merek orang lain di dalamnya cuma bikin
bingung. Tapi **atribusi hukumnya tetap**: header copyright di file sumber, teks
lisensi, dan file NOTICE. Dua hal itu beda, dan yang kedua bukan hak saya buat
hapus.

Kalau kamu pakai ini lewat jaringan, AGPL pasal 13 tetap berlaku, mau dijual
atau enggak.

## Lisensi

GNU Affero General Public License v3.0. Lihat [LICENSE.txt](LICENSE.txt).
