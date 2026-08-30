CREATE TABLE IF NOT EXISTS status_enrichment_batches (
  batch_id CHAR(64) PRIMARY KEY,
  parent_version_id TEXT NOT NULL,
  policy_version TEXT NOT NULL REFERENCES source_policies(policy_version),
  ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
  gap_count INTEGER NOT NULL CHECK (gap_count > 0),
  first_key TEXT NOT NULL,
  last_key TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED')),
  attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  last_error TEXT,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  UNIQUE (parent_version_id, policy_version, ordinal)
);
