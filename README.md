# CrewAI Multi-Agent Reklam Ajansı

> 12 uzman AI ajanlı, çok müşterili (multi-tenant), tamamen ücretsiz reklam ajansı sistemi.
> OpenRouter free + Google Gemini AI Pro + Ollama hibrit dağılım. Obsidian Vault hafıza,
> Google Drive senkron, Postiz ile gerçek sosyal medya yayını, CRM/Fatura modülü.

**Durum:** AŞAMA 1 (Foundation) tamamlandı | Geliştirme devam ediyor

---

## Hızlı Başlangıç (Windows + PowerShell)

```powershell
# 1) Repo'yu klonla / bu klasörü aç
cd c:\YapayZekaa\Cursor\sesli_asistan

# 2) İlk kurulum (sihirbaz)
.\scripts\setup.ps1

# 3) Veya sadece core stack'i başlat
.\scripts\start.ps1

# 4) Sağlık kontrolü
.\scripts\doctor.ps1

# 5) Durdur
.\scripts\stop.ps1
```

## Aşamalı Mimari

| Aşama | Bileşen | Durum |
|---|---|---|
| 0 | Preflight (Docker/Ollama/Drive/Obsidian kontrol) | TAMAM |
| **1** | **Foundation (postgres+pgvector, redis)** | **TAMAM** |
| 2 | Agency Core (FastAPI + CrewAI v1.14.3) | Bekliyor |
| 2.5 | Multi-tenant altyapı | Bekliyor |
| 3 | 12 Ajan + Hibrit Model Router | Bekliyor |
| 4 | Obsidian Vault + Drive Sync | Bekliyor |
| 4.5 | Drive Staging-First Pattern | Bekliyor |
| 5 | Guardrails + Langfuse Observability | Bekliyor |
| 6 | MCP Gateway + Postiz + Tools | Bekliyor |
| 7 | CRM & Fatura Servisi | Bekliyor |
| 8 | Flowise UI (webhook tetikleyici) | Bekliyor |
| 9 | Dokümantasyon | Bekliyor |
| 10 | E2E Test | Bekliyor |
| 11 | Final Review | Bekliyor |

## Servisler ve Portlar

| Servis | Port | Profil | Durum |
|---|---|---|---|
| Postgres + pgvector | 5432 | core | AKTIF |
| Redis 7 | 6379 | core | AKTIF |
| Agency API | 8000 | agents | Aşama 2 |
| Flowise | 3000 | ui | Aşama 8 |
| CRM Service | 8001 | ui | Aşama 7 |
| Langfuse | 3001 | obs | Aşama 5 |
| MCP Gateway | 8811 | mcp | Aşama 6 |
| Postiz | 5000 | social | Aşama 6 |
| Gotenberg (PDF) | 3010 | ui | Aşama 7 |
| Ollama (host) | 11434 | - | Aşama 3 |

## Ana Komutlar

```powershell
# Docker
docker compose --profile core up -d           # core stack
docker compose --profile "*" up -d            # tüm sistem
docker compose ps                             # çalışanlar
docker compose logs -f postgres               # log takip

# PowerShell scriptler
.\scripts\setup.ps1                           # tam kurulum sihirbazı
.\scripts\setup.ps1 -Stage 3                  # belirli aşamadan
.\scripts\setup.ps1 -Resume                   # kaldığı yerden
.\scripts\start.ps1 -Profile agents           # belirli profil
.\scripts\doctor.ps1                          # sağlık kontrolü
.\scripts\backup.ps1                          # yedek al
.\scripts\stop.ps1                            # temiz kapat

# Make (opsiyonel - Git Bash veya WSL içinde)
make up                                       # core
make doctor                                   # sağlık
make logs SERVICE=postgres                    # log filtre
make backup                                   # yedek
```

## Mimari Karar Özeti

- **Multi-agent:** CrewAI v1.14.3 (Flow + @persist + checkpoint/resume)
- **LLM:** Hibrit — OpenRouter free (7 model) + Google Gemini AI Pro + Ollama yerel
- **Multi-tenant:** X-Client-Id middleware + namespace isolation
- **Hafıza:** Obsidian Vault (MD) + pgvector hybrid, Google Drive senkron
- **Yayın:** Postiz MCP (self-hosted) → X/IG/TikTok/LinkedIn/FB/+15
- **CRM:** FastAPI + Postgres + Gotenberg (PDF), Türkiye KDV %20
- **Sandbox:** Yerel Docker (E2B cloud yerine, KVKK uyumlu)
- **Observability:** Langfuse self-hosted + OpenTelemetry

Detaylı mimari için: `MIMARI.md` (Aşama 9'da hazırlanacak)

## Dizin Yapısı

```
sesli_asistan/
  docker-compose.yml          # Profil bazlı servisler
  .env                        # Gerçek secrets (gitignored)
  .env.example                # Şablon
  Makefile                    # make up/down/logs/doctor
  scripts/                    # PowerShell setup/doctor/backup
    sql/init/                 # Postgres init SQL
  agency/                     # Aşama 2'de doldurulacak
  mcp/                        # Aşama 6'da doldurulacak
  data/                       # Volume mount (gitignored)
  docs/                       # Detaylı dökümanlar
```

## Lisans

Özel proje. Berat Bey'e ait.
