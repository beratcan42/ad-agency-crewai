-- =================================================================
-- Asama 4 — Obsidian Vault chunk + embedding (hybrid arama icin)
-- =================================================================
-- Not: Mevcut Postgres volume'da init yeniden calismaz; doctor hatada
--      `psql -f scripts/sql/init/03-note-embeddings.sql` ile manuel apply.
-- =================================================================

CREATE TABLE IF NOT EXISTS agency.note_embeddings (
    id              BIGSERIAL PRIMARY KEY,
    client_id       VARCHAR(64) NOT NULL,
    rel_path        TEXT NOT NULL,
    chunk_index     INT NOT NULL DEFAULT 0,
    content_hash    TEXT NOT NULL,
    body            TEXT NOT NULL,
    embedding       vector(768),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, rel_path, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_note_emb_client ON agency.note_embeddings (client_id);
CREATE INDEX IF NOT EXISTS idx_note_emb_client_path ON agency.note_embeddings (client_id, rel_path);
CREATE INDEX IF NOT EXISTS idx_note_emb_updated ON agency.note_embeddings (updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_note_emb_trgm
    ON agency.note_embeddings USING gin (body gin_trgm_ops);

COMMENT ON TABLE agency.note_embeddings IS 'Vault markdown chunklari; watcher Gemini embedding yazar; hybrid arama pg_trgm + vector.';
COMMENT ON COLUMN agency.note_embeddings.embedding IS '768d gemini-embedding-001; bos ise NULL (sadece lexical arama).';
