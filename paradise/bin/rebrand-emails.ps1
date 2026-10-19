# Buang merek & saluran vendor dari template email, pasang tanda Paradise Task Tracker.
#
# KENAPA TEKS, BUKAN GAMBAR
# Server ini LAN-only di balik NAT, jadi URL gambar apa pun, termasuk logo
# yang di-host sendiri, TIDAK bisa dijangkau Gmail/Outlook karyawan
# yang membuka email di luar kantor. Teks HTML selalu ter-render. Bonus: memuat
# logo dari media.docs.plane.so berarti setiap email yang dibuka mengirim ping
# ke server vendor. Itu kebocoran, bukan sekadar soal merek.
#
# KENAPA TIDAK ADA POLA `.*?` DI SINI
# Percobaan pertama membuang tautan sosial dengan `<a ...>.*?</a>` dan MERUSAK
# 3 template: template mail-builder ini punya `<a>` tak tertutup bawaan upstream
# (project_invitation sudah 9 buka / 5 tutup sebelum disentuh), jadi `</a>`
# pertama sesudah pola BUKAN pasangannya, pencocokan melompati beberapa `<td>`
# dan melahapnya (46/46 sel jadi 35/38). Sekarang semua operasi bersifat
# self-contained: mengganti tag void (`<img>`), mengganti nilai atribut, atau
# mengganti satu baris `<p>` yang sudah seimbang. Tidak ada yang menjangkau
# melewati batas tag.
#
# Idempoten: dijalankan ulang tidak menggandakan apa pun.
# Pakai:  powershell -NoProfile -File paradise/bin/rebrand-emails.ps1 [-WhatIf]
param([switch]$WhatIf)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..\apps\api\templates\emails")).Path

$MARK    = "Paradise Task Tracker"
$PRODUK  = "Paradise Task Tracker"
$KANTOR  = "PT Paradise Perkasa"

function New-Wordmark([string]$warna) {
  # 16px, bukan 20px: pada keluarga template mailinblue slot logo cuma selebar
  # 120-150px, dan 20px bold membuat "Paradise Task Tracker" pecah jadi 3 baris.
  '<div style="font-family: Arial, Helvetica, sans-serif; font-size: 16px; ' +
  "font-weight: bold; letter-spacing: 0.2px; color: $warna; " +
  "text-align: center; line-height: 1.3;`">$PRODUK</div>"
}

# Pengganti paragraf pemasaran vendor: aslinya menyuruh karyawan melaporkan bug
# ke Forum & GitHub milik vendor, saluran yang tidak melayani kantor ini.
#
# String yang IKUT DITULIS ke berkas wajib ASCII murni. Skrip .ps1 ini tersimpan
# UTF-8 tanpa BOM, dan Windows PowerShell 5.1 membaca berkas skrip semacam itu
# dengan codepage ANSI, jadi em-dash "—" di sini keluar sebagai "â€”" di HTML.
# Sudah terjadi sekali. Menambah BOM juga menyembuhkan, tapi BOM gampang hilang
# saat berkas disimpan ulang editor lain; ASCII tidak bisa rusak.
$ParagrafInternal =
  '<p style="margin: 0"> <span style=" font-size: 12px; " >Catatan: ini sistem ' +
  "internal $KANTOR. Kalau menemukan kendala atau punya usulan, hubungi tim IT " +
  'lewat kanal internal, bukan lewat kanal publik mana pun.</span > </p>'

$ubah = 0
Get-ChildItem $root -Recurse -Filter *.html | ForEach-Object {
  $path = $_.FullName
  # UTF-8 EKSPLISIT. `Get-Content -Raw` di Windows PowerShell 5.1 membaca berkas
  # UTF-8 tanpa BOM memakai codepage ANSI sistem; ditulis balik sebagai UTF-8
  # hasilnya dobel-encode ("doesn’t" -> "doesnâ€™t"). Terjadi sungguhan di sini
  # dan baru ketahuan waktu template dibuka di browser, bukan dari uji teks.
  $asli = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
  $c = $asli

  # 1) <img> logo vendor -> wordmark teks.
  #
  #    Warna ditentukan dari LATAR YANG DIUKUR di tiap template, bukan ditebak
  #    dari nama berkas logo. Nama itu menunjuk VARIAN HEADER, bukan warna tinta:
  #
  #      new-logo-dark.png  -> header GELAP  (<td background-color:#000000>)
  #      new-logo-white.png -> header TERANG (<body bgcolor="#ffffff">, #f8f9fa)
  #
  #    Menebak dari nama (dark=tinta gelap) menaruh teks #1f2937 di atas hitam
  #    pada 5 template: tak terbaca sama sekali. Terbukti lewat pembacaan latar
  #    di sekitar tiap titik sisip, bukan lewat penalaran atas nama berkas.
  $c = [regex]::Replace($c, '<img[^>]*media\.docs\.plane\.so/logo/new-logo-dark\.png[^>]*>',  (New-Wordmark '#ffffff'))
  $c = [regex]::Replace($c, '<img[^>]*media\.docs\.plane\.so/logo/new-logo-white\.png[^>]*>', (New-Wordmark '#1f2937'))

  # 2) Ikon sosial vendor dibuang (tag void, aman). Anchor pembungkusnya
  #    ditinggalkan kosong pada langkah 3, merombak <td>-nya jauh lebih rawan.
  #    Daftar ikon lengkap: twitter, linkedin, github, website. Disajikan dari
  #    `{{ current_site }}/static/logos/`, jadi tidak tertangkap penyaringan
  #    berbasis host, ketahuan justru dari kotak gambar rusak di screenshot.
  #    JANGAN sentuh <img> ber-`avatar_url`: itu foto profil user sungguhan.
  $c = [regex]::Replace($c, '<img[^>]*(?:twitter_32px|linkedin_32px|github_32px|website_32px)[^>]*>', '')

  # 3) Paragraf pemasaran vendor -> catatan internal.
  #    Ketiganya blok <p> TANPA <p> bersarang, jadi `</p>` pertama sesudah teks
  #    pembuka memang penutupnya. Ditemukan lewat MELIHAT email di browser,
  #    ketiganya lolos pencarian teks karena tidak memuat kata "Plane".
  #    Jarak antar-tag ditulis `\s+`/`\s*`, BUKAN spasi harfiah: sebagian
  #    template termampat satu baris, sebagian lagi memecah <p> dan <span> ke
  #    baris terpisah dengan indentasi. Pola berspasi harfiah hanya mengenai
  #    yang termampat dan diam-diam melewatkan sisanya.
  $c = [regex]::Replace($c, '<p style="margin: 0">\s*<span style="\s*font-size: 12px;\s*"\s*>Note: Plane is still in its early days.*?</p>',
                        $ParagrafInternal, 'Singleline')
  #    "Despite our popularity, we are humbly early-stage...", ajakan vendor
  #    supaya pembaca mengirim feature request & melihat public roadmap mereka.
  $c = [regex]::Replace($c, '<p style="margin: 0">\s*<span style="font-size: 13px"\s*>Despite our popularity.*?</p>',
                        $ParagrafInternal, 'Singleline')
  #    "Proudly made on Planet Earth", tagline vendor.
  $c = [regex]::Replace($c, '<p style="\s*margin: 0;\s*font-size: 14px;\s*"\s*>\s*Proudly made on.*?</p>',
                        '<p style="margin: 0; font-size: 14px;">Sistem internal ' + $KANTOR + '.</p>', 'Singleline')

  # 3b) Gambar dari host pihak ketiga: ikon sosial/hiasan vendor & mail-builder.
  #     Tidak satu pun melayani kantor ini, dan tiap email yang dibuka memberi
  #     tahu server mereka. Tag void, aman dibuang.
  $c = [regex]::Replace($c, '<img[^>]*(?:plane-marketing\.s3[^>]*|creative-assets\.mailinblue\.com[^>]*|ik\.imagekit\.io[^>]*)>', '')

  # 4) Tautan vendor dinetralkan (ganti NILAI atribut saja, struktur utuh).
  #    CATATAN: daftar ini hasil MENDATA seluruh host di template, bukan menebak
  #    pola. Tebakan awal ('plane.so|planepowers') melewatkan `plane.sh` dan
  #    `github.com/makeplane` polos. `www.w3.org` SENGAJA tidak disentuh, itu
  #    deklarasi namespace VML yang dibutuhkan Outlook, bukan merek.
  foreach ($u in @(
    'https://x\.com/planepowers',
    'https://www\.linkedin\.com/company/planepowers/?',
    'https://forum\.plane\.so',
    'https://github\.com/makeplane(?:/plane)?',
    'https://plane\.sh[^"''\s]*',
    'https://plane\.so/?'
  )) { $c = [regex]::Replace($c, $u, '#') }

  # 5) Nama & atribut bermerek vendor. WAJIB sebelum langkah 6, kalau tidak
  #    "Plane Software, Inc." ikut jadi "Paradise Task Tracker Software, Inc.".
  $c = $c -replace 'Plane Software, Inc\.', $KANTOR
  $c = $c -replace 'Team Plane', "Tim IT $KANTOR"
  $c = $c -replace 'title="@planepowers"', ''

  # 6) Sisa kata "Plane" di teks tampak: judul, "project on Plane",
  #    tombol "Go to Plane", "your Plane instance".
  $c = [regex]::Replace($c, '\bPlane\b', $PRODUK)
  #    Judul komentar HTML memakai huruf besar ("<!-- PLANE LOGIN CODE EMAIL -->").
  #    Tak terlihat user, tapi ikut terbawa kalau source disalin.
  $c = [regex]::Replace($c, '\bPLANE\b', 'PARADISE TASK TRACKER')

  # 7) Tanda produksi sebelum </body>, sekali saja.
  if ($c -notmatch [regex]::Escape($MARK) -and $c -match '</body>') {
    $c = $c -replace '</body>', ((
      '<div style="font-family: Arial, Helvetica, sans-serif; font-size: 11px; ' +
      'color: #9ca3af; text-align: center; padding: 16px 8px 24px 8px;">' +
      "$MARK</div>") + "`n</body>")
  }

  if ($c -ne $asli) {
    $ubah++
    if ($WhatIf) { "WHATIF  $($path.Replace($root,''))" }
    else {
      [System.IO.File]::WriteAllText($path, $c, (New-Object System.Text.UTF8Encoding $false))
      "UBAH    $($path.Replace($root,''))"
    }
  }
}
"`n$ubah berkas berubah."
