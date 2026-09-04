CREATE TABLE IF NOT EXISTS news_items (
  news_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  canonical_url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  language TEXT NOT NULL,
  published_at TIMESTAMPTZ NOT NULL,
  collected_at TIMESTAMPTZ NOT NULL,
  available_at TIMESTAMPTZ NOT NULL,
  source_reliability NUMERIC(4, 3) NOT NULL CHECK (source_reliability >= 0 AND source_reliability <= 1),
  content_hash TEXT NOT NULL UNIQUE,
  evidence_uri TEXT NOT NULL,
  license_policy_id TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('RAW', 'PROCESSED', 'DUPLICATE', 'FAILED')),
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS news_items_available_idx ON news_items (available_at DESC);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  run_id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED')),
  items_seen INTEGER NOT NULL DEFAULT 0 CHECK (items_seen >= 0),
  items_stored INTEGER NOT NULL DEFAULT 0 CHECK (items_stored >= 0),
  payload JSONB NOT NULL
);
