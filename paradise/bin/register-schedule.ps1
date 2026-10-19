# Daftarkan scheduled task backup DB + healthcheck. Paradise Task Tracker.
# Jalankan sekali: klik-kanan > Run with PowerShell, ATAU dari PowerShell:
#   powershell -ExecutionPolicy Bypass -File "paradise\bin\register-schedule.ps1"
#
# Tidak butuh admin. CATATAN: file ini sengaja MURNI ASCII - PowerShell 5.1
# membaca .ps1 tanpa BOM sebagai ANSI, jadi satu em-dash saja bikin parser error.
#
# Pendaftaran lewat `schtasks /xml`, BUKAN Register-ScheduledTask: cmdlet itu
# lewat jalur CIM yang minta elevasi di mesin ini (HRESULT 0x80070005), sedangkan
# schtasks.exe jalan sebagai user biasa. XML juga bikin dua trigger dalam satu
# task jadi mungkin, tanpa quoting bertingkat di /tr.

$ErrorActionPreference = "Stop"

$bash = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $bash)) { throw "Git Bash tidak ditemukan di $bash - sesuaikan path." }

# Root repo = dua level di atas file ini, dalam format path Git Bash (/d/...)
$repoWin = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$drive = $repoWin.Substring(0,1).ToLower()
$repo = "/$drive" + $repoWin.Substring(2).Replace("\","/")
$user = "$env:USERDOMAIN\$env:USERNAME"

function New-TaskXml {
    param(
        [string]$Description,
        [string]$Arguments,
        [string]$TriggersXml,
        [string]$TimeLimit,   # ISO 8601, mis. PT30M
        [string]$Enabled = "true"
    )
    $esc = [System.Security.SecurityElement]::Escape($Arguments)
    @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>$Description</Description>
  </RegistrationInfo>
  <Triggers>
$TriggersXml
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$user</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>$TimeLimit</ExecutionTimeLimit>
    <Enabled>$Enabled</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$bash</Command>
      <Arguments>$esc</Arguments>
    </Exec>
  </Actions>
</Task>
"@
}

function Register-FromXml {
    param([string]$TaskName, [string]$Xml)
    $tmp = Join-Path $env:TEMP ("paradise-task-" + [guid]::NewGuid().ToString("N") + ".xml")
    # schtasks butuh UTF-16 sesuai deklarasi XML di atas.
    $Xml | Out-File -FilePath $tmp -Encoding Unicode
    try {
        $out = & schtasks /create /tn $TaskName /xml $tmp /f 2>&1
        if ($LASTEXITCODE -ne 0) { throw "schtasks gagal untuk '$TaskName': $out" }
    } finally {
        Remove-Item $tmp -ErrorAction SilentlyContinue
    }
}

# --- Task 1: Backup DB ---
# Dua trigger: 02:00 kalau mesin nyala semalaman, DAN saat logon (delay 5 menit
# supaya Docker Desktop sempat siap). Di laptop yang dimatikan malam hari,
# trigger 02:00 saja tidak akan pernah jalan - backup-db.sh butuh container
# plane-db hidup, kalau tidak ia exit 1 dan gagalnya cuma masuk backup.log.
$bkArgs = "-lc ""cd '$repo' && COMPOSE_FILE=docker-compose-local.yml bash paradise/bin/backup-db.sh >> paradise/backup.log 2>&1"""
$bkTriggers = @"
    <CalendarTrigger>
      <StartBoundary>2026-01-01T02:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
    </CalendarTrigger>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>$user</UserId>
      <Delay>PT5M</Delay>
    </LogonTrigger>
"@
Register-FromXml "Paradise - Backup DB" (New-TaskXml `
    -Description "Backup PostgreSQL harian + retensi 14 hari" `
    -Arguments $bkArgs -TriggersXml $bkTriggers -TimeLimit "PT30M")
Write-Host "OK: 'Paradise - Backup DB' terdaftar (02:00 + saat logon +5m)." -ForegroundColor Green

# --- Task 2: Healthcheck tiap 30 menit --- DIDAFTARKAN NONAKTIF ---
# WEB_URL harus 4000 - `react-router dev --port 4000`, bukan 3000. Port salah =
# healthcheck selalu lapor "ADA MASALAH" (HTTP 000) alias alarm palsu tiap 30 menit.
#
# Didaftarkan NONAKTIF (keputusan 2026-07-30). Alasannya: frontend cuma hidup
# kalau ada yang menjalankan `pnpm dev` manual, jadi task ini akan melapor
# "ADA MASALAH" hampir sepanjang waktu. Alarm yang salah terus akan diabaikan,
# dan itu lebih buruk daripada tidak ada alarm.
#
# NYALAKAN saat server produksi sudah ada dan layanannya memang hidup 24/7:
#   schtasks /change /tn "Paradise - Healthcheck" /enable
# Skripnya sendiri tetap bisa dipakai manual: bash paradise/bin/healthcheck.sh
$hcArgs = "-lc ""cd '$repo' && COMPOSE_FILE=docker-compose-local.yml WEB_URL=http://localhost:4000 bash paradise/bin/healthcheck.sh >> paradise/healthcheck.log 2>&1"""
$hcTriggers = @"
    <LogonTrigger>
      <Enabled>true</Enabled>
      <UserId>$user</UserId>
      <Delay>PT5M</Delay>
      <Repetition>
        <Interval>PT30M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </LogonTrigger>
"@
Register-FromXml "Paradise - Healthcheck" (New-TaskXml `
    -Description "Cek kesehatan layanan tiap 30 menit - nonaktif sampai ada server produksi" `
    -Arguments $hcArgs -TriggersXml $hcTriggers -TimeLimit "PT5M" -Enabled "false")
Write-Host "OK: 'Paradise - Healthcheck' terdaftar NONAKTIF (sengaja)." -ForegroundColor Yellow
Write-Host "    Nyalakan saat produksi siap: schtasks /change /tn ""Paradise - Healthcheck"" /enable" -ForegroundColor DarkGray

Write-Host ""
Get-ScheduledTask -TaskName "Paradise*" | Select-Object TaskName, State | Format-Table -AutoSize
Write-Host "Selesai. Tes backup sekarang:  schtasks /run /tn ""Paradise - Backup DB""" -ForegroundColor Cyan
