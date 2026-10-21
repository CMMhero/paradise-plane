# Lanjutan rebrand permukaan terlihat user, sisa yang tidak tertangkap tahap 1.
#
# Menelusuri berkas lewat `git ls-files`, BUKAN Get-ChildItem berwildcard:
# nama folder react-router memakai kurung siku (`[workspaceSlug]`, `[anchor]`)
# dan PowerShell memperlakukannya sebagai kelas karakter, jadi berkas di dalamnya
# diam-diam tidak pernah kena. Sudah terjadi di tahap 1.
#
# Idempoten. Pakai: powershell -NoProfile -File paradise/bin/rebrand-visible2.ps1 [-WhatIf]
param([switch]$WhatIf)

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path (Join-Path $PSScriptRoot "..\.."))
$PRODUK = "Paradise Task Tracker"

$peta = [ordered]@{
  # --- nama pelaku aktivitas -----------------------------------------------
  # Sistem menulis dirinya sendiri di feed aktivitas ("Plane mengarsipkan...").
  # "Sistem" lebih jujur daripada nama produk: yang bertindak memang otomatisasi,
  # bukan orang.
  'customUserName || "Plane"'                    = 'customUserName || "Sistem"'
  '? "Plane" : undefined'                        = '? "Sistem" : undefined'
  'name={"Plane"}'                               = 'name={"Sistem"}'
  '"-intake") ? "Plane"'                         = '"-intake") ? "Sistem"'
  '<span className="text-gray font-medium">Plane</span>' = '<span className="text-gray font-medium">Sistem</span>'
  'activity.new_value === "archive" ? "Plane" : undefined' = 'activity.new_value === "archive" ? "Sistem" : undefined'

  # --- user bot hasil seed --------------------------------------------------
  'display_name="Plane",'                        = 'display_name="Sistem",'
  'first_name="Plane",'                          = 'first_name="Sistem",'

  # --- onboarding tour ------------------------------------------------------
  'The work item is the building block of the Plane. Most concepts in Plane are either associated with work items a' = "Work item adalah satuan kerja terkecil di $PRODUK. Hampir semua konsep lain bertaut dengan work item a"

  # --- God Mode: form autentikasi ------------------------------------------
  'Plane-provided details for Gitea'              = "Detail dari $PRODUK untuk Gitea"
  'Plane-provided details for GitHub'             = "Detail dari $PRODUK untuk GitHub"
  'Plane-provided details for GitLab'             = "Detail dari $PRODUK untuk GitLab"
  'Plane-provided details for Google'             = "Detail dari $PRODUK untuk Google"

  # --- alt text (dibaca pembaca layar) -------------------------------------
  'alt="Plane instance failure image"'            = 'alt="Gambar kegagalan instance"'
  'alt="Plane background pattern"'                = 'alt="Pola latar belakang"'

  # --- layar undangan workspace --------------------------------------------
  "organize different streams of work in your Plane account." = "organize different streams of work in your $PRODUK account."

  # --- intake ---------------------------------------------------------------
  'workspace: "Plane",'                           = 'workspace: "Sistem",'
}

# CATATAN sengaja TIDAK diubah:
#   - Teks telemetri di God Mode ("data dikirim ke pembuat perangkat lunak
#     (Plane)"), itu FAKTA soal ke mana data pergi. Mengaburkannya membuat
#     pernyataan privasi jadi menyesatkan.
#   - manifest.json "(berbasis Plane CE)", atribusi jujur atas basis kode.
#   - billing/comparison/plans.tsx & base-paid-plan-card.tsx, kode mati, rutenya
#     sudah dibuang (routes/core.ts:285) dan tak satu pun berkas mengimpornya.

$ubah = 0; $tot = 0
git ls-files | Where-Object { $_ -match '\.(tsx|ts|py|json)$' -and $_ -notmatch '^packages/i18n/src/locales/' } | ForEach-Object {
  $path = $_
  if (-not (Test-Path -LiteralPath $path)) { return }
  $asli = [System.IO.File]::ReadAllText((Resolve-Path -LiteralPath $path), [System.Text.Encoding]::UTF8)
  $c = $asli; $n = 0
  foreach ($k in $peta.Keys) {
    if ($c.Contains($k)) { $n += ([regex]::Matches($c, [regex]::Escape($k))).Count; $c = $c.Replace($k, $peta[$k]) }
  }
  if ($c -ne $asli) {
    $ubah++; $tot += $n
    if ($WhatIf) { "WHATIF  ({0,2}) {1}" -f $n, $path }
    else {
      [System.IO.File]::WriteAllText((Resolve-Path -LiteralPath $path), $c, (New-Object System.Text.UTF8Encoding $false))
      "UBAH    ({0,2}) {1}" -f $n, $path
    }
  }
}
"`n$ubah berkas, $tot penggantian."
