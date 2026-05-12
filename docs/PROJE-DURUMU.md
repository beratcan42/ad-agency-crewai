# Proje Durumu — Kaldığımız Yer Rehberi

**Son Güncelleme:** 13 Mayıs 2026, 00:15 (UTC+3)
**Aktif Branch:** `main`
**GitHub:** [`beratcan42/ad-agency-crewai`](https://github.com/beratcan42/ad-agency-crewai) (private)
**API Sürüm:** `0.4.0`
**Son Commit:** AŞAMA 5 tamamlandı (Langfuse + guardrails + token bütçesi; `git log -1`)

---

## 1. Tamamlanan Aşamalar

### ✅ AŞAMA 0 — Preflight

Sistem hazır: Windows 11 + Docker Desktop v29.4.3 + Ollama v0.23.2 + Google Drive senkron (`D:\Google_Drive\AjansKlasoru`) + Git + GitHub Desktop.

Local Ollama modelleri: `qwen3.5:9b`, `qwen3:8b`, `qwen3-coder:30b`, `qwen3-vl:8b`, `gemma3:12b`, `gpt-oss:20b`, `llama3.1:latest`.

API key'leri canlı doğrulandı: OpenRouter, Google Gemini, HuggingFace.

### ✅ AŞAMA 1 — Foundation (`305a3ed`)

- `adagency-postgres` (Postgres 16.13 + pgvector 0.8.2)
- `adagency-redis` (Redis 7.4.9, 512MB, `allkeys-lru`, AOF)
- Schema'lar: `agency`, `crm`, `memory`, `audit`

### ✅ AŞAMA 2 — Agency Core (`f842b59`)

- FastAPI + CrewAI v1.14.3 + Celery 5.6.3
- LiteLLM 4-katmanlı fallback router (minimal)
- 1 ajan: Account Manager (uçtan uca canlı)
- Endpoint: `/healthz`, `/readyz`, `/version`, `/brief`

### ✅ AŞAMA 3 — 12 Ajan + Akıllı Router

| Alt-aşama | İçerik | Commit |
|---|---|---|
| **3.A** | OpenRouter canlı `:free` envanter (29 model) ile 12 ajan zinciri recalibre. Owl Alpha 1M ctx (`openrouter/owl-alpha`). | `665c939` |
| **3.B** | LiteLLM native syntax: `gemini/<model>` ve `ollama_chat/<model>`. OpenAI-compat shim kaldırıldı. | `665c939` |
| **3.C** | 12 ajan registry (`crew/agents/registry.py`) + generic `run_agent` builder + Celery task factory (her ajan models.yaml'daki queue'sunda otomatik). | `4ed5c40` |
| **3.D** | Redis rolling window rate limiter (RPM/RPD) + Postgres `agency.usage_logs` telemetry + proactive fallback (%85 RPM, %90 RPD eşik). | `66dbb16` |
| **3.E** | `/agents`, `/agents/{id}/run`, `/agents/{id}/dispatch`, `/tasks/{id}`, `/stats/usage`, `/stats/limits` endpoint'leri. | `4ed5c40` + `66dbb16` |

### ✅ AŞAMA 4 — Obsidian Vault + Drive + Hybrid Bellek

| Parça | Dosya / davranış |
|---|---|
| Bind mount | `docker-compose.yml`: `agency-api` + `agency-worker` → `${VAULT_BASE_PATH_HOST:-./data/staging/vaults}:/vaults` |
| Şablon | `scripts/templates/vault/` (00-Inbox … 99-Arsiv) |
| Yeni müşteri | `scripts/new-client.ps1 -ClientId "slug"` |
| SQL | `scripts/sql/init/03-note-embeddings.sql` → tablo `agency.note_embeddings` |
| Watcher | `src/vault/poller.py` asyncio döngüsü; `.md` değişince chunk + `litellm` Gemini embedding |
| Heartbeat | `<vault>/<client>/.agency-heartbeat.json` |
| REST | `/vault/status`, `/vault/files`, `/vault/note`, `/vault/search` |
| Crew (sync) | `src/crew/tools/vault_fs.py` |

### ✅ AŞAMA 5 — Langfuse + Guardrails + Token Bütçesi (v0.4.0)

| Parça | Dosya / davranış |
|---|---|
| **Langfuse v3 self-hosted** | 6 container (`obs` profili): `langfuse-web` (UI port 3001), `langfuse-worker`, ayrı Postgres/Redis/ClickHouse/MinIO |
| **Headless init** | `LANGFUSE_INIT_*` env vars → org/proje/key otomatik oluşturma (UI gerekmez) |
| **LiteLLM callback** | `src/observability/langfuse_integration.py` — `litellm.success_callback` + `failure_callback` ile her LLM çağrısı trace olarak Langfuse'a gönderilir |
| **Circuit breaker** | `src/guardrails/circuit_breaker.py` — Redis key ile provider bazlı ardışık hata takibi; eşik aşılınca (3 hata) 5dk devre dışı |
| **Token bütçesi** | `src/guardrails/token_budget.py` — Postgres `agency.token_budgets` tablosu; müşteri bazlı günlük/kampanya limiti; günlük otomatik reset |
| **Budget middleware** | `src/middleware/token_budget.py` — POST `/agents/*/run\|dispatch` için bütçe kontrolü; bütçe aşılırsa HTTP 429 |
| **Vault @tool** | `src/crew/tools/vault_tools.py` — CrewAI `@tool` dekoratörü ile 4 tool: `VaultReadNote`, `VaultWriteNote`, `VaultListFiles`, `VaultSemanticSearch` |
| **Model router** | `src/router/model_router.py` — Langfuse metadata + circuit breaker check + token budget kaydı entegre |
| **REST** | `/stats/langfuse`, `/stats/budget` endpoint'leri |
| **SQL** | `scripts/sql/init/04-token-budgets.sql` |
| **Doctor** | Langfuse container'ları + `token_budgets` tablo + `/stats/langfuse` kontrolleri |

---

## 2. Çalışan Servisler

| Container | Port (host) | Profil | Health | Aşama |
|---|---|---|---|---|
| `adagency-postgres` | 5432 | core | ✅ | 1 |
| `adagency-redis` | 6379 | core | ✅ | 1 |
| `adagency-api` (FastAPI + CrewAI) | **8010** | agents | ✅ | 2–5 |
| `adagency-worker` (Celery, 12 task) | - | agents | ✅ | 2–5 |
| `adagency-langfuse-web` | **3001** | obs | ✅ | 5 |
| `adagency-langfuse-worker` | - | obs | ✅ | 5 |
| `adagency-langfuse-postgres` | - | obs | ✅ | 5 |
| `adagency-langfuse-redis` | - | obs | ✅ | 5 |
| `adagency-langfuse-clickhouse` | - | obs | ✅ | 5 |
| `adagency-langfuse-minio` | - | obs | ✅ | 5 |

Bekleyen: Postiz (6), MCP Gateway (6), CRM (7), Flowise (8).

---

## 3. 12 Ajan Modeli ve Queue Dağılımı

| # | Agent ID | Primary | Gemini | Alt. | Ollama | Queue |
|---|---|---|---|---|---|---|
| 1 | `account_manager` | `openrouter/owl-alpha` (1M) | `gemini-2.5-pro` | `nvidia/nemotron-3-super-120b` | `qwen3.5:9b` | q_heavy |
| 2 | `customer_service` | `google/gemma-4-31b-it:free` | `gemini-2.5-flash` | `meta-llama/llama-3.3-70b` | `gemma3:12b` | q_fast |
| 3 | `strategist` | `nvidia/nemotron-3-super-120b` | `gemini-2.5-pro` | `openai/gpt-oss-120b` | `gpt-oss:20b` | q_heavy |
| 4 | `copywriter` | `meta-llama/llama-3.3-70b` | `gemini-2.5-flash` | `dolphin-mistral-24b-venice` | `gemma3:12b` | q_heavy |
| 5 | `social_media` | `qwen/qwen3-next-80b-a3b-instruct` | `gemini-2.5-flash` | `llama-3.3-70b` | `qwen3:8b` | q_fast |
| 6 | `seo_specialist` | `google/gemma-4-31b-it` | `gemini-2.5-pro` | `qwen3-next-80b` | `gemma3:12b` | q_research |
| 7 | `creative_director` | `nvidia/nemotron-nano-12b-v2-vl` (vision) | `gemini-2.5-pro` | `gemma-4-31b-it` | `qwen3-vl:8b` | q_heavy |
| 8 | `data_analyst` | `qwen/qwen3-coder:free` | `gemini-2.5-pro` | `gpt-oss-120b` | `qwen3-coder:30b` | q_research |
| 9 | `budget_manager` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | `gemini-2.5-pro` | `qwen3-coder:free` | `gpt-oss:20b` | q_research |
| 10 | `ecommerce_specialist` | `qwen3-next-80b-a3b-instruct` | - | `gemini-2.5-flash` | `qwen3:8b` | q_research |
| 11 | `publisher` | `gemini-2.5-flash` | - | `llama-3.2-3b-instruct` | `llama3.1` | q_fast |
| 12 | `crm_billing` | `gemini-2.5-flash` | - | `qwen3-coder:free` | `qwen3-coder:30b` | q_fast |

---

## 4. API Endpoint Kontrol Listesi

```bash
# Health
curl http://127.0.0.1:8010/healthz

# Ajan registry (public)
curl http://127.0.0.1:8010/agents

# Senkron çağrı
curl -X POST http://127.0.0.1:8010/agents/copywriter/run \
  -H "X-Client-Id: akme-tekstil" -H "Content-Type: application/json" \
  -d '{"title":"...","content":"...","max_tokens":600}'

# Async dispatch
curl -X POST http://127.0.0.1:8010/agents/social_media/dispatch \
  -H "X-Client-Id: akme-tekstil" -H "Content-Type: application/json" \
  -d '{"title":"...","content":"..."}'

# Task durumu
curl http://127.0.0.1:8010/tasks/<task_id>

# Telemetry
curl http://127.0.0.1:8010/stats/usage?hours=24
curl http://127.0.0.1:8010/stats/limits

# Vault (Asama 4)
curl http://127.0.0.1:8010/vault/status
curl -H "X-Client-Id: akme-tekstil" http://127.0.0.1:8010/vault/files
curl -s -X POST http://127.0.0.1:8010/vault/search \
  -H "X-Client-Id: akme-tekstil" -H "Content-Type: application/json" \
  -d "{\"query\":\"kampanya\",\"limit\":5}"

# Langfuse + Budget (Asama 5)
curl http://127.0.0.1:8010/stats/langfuse
curl -H "X-Client-Id: akme-tekstil" http://127.0.0.1:8010/stats/budget
```

---

## 5. Bilinen Sınırlamalar / Notlar

- **Ollama**: `host.docker.internal:11434` üzerinden erişiliyor; container içi DNS düzgün ayarlanmış (`extra_hosts`).
- **Multi-stage Dockerfile**: Şu an single-stage (transitive dep sorunları nedeniyle); optimize edilebilir.
- **Account Manager geriye dönük endpoint**: `/brief` hâlâ çalışır (Asama 2 demo), `/agents/account_manager/run` ile aynı işi yapar.
- **`logs/`**: Cursor ortamında gitignore; vault/E2E test payload'ları için `logs/` altına yazılan dosyalar repoda olmayabilir.
- **`note_embeddings`**: Eski Postgres volume kullanıyorsanız `03-note-embeddings.sql` dosyasını container'a kopyalayıp `psql -f` ile bir kez çalıştırın.
- **`token_budgets`**: Eski Postgres volume kullanıyorsanız `04-token-budgets.sql` dosyasını container'a kopyalayıp `psql -f` ile bir kez çalıştırın.
- **Langfuse v3**: 6 ek container gerektirir (CH + MinIO kaynak tüketimi yüksek); dev makinede 4+ core, 16GB+ RAM önerilir.
- **Langfuse headless init**: İlk başlatmada org/proje/key otomatik oluşturulur; UI'da ek yapılandırma gerekmez.

---

## 6. Sonraki Adım: AŞAMA 6 — Postiz + MCP Gateway

- Postiz self-hosted (sosyal medya paylaşım otoması)
- MCP Gateway (ajan<->araç köprüsü)
- CrewAI Flow'larla çok-ajanlı kampanya pipeline'ı

---

## 7. Bir Sonraki Sohbete Geçerken

1. `docs/PROJE-DURUMU.md` + `README.md`
2. `git log --oneline -8`
3. `.\scripts\doctor.ps1`
4. `curl http://127.0.0.1:8010/stats/langfuse`
5. Berat Bey'den **AŞAMA 6** onayı
