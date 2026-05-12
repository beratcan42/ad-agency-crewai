-- =================================================================
-- Postgres Init Script (pgvector etkinlestir + temel schema)
-- =================================================================
-- Bu dosya postgres ilk acilisinda /docker-entrypoint-initdb.d
-- tarafindan otomatik calistirilir.
-- =================================================================

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Schema'lar (sonraki asamalarda doldurulacak)
CREATE SCHEMA IF NOT EXISTS agency;
CREATE SCHEMA IF NOT EXISTS crm;
CREATE SCHEMA IF NOT EXISTS memory;
CREATE SCHEMA IF NOT EXISTS audit;

-- Multi-tenant temel: clients tablosu (Asama 2.5'te detaylandirilacak)
CREATE TABLE IF NOT EXISTS agency.clients (
  id              SERIAL PRIMARY KEY,
  client_id       VARCHAR(64) UNIQUE NOT NULL,
  name            VARCHAR(255) NOT NULL,
  vault_path      TEXT,
  allowed_tools   JSONB DEFAULT '[]'::jsonb,
  token_budget    INT DEFAULT 50000,
  active          BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_client_id ON agency.clients(client_id);

-- Health check tablosu
CREATE TABLE IF NOT EXISTS agency.health_check (
  id          SERIAL PRIMARY KEY,
  checked_at  TIMESTAMPTZ DEFAULT NOW(),
  status      VARCHAR(16) DEFAULT 'ok'
);

INSERT INTO agency.health_check (status) VALUES ('init')
ON CONFLICT DO NOTHING;
