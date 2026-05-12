-- =================================================================
-- Asama 3.D — Akilli Router telemetry tablosu
-- =================================================================
-- Her LLM cagrisi (basarili, fallback, error) icin satir yazilir.
-- Stats endpoint'leri bu tablodan agregasyon yapar.
-- =================================================================

CREATE TABLE IF NOT EXISTS agency.usage_logs (
    id              BIGSERIAL PRIMARY KEY,
    ts              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    client_id       TEXT NOT NULL,
    agent_id        TEXT NOT NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    chain_idx       INT  NOT NULL DEFAULT 0,        -- zincirde kacinci katman
    status          TEXT NOT NULL,                  -- success | fallback | error | skip_ratelimit
    prompt_tokens   INT,
    completion_tokens INT,
    total_tokens    INT,
    latency_ms      INT,
    error_class     TEXT,                           -- RateLimitError, Timeout, vs.
    error_msg       TEXT,
    extra           JSONB
);

CREATE INDEX IF NOT EXISTS idx_usage_logs_ts
    ON agency.usage_logs (ts DESC);

CREATE INDEX IF NOT EXISTS idx_usage_logs_client_ts
    ON agency.usage_logs (client_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_usage_logs_agent_ts
    ON agency.usage_logs (agent_id, ts DESC);

CREATE INDEX IF NOT EXISTS idx_usage_logs_provider_model_ts
    ON agency.usage_logs (provider, model, ts DESC);

CREATE INDEX IF NOT EXISTS idx_usage_logs_status
    ON agency.usage_logs (status)
    WHERE status IN ('error', 'fallback', 'skip_ratelimit');

COMMENT ON TABLE  agency.usage_logs IS 'Asama 3.D: per-call LLM telemetry; routerin her cagrisindan sonra yazilir.';
COMMENT ON COLUMN agency.usage_logs.chain_idx IS 'models.yaml chain icinde kacinci eleman (0=primary).';
COMMENT ON COLUMN agency.usage_logs.status   IS 'success: kullanildi | fallback: 429/timeout sonra siradakine gecildi | skip_ratelimit: proactive atlandi | error: zincir tukendi.';
