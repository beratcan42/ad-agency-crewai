# =================================================================
# CrewAI Multi-Agent Reklam Ajansi - Makefile
# =================================================================
# Windows uyumlu (PowerShell + Git Bash / WSL2 hepsinde calisir).
# PowerShell'den `make` icin: `choco install make` veya `scoop install make`
# Alternatif: PowerShell'den dogrudan `.\scripts\*.ps1` calistir.
# =================================================================

SHELL := /bin/sh
COMPOSE := docker compose
PROFILE_CORE := --profile core
PROFILE_FULL := --profile core --profile agents --profile memory --profile ui --profile social --profile obs --profile mcp

.DEFAULT_GOAL := help

.PHONY: help up up-core up-full down stop logs ps doctor reset clean backup new-client

help:  ## Bu yardim mesajini goster
	@echo "==========================================="
	@echo "  CrewAI Multi-Agent Reklam Ajansi"
	@echo "==========================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: up-core  ## Varsayilan: core profil baslat (postgres+redis)

up-core:  ## Core profil baslat (postgres+pgvector + redis)
	$(COMPOSE) $(PROFILE_CORE) up -d --wait
	@echo ""
	@echo "Core servisler hazir:"
	@echo "  - Postgres : 127.0.0.1:5432"
	@echo "  - Redis    : 127.0.0.1:6379"

up-full:  ## Tum profilleri baslat (gelistirme tamamlandiginda)
	$(COMPOSE) $(PROFILE_FULL) up -d --wait

down:  ## Tum servisleri durdur (volume korunur)
	$(COMPOSE) down

stop:  ## Sadece duraklat (container'lar silinmez)
	$(COMPOSE) stop

logs:  ## Tum loglari takip et (SERVICE=postgres ile filtrelenebilir)
	$(COMPOSE) logs -f --tail=100 $(SERVICE)

ps:  ## Calisan container'lari listele
	$(COMPOSE) ps

doctor:  ## Saglik kontrolu (PowerShell scripti calistir)
	@powershell -ExecutionPolicy Bypass -File ./scripts/doctor.ps1

reset:  ## TUM VOLUME'LARI SIL (DIKKAT! Veriler kaybolur)
	@echo "DIKKAT: Tum veriler silinecek. Devam icin RESET yazin:"
	@read confirm; if [ "$$confirm" = "RESET" ]; then $(COMPOSE) down -v; else echo "Iptal"; fi

clean:  ## Image'lari ve volume'lari temizle (FULL RESET)
	$(COMPOSE) down -v --rmi all --remove-orphans

backup:  ## Backup script calistir (Postgres + Vault + Redis)
	@powershell -ExecutionPolicy Bypass -File ./scripts/backup.ps1

new-client:  ## Yeni musteri olustur. Kullanim: make new-client NAME=akme SECTOR=tekstil
	@powershell -ExecutionPolicy Bypass -File ./scripts/new-client.ps1 -Name "$(NAME)" -Sector "$(SECTOR)"
