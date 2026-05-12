<#
.SYNOPSIS
    Yeni musteri icin Obsidian Vault klasoru olusturur (Drive senkron yoluna).

.PARAMETER ClientId
    Kucuk harf, rakam, tire; ornek: akme-tekstil

.EXAMPLE
    .\scripts\new-client.ps1 -ClientId "akme-tekstil"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ClientId
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($ClientId -notmatch '^[a-z0-9][a-z0-9_-]{1,63}$') {
    Write-Error "Gecersiz ClientId. Ornek: akme-tekstil"
}

$envFile = Join-Path $root '.env'
if (-not (Test-Path $envFile)) { Write-Error ".env bulunamadi" }

$vaultHostLine = (Get-Content $envFile | Select-String '^VAULT_BASE_PATH_HOST=').Line
if (-not $vaultHostLine) { Write-Error "VAULT_BASE_PATH_HOST .env icinde yok" }
$vaultBase = ($vaultHostLine -split '=', 2)[1].Trim().Trim('"')

$dest = Join-Path $vaultBase $ClientId
if (Test-Path $dest) {
    Write-Host "Vault zaten var: $dest" -ForegroundColor Yellow
    exit 0
}

$template = Join-Path $root 'scripts\templates\vault'
if (-not (Test-Path $template)) { Write-Error "Sablon yok: $template" }

New-Item -ItemType Directory -Force -Path $dest | Out-Null
Get-ChildItem -Path $template -Force | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $dest $_.Name) -Recurse -Force
}

$readmeClient = @"
# $ClientId - Ajans Vault

Bu klasor Google Drive ile senkron; Obsidian ile acabilirsiniz.
Watcher: Agency API container icinde /vaults altinda bu klasoru tarar.

Olusturulma: $(Get-Date -Format 'yyyy-MM-dd HH:mm')
"@
$readmeOut = Join-Path $dest 'README.md'
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($readmeOut, $readmeClient, $enc)

Write-Host "Vault olusturuldu: $dest" -ForegroundColor Green
Write-Host "Sonraki: Docker stack'i yeniden baslatin (volume mount), sonra GET http://127.0.0.1:8010/vault/status" -ForegroundColor Cyan
