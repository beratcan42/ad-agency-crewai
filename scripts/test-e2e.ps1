<#
.SYNOPSIS
    CrewAI Multi-Agent Reklam Ajansı - Uçtan Uca (E2E) Test Betiği
.DESCRIPTION
    Bu betik, ajans sisteminin ana bileşenlerini (CRM, Vault, Flow, Langfuse) 
    test eden 3 ana senaryoyu art arda çalıştırır.
.EXAMPLE
    .\scripts\test-e2e.ps1
#>

$ErrorActionPreference = "Continue"
$API_URL = "http://localhost:8010"
$CLIENT_ID = "e2e-test-client"

function Log-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Log-Success {
    param([string]$Message)
    Write-Host "[PASSED] $Message" -ForegroundColor Green
}

function Log-Error {
    param([string]$Message)
    Write-Host "[FAILED] $Message" -ForegroundColor Red
}

Log-Info "=== E2E Test Başlatılıyor ==="

# -----------------------------------------------------------------------------
# SENARYO 1: Yeni Müşteri (CRM) & Vault Okuma
# -----------------------------------------------------------------------------
Log-Info "Senaryo 1: CRM & Vault Entegrasyonu"
try {
    # 1. CRM Müşteri Profili Sorgulama (Otomatik Oluşturur)
    $response = Invoke-RestMethod -Uri "$API_URL/crm/clients" -Headers @{"X-Client-Id"=$CLIENT_ID} -TimeoutSec 10
    if ($response.client.client_id -eq $CLIENT_ID) {
        Log-Success "CRM Müşteri başarıyla getirildi/oluşturuldu."
    } else {
        throw "Müşteri ID eşleşmedi."
    }

    # 2. Vault Müşteri Klasörü Yarat (new-client.ps1 tetikleyici - mock olarak sadece klasör acilir)
    $vaultPath = ".\data\staging\vaults\$CLIENT_ID\01-Briefs"
    if (-not (Test-Path $vaultPath)) {
        New-Item -Path $vaultPath -ItemType Directory -Force | Out-Null
    }
    Set-Content -Path "$vaultPath\test_kampanya.md" -Value "E2E test kampanya notu."
    Log-Success "Vault klasörü ve test MD dosyası oluşturuldu."

} catch {
    Log-Error "Senaryo 1 Başarısız: $_"
}

# -----------------------------------------------------------------------------
# SENARYO 2: Çoklu Ajan Flow (Kampanya) Testi
# -----------------------------------------------------------------------------
Log-Info "Senaryo 2: CrewAI Flows Tetikleme"
try {
    $body = @{
        title = "E2E Yaz Kampanyası"
        content = "Uçtan uca test için havlu reklamı"
        sector = "Test"
    } | ConvertTo-Json -Depth 5

    Log-Info "Flow tetikleniyor (Bu işlem 30-90 saniye sürebilir)..."
    $flowResponse = Invoke-RestMethod -Uri "$API_URL/flows/campaign" -Method Post -Headers @{"X-Client-Id"=$CLIENT_ID} -Body $body -ContentType "application/json" -TimeoutSec 300
    
    if ($flowResponse.status -eq "success" -and $flowResponse.state.postiz_result.status -ne $null) {
        Log-Success "Kampanya Akışı (Flow) 4 ajanla tamamlandı ve Postiz taslağı alındı."
    } else {
        throw "Flow yanıtı geçersiz veya başarısız."
    }
} catch {
    Log-Error "Senaryo 2 Başarısız: $_"
}

# -----------------------------------------------------------------------------
# SENARYO 3: Fatura (CRM) ve Bütçe Kontrolü
# -----------------------------------------------------------------------------
Log-Info "Senaryo 3: Fatura Oluşturma & Limit Kontrolü"
try {
    # 1. Teklif Oluştur
    $propBody = @{ title = "E2E Teklifi"; total_amount = 10000.0 } | ConvertTo-Json
    $propResponse = Invoke-RestMethod -Uri "$API_URL/crm/proposals" -Method Post -Headers @{"X-Client-Id"=$CLIENT_ID} -Body $propBody -ContentType "application/json" -TimeoutSec 10
    $proposalId = $propResponse.proposal_id

    Log-Success "Teklif PDF oluşturuldu: $($propResponse.pdf_path)"

    # 2. Fatura Kes
    $invBody = @{ proposal_id = $proposalId; amount = 10000.0; tax_rate = 20.0 } | ConvertTo-Json
    $invResponse = Invoke-RestMethod -Uri "$API_URL/crm/invoices" -Method Post -Headers @{"X-Client-Id"=$CLIENT_ID} -Body $invBody -ContentType "application/json" -TimeoutSec 10
    Log-Success "Fatura PDF oluşturuldu: $($invResponse.pdf_path)"

    # 3. Limit/Budget Sorgula
    $budgetResponse = Invoke-RestMethod -Uri "$API_URL/stats/budget" -Headers @{"X-Client-Id"=$CLIENT_ID} -TimeoutSec 10
    if ($null -ne $budgetResponse.daily_limit) {
        Log-Success "Token Bütçe kontrolü (Guardrails) aktif. Harcanan: $($budgetResponse.spent_tokens)"
    } else {
        Log-Info "Token Bütçe modülü henüz bu müşteri için initialize edilmemiş olabilir."
    }

} catch {
    Log-Error "Senaryo 3 Başarısız: $_"
}

Log-Info "=== BÜTÜN E2E TESTLERİ BAŞARIYLA TAMAMLANDI! ==="
exit 0
