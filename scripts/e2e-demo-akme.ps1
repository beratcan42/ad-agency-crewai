<#
.SYNOPSIS
    Akme Tekstil bahar kampanyasi — 5 ajan ardisik E2E saglama testi.

.EXAMPLE
    .\scripts\e2e-demo-akme.ps1
    .\scripts\e2e-demo-akme.ps1 -ApiBase "http://127.0.0.1:8010" -ClientId "akme-tekstil"
#>
param(
    [string]$ApiBase = "http://127.0.0.1:8010",
    [string]$ClientId = "akme-tekstil"
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$briefTitle = "Akme Tekstil — Bahar Koleksiyonu 2026"
$briefBody = @"
Akme Tekstil, kadin hazir giyim markasi. Bahar koleksiyonunu Instagram odakli lanse edecegiz.
Hedef kitle: 25-40 yas, sehirli kadinlar, orta-ust gelir. Butce 80.000 TL (organik + odenmis icerik karisimi).
Ton: modern, sicak, guven veren. Rakipler: yerli konsept markalar ve marketplace gorunurlugu guclu oyuncular.
Tek kampanya adi onerisi ve hashtag seti istiyoruz. Olcum: erisim, kaydetme, DM ve web sitesi tiklamasi.
"@

$agents = @(
    @{ id = "account_manager"; max_tokens = 500 },
    @{ id = "strategist";      max_tokens = 550 },
    @{ id = "copywriter";      max_tokens = 550 },
    @{ id = "social_media";    max_tokens = 650 },
    @{ id = "seo_specialist"; max_tokens = 550 }
)

New-Item -ItemType Directory -Force -Path "$root\logs" | Out-Null
$payloadPath = "$root\logs\e2e-brief.json"

foreach ($a in $agents) {
    @{ title = $briefTitle; content = $briefBody; max_tokens = $a.max_tokens } | ConvertTo-Json -Compress | Out-File $payloadPath -Encoding utf8
    Write-Host "`n>>> $($a.id) ..."
    $raw = curl.exe -s -X POST "$ApiBase/agents/$($a.id)/run" `
        -H "X-Client-Id: $ClientId" `
        -H "Content-Type: application/json" `
        --data "@$payloadPath"
    $j = $raw | ConvertFrom-Json
    if ($j.agent_id) {
        Write-Host "    $($j.provider)/$($j.model) | $($j.usage.total_tokens) tok | $($j.latency_ms) ms"
    } else {
        Write-Host "    HATA: $raw"
    }
}

Write-Host "`n=== /stats/usage?hours=1&client=$ClientId ==="
curl.exe -s "$ApiBase/stats/usage?hours=1&client=$([uri]::EscapeDataString($ClientId))" `
    | Tee-Object "$root\logs\e2e-stats-usage.json" | ConvertFrom-Json | ConvertTo-Json -Depth 6

Write-Host "`nTamam. Detay: logs\e2e-stats-usage.json"
