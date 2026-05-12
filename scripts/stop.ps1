<#
.SYNOPSIS
    Stack'i temiz kapatir (volume'lar korunur).

.EXAMPLE
    .\scripts\stop.ps1
    .\scripts\stop.ps1 -RemoveOrphans
#>

[CmdletBinding()]
param(
    [switch]$RemoveOrphans
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "Stack durduruluyor..." -ForegroundColor Yellow
$args = @('compose','down')
if ($RemoveOrphans) { $args += '--remove-orphans' }
& docker @args

if ($LASTEXITCODE -eq 0) {
    Write-Host "Stack durduruldu. Volume'lar korundu." -ForegroundColor Green
} else {
    Write-Host "docker compose down hata verdi." -ForegroundColor Red
}
