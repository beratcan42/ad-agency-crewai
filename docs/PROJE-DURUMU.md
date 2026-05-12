# Proje Durumu — Kaldığımız Yer Rehberi

**Son Güncelleme:** 12 Mayıs 2026, 19:15 (UTC+3)
**Aktif Branch:** `main`
**Son Commit:** `f842b59 feat(stage-2): Agency Core - FastAPI + CrewAI 1.14.3 + Account Manager + Celery`

---

## 1. Tamamlanan Aşamalar

### ✅ AŞAMA 0 — Preflight (sistem tespiti)

| Bileşen | Sürüm | Durum |
|---|---|---|
| Windows 11 | build 26100 | OK |
| PowerShell | 5.1.26100 | OK |
| WSL2 | Ubuntu-22.04 (default) | OK |
| Docker Desktop | v29.4.3 | Daemon çalışıyor |
| Ollama | v0.23.2 | Port 11434 dinliyor, qwen3.5:9b + 9 başka model var |
| Git | v2.52.0 | OK |
| GitHub Desktop | v3.5.8 | OK |
| Obsidian | v1.12.7 | OK |
| Google Drive | v124.0.3.0 | `D:\Google_Drive\AjansKlasoru` senkron aktif |
| CPU | Ryzen 5 7600 (6c/12t) | `UVICORN_WORKERS=5` |
| RAM | 31.1 GB | OK |

**API Key'leri canlı doğrulandı (.env'de manuel dolu):**
- `OPENROUTER_API_KEY` (sk-or-..., 73 char) → `/auth/key` OK
- `GOOGLE_GEMINI_API_KEY` (AIza..., 39 char) → gemini-2.5-flash/pro/2.0-flash listelendi
- `HUGGINGFACE_TOKEN` (hf_..., 37 char) → user: dddd232

### ✅ AŞAMA 1 — Foundation (commit `305a3ed`)

**Container'lar (her ikisi healthy):**
- `adagency-postgres` — Postgres 16.13 + pgvector 0.8.2, port 5432
  - Schemas oluşturuldu: `agency`, `crm`, `memory`, `audit` (4/4)
  - Tablolar: `agency.clients`, `agency.health_check`
- `adagency-redis` — Redis 7.4.9, port 6379, `maxmemory 512mb`, `allkeys-lru`, appendonly

**Üretilen Dosyalar (14):**
- `docker-compose.yml` (7 profil: `core/agents/memory/ui/social/obs/mcp`)
- `.env` + `.env.example` (random secrets — Postgres/Redis/JWT)
- `.gitignore` + `.gitattributes` (CRLF için PS1, LF gerisi)
- `Makefile` (Windows uyumlu)
- `scripts/setup.ps1` (aşamalı sihirbaz)
- `scripts/doctor.ps1` (sağlık kontrolü)
- `scripts/start.ps1`, `stop.ps1`, `backup.ps1`
- `scripts/sql/init/01-init-pgvector.sql`
- `README.md`

**Production hardening uygulananlar:**
- Redis OOM: `maxmemory 512mb`, `allkeys-lru`, appendonly yes
- Health check her container'da (interval 10s, retries 10)
- Port binding `127.0.0.1` (dış dünya kapalı)
- Random secrets (32 byte base64url)
- `restart: unless-stopped`

### ✅ AŞAMA 2 — Agency Core (commit `f842b59`)

**Yeni Container'lar:**
- `adagency-api` — FastAPI + CrewAI, **port 8010** (host'ta 8000 başka servis tarafından tutuldu)
- `adagency-worker` — Celery, 4 queue (`q_heavy/q_fast/q_io/q_research`)

**Bağımlılık Pinleri (`agency/pyproject.toml`):**
```
crewai==1.14.3
crewai-tools>=1.14,<1.16
litellm                              # CrewAI artık transitive getirmiyor; ekledim
fastapi==0.136.1
uvicorn[standard]==0.35.0
pydantic-settings==2.10.1
asyncpg==0.30.0
psycopg[binary]==3.2.5
sqlalchemy[asyncio]==2.0.36
alembic==1.14.0
redis[hiredis]==5.2.1
pgvector==0.3.6
celery[redis]==5.6.3                 # kombu transitive (>=5.6)
langfuse==4.6.1
opentelemetry-instrumentation-*      # crewai ~=1.34 pin'liyor, biz pinsiz bıraktık
structlog==24.4.0
packaging>=24.0                      # litellm langfuse integration için
pyyaml, watchdog, orjson, tenacity, python-multipart
```

**Üretilen Modüller (`agency/src/`):**
```
src/
├── main.py                          # FastAPI lifespan + middleware + router
├── api/routes.py                    # /healthz, /readyz, /version, /brief
├── middleware/client_context.py     # X-Client-Id zorunlu (JSONResponse, regex doğrulamalı)
├── router/model_router.py           # 4-katmanlı fallback (litellm)
├── config/
│   ├── settings.py                  # Pydantic Settings (.env okur)
│   ├── loader.py                    # models.yaml yükleyici
│   └── models.yaml                  # SADECE account_manager dolu
├── crew/agents/account_manager.py   # System prompt + agent meta
├── crew/builder.py                  # run_account_manager() async
├── workers/celery_app.py            # 4 queue + Celery config
└── workers/account_manager_worker.py # @shared_task on q_heavy
```

**Canlı Test (Akme Tekstil Brief):**
```
POST /brief  (X-Client-Id: akme-tekstil)
  body: "Akme Tekstil 2026 yaz koleksiyonu IG+TikTok kampanyası..."

Result:
  provider: openrouter
  model:    nvidia/nemotron-3-super-120b-a12b:free  (3. fallback)
  latency:  31.8s
  tokens:   1018 (418 prompt + 600 completion)
  cost:     $0
```

**Fallback Zinciri Gözlemi:**
1. `owl/owl-alpha:free` → 404/ERROR (OpenRouter'da yok — plan varsayım)
2. `gemini-2.5-pro` → FAIL (OpenAI-compat base_url `/v1beta/openai/` yanlış)
3. `nvidia/nemotron-3-super-120b-a12b:free` → ✅ SUCCESS

**Middleware testi:**
- `POST /brief` (X-Client-Id eksik) → **400** OK
- `GET /healthz` → **200** (exempt)

---

## 2. Önemli Çevresel Değişkenler

```
PROJE KOK         : c:\YapayZekaa\Cursor\sesli_asistan
VAULT_BASE_PATH_HOST : D:\Google_Drive\AjansKlasoru        # Drive senkron aktif
VAULT_BASE_PATH      : /vaults                              # container içi
AGENCY_API_PORT      : 8010 (host) -> 8000 (container)
UVICORN_WORKERS      : 5
OLLAMA_URL           : http://host.docker.internal:11434
OLLAMA_DEFAULT_MODEL : qwen3.5:9b
COMPOSE_PROJECT_NAME : adagency
```

API key'ler `.env`'de dolu (sk-or-..., AIzaSy..., hf_...). `.env` **gitignored**.

Random secrets (üretilmiş, `.env`'de):
- `POSTGRES_PASSWORD` (24B base64url)
- `REDIS_PASSWORD` (24B base64url)
- `POSTIZ_JWT_SECRET` (32B base64url)
- `FLOWISE_PASSWORD`, `LANGFUSE_SECRET`, `POSTIZ_DB_PASS`

---

## 3. Sonraki Aşama: AŞAMA 3 — 12 Ajan + Hibrit Router

> Plan dosyası: `c:\Users\BERAT\.cursor\plans\crewai_multi-agent_reklam_ajansı_1111b97e.plan.md`

### 3.A — OpenRouter free model envanteri (canlı, ilk iş)

```powershell
curl.exe -s -H "Authorization: Bearer $env:OPENROUTER_API_KEY" `
  https://openrouter.ai/api/v1/models | ConvertFrom-Json | `
  Where-Object { $_.id -like "*:free" } | Select-Object id, context_length
```

`agency/src/config/models.yaml` her ajan için bu listeden geçerli `:free` modellerle yeniden kalibre edilecek. Plan'daki varsayım model adları (owl/owl-alpha, qwen3.6-plus, gemma-4-27b, qwen3-coder-480b, qwen3-next-80b vb.) **doğrulanmadan kullanılmamalı**.

### 3.B — Gemini provider düzeltmesi

Şu anki `models.yaml`:
```yaml
google:
  base_url: https://generativelanguage.googleapis.com/v1beta/openai
```

LiteLLM ile Gemini için doğru kullanım:
- Model adı: `gemini/gemini-2.5-flash` (native) **VEYA**
- OpenAI-compat: base_url `https://generativelanguage.googleapis.com/v1beta/openai/` (sondaki `/` önemli)
- API key parametresi: `api_key` LiteLLM tarafında **`GOOGLE_API_KEY`** env var bekler

`agency/src/router/model_router.py` içindeki `_build_litellm_params` Google dalı yeniden test edilmeli.

### 3.C — 11 yeni ajan dosyası

`agency/src/crew/agents/` altına:
- `customer_service.py` — Müşteri Hizmetleri & Brief
- `strategist.py` — Strateji Analisti (DDG MCP)
- `copywriter.py` — Copywriter
- `social_media.py` — Sosyal Medya Uzmanı
- `seo_specialist.py` — SEO Uzmanı
- `creative_director.py` — Kreatif Direktör (vision)
- `data_analyst.py` — Veri Analisti (sandbox)
- `budget_manager.py` — Reklam Bütçe Yöneticisi
- `ecommerce_specialist.py` — E-ticaret & Ürün
- `publisher.py` — Yayın & Zamanlama (Postiz)
- `crm_billing.py` — CRM & Fatura

Her biri için `models.yaml` chain'i + `tasks.yaml` görev tanımı + Celery worker task'ı (uygun queue ile).

**Queue dağılımı (planda):**
| Queue | Ajanlar | Concurrency |
|---|---|---|
| `q_heavy` | Account Manager, Strateji, Copywriter, Kreatif | 2 |
| `q_fast` | Müşteri Hizmetleri, Yayın, CRM/Fatura | 4 |
| `q_io` | Sosyal Medya, Veri Analist | 2 |
| `q_research` | SEO, Bütçe, E-ticaret | 2 |

### 3.D — Akıllı Router yükseltmesi

- **Redis rolling window sayacı**: `c:{client}:rpm:{minute}` ve `c:{client}:daily:{date}` keyleriyle her model için RPM + günlük kullanım takibi
- **Proaktif fallback**: Limit %90'a ulaşmadan bir sonraki katmana geç (429 beklemeden)
- **Telemetri**: Postgres `agency.usage_log` tablosu (client_id, agent, provider, model, tokens, cost, latency)
- **Dynamic Agent Tuner** (`router/dynamic_agent_tuner.py`): Provider değişiminde CrewAI agent `max_rpm` ve `max_execution_time` runtime ezilir
  - Ollama: `max_rpm=None`, `max_execution_time=600`
  - Google: `max_rpm=60`, `max_execution_time=300`
  - OpenRouter: `max_rpm=20`, `max_execution_time=300`

### 3.E — Orchestrator API endpoint'leri

- `POST /agents/{agent_id}/run` — tek ajan manual test
- `POST /campaigns` — Account Manager → seçtiği ajanları Celery'ye dispatch
- `GET /campaigns/{id}` — durum takibi
- `GET /stats/usage` — model/ajan/müşteri başına token kullanımı

### 3.F — Doctor + commit

`doctor.ps1`'e her ajan worker'ı için ayrı health gösterimi.

**Tahmini süre:** 40-60 dakika

---

## 4. Bilinen Sorunlar / TODO

| # | Sorun | Aşama | Öncelik |
|---|---|---|---|
| 1 | `owl/owl-alpha:free` OpenRouter'da yok — models.yaml kalibrasyonu | 3.A | YÜKSEK |
| 2 | Gemini OpenAI-compat base_url yanlış — native syntax | 3.B | YÜKSEK |
| 3 | `agency-worker` healthcheck `celery inspect ping` yavaş başlıyor (~45s) | 3 | DÜŞÜK |
| 4 | Multi-stage Dockerfile transitive dep kaybediyordu — single-stage kaldı, ileride wheel-based optimize edilebilir | 9 | DÜŞÜK |
| 5 | Vault klasörü `D:\Google_Drive\AjansKlasoru` altında `Drive'ım` Türkçe — Aşama 4 öncesi Drive dili İngilizce'ye veya bir alt klasöre kurulum | 4 | ORTA |

---

## 5. Yeni Sohbette Başlatma Komutu

Yeni sohbette aşağıdaki promptu ver:

```
Plan: c:\Users\BERAT\.cursor\plans\crewai_multi-agent_reklam_ajansı_1111b97e.plan.md
Durum: c:\YapayZekaa\Cursor\sesli_asistan\docs\PROJE-DURUMU.md

Berat Bey, kaldığımız yerden devam ediyoruz.
AŞAMA 2 (Agency Core) tamamlandı, son commit f842b59.
Account Manager canlı çalışıyor, fallback zinciri test edildi.

Şimdi AŞAMA 3'e geçelim:
1) Önce OpenRouter'dan canlı :free model envanteri çek
2) Gemini provider'ı native LiteLLM syntax'ına çevir
3) 11 yeni ajanı ekle (customer_service ... crm_billing)
4) Akıllı router (Redis rolling window + proaktif fallback + dynamic agent tuner)
5) /campaigns endpoint + Celery dispatch

PROJE-DURUMU.md'yi oku, AŞAMA 3.A'dan başla.
```

---

## 6. Hızlı Doğrulama (Yeni sohbet açtığında ilk çalıştırılacak)

```powershell
cd c:\YapayZekaa\Cursor\sesli_asistan

# 1) Container'lar ayakta mı?
docker compose ps

# 2) Sağlık kontrolü
.\scripts\doctor.ps1

# 3) /healthz canlı mı?
curl http://127.0.0.1:8010/healthz

# 4) Git durumu
git log --oneline -5
git status
```

Bunların hepsi yeşil dönerse AŞAMA 3'e güvenle başlanabilir.
