<#
.SYNOPSIS
    CrewAI Reklam Ajansi - Saglik Kontrolu (doctor)

.DESCRIPTION
    Tum servisleri kontrol eder, /health endpoint'lerini pingler, raporlar.
    Aktif profile gore farkli kontroller yapar.

.EXAMPLE
    .\scripts\doctor.ps1
    .\scripts\doctor.ps1 -Verbose
#>

[CmdletBinding()]
param(
    [switch]$Detailed
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# Renkli output
function Write-Status {
    param([string]$Label, [string]$Status, [string]$Detail = "")
    $color = switch ($Status) {
        'OK'       { 'Green' }
        'WARN'     { 'Yellow' }
        'FAIL'     { 'Red' }
        'INFO'     { 'Cyan' }
        default    { 'White' }
    }
    Write-Host ("  {0,-30} " -f $Label) -NoNewline
    Write-Host ("[{0}]" -f $Status) -ForegroundColor $color -NoNewline
    if ($Detail) { Write-Host " $Detail" } else { Write-Host "" }
}

function Test-DockerRunning {
    try { docker info --format "{{.ServerVersion}}" 2>$null | Out-Null; return $LASTEXITCODE -eq 0 } catch { return $false }
}

function Test-ContainerHealth {
    param([string]$Name)
    $info = docker inspect --format='{{.State.Health.Status}}' $Name 2>$null
    if (-not $info) { return 'missing' }
    return $info.Trim()
}

function Test-TCPPort {
    param([string]$HostName, [int]$Port, [int]$Timeout = 2000)
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect($HostName, $Port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne($Timeout, $false)
        if ($wait -and $tcp.Connected) { $tcp.EndConnect($iar); $tcp.Close(); return $true }
        $tcp.Close(); return $false
    } catch { return $false }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  CrewAI Reklam Ajansi - Saglik Kontrolu" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# --- Sistem Kontrolleri ------------------------------------------
Write-Host "Sistem:" -ForegroundColor White

if (Test-DockerRunning) {
    $ver = docker info --format "{{.ServerVersion}}" 2>$null
    Write-Status "Docker daemon" "OK" "v$ver"
} else {
    Write-Status "Docker daemon" "FAIL" "Docker Desktop'i baslatin"
    exit 1
}

# Ollama
try {
    $ollama = Invoke-RestMethod -Uri "http://localhost:11434/api/version" -TimeoutSec 3 -ErrorAction Stop
    Write-Status "Ollama API" "OK" "v$($ollama.version)"
} catch {
    Write-Status "Ollama API" "WARN" "host'ta calismiyor (Asama 3'te gerekli)"
}

# .env varligi
if (Test-Path "$root\.env") {
    Write-Status ".env dosyasi" "OK"
    function Test-EnvKey {
        param([string]$EnvPath, [string]$Key)
        $line = (Get-Content $EnvPath | Where-Object { $_ -match "^${Key}=" } | Select-Object -First 1)
        if (-not $line) { return $false }
        $val = ($line -split '=', 2)[1].Trim()
        return -not [string]::IsNullOrWhiteSpace($val)
    }
    foreach ($k in @('OPENROUTER_API_KEY','GOOGLE_GEMINI_API_KEY','HUGGINGFACE_TOKEN')) {
        if (Test-EnvKey -EnvPath "$root\.env" -Key $k) {
            Write-Status $k "OK" "doldurulmus"
        } else {
            $sev = if ($k -eq 'HUGGINGFACE_TOKEN') { 'INFO' } else { 'WARN' }
            Write-Status $k $sev "henuz doldurulmamis"
        }
    }
} else {
    Write-Status ".env dosyasi" "FAIL" ".env.example'dan kopyalayin"
}

# Vault path
$vaultPath = $null
if (Test-Path "$root\.env") {
    $vaultLine = (Get-Content "$root\.env" | Select-String -Pattern "^VAULT_BASE_PATH_HOST=").Line
    if ($vaultLine) {
        $vaultPath = ($vaultLine -split '=', 2)[1].Trim()
    }
}
if ($vaultPath -and (Test-Path $vaultPath)) {
    Write-Status "Vault klasoru" "OK" $vaultPath
} elseif ($vaultPath) {
    Write-Status "Vault klasoru" "WARN" "yol var ama erisilemiyor: $vaultPath"
} else {
    Write-Status "Vault klasoru" "WARN" "VAULT_BASE_PATH_HOST tanimsiz"
}

Write-Host ""
Write-Host "Container'lar:" -ForegroundColor White

# --- Container Health --------------------------------------------
$containers = @(
    @{ Name='adagency-postgres'; Port=5432; Service='Postgres+pgvector' }
    @{ Name='adagency-redis';    Port=6379; Service='Redis 7' }
    @{ Name='adagency-api';      Port=8000; Service='Agency API (Asama 2)' }
    @{ Name='adagency-flowise';  Port=3000; Service='Flowise (Asama 8)' }
    @{ Name='adagency-postiz';   Port=5000; Service='Postiz (Asama 6)' }
    @{ Name='adagency-langfuse'; Port=3001; Service='Langfuse (Asama 5)' }
)

foreach ($c in $containers) {
    $status = Test-ContainerHealth -Name $c.Name
    switch ($status) {
        'healthy'      { Write-Status $c.Service "OK" "container saglikli" }
        'starting'     { Write-Status $c.Service "WARN" "baslatiliyor..." }
        'unhealthy'    { Write-Status $c.Service "FAIL" "saglik kontrolu basarisiz" }
        'none'         { Write-Status $c.Service "INFO" "calisiyor (health check yok)" }
        'missing'      { Write-Status $c.Service "INFO" "henuz baslatilmamis (sonraki asama)" }
        default        { Write-Status $c.Service "WARN" $status }
    }
}

# --- Port Erisim -------------------------------------------------
Write-Host ""
Write-Host "Port erisim:" -ForegroundColor White

$ports = @(
    @{ HostName='127.0.0.1'; Port=5432; Label='Postgres' }
    @{ HostName='127.0.0.1'; Port=6379; Label='Redis' }
)

foreach ($p in $ports) {
    if (Test-TCPPort -HostName $p.HostName -Port $p.Port) {
        Write-Status "$($p.Label) ($($p.HostName):$($p.Port))" "OK"
    } else {
        Write-Status "$($p.Label) ($($p.HostName):$($p.Port))" "FAIL" "port erisilemiyor"
    }
}

# --- Postgres pgvector kontrol -----------------------------------
$pgRunning = Test-ContainerHealth -Name 'adagency-postgres'
if ($pgRunning -eq 'healthy') {
    Write-Host ""
    Write-Host "Postgres detay:" -ForegroundColor White
    $envFile = "$root\.env"
    $pgUser = (Get-Content $envFile | Select-String "^POSTGRES_USER=").Line -split '=', 2 | Select-Object -Last 1
    $pgDb   = (Get-Content $envFile | Select-String "^POSTGRES_DB=").Line   -split '=', 2 | Select-Object -Last 1

    $pgver = docker exec adagency-postgres psql -U $pgUser -d $pgDb -tAc "SELECT version();" 2>$null
    if ($pgver) { Write-Status "Postgres version" "OK" ($pgver -split ' ')[1] }

    $extver = docker exec adagency-postgres psql -U $pgUser -d $pgDb -tAc "SELECT extversion FROM pg_extension WHERE extname='vector';" 2>$null
    if ($extver) { Write-Status "pgvector extension" "OK" "v$extver" } else { Write-Status "pgvector extension" "FAIL" "kurulamamis" }

    $schemas = docker exec adagency-postgres psql -U $pgUser -d $pgDb -tAc "SELECT count(*) FROM information_schema.schemata WHERE schema_name IN ('agency','crm','memory','audit');" 2>$null
    if ($schemas) { Write-Status "Schema'lar (agency/crm/memory/audit)" "OK" "$schemas/4" }
}

# --- Redis detay -------------------------------------------------
$rdRunning = Test-ContainerHealth -Name 'adagency-redis'
if ($rdRunning -eq 'healthy') {
    Write-Host ""
    Write-Host "Redis detay:" -ForegroundColor White
    $envFile = "$root\.env"
    $rdPass = ((Get-Content $envFile | Select-String "^REDIS_PASSWORD=").Line -split '=', 2)[1]

    $rdver = docker exec adagency-redis redis-cli -a $rdPass --no-auth-warning INFO server 2>$null | Select-String "redis_version:" | ForEach-Object { ($_ -split ':')[1].Trim() }
    if ($rdver) { Write-Status "Redis version" "OK" "v$rdver" }

    $maxmem = docker exec adagency-redis redis-cli -a $rdPass --no-auth-warning CONFIG GET maxmemory 2>$null | Select-Object -Last 1
    if ($maxmem) {
        $mb = [int]($maxmem) / 1MB
        Write-Status "maxmemory" "OK" "$mb MB"
    }
    $policy = docker exec adagency-redis redis-cli -a $rdPass --no-auth-warning CONFIG GET maxmemory-policy 2>$null | Select-Object -Last 1
    if ($policy) { Write-Status "eviction policy" "OK" $policy }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Saglik kontrolu tamamlandi" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
