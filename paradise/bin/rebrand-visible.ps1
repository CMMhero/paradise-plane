# Buang merek Plane dari SEMUA yang bisa dilihat/diterima karyawan.
#
# Cakupan sengaja dibatasi pada permukaan yang terlihat user: subjek email,
# judul halaman & nama aplikasi, nama pelaku aktivitas, teks onboarding, dan
# label locale. README/package.json/storybook/seed demo/komentar DITINGGAL,
# tidak ada yang melihatnya, dan menyentuhnya memperbesar konflik saat sync
# upstream berikutnya tanpa manfaat.
#
# Peta di bawah berisi PASANGAN STRING PERSIS, bukan pola. Penggantian
# `\bPlane\b` menyeluruh akan merusak `@plane/...`, `plane-web`, `PlaneLogo`,
# dan `X-Plane-Signature` (header webhook yang dibaca sistem lain).
#
# Idempoten. Pakai: powershell -NoProfile -File paradise/bin/rebrand-visible.ps1 [-WhatIf]
param([switch]$WhatIf)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PRODUK = "Paradise Task Tracker"

# --- subjek email (dikirim ke 89 karyawan) ---------------------------------
$peta = [ordered]@{
  'A new password to your Plane account has been requested' = "Permintaan kata sandi baru untuk akun $PRODUK"
  'Your unique Plane login code is'                         = "Kode masuk $PRODUK Anda:"
  'You have been invited to a Plane project'                = "Anda diundang ke sebuah project di $PRODUK"
  'invited you to join {project.name} on Plane'             = "mengundang Anda ke {project.name} di $PRODUK"
  'has been activated on Plane'                             = "telah diaktifkan di $PRODUK"
  'has been deactivated on Plane'                           = "telah dinonaktifkan di $PRODUK"
  'Plane email address successfully updated'                = "Alamat email $PRODUK berhasil diperbarui"
  'on Plane"  # noqa: E501'                                 = "di $PRODUK`"  # noqa: E501"
  'Test email from Plane'                                   = "Email uji dari $PRODUK"
  'Email Notification from Plane'                           = "Notifikasi email dari $PRODUK"
  'This is a sample email notification sent from Plane application.' = "Ini contoh notifikasi email yang dikirim dari $PRODUK."

  # --- nama pelaku aktivitas: sistem menulis dirinya sendiri --------------
  'Plane has archived the issue'                            = "Sistem mengarsipkan work item ini"
  'Plane updated the state to '                             = "Sistem mengubah status menjadi "

  # --- judul halaman & nama aplikasi -------------------------------------
  'Plane | Simple, extensible, open-source project management tool.' = "$PRODUK | Manajemen proyek & issue internal kantor."
  'Sign up - Plane'                                         = "Masuk - $PRODUK"
  'Set Password - Plane'                                    = "Atur Kata Sandi - $PRODUK"
  'Reset Password - Plane'                                  = "Atur Ulang Kata Sandi - $PRODUK"
  'Forgot Password - Plane'                                 = "Lupa Kata Sandi - $PRODUK"
  'pageTitle + " - Plane"'                                  = "pageTitle + `" - $PRODUK`""
  'Made with Plane, an AI-powered work management platform with publishing capabilities.' = "Sistem internal PT Paradise Perkasa."

  # --- teks onboarding & auth (terlihat user baru) ------------------------
  'Sign up or log in to work with Plane work items and Pages.' = "Masuk untuk melihat dan mengomentari work item serta halaman."
  'Work in all dimensions.'                                 = "Selamat datang."
  'Welcome to Plane, '                                      = "Selamat datang di $PRODUK, "
  'glad that you decided to try out Plane'                  = "senang Anda bergabung"
  'Get more out of Plane.'                                  = "Kenali $PRODUK lebih jauh."
  'I agree to Plane marketing communications'               = "Saya bersedia menerima pemberitahuan dari kantor"
  "Let's set up Plane for how you work."                    = "Sesuaikan $PRODUK dengan cara Anda bekerja."
  'What brings you to Plane?'                               = "Apa yang Anda kerjakan di sini?"
  'use Plane to its potential.'                             = "memakai $PRODUK sepenuhnya."
  'This is how you will appear in Plane'                    = "Beginilah Anda akan terlihat di $PRODUK"
  'Connect with GitHub with your Plane workspace to sync project work items.' = "Hubungkan GitHub ke workspace $PRODUK untuk menyinkronkan work item."
  'Connect with Slack with your Plane workspace to sync project work items.'  = "Hubungkan Slack ke workspace $PRODUK untuk menyinkronkan work item."

  # --- locale -------------------------------------------------------------
  '"pi_chat": "Plane AI"'                                   = '"pi_chat": "Asisten AI"'
  '"plane_pro": "Plane Pro"'                                = '"plane_pro": "Paket Pro"'
}

# Berkas yang boleh disentuh. Daftar putih, bukan sapuan repo, supaya README,
# storybook, dan seed demo benar-benar tidak ikut terbawa.
$sasaran = @(
  "apps\api\plane\bgtasks\*.py"
  "apps\api\plane\license\api\views\configuration.py"
  "apps\api\plane\db\management\commands\test_email.py"
  "apps\web\app\layout.tsx"
  "apps\web\app\(all)\sign-up\layout.tsx"
  "apps\web\app\(all)\accounts\*\layout.tsx"
  "apps\web\core\components\core\page-title.tsx"
  "apps\web\core\components\auth-screens\header.tsx"
  "apps\web\core\components\account\auth-forms\auth-header.tsx"
  "apps\web\core\components\onboarding\*.tsx"
  "apps\web\core\components\onboarding\steps\*\*.tsx"
  "apps\web\core\components\integration\single-integration-card.tsx"
  "apps\web\ce\components\onboarding\tour\*.tsx"
  "apps\space\app\issues\[anchor]\layout.tsx"
  "apps\space\components\account\auth-forms\auth-header.tsx"
  "packages\i18n\src\locales\*\common.json"
  "packages\i18n\src\locales\*\navigation.json"
)

$ubah = 0; $totalGanti = 0
foreach ($pola in $sasaran) {
  Get-ChildItem (Join-Path $root $pola) -ErrorAction SilentlyContinue | ForEach-Object {
    $path = $_.FullName
    # UTF-8 eksplisit, `Get-Content -Raw` di PS 5.1 membaca UTF-8 tanpa BOM
    # sebagai ANSI dan merusak karakter non-ASCII saat ditulis balik.
    $asli = [System.IO.File]::ReadAllText($path, [System.Text.Encoding]::UTF8)
    $c = $asli
    $n = 0
    foreach ($k in $peta.Keys) {
      if ($c.Contains($k)) { $n += ([regex]::Matches($c, [regex]::Escape($k))).Count; $c = $c.Replace($k, $peta[$k]) }
    }
    if ($c -ne $asli) {
      $ubah++; $totalGanti += $n
      $rel = $path.Replace($root, '')
      if ($WhatIf) { "WHATIF  ({0,2}) {1}" -f $n, $rel }
      else {
        [System.IO.File]::WriteAllText($path, $c, (New-Object System.Text.UTF8Encoding $false))
        "UBAH    ({0,2}) {1}" -f $n, $rel
      }
    }
  }
}
"`n$ubah berkas, $totalGanti penggantian."
