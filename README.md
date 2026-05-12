# CrewAI Multi-Agent Reklam Ajansı

> 12 uzman AI ajanlı, çok müşterili (multi-tenant), tamamen ücretsiz reklam ajansı sistemi.
> OpenRouter free + Google Gemini AI Pro + Ollama hibrit dağılım. Obsidian Vault hafıza,
> Google Drive senkron, Postiz ile gerçek sosyal medya yayını, CRM/Fatura modülü.

**Durum:** AŞAMA 10 TAMAMLANDI — Final Review aşamasında | API `v0.4.0` | Hedef: `v1.0.0`

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
| 11 | Final Review (v1.0.0 Release) | ⏳ | - |

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

## Lisans

Özel proje. Berat Bey'e ait.
