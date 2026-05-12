# CrewAI Multi-Agent Reklam Ajansı

> 12 uzman AI ajanlı, çok müşterili (multi-tenant), tamamen ücretsiz reklam ajansı sistemi.
> OpenRouter free + Google Gemini AI Pro + Ollama hibrit dağılım. Obsidian Vault hafıza,
> Google Drive senkron, Postiz ile gerçek sosyal medya yayını, CRM/Fatura modülü.

**Durum:** AŞAMA 3 (12 Ajan + Akıllı Router + Telemetry) TAMAMLANDI | 12 ajan canlı, Redis rate limit + Postgres telemetry aktif | AŞAMA 4 (Obsidian + Drive) bekliyor

> Detaylı kaldığımız yer ve sonraki adımlar için: [`docs/PROJE-DURUMU.md`](docs/PROJE-DURUMU.md)

---

## Hızlı Başlangıç (Windows + PowerShell)

```powershell
cd c:\YapayZekaa\Cursor\sesli_asistan

# Stack'i baslat (core + agents)
.\scripts\start.ps1 -Profile core
.\scripts\start.ps1 -Profile agents

# Saglik kontrolu
.\scripts\doctor.ps1

# Account Manager canli test
curl http://127.0.0.1:8010/healthz
curl -X POST http://127.0.0.1:8010/brief `
  -H "Content-Type: application/json" `
  -H "X-Client-Id: akme-tekstil" `
  --data "@logs/test-brief.json"

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
| 4 | Obsidian Vault + Drive Sync (staging-first) | ⏳ Bekliyor | - |
| 5 | Guardrails + Langfuse Observability | ⏳ | - |
| 6 | MCP Gateway + Postiz + Tools | ⏳ | - |
| 7 | CRM & Fatura Servisi | ⏳ | - |
| 8 | Flowise UI (webhook tetikleyici) | ⏳ | - |
| 9 | Dokümantasyon | ⏳ | - |
| 10 | E2E Test (3 senaryo) | ⏳ | - |
| 11 | Final Review | ⏳ | - |

## Çalışan Servisler

| Servis | Container | Port (host) | Profil | Health |
|---|---|---|---|---|
| Postgres 16 + pgvector 0.8.2 | `adagency-postgres` | 5432 | core | ✅ |
| Redis 7.4.9 | `adagency-redis` | 6379 | core | ✅ |
| **Agency API** (FastAPI + CrewAI) | `adagency-api` | **8010** | agents | ✅ |
| **Celery Worker** (4 queue) | `adagency-worker` | - | agents | ✅ |

> NOT: Host'ta port 8000 başka bir Windows servisi (`Manager`, PID 6464) tarafından tutulduğu için Agency API host portu **8010** olarak ayarlandı. Container içi hala 8000.

### Bekleyen Servisler (sonraki aşamalar)

| Servis | Port | Profil | Aşama |
|---|---|---|---|
| Langfuse | 3001 | obs | 5 |
| MCP Gateway | 8811 | mcp | 6 |
| Postiz | 5000 | social | 6 |
| Gotenberg (PDF) | 3010 | ui | 7 |
| CRM Service | 8001 | ui | 7 |
| Flowise | 3000 | ui | 8 |
| Ollama (host) | 11434 | - | aktif |

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
├── .env                          # gerçek secrets (gitignored)
├── .env.example                  # şablon
├── .gitignore / .gitattributes
├── docker-compose.yml            # 7 profil: core/agents/memory/ui/social/obs/mcp
├── Makefile                      # make up/down/logs/doctor
├── README.md                     # bu dosya
├── docs/
│   └── PROJE-DURUMU.md          # detaylı kaldığımız yer rehberi
├── scripts/
│   ├── setup.ps1                # aşamalı sihirbaz (Stage 0-1 dolu)
│   ├── doctor.ps1               # sağlık kontrolü + 12 ajan + telemetry + rate-limit
│   ├── start.ps1, stop.ps1
│   ├── backup.ps1               # pg_dumpall + vault zip + redis rdb
│   └── sql/init/
│       ├── 01-init-pgvector.sql # şema + pgvector extension
│       └── 02-usage-logs.sql    # AŞAMA 3.D telemetry tablosu
├── agency/                       # ✅ AŞAMA 2-3 dolu
│   ├── pyproject.toml           # crewai==1.14.3 + litellm + fastapi + celery
│   ├── Dockerfile               # Python 3.12-slim single-stage
│   ├── .dockerignore
│   └── src/
│       ├── main.py              # FastAPI app
│       ├── api/routes.py        # /healthz /agents /run /dispatch /tasks /stats
│       ├── middleware/          # X-Client-Id zorunlu (stats+agents muaf)
│       ├── router/
│       │   ├── model_router.py  # 4-katmanlı fallback + telemetry + rate limit
│       │   ├── rate_limiter.py  # Redis rolling window (RPM+RPD)
│       │   └── telemetry.py     # Postgres async insert + agregasyon
│       ├── config/              # Pydantic Settings + models.yaml (12 ajan)
│       ├── crew/
│       │   ├── builder.py       # generic run_agent(agent_id, ...)
│       │   └── agents/
│       │       ├── registry.py  # 12 ajan task template + system_prompt builder
│       │       └── account_manager.py  # geriye dönük
│       └── workers/
│           ├── celery_app.py    # 4 queue + 12 task auto-route
│           ├── agent_tasks.py   # 12 ajan için Celery task factory
│           └── account_manager_worker.py  # geriye dönük
├── mcp/                          # ⏳ Aşama 6
├── data/                         # gitignored - volume mount
│   ├── postgres/
│   ├── redis/
│   ├── staging/
│   └── outputs/
└── logs/
    └── test-brief.json          # /brief test payload
```

## Lisans

Özel proje. Berat Bey'e ait.
