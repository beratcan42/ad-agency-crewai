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
    @{ Name='adagency-api';      Port=8010; Service='Agency API (Asama 2)' }
    @{ Name='adagency-worker';   Port=0;    Service='Celery Worker (Asama 2)' }
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
    @{ HostName='127.0.0.1'; Port=8010; Label='Agency API' }
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

    $usageTbl = docker exec adagency-postgres psql -U $pgUser -d $pgDb -tAc "SELECT count(*) FROM pg_tables WHERE schemaname='agency' AND tablename='usage_logs';" 2>$null
    if ($usageTbl -and ($usageTbl.Trim() -eq '1')) {
        $rowCount = docker exec adagency-postgres psql -U $pgUser -d $pgDb -tAc "SELECT count(*) FROM agency.usage_logs;" 2>$null
        Write-Status "agency.usage_logs" "OK" "tablo var ($($rowCount.Trim()) row)"
    } else {
        Write-Status "agency.usage_logs" "WARN" "tablo yok (3.D SQL apply edilmemis)"
    }
}

# --- Agency API detay --------------------------------------------
$apiRunning = Test-ContainerHealth -Name 'adagency-api'
if ($apiRunning -eq 'healthy') {
    Write-Host ""
    Write-Host "Agency API detay:" -ForegroundColor White
    try {
        $h = Invoke-RestMethod -Uri "http://127.0.0.1:8010/healthz" -TimeoutSec 5
        Write-Status "Agency API /healthz" "OK" "version $($h.version) status=$($h.status)"
        Write-Status "API -> Postgres ping" "OK" "$($h.checks.postgres.latency_ms) ms"
        Write-Status "API -> Redis ping" "OK" "$($h.checks.redis.latency_ms) ms"
    } catch {
        Write-Status "Agency API /healthz" "FAIL" $_.Exception.Message
    }

    # 12 ajan registry
    try {
        $ag = Invoke-RestMethod -Uri "http://127.0.0.1:8010/agents" -TimeoutSec 5
        if ($ag.count -eq 12) {
            Write-Status "12 ajan registry" "OK" "$($ag.count) ajan tanimli"
        } else {
            Write-Status "12 ajan registry" "WARN" "$($ag.count) ajan (12 beklenir)"
        }
    } catch { Write-Status "/agents endpoint" "FAIL" $_.Exception.Message }

    # 24 saatlik kullanim ozeti (telemetry)
    try {
        $u = Invoke-RestMethod -Uri "http://127.0.0.1:8010/stats/usage?hours=24" -TimeoutSec 8
        $calls = $u.totals.total_calls
        $tokens = $u.totals.total_tokens
        if ($calls -gt 0) {
            $succ = ($u.by_status | Where-Object { $_.status -eq 'success' } | Select-Object -ExpandProperty count -First 1)
            $fall = ($u.by_status | Where-Object { $_.status -eq 'fallback' } | Select-Object -ExpandProperty count -First 1)
            $skip = ($u.by_status | Where-Object { $_.status -eq 'skip_ratelimit' } | Select-Object -ExpandProperty count -First 1)
            Write-Status "Telemetry (24h)" "OK" "$calls cagri, $tokens token (success=$succ fallback=$fall skip=$skip)"
        } else {
            Write-Status "Telemetry (24h)" "INFO" "henuz cagri yok"
        }
    } catch { Write-Status "/stats/usage endpoint" "FAIL" $_.Exception.Message }

    # Anlik rate limit snapshot
    try {
        $l = Invoke-RestMethod -Uri "http://127.0.0.1:8010/stats/limits" -TimeoutSec 5
        $hot = $l.items | Where-Object { $_.rpm_pct -ge 0.5 -or $_.rpd_pct -ge 0.5 }
        if ($hot) {
            Write-Status "Sicak modeller" "WARN" "$($hot.Count) model %50+ kullanimda"
            foreach ($m in $hot) {
                Write-Host ("      - {0}/{1}: RPM {2:P0} ({3}/{4}), RPD {5:P0} ({6}/{7})" -f $m.provider, $m.model, $m.rpm_pct, $m.rpm_used, $m.rpm_limit, $m.rpd_pct, $m.rpd_used, $m.rpd_limit) -ForegroundColor Yellow
            }
        } else {
            Write-Status "Rate limit havuzu" "OK" "$($l.count) model, hepsi <%50"
        }
    } catch { Write-Status "/stats/limits endpoint" "FAIL" $_.Exception.Message }
}

# --- Celery worker detay -----------------------------------------
$wkRunning = Test-ContainerHealth -Name 'adagency-worker'
if ($wkRunning -eq 'healthy') {
    Write-Host ""
    Write-Host "Celery worker detay:" -ForegroundColor White
    try {
        $reg = docker exec adagency-worker celery -A src.workers.celery_app inspect registered 2>$null | Select-String "src.workers.agent_tasks\." | Measure-Object | Select-Object -ExpandProperty Count
        if ($reg -ge 12) {
            Write-Status "Celery task registry" "OK" "$reg / 12 ajan task'i aktif"
        } else {
            Write-Status "Celery task registry" "WARN" "$reg / 12 task (eksik)"
        }
    } catch { Write-Status "Celery inspect" "FAIL" $_.Exception.Message }

    try {
        $active = docker exec adagency-worker celery -A src.workers.celery_app inspect active_queues 2>$null | Select-String "name" | Measure-Object | Select-Object -ExpandProperty Count
        Write-Status "Aktif queue'lar" "OK" "$active queue (q_heavy, q_fast, q_io, q_research)"
    } catch { Write-Status "Aktif queue'lar" "WARN" "okunamiyor" }
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
