# CrewAI Multi-Agent Reklam Ajansı

> 12 uzman AI ajanlı, çok müşterili (multi-tenant), tamamen ücretsiz reklam ajansı sistemi.
> OpenRouter free + Google Gemini AI Pro + Ollama hibrit dağılım. Obsidian Vault hafıza,
> Google Drive senkron, Postiz ile gerçek sosyal medya yayını, CRM/Fatura modülü.

**Durum:** ✅ **v1.0.0 RELEASED** — Tüm aşamalar tamamlandı.

> Detaylı kaldığımız yer ve sonraki adımlar için: [`docs/PROJE-DURUMU.md`](docs/PROJE-DURUMU.md)

---

## Hızlı Başlangıç (Windows + PowerShell)

```powershell
cd c:\YapayZekaa\Cursor\sesli_asistan

# Tüm sistemi ayağa kaldır (core + agents + obs + social + mcp + ui)
docker compose --profile core --profile agents --profile obs --profile social --profile mcp --profile ui up -d

# Sadece temel servisler
docker compose --profile core --profile agents up -d --wait

# Sağlık kontrolü
.\scripts\doctor.ps1

# Yeni müşteri vault oluştur
.\scripts\new-client.ps1 -ClientId "akme-tekstil"

# Uçtan uca test
.\scripts\test-e2e.ps1

# Durdur
.\scripts\stop.ps1
```

## Aşamalı Mimari

| Aşama | Bileşen | Durum | Commit |
|---|---|---|---|
| 0 | Preflight (Docker/Ollama/Drive/Obsidian) | ✅ TAMAM | - |
| 1 | Foundation (postgres+pgvector, redis) | ✅ TAMAM | `305a3ed` |
| 2 | Agency Core (FastAPI + CrewAI 1.14.3 + Account Manager) | ✅ TAMAM | `f842b59` |
| **3.A** | **OpenRouter canlı envanter + 12 ajan zinciri (4 katman)** | **✅** | **`665c939`** |
| **3.B** | **LiteLLM native `gemini/` + `ollama_chat/` provider** | **✅** | **`665c939`** |
| **3.C** | **12 ajan registry + Celery task factory** | **✅** | **`4ed5c40`** |
| **3.D** | **Akıllı Router: Redis rate limit + Postgres telemetry + proactive fallback** | **✅** | **`66dbb16`** |
| **3.E** | **`/agents`, `/run`, `/dispatch`, `/tasks/{id}`, `/stats/*` endpoint'leri** | **✅** | **`4ed5c40` + `66dbb16`** |
| 4 | Vault `/vaults` bind mount, poller, `note_embeddings`, hybrid `/vault/search`, `new-client.ps1` | ✅ | `aa0882a` |
| **5** | **Langfuse v3 self-hosted, LiteLLM OTEL callback, Guardrails (circuit breaker + token budget)** | **✅** | **`87cfb3a`** |
| **6** | **MCP Gateway + Postiz + CrewAI Flows** | **✅** | **`fd27652`** |
| **7** | **CRM & Fatura Servisi (Postgres + ReportLab PDF + CrewAI Tools)** | **✅** | **`6815c76`** |
| **8** | **Flowise UI (docker-compose ui profili + Custom Tool Entegrasyonu)** | **✅** | **`eeefb38`** |
| **9** | **Dokümantasyon (API Reference, Agent Architecture)** | **✅** | **`8a0ec1f`** |
| **10** | **E2E Test (Müşteri Senkronu, Flow, Fatura, Telemetry)** | **✅** | **`3f205d2`** |
| **11** | **Final Review (v1.0.0 Release)** | **✅** | **`PENDING`** |

## Çalışan Servisler

| Servis | Container | Port (host) | Profil | Health |
|---|---|---|---|---|
| Postgres 16 + pgvector 0.8.2 | `adagency-postgres` | 5432 | core | ✅ |
| Redis 7.4.9 | `adagency-redis` | 6379 | core | ✅ |
| **Agency API** (FastAPI + CrewAI) | `adagency-api` | **8010** | agents | ✅ |
| **Celery Worker** (4 queue) | `adagency-worker` | - | agents | ✅ |
| **Langfuse Web** | `adagency-langfuse-web` | **3001** | obs | ✅ |
| **Postiz** | `adagency-postiz` | **5000** | social | ✅ |
| **MCP Gateway** | `adagency-mcp-gateway` | **8811** | mcp | ✅ |
| **Flowise UI** | `adagency-flowise` | **3000** | ui | ✅ |

> NOT: Host'ta port 8000 başka bir Windows servisi (`Manager`, PID 6464) tarafından tutulduğu için Agency API host portu **8010** olarak ayarlandı. Container içi hala 8000. Langfuse Web portu ise **3001**. Flowise **3000**, Postiz **5000** portundadır.

## Ana Komutlar

```powershell
# Docker
docker compose --profile core --profile agents up -d --wait
docker compose ps
docker compose logs -f agency-api
docker compose logs -f agency-worker

# PowerShell scriptler
.\scripts\setup.ps1                           # tam kurulum sihirbazı (Stage 0-1 dolu)
.\scripts\start.ps1 -Profile agents           # belirli profil
.\scripts\doctor.ps1                          # sağlık kontrolü
.\scripts\backup.ps1                          # yedek al
.\scripts\stop.ps1                            # temiz kapat

# Make (Git Bash veya WSL)
make up                                       # core
make doctor                                   # sağlık
make logs SERVICE=agency-api                  # log filtre
```

## Canlı API Endpoint'leri

| Method | Path | Auth | Açıklama |
|---|---|---|---|
| GET | `/` | - | Root info |
| GET | `/healthz` | - | DB+Redis ping (latency_ms döner) |
| GET | `/readyz` | - | Readiness (200/503) |
| GET | `/version` | - | App version |
| POST | `/brief` | `X-Client-Id` | Account Manager'a brief gönderir (geriye dönük) |
| **GET** | **`/agents`** | - | **12 ajan registry + 4-katmanlı zincir listesi** |
| **POST** | **`/agents/{id}/run`** | `X-Client-Id` | **Bir ajanı senkron çalıştır (LLM bekler)** |
| **POST** | **`/agents/{id}/dispatch`** | `X-Client-Id` | **Async — Celery'e gönderir, task_id döner** |
| **GET** | **`/tasks/{task_id}`** | - | **Celery durum sorgusu (PENDING/SUCCESS/FAILURE)** |
| **GET** | **`/stats/usage?hours=24&client=...`** | - | **Telemetry: total token, by_status/agent/model özet** |
| **GET** | **`/stats/limits`** | - | **Redis anlık RPM/RPD snapshot (her provider+model)** |
| **GET** | **`/vault/status`** | - | **Vault mount, watcher, heartbeat listesi (doctor)** |
| **GET** | **`/vault/files`** | `X-Client-Id` | **Vault içi `.md` listesi** |
| **GET** | **`/vault/note?path=...`** | `X-Client-Id` | **Markdown oku** |
| **PUT** | **`/vault/note`** | `X-Client-Id` | **Markdown yaz / güncelle** |
| **POST** | **`/vault/search`** | `X-Client-Id` | **Hybrid arama (pg_trgm + embedding)** |
| **GET** | **`/stats/langfuse`** | - | **Langfuse UI/OTEL durumu** |
| **GET** | **`/stats/budget`** | `X-Client-Id` | **Token bütçesi limiti ve durumu** |
| **POST** | **`/flows/campaign`** | `X-Client-Id` | **CrewAI Flow: 4 ajan zincirleme kampanya (Aşama 6)** |
| **GET** | **`/crm/clients`** | `X-Client-Id` | **Müşteri profili + teklifler + faturalar (Aşama 7)** |
| **POST** | **`/crm/proposals`** | `X-Client-Id` | **Yeni teklif + PDF oluşturma** |
| **POST** | **`/crm/invoices`** | `X-Client-Id` | **Fatura kesme + PDF (KDV %20)** |
| GET | `/docs` | - | Swagger UI |

### 12 Ajan (registry)

| Agent ID | Queue | Primary Model | Görev |
|---|---|---|---|
| `account_manager` | q_heavy | `openrouter/owl-alpha` (1M ctx) | Brief analizi, orkestrasyon |
| `customer_service` | q_fast | `google/gemma-4-31b-it:free` | Eksik bilgi tespiti, müşteri diyaloğu |
| `strategist` | q_heavy | `nvidia/nemotron-3-super-120b-a12b:free` | Pazar/rakip/SWOT/persona |
| `copywriter` | q_heavy | `meta-llama/llama-3.3-70b-instruct:free` | Reklam metni, slogan |
| `social_media` | q_fast | `qwen/qwen3-next-80b-a3b-instruct:free` | IG/TT/LinkedIn takvim |
| `seo_specialist` | q_research | `google/gemma-4-31b-it:free` | Anahtar kelime, meta, içerik |
| `creative_director` | q_heavy | `nvidia/nemotron-nano-12b-v2-vl:free` | Görsel konsept + FLUX prompt |
| `data_analyst` | q_research | `qwen/qwen3-coder:free` | KPI, ölçüm planı, kod |
| `budget_manager` | q_research | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | Bütçe dağılım, ROAS |
| `ecommerce_specialist` | q_research | `qwen/qwen3-next-80b-a3b-instruct:free` | Marketplace listing |
| `publisher` | q_fast | `gemini-2.5-flash` | Yayın planı (Postiz JSON) |
| `crm_billing` | q_fast | `gemini-2.5-flash` | Müşteri+teklif+KDV%20 fatura |

## Mimari Karar Özeti

- **Multi-agent:** CrewAI v1.14.3 (Flow + @persist + checkpoint/resume — Aşama 3'te aktive)
- **LLM:** Hibrit — OpenRouter free + Google Gemini AI Pro + Ollama yerel (4-katmanlı fallback)
- **Multi-tenant:** `X-Client-Id` middleware + namespace isolation (zorunlu, regex doğrulamalı)
- **Hafıza:** Obsidian Vault (MD) + pgvector hybrid — `D:\Google_Drive\AjansKlasoru` Drive senkronlu
- **Yayın:** Postiz MCP (self-hosted) → X/IG/TikTok/LinkedIn/FB/+15
- **CRM:** FastAPI + Postgres + Gotenberg (PDF), Türkiye KDV %20
- **Sandbox:** Yerel Docker (E2B cloud yerine, KVKK uyumlu)
- **Observability:** Langfuse self-hosted + OpenTelemetry
- **Celery:** 4 queue (`q_heavy/q_fast/q_io/q_research`) — 12 worker yerine 4 container

## Dizin Yapısı (Güncel)

```
sesli_asistan/
├── .env                            # gerçek secrets (gitignored)
├── .env.example                    # şablon
├── docker-compose.yml              # 7 profil: core/agents/memory/ui/social/obs/mcp
├── Makefile                        # make up/down/logs/doctor
├── README.md
├── docs/
│   ├── PROJE-DURUMU.md            # detaylı kaldığımız yer rehberi
│   ├── API_REFERENCE.md           # tüm endpoint detayları (Aşama 9)
│   ├── AGENT_ARCHITECTURE.md      # 12 ajan + Flow + Tools (Aşama 9)
│   └── flowise_templates/         # Flowise Custom Tool rehberi (Aşama 8)
├── scripts/
│   ├── setup.ps1                  # aşamalı sihirbaz
│   ├── doctor.ps1                 # sağlık kontrolü
│   ├── new-client.ps1             # yeni müşteri vault oluştur
│   ├── test-e2e.ps1               # uçtan uca test (3 senaryo, Aşama 10)
│   ├── e2e-demo-akme.ps1
│   ├── start.ps1, stop.ps1, backup.ps1
│   ├── templates/vault/           # Obsidian klasör şablonu
│   └── sql/init/
│       ├── 01-init-pgvector.sql
│       ├── 02-usage-logs.sql
│       ├── 03-note-embeddings.sql # hybrid RAG chunk tablosu
│       ├── 04-token-budgets.sql   # müşteri bütçe tablosu
│       └── 05-crm-schema.sql     # CRM tabloları (Aşama 7)
├── agency/                         # FastAPI + CrewAI v1.14.x
│   ├── pyproject.toml             # v0.4.0
│   ├── Dockerfile                 # Python 3.12-slim
│   ├── Dockerfile.mcp             # MCP Gateway imajı (Aşama 6)
│   └── src/
│       ├── main.py
│       ├── api/
│       │   ├── routes.py          # ana endpoint'ler + /flows/campaign
│       │   ├── routes_crm.py      # /crm/* (Aşama 7)
│       │   └── vault_routes.py    # /vault/*
│       ├── middleware/            # X-Client-Id + token budget
│       ├── router/                # model_router + rate_limiter + telemetry
│       ├── config/                # Pydantic Settings + models.yaml
│       ├── guardrails/            # circuit_breaker + token_budget (Aşama 5)
│       ├── observability/         # langfuse_integration (Aşama 5)
│       ├── crm/
│       │   └── pdf_gen.py         # ReportLab PDF üretici (Aşama 7)
│       ├── mcp_gateway/
│       │   └── server.py          # MCP FastAPI bridge (Aşama 6)
│       ├── vault/                 # poller + embedder + search
│       ├── crew/
│       │   ├── builder.py         # generic run_agent(agent_id, ...)
│       │   ├── flows/
│       │   │   └── campaign_flow.py  # CrewAI Flow (Aşama 6)
│       │   ├── tools/
│       │   │   ├── vault_fs.py    # senkron Vault helper
│       │   │   ├── vault_tools.py # @tool sarmalayıcı (Aşama 5)
│       │   │   ├── crm_tools.py   # CRM araçları (Aşama 7)
│       │   │   └── postiz_tool.py # Postiz taslak (Aşama 6)
│       │   └── agents/
│       │       └── registry.py    # 12 ajan task template + prompt builder
│       └── workers/               # celery_app + agent_tasks
├── data/                           # gitignored - volume mount
└── logs/
```
---

## Kullanım Kılavuzu

### 1. Ön Gereksinimler

| Bileşen | Minimum Sürüm | Kontrol |
|---|---|---|
| **Windows** | 10/11 (64-bit) | - |
| **Docker Desktop** | v4.30+ | `docker --version` |
| **Git** | 2.40+ | `git --version` |
| **PowerShell** | 7.x+ önerilir | `$PSVersionTable.PSVersion` |
| **Ollama** (opsiyonel) | 0.20+ | `ollama --version` |

**Donanım önerisi:** Tüm profilleri çalıştırmak için 16 GB+ RAM, 4+ core CPU.

### 2. Kurulum (Sıfırdan)

```powershell
# 1. Repoyu klonla
git clone https://github.com/beratcan42/ad-agency-crewai.git
cd ad-agency-crewai

# 2. .env dosyasını hazırla
Copy-Item .env.example .env
# .env içindeki CHANGE_ME değerlerini gerçek parolalarla değiştirin.

# 3. API anahtarlarını ekle (.env içinde)
#    OPENROUTER_API_KEY=sk-or-...
#    GOOGLE_GEMINI_API_KEY=AIza...

# 4. Temel servisleri başlat
docker compose --profile core --profile agents up -d --wait

# 5. Sağlık kontrolü
.\scripts\doctor.ps1
```

### 3. Docker Profilleri

Sistem modüler profiller ile yönetilir. İhtiyacınız olan profilleri birleştirerek çalıştırabilirsiniz:

| Profil | İçerik | Kaynak Tüketimi |
|---|---|---|
| `core` | Postgres + Redis | ~300 MB |
| `agents` | Agency API + Celery Worker | ~500 MB |
| `obs` | Langfuse (6 container: Web, Worker, Postgres, Redis, ClickHouse, MinIO) | ~2 GB |
| `social` | Postiz + Temporal + yardımcı DB/Redis | ~1 GB |
| `mcp` | MCP Gateway | ~100 MB |
| `ui` | Flowise (görsel ajan arayüzü) | ~400 MB |

```powershell
# Minimum (sadece API + DB)
docker compose --profile core --profile agents up -d

# Tam sistem (tüm profiller)
docker compose --profile core --profile agents --profile obs --profile social --profile mcp --profile ui up -d

# Tek profili kaldır
docker compose --profile ui up -d flowise

# Durdur
docker compose --profile core --profile agents down
```

### 4. Ortam Değişkenleri (.env)

`.env.example` dosyasını `.env` olarak kopyalayın ve aşağıdaki **zorunlu** değişkenleri doldurun:

| Değişken | Açıklama | Örnek |
|---|---|---|
| `POSTGRES_PASSWORD` | Ana veritabanı şifresi | `my_secret_pg_123` |
| `REDIS_PASSWORD` | Redis şifresi | `my_secret_redis` |
| `OPENROUTER_API_KEY` | OpenRouter API anahtarı (ücretsiz modeller) | `sk-or-v1-xxx` |
| `GOOGLE_GEMINI_API_KEY` | Google Gemini Pro erişimi | `AIzaSy...` |
| `VAULT_BASE_PATH_HOST` | Müşteri Vault dizini (Windows yolu) | `D:\Google_Drive\AjansKlasoru` |

> **Güvenlik:** `.env` dosyası `.gitignore` içindedir, **asla** commit etmeyin.

### 5. Yeni Müşteri Ekleme

```powershell
# Vault klasör yapısını oluşturur (00-Inbox, 01-Briefs, ... 99-Arsiv)
.\scripts\new-client.ps1 -ClientId "yeni-firma"

# Müşteri CRM'de otomatik kayıt olur (ilk API çağrısında)
```

Müşteri slug'ı (`ClientId`) tüm API çağrılarında `X-Client-Id` header'ı olarak kullanılır.

### 6. Tek Ajan Çalıştırma

12 ajandan herhangi birini doğrudan çalıştırabilirsiniz:

```powershell
# Senkron çalıştırma (yanıtı bekler, 30-90 sn)
curl -X POST http://localhost:8010/agents/copywriter/run `
  -H "X-Client-Id: akme-tekstil" `
  -H "Content-Type: application/json" `
  -d '{
    "title": "Yaz İndirimi",
    "content": "Tüm plaj ürünlerinde %40 indirim kampanyası",
    "sector": "E-ticaret",
    "max_tokens": 800
  }'
```

```powershell
# Asenkron çalıştırma (Celery kuyruğuna gönderir, hemen task_id döner)
$response = Invoke-RestMethod -Uri "http://localhost:8010/agents/strategist/dispatch" `
  -Method Post `
  -Headers @{"X-Client-Id"="akme-tekstil"; "Content-Type"="application/json"} `
  -Body '{"title":"Pazar Analizi","content":"Türkiye tekstil pazarı"}'

# Görev durumunu sorgula
Invoke-RestMethod -Uri "http://localhost:8010/tasks/$($response.task_id)"
```

**Kullanılabilir ajanlar:** `account_manager`, `customer_service`, `strategist`, `copywriter`, `social_media`, `seo_specialist`, `creative_director`, `data_analyst`, `budget_manager`, `ecommerce_specialist`, `publisher`, `crm_billing`

### 7. Kampanya Akışı (CrewAI Flow)

Tek bir API çağrısıyla 4 ajanı zincirleme çalıştıran uçtan uca kampanya pipeline'ı:

```
Brief → Account Manager → Strategist → Copywriter → Social Media → Postiz Taslağı
```

```powershell
Invoke-RestMethod -Uri "http://localhost:8010/flows/campaign" `
  -Method Post `
  -Headers @{"X-Client-Id"="akme-tekstil"; "Content-Type"="application/json"} `
  -Body '{
    "title": "Kış Kampanyası 2026",
    "content": "Kışlık kaban ve mont koleksiyonu için dijital pazarlama kampanyası. Hedef: 25-45 yaş, orta-üst gelir.",
    "sector": "Tekstil"
  }' `
  -TimeoutSec 300
```

> ⚠️ Flow 4 ardışık LLM çağrısı yaptığı için **2-5 dakika** sürebilir. `TimeoutSec` değerini yeterli tutun.

Yanıt her ajanın çıktısını state içinde döner:

```json
{
  "status": "success",
  "state": {
    "account_manager_output": "## Brief Özeti ...",
    "strategist_output": "## Pazar Özeti ...",
    "copywriter_output": "## Ana Başlık ...",
    "postiz_result": { "status": "success", "content": "## Platform Stratejisi ..." }
  }
}
```

### 8. CRM ve Fatura İşlemleri

```powershell
# Müşteri bilgilerini getir (otomatik kayıt yapar)
Invoke-RestMethod -Uri "http://localhost:8010/crm/clients" `
  -Headers @{"X-Client-Id"="akme-tekstil"}

# Kampanya teklifi oluştur (PDF üretir)
Invoke-RestMethod -Uri "http://localhost:8010/crm/proposals" `
  -Method Post `
  -Headers @{"X-Client-Id"="akme-tekstil"; "Content-Type"="application/json"} `
  -Body '{"title": "2026 Yaz Kampanyası", "total_amount": 75000}'

# Fatura kes (KDV %20 otomatik hesaplanır, PDF üretir)
Invoke-RestMethod -Uri "http://localhost:8010/crm/invoices" `
  -Method Post `
  -Headers @{"X-Client-Id"="akme-tekstil"; "Content-Type"="application/json"} `
  -Body '{"proposal_id": "<UUID>", "amount": 75000, "tax_rate": 20}'
```

PDF dosyaları container içinde `/tmp/proposals/` ve `/tmp/invoices/` altına oluşturulur.

### 9. Obsidian Vault (Müşteri Dosyaları)

Her müşterinin izole bir Vault klasörü vardır. Ajanlar bu dosyaları okuyup yazabilir:

```powershell
# Vault durumu
Invoke-RestMethod -Uri "http://localhost:8010/vault/status"

# Müşteri dosyalarını listele
Invoke-RestMethod -Uri "http://localhost:8010/vault/files" `
  -Headers @{"X-Client-Id"="akme-tekstil"}

# Not oku
Invoke-RestMethod -Uri "http://localhost:8010/vault/note?path=01-Briefs/kampanya.md" `
  -Headers @{"X-Client-Id"="akme-tekstil"}

# Semantik arama (embedding tabanlı)
Invoke-RestMethod -Uri "http://localhost:8010/vault/search" `
  -Method Post `
  -Headers @{"X-Client-Id"="akme-tekstil"; "Content-Type"="application/json"} `
  -Body '{"query": "sosyal medya stratejisi", "limit": 5}'
```

Vault Poller arka planda `.md` dosyalarını izleyerek otomatik olarak vektörel embedding oluşturur.

### 10. İzlenebilirlik (Observability)

#### Langfuse Dashboard

`obs` profilini çalıştırdığınızda Langfuse UI'a erişebilirsiniz:

- **URL:** http://localhost:3001
- **Auth:** `.env`'deki `LANGFUSE_INIT_USER_*` değerleri
- Her LLM çağrısı otomatik olarak Langfuse'a trace olarak gönderilir.

```powershell
# Langfuse bağlantı durumu
Invoke-RestMethod -Uri "http://localhost:8010/stats/langfuse"

# Token kullanım istatistikleri
Invoke-RestMethod -Uri "http://localhost:8010/stats/usage?hours=24"

# Müşteri token bütçesi
Invoke-RestMethod -Uri "http://localhost:8010/stats/budget" `
  -Headers @{"X-Client-Id"="akme-tekstil"}

# Rate limit durumu (tüm model/provider)
Invoke-RestMethod -Uri "http://localhost:8010/stats/limits"
```

#### Koruma Katmanları (Guardrails)

| Mekanizma | Açıklama | Yapılandırma (.env) |
|---|---|---|
| **Rate Limiter** | Redis rolling window ile müşteri başına RPM/RPD | `CREW_MAX_RPM=20` |
| **Circuit Breaker** | Ardışık 3 hata → model 5dk devre dışı, otomatik fallback | `CIRCUIT_BREAKER_FAILURE_THRESHOLD=3` |
| **Token Budget** | Müşteri başına günlük token limiti, aşılırsa HTTP 429 | `TOKEN_BUDGET_DAILY_GLOBAL=500000` |

### 11. Flowise (Görsel Arayüz)

`ui` profilini çalıştırdığınızda Flowise'a erişebilirsiniz:

- **URL:** http://localhost:3000
- **Auth:** admin / admin (`.env`'den değiştirin)
- Flowise üzerinden Custom Tool ile Agency API'yi tetikleyebilirsiniz.
- Detaylı entegrasyon rehberi: [`docs/flowise_templates/README.md`](docs/flowise_templates/README.md)

### 12. Yedekleme ve Bakım

```powershell
# Tam yedek (Postgres dump + Redis RDB + Vault zip)
.\scripts\backup.ps1

# Sağlık kontrolü (DB, Redis, Langfuse, Vault, tüm container'lar)
.\scripts\doctor.ps1

# Uçtan uca test (3 senaryo)
.\scripts\test-e2e.ps1

# Docker imajlarını yeniden derle (kod değişikliği sonrası)
docker compose --profile agents build --no-cache agency-api
docker compose --profile agents up -d agency-api
```

### 13. Sorun Giderme

| Sorun | Çözüm |
|---|---|
| `port 8000 already in use` | `.env`'de `AGENCY_API_PORT=8010` olarak bırakın (varsayılan). |
| Langfuse container'ları başlamıyor | Minimum 8 GB boş RAM gerekli. `obs` profilini opsiyonel tutabilirsiniz. |
| Ollama modelleri çalışmıyor | `ollama list` ile modellerin yüklü olduğunu doğrulayın. Container `host.docker.internal:11434` kullanır. |
| Flow timeout (> 5dk) | OpenRouter ücretsiz modellerin yanıt süreleri değişkendir. `.env`'de `CREW_MAX_EXECUTION_TIME=600` artırın. |
| `crm.clients` tablosu yok | Eski DB volume: `Get-Content scripts\sql\init\05-crm-schema.sql \| docker exec -i adagency-postgres psql -U agency -d agency` |
| `note_embeddings` tablosu yok | Eski DB volume: `Get-Content scripts\sql\init\03-note-embeddings.sql \| docker exec -i adagency-postgres psql -U agency -d agency` |
| Swagger UI'a erişim | http://localhost:8010/docs adresini ziyaret edin. |

### 14. Detaylı Dokümantasyon

| Doküman | İçerik |
|---|---|
| [`docs/PROJE-DURUMU.md`](docs/PROJE-DURUMU.md) | Proje tarihçesi, aşama detayları, kaldığımız yer |
| [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md) | Tüm endpoint'lerin istek/yanıt örnekleri |
| [`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md) | 12 ajan listesi, tool'lar, Flow mimarisi, fallback katmanları |
| [`docs/flowise_templates/README.md`](docs/flowise_templates/README.md) | Flowise Custom Tool ve Webhook entegrasyon rehberi |

---

## Lisans

Özel proje. Berat Bey'e ait.
