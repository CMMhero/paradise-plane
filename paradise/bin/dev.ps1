# Dev environment Paradise Task Tracker (build dari source) - Windows.
# Wrapper tipis di atas docker-compose-local.yml. Jalankan dari root repo.
#   .\paradise\bin\dev.ps1 up|down|logs|rebuild|ps
param([string]$cmd = "up", [string]$svc = "")
$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..")   # -> root repo
if (-not (Test-Path .env)) {
  Write-Error "ERROR: .env tidak ada. Jalankan: cp paradise/.env.example .env"; exit 1
}
$compose = @("compose", "-f", "docker-compose-local.yml")

switch ($cmd) {
  "up"      { docker @compose up -d --build }
  "down"    { docker @compose down }
  "logs"    { docker @compose logs -f --tail=100 $svc }
  "rebuild" { docker @compose up -d --build --force-recreate $svc }
  "ps"      { docker @compose ps }
  default   { Write-Host "usage: dev.ps1 up|down|logs|rebuild|ps"; exit 2 }
}
