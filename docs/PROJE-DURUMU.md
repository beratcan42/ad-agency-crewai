# Proje Durumu — Kaldığımız Yer Rehberi

**Son Güncelleme:** 12 Mayıs 2026, 21:10 (UTC+3)
**Aktif Branch:** `main`
**GitHub:** [`beratcan42/ad-agency-crewai`](https://github.com/beratcan42/ad-agency-crewai) (private)
**Son Commit:** AŞAMA 3 tamamlandı (bkz. commit özetleri aşağıda)

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

#### Canlı kanıt (12 May 2026)
- `account_manager` → openrouter/owl-alpha primary, 952 token, 25.3s
- `social_media` → gemini-2.5-flash (organic fallback), 672 token, 2.7s
- `crm_billing` → gemini-2.5-flash, 706 token, 2.5s, JSON çıktı doğru
- `publisher` async dispatch → Celery task SUCCESS, 568 token, 2.3s
- `/stats/usage`: 4 çağrı, 2330 token, by_status: success=3 fallback=1
- `/stats/limits`: 20 model takip ediliyor (örn. gemini-2.5-flash %20 RPM)
- Postgres `agency.usage_logs`: tablo aktif, 5 index

---

## 2. Çalışan Servisler

| Container | Port (host) | Profil | Health | Aşama |
|---|---|---|---|---|
| `adagency-postgres` | 5432 | core | ✅ | 1 |
| `adagency-redis` | 6379 | core | ✅ | 1 |
| `adagency-api` (FastAPI + CrewAI) | **8010** | agents | ✅ | 2-3 |
| `adagency-worker` (Celery, 12 task) | - | agents | ✅ | 2-3 |

Bekleyen: Langfuse (5), Postiz (6), Flowise (8), MCP Gateway (6), CRM (7).

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
```

---

## 5. Bilinen Sınırlamalar / Notlar

- **Ollama**: `host.docker.internal:11434` üzerinden erişiliyor; container içi DNS düzgün ayarlanmış (`extra_hosts`).
- **Multi-stage Dockerfile**: Şu an single-stage (transitive dep sorunları nedeniyle); optimize edilebilir.
- **Account Manager geriye dönük endpoint**: `/brief` hâlâ çalışır (Asama 2 demo), `/agents/account_manager/run` ile aynı işi yapar.
- **Account Manager logs hatası**: PowerShell `return` döngüden çıkamıyor — sadece test scriptinde, ürünü etkilemez.
- **`logs/test-*.json`**: gitignored olmamalı (test scriptleri kullanıyor); şu an logs/ dizini gitignore'da, sorun çıkarsa dosyaları repo'ya alacağız.

---

## 6. Sonraki Adım: AŞAMA 4 — Obsidian Vault + Drive Sync

Berat Bey'in onayıyla başlanacak görevler:

### 4.A — Vault iskeleti & MCP entegrasyonu
- `vaults/<client_id>/` (D:\Google_Drive\AjansKlasoru altında)
- Obsidian klasör yapısı: `00-Inbox`, `01-Brief`, `02-Strateji`, `03-Copy`, `04-Sosyal`, `05-SEO`, `06-Gorsel`, `07-Veri`, `08-Bütçe`, `09-Yayın`, `99-Arsiv`
- `new-client.ps1`: yeni müşteri için Vault oluştur (şablondan)

### 4.B — Vault okuma/yazma CrewAI tool'u
- `agency/src/crew/tools/obsidian_vault.py`: read_note, write_note, list_notes, search_notes
- Tüm 12 ajan bu tool'u kullanabilir

### 4.C — Embedder & pgvector hybrid search
- Watcher (watchdog) Vault'ta değişiklik takip eder
- Yeni/değişen notları embed eder (Gemini → fallback bge-m3) ve `agency.note_embeddings` tablosuna yazar
- Hybrid search: BM25 (`pg_trgm`) + dense vector (cosine)

### 4.D — Drive senkron sağlığı
- Vault klasörünün Drive ile sync olduğunu doğrulamak için heartbeat dosyası
- `doctor.ps1`'a yeni check

### Tahmini efor
~400 satır kod + ~50 satır SQL + 5-6 endpoint + tool entegrasyonu. 60-90 dakika.

---

## 7. Bir Sonraki Sohbete Geçerken

Bu dosya kaldığımız yerin tam haritasıdır. Yeni bir sohbet açtığında:

1. Bu dosyayı oku (`docs/PROJE-DURUMU.md`)
2. `git log --oneline -10` → son commitleri gör
3. `.\scripts\doctor.ps1` → canlı sistem durumu
4. `curl http://127.0.0.1:8010/agents` → 12 ajan yaşıyor mu doğrula
5. Berat Bey'den AŞAMA 4 onayı al, başla
