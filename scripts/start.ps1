<#
.SYNOPSIS
    Stack'i baslat (kontrollu, health check'li).

.DESCRIPTION
    Belirli bir profil veya hepsini baslatir, container'larin saglikli oldugunu bekler.

.PARAMETER Profile
    Hangi profili acmak istediginiz: core, agents, memory, ui, social, obs, mcp, all
    Varsayilan: core

.EXAMPLE
    .\scripts\start.ps1
    .\scripts\start.ps1 -Profile agents
    .\scripts\start.ps1 -Profile all
#>

[CmdletBinding()]
param(
    [ValidateSet('core','agents','memory','ui','social','obs','mcp','all')]
    [string]$Profile = 'core'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path "$root\.env")) {
    Write-Error ".env dosyasi yok. Once: Copy-Item .env.example .env"
    exit 1
}

$profileArgs = switch ($Profile) {
    'all' { @('--profile','core','--profile','agents','--profile','memory','--profile','ui','--profile','social','--profile','obs','--profile','mcp') }
    default { @('--profile', $Profile) }
}

Write-Host "Profil baslatiliyor: $Profile" -ForegroundColor Cyan
$dockerArgs = @('compose') + $profileArgs + @('up','-d','--wait')
& docker @dockerArgs

if ($LASTEXITCODE -ne 0) {
    Write-Error "docker compose up basarisiz oldu (exit: $LASTEXITCODE)"
    exit 1
}

Write-Host ""
Write-Host "Container'lar baslatildi. Saglik kontrolu calistiriliyor..." -ForegroundColor Green
Start-Sleep -Seconds 2
& "$PSScriptRoot\doctor.ps1"
