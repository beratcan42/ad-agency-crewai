<#
.SYNOPSIS
    Postgres + Vault + Redis yedek alir.

.PARAMETER BackupRoot
    Yedek klasoru (varsayilan: C:\AjansBackup)

.EXAMPLE
    .\scripts\backup.ps1
    .\scripts\backup.ps1 -BackupRoot "E:\Backups\Ajans"
#>

[CmdletBinding()]
param(
    [string]$BackupRoot = "C:\AjansBackup",
    [int]$KeepDays = 30
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$dest = Join-Path $BackupRoot "backup-$ts"
New-Item -ItemType Directory -Path $dest -Force | Out-Null

Write-Host "Yedek aliniyor: $dest" -ForegroundColor Cyan

# 1) Postgres dump
Write-Host "  Postgres dump..." -ForegroundColor White
$pgUser = ((Get-Content "$root\.env" | Select-String "^POSTGRES_USER=").Line -split '=', 2)[1]
docker exec adagency-postgres pg_dumpall -U $pgUser | Out-File "$dest\postgres-all.sql" -Encoding UTF8

# 2) Vault klasoru
$vaultPath = ((Get-Content "$root\.env" | Select-String "^VAULT_BASE_PATH_HOST=").Line -split '=', 2)[1]
if ($vaultPath -and (Test-Path $vaultPath)) {
    Write-Host "  Vault: $vaultPath -> vaults.zip" -ForegroundColor White
    Compress-Archive -Path "$vaultPath\*" -DestinationPath "$dest\vaults.zip" -ErrorAction SilentlyContinue
}

# 3) Staging
if (Test-Path "$root\data\staging") {
    Write-Host "  Staging..." -ForegroundColor White
    Compress-Archive -Path "$root\data\staging\*" -DestinationPath "$dest\staging.zip" -ErrorAction SilentlyContinue
}

# 4) Redis snapshot
Write-Host "  Redis BGSAVE..." -ForegroundColor White
$rdPass = ((Get-Content "$root\.env" | Select-String "^REDIS_PASSWORD=").Line -split '=', 2)[1]
docker exec adagency-redis redis-cli -a $rdPass --no-auth-warning BGSAVE | Out-Null
Start-Sleep -Seconds 3
docker cp adagency-redis:/data/dump.rdb "$dest\redis-dump.rdb"

# 5) .env (sifrelenmis - opsiyonel)
Copy-Item "$root\.env" "$dest\.env.backup"

# 6) Eski yedekleri temizle
Write-Host "  Eski yedekler temizleniyor ($KeepDays gunden eski)..." -ForegroundColor White
if (Test-Path $BackupRoot) {
    Get-ChildItem $BackupRoot -Directory | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$KeepDays) } | Remove-Item -Recurse -Force
}

$sizeMB = [math]::Round((Get-ChildItem $dest -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
Write-Host ""
Write-Host "Yedekleme tamamlandi: $dest ($sizeMB MB)" -ForegroundColor Green
