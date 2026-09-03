CREATE TABLE IF NOT EXISTS portfolio_ledger_entries (
  entry_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  entry_type TEXT NOT NULL CHECK (entry_type IN ('OPENING', 'BUY', 'SELL', 'FEE', 'DIVIDEND', 'REVERSAL')),
  amount TEXT NOT NULL CHECK (amount ~ '^-?[0-9]+(\\.[0-9]{1,8})?$'),
  occurred_at TIMESTAMPTZ NOT NULL,
  available_at TIMESTAMPTZ NOT NULL CHECK (available_at >= occurred_at),
  source_ref TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  as_of TIMESTAMPTZ NOT NULL,
  cash TEXT NOT NULL CHECK (cash ~ '^-?[0-9]+(\\.[0-9]{1,8})?$'),
  positions JSONB NOT NULL,
  ledger_version INTEGER NOT NULL CHECK (ledger_version > 0),
  source_ref TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS portfolio_snapshots_latest_idx ON portfolio_snapshots (portfolio_id, ledger_version DESC);

CREATE TABLE IF NOT EXISTS portfolio_snapshot_idempotency (
  portfolio_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  snapshot_id TEXT NOT NULL REFERENCES portfolio_snapshots(snapshot_id),
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (portfolio_id, idempotency_key)
);
