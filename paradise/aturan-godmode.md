# Aturan God Mode: cara menambah satu aturan

Kontrak untuk siapa pun (orang atau agen) yang memindahkan aturan yang masih
terkunci di kode ke God Mode > Work rules > All rules. Inventarisnya ada di
`.rules-inventory.local.md` (lokal, tidak di-commit), area A sampai G.

## Bentuknya

- **Registri**: `apps/api/plane/utils/aturan/`. Satu `Rule` per aturan,
  dideklarasikan di `area_<nama>.py` dalam tuple `ATURAN`. Berkas area ditemukan
  sendiri (pindai nama modul `area_*`), jadi tidak ada daftar bersama yang harus
  disunting.
- **Area -> berkas**: A `area_visibilitas.py`, B `area_tugas.py`, C
  `area_tampilan.py`, D `area_notifikasi.py`, E `area_obrolan.py`, F
  `area_keamanan.py`, G `area_keputusan.py`. Cermin web-nya di
  `packages/constants/src/aturan/area-<nama>.ts` dengan nama yang sama.
- **Penyimpanan**: baris `InstanceConfiguration` dengan kunci yang sama dengan
  `key`. Bawaan tampilan untuk akun baru (`member_default="tampilan.<kolom>"`)
  disimpan di PARADISE_BAWAAN_MEMBER, bagian `tampilan`.
- **Pembaca**: `aturan.get(key)`, `aturan.get_bool`, `aturan.get_int` (int dan
  level), `aturan.get_choice`, `aturan.get_list`. Nilai rusak di database jatuh
  ke `default`, tidak pernah melempar galat. Kunci tak terdaftar = `KeyError`.
- **Cache**: potret semua baris registri per proses, satu kueri, umur 5 detik.
  Proses yang menulis langsung membuangnya (sinyal `post_save`/`post_delete`).
  `applies="live"` berarti berlaku dalam 5 detik di setiap proses.
- **Endpoint**: `GET/PATCH /api/instances/rules/`, `POST /api/instances/rules/reset/`.
  Aturan `risk="high"` hanya berubah (dan kembali ke bawaan) dengan frasa
  `CHANGE RULES`. Setiap perubahan tercatat di Logs > Audit log sebagai `Rule: KEY`.
  `PATCH /api/instances/configurations/` menolak kunci registri.
- **Web**: aturan `web=True` dikirim di `config.paradise_rules` pada
  `/api/instances/`. apps/web membacanya lewat `useAturan().get("KEY")`, bertipe,
  dengan bawaan dari `@plane/constants`.
- **Layar God Mode** membaca semuanya dari API. Aturan baru tidak butuh baris di
  apps/admin: label, bantuan, pilihan, batas, dan risiko datang dari `Rule`.

## Enam langkah

1. **Deklarasikan** di berkas areamu. Konstanta kunci di atas, lalu `Rule` di
   `ATURAN`. Impor hanya dari `plane.utils.aturan.jenis` (bukan dari
   `plane.utils.aturan`: paketnya sedang dimuat saat berkas area diimpor).

   ```python
   from plane.utils.aturan.jenis import LEVEL, TINGGI, Rule

   APPROVER_MIN_LEVEL = "APPROVER_MIN_LEVEL"

   ATURAN = (
       Rule(
           key=APPROVER_MIN_LEVEL,
           kind=LEVEL,
           default=20,
           choices=(20, 30),
           group="approvals",
           label="Lowest level that can approve",
           help="Finished work waits for someone at this level or above ...",
           risk=TINGGI,
           kep="P29",
       ),
   )
   ```

   - `key`: UPPER_SNAKE, stabil selamanya (itu kunci baris di database). Tidak
     boleh sama dengan kunci registri lama (`saklar_instance.py`,
     `setelan_instance.py`); impor gagal kalau bentrok.
   - `kind`: `BOOL`, `INT` (wajib `min`, `max`), `CHOICE` (`choices` berisi
     `(nilai, "Label")`), `TEXT` (`max_length`, bawaan 200), `LEVEL` (`choices`
     berisi angka jenjang; labelnya otomatis), `KEY_LIST` (`choices` berisi
     `(kunci, "Label")`; nilainya tuple kunci).
   - `default`: **persis perilaku hari ini.** Ini bukan tempat memperbaiki
     perilaku; perbaikan adalah keputusan pemilik yang terpisah.
   - `group`: salah satu topik di `aturan/grup.py`. Topik sudah lengkap untuk
     ketujuh area; menambah topik baru = satu baris di berkas bersama itu, jadi
     hindari kalau bisa.
   - `label` dan `help`: bahasa Inggris (KEP-46), kalimat pendek, tanpa tanda
     pisah panjang. `help` menyebut siapa yang terkena dan apa yang tidak berubah.
   - `risk`: `high` kalau nilai salah membuka data atau membuka izin ubah;
     `medium` kalau mengubah siapa diberi tahu, dihitung, atau data yang ditulis;
     `low` kalau tampilan saja. Ikuti kolom Risk di inventaris.
   - `applies`: `LIVE` (bawaan), `NEXT_RUN` (dibaca task terjadwal), atau
     `RESTART` (dibaca sekali saat proses mulai; hindari).
   - `web=True` hanya kalau apps/web perlu nilainya untuk TAMPILAN. Tidak pernah
     untuk rahasia. Untuk aturan web, tulis `key=` dan `default=<literal>` masing
     masing di satu baris (tes TS membaca sumber Python).
   - `kep`: rujukan keputusan (`"KEP-83"`) kalau ada.

2. **Pakai di server, di satu tempat.** Ganti konstanta atau perbandingan yang
   terkunci dengan `aturan.get_*` di fungsi yang memang memutuskan (resolver,
   gerbang izin, task). Untuk aturan izin dan cakupan data, **penegakannya wajib
   di API**. Web boleh menyembunyikan tombol, tidak pernah jadi satu-satunya
   penjaga, dan tidak pernah menghitung ulang izin dari nilai aturan: izin per
   orang tetap datang dari API (`boleh_*`, `bisa_*`).

3. **Cermin web** (hanya kalau `web=True`): tambahkan kunci yang sama ke
   `ATURAN_WEB_<AREA>` di `packages/constants/src/aturan/area-<nama>.ts` dengan
   `boolWeb`, `angkaWeb`, `teksWeb`, `pilihanWeb`, atau `daftarWeb`. Pakai di
   komponen `observer`:

   ```ts
   const { get } = useAturan();
   const tersembunyi = get("DIRECTOR_SIDEBAR_HIDES"); // bertipe, bawaan sebelum config datang
   ```

   `index.ts` di folder itu sudah mendaftarkan ketujuh area; jangan disunting.

4. **Bawaan tampilan untuk akun baru** (area C): pakai
   `member_default="tampilan.<kolom>"`. Kalau nilainya hidup di `Profile.theme`,
   isi juga `profile_theme_key` dan `profile_values` (peta setiap nilai aturan ke
   nilai yang disimpan di profil). Akun baru mendapat nilainya hanya kalau
   berbeda dari `default` (kunci yang tidak ada dibaca web sebagai default), dan
   tombol "Apply to existing members" yang sudah ada (bagian `tampilan`)
   menuliskannya ke semua akun. Nilai yang tinggal di localStorage butuh
   penerapan sendiri di web; tulis itu di PR, jangan membuat jalur bawaan kedua.
   Layar All rules sudah menampilkan aturan ini lengkap dengan tombol "Apply to
   all members". Baris di People > New member defaults tidak wajib (contohnya
   ACTIVITY_NEWEST_FIRST); kalau ditambah, itu satu berkas bersama.

5. **Tes, pola yang sama untuk setiap aturan:**
   - _Bawaan tidak berubah_: tanpa baris database, perilaku yang diuji sama
     dengan sebelum aturannya ada (jalankan tes lama yang menyentuh perilaku itu,
     dan tambahkan satu yang eksplisit).
   - _Nilai lain berlaku_: tulis baris `InstanceConfiguration` (atau PATCH lewat
     endpoint) lalu buktikan respons API berubah. Contoh:
     `tests/contract/app/test_aturan_penyetuju_app.py`,
     `tests/unit/views/test_chat_sematan.py::test_batas_sematan_dari_god_mode`.
   - Pagar registri (`tests/unit/utils/test_aturan_registri.py`) dan endpoint
     (`tests/contract/app/test_aturan_god_mode.py`) otomatis meliput aturan baru:
     metadata lengkap, bawaan lolos validator, aturan `high` butuh frasa,
     `paradise_rules` hanya memuat aturan web.
   - Web: `packages/constants/src/aturan/aturan.test.ts` gagal kalau kunci,
     bawaan, atau pilihan web berbeda dari Python. Layar admin punya tes yang
     membaca `area_*.py` dan memastikan setiap aturan tampil.
   - Jangan pakai `monkeypatch.setattr` pada konstanta lama; tulis barisnya.
     Fixture autouse di `plane/tests/conftest.py` membuang cache antar tes.

6. **Rapikan dan catat**: hapus konstanta lama yang tergantikan (jangan
   biarkan dua sumber), perbarui komentar di tempat pemakaiannya, dan jalankan
   cek per paket yang disentuh. Tidak ada migrasi untuk aturan baru (barisnya
   baru dibuat saat Super Admin mengubahnya). Tidak ada env baru (KEP-48).

## Area A: yang sengaja tidak dipindah

- **A1 ambang jangkauan seluruh organisasi (35 atau 40): ditunda.** Angka 35 bukan
  satu perbandingan, melainkan bentuk data. `db/direktur.py` menjadikan setiap orang
  jenjang 35 ke atas anggota role 20 di SEMUA project (tidak pernah dicabut),
  `db/penempatan.py` dan editor God Mode (`menjangkauSeluruhOrganisasi` di
  apps/admin) menolak memberi sekretaris tempat. Pilihan 40 akan membuat sekretaris
  tetap admin di semua project, tanpa wewenang mengawasi dan tanpa cara
  menempatkannya: pelebaran yang menyamar sebagai penyempitan. Butuh keputusan
  pemilik soal nasib keanggotaan itu (cabut? biarkan?) dan perubahan editor dulu.
- **A2 cakupan pengawasan per jenjang: ditunda.** `divisi_diawasi` sudah datang dari
  penempatan (departemen, divisi, cabang); satu-satunya tuas jenjang yang punya
  alternatif nyata adalah A1 (di atas) dan jenjang penyetuju (APPROVER_MIN_LEVEL,
  area B). Pilihan bernama lain akan berupa no-op atau memberi wewenang lintas unit
  yang tidak ada di data. Resolver ini juga milik gerbang area B.
- **A8 "direktur" di web = 40, di API = 35 ke atas:** dua definisi tetap ada.
  Teks bantuan setiap aturan menyebut jenjangnya dengan angka, dan
  DIRECTOR_MENUS_APPLY_TO memilih apakah aturan menu juga berlaku untuk sekretaris.
- **A11** mengikuti aturan penyetuju (tanpa kunci sendiri), **A12** proyeksi
  permintaan lintas divisi tetap di kode (batas kebocoran data, KEP-02), **A14**
  sudah ada di Rules > Projects.
- **A7** hanya tab: endpoint Analytics dan Division dashboard tetap melayani anggota
  mana pun. Kalau pemilik ingin itu jadi kontrol akses, API harus menjaganya dulu.

## Yang belum dipindah

Registri lama (`SAKLAR_BAWAAN`/`_MODUL_BAWAAN`, `SETELAN_ANGKA`/`SETELAN_PILIHAN`,
`SETELAN_TEKS`) tetap berdiri dengan pembaca dan endpoint lamanya
(`/api/instances/settings/`). Layar All rules menampilkannya baca-saja dengan
tautan ke tab masing-masing. Memindahkannya ke registri ini adalah pekerjaan
terpisah satu orang sesudah migrasi area selesai: kuncinya dan pembacanya
(`saklar_aktif`, `setelan_angka`, `setelan_teks`) dipakai di puluhan tempat dan
membawa benih env, jadi jangan disentuh paralel. Agen area hanya MENAMBAH aturan.
