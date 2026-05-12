<#
.SYNOPSIS
    CrewAI Reklam Ajansi - Asamali Kurulum Sihirbazi

.DESCRIPTION
    5+ asamali kontrollu kurulum. Her asama sonunda doctor.ps1 calistirir,
    kullanicidan "Devam et?" onayi bekler.

.PARAMETER Stage
    Belirli asamadan baslat (0-11). Varsayilan: 0

.PARAMETER Resume
    Son kaldigi yerden devam et (logs/.stage_state'i okur)

.PARAMETER DryRun
    Sadece kontrol et, kurulum yapma

.EXAMPLE
    .\scripts\setup.ps1                 # interactive, basindan
    .\scripts\setup.ps1 -Stage 4        # asama 4'ten basla
    .\scripts\setup.ps1 -Resume         # son durumdan devam
    .\scripts\setup.ps1 -DryRun         # sadece kontrol

.NOTES
    Bu script Asama 1 icin temel iskelet. Sonraki asamalar
    eklendikce her stage fonksiyonu doldurulacak.
#>

[CmdletBinding()]
param(
    [int]$Stage = 0,
    [switch]$Resume,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$stateFile = "$root\logs\.stage_state"
$logDir = "$root\logs"
New-Item -ItemType Directory -Path $logDir -Force -ErrorAction SilentlyContinue | Out-Null

# ---------------------------------------------------------------
# Yardimcilar
# ---------------------------------------------------------------

function Convert-WindowsPathToWSL {
    param([string]$WindowsPath)
    if (-not $WindowsPath) { return "" }
    $drive = $WindowsPath.Substring(0, 1).ToLower()
    $rest = $WindowsPath.Substring(2).Replace('\', '/')
    return "/mnt/$drive$rest"
}

function Write-Stage {
    param([int]$N, [string]$Title)
    Write-Host ""
    Write-Host "===================================================" -ForegroundColor Cyan
    Write-Host "  ASAMA $N - $Title" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor Cyan
}

function Wait-UserConfirm {
    param([string]$Msg = "Bu asama tamamlandi. Devam edelim mi?")
    Write-Host ""
    Write-Host $Msg -ForegroundColor Yellow
    $r = Read-Host "Devam etmek icin E (evet) yazin, durmak icin H (hayir)"
    if ($r -notmatch '^[Ee]') {
        Write-Host "Kurulum durduruldu. Devam etmek icin: .\scripts\setup.ps1 -Resume" -ForegroundColor Yellow
        exit 0
    }
}

function Save-State {
    param([int]$Stage)
    Set-Content -Path $stateFile -Value $Stage -Encoding ASCII
}

function Get-LastStage {
    if (Test-Path $stateFile) { return [int](Get-Content $stateFile -Raw).Trim() }
    return 0
}

# ---------------------------------------------------------------
# Stage 0: Preflight
# ---------------------------------------------------------------
function Invoke-Stage0 {
    Write-Stage 0 "Preflight (sistem kontrolu)"

    Write-Host "  Docker Desktop..." -NoNewline
    docker info --format "{{.ServerVersion}}" 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host " FAIL" -ForegroundColor Red
        Write-Host "  Docker Desktop calismiyor. Once Docker Desktop'i baslatin." -ForegroundColor Red
        exit 1
    }
    Write-Host " OK" -ForegroundColor Green

    Write-Host "  Ollama..." -NoNewline
    try {
        Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 3 | Out-Null
        Write-Host " OK" -ForegroundColor Green
    } catch {
        Write-Host " WARN (Asama 3'te gerekli)" -ForegroundColor Yellow
    }

    Write-Host "  .env dosyasi..." -NoNewline
    if (Test-Path "$root\.env") {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " EKSIK" -ForegroundColor Red
        Write-Host "  Olusturuluyor: .env.example -> .env"
        Copy-Item "$root\.env.example" "$root\.env"
    }

    if (-not $DryRun) { Save-State 0 }
    Wait-UserConfirm "Asama 0 (Preflight) tamamlandi. Asama 1'e gecelim mi?"
}

# ---------------------------------------------------------------
# Stage 1: Foundation
# ---------------------------------------------------------------
function Invoke-Stage1 {
    Write-Stage 1 "Foundation (postgres+redis + scriptler)"

    if ($DryRun) {
        Write-Host "  [DryRun] docker compose --profile core up -d --wait calistirilacak"
        return
    }

    Write-Host "  Image'lar indiriliyor..." -ForegroundColor White
    docker compose --profile core pull
    if ($LASTEXITCODE -ne 0) { Write-Host "  pull basarisiz" -ForegroundColor Red; exit 1 }

    Write-Host "  Container'lar baslatiliyor..." -ForegroundColor White
    docker compose --profile core up -d --wait
    if ($LASTEXITCODE -ne 0) { Write-Host "  up basarisiz" -ForegroundColor Red; exit 1 }

    Write-Host "  Saglik kontrolu..." -ForegroundColor White
    & "$PSScriptRoot\doctor.ps1"

    Save-State 1
    Wait-UserConfirm "Asama 1 (Foundation) tamamlandi. Asama 2 (Agency Core) icin onay bekleniyor."
}

# ---------------------------------------------------------------
# Stage 2-11: Placeholder (sonraki asamalarda doldurulacak)
# ---------------------------------------------------------------
function Invoke-StagePlaceholder { param([int]$N, [string]$T)
    Write-Stage $N $T
    Write-Host "  Bu asama henuz hazir degil. Bir sonraki sohbet adiminda doldurulacak." -ForegroundColor Yellow
    Save-State $N
    exit 0
}

# ---------------------------------------------------------------
# Ana akis
# ---------------------------------------------------------------

if ($Resume) {
    $Stage = (Get-LastStage) + 1
    Write-Host "Resume: Asama $Stage'tan devam ediliyor" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  CrewAI Reklam Ajansi - Kurulum Sihirbazi" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

if ($Stage -le 0) { Invoke-Stage0 }
if ($Stage -le 1) { Invoke-Stage1 }
if ($Stage -le 2) { Invoke-StagePlaceholder 2 "Agency Core (FastAPI + CrewAI)" }
if ($Stage -le 3) { Invoke-StagePlaceholder 3 "12 Ajan + Hibrit Router" }
if ($Stage -le 4) { Invoke-StagePlaceholder 4 "Obsidian Vault + Drive Sync" }
if ($Stage -le 5) { Invoke-StagePlaceholder 5 "Guardrails + Langfuse" }
if ($Stage -le 6) { Invoke-StagePlaceholder 6 "MCP Gateway + Postiz" }
if ($Stage -le 7) { Invoke-StagePlaceholder 7 "CRM + Fatura" }
if ($Stage -le 8) { Invoke-StagePlaceholder 8 "Flowise UI" }
if ($Stage -le 9) { Invoke-StagePlaceholder 9 "Dokumantasyon" }
if ($Stage -le 10) { Invoke-StagePlaceholder 10 "E2E Test" }
if ($Stage -le 11) { Invoke-StagePlaceholder 11 "Final Review" }

Write-Host ""
Write-Host "Kurulum tamamlandi." -ForegroundColor Green
