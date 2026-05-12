-- =================================================================
-- Asama 5: Token butcesi tablosu
-- =================================================================
-- Yeni Postgres volume: docker-entrypoint-initdb.d otomatik calistirir.
-- Mevcut volume: container icinden psql -f ile bir kez calistirin.
-- =================================================================

CREATE TABLE IF NOT EXISTS agency.token_budgets (
    client_id       TEXT NOT NULL,
    period          TEXT NOT NULL DEFAULT 'daily',  -- daily | campaign
    budget_tokens   BIGINT NOT NULL DEFAULT 500000,
    used_tokens     BIGINT NOT NULL DEFAULT 0,
    period_start    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (client_id, period)
);

-- Gunluk reset: cron veya uygulama tarafindan tetiklenir
CREATE INDEX IF NOT EXISTS idx_token_budgets_period
    ON agency.token_budgets (period, period_start);

COMMENT ON TABLE agency.token_budgets IS 'Musteri bazli token butcesi (Asama 5)';
