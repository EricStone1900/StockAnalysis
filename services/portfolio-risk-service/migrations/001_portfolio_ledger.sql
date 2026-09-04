CREATE TABLE IF NOT EXISTS portfolio_ledger_entries (
  entry_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  entry_type TEXT NOT NULL CHECK (entry_type IN ('OPENING', 'BUY', 'SELL', 'FEE', 'DIVIDEND', 'SPLIT', 'REVERSAL')),
  security_id TEXT,
  quantity TEXT CHECK (quantity IS NULL OR quantity ~ '^-?[0-9]+(\.[0-9]{1,8})?$'),
  amount TEXT NOT NULL CHECK (amount ~ '^-?[0-9]+(\.[0-9]{1,8})?$'),
  occurred_at TIMESTAMPTZ NOT NULL,
  available_at TIMESTAMPTZ NOT NULL CHECK (available_at >= occurred_at),
  source_ref TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  reversal_of_entry_id TEXT REFERENCES portfolio_ledger_entries(entry_id),
  idempotency_key TEXT,
  correlation_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE portfolio_ledger_entries ADD COLUMN IF NOT EXISTS reversal_of_entry_id TEXT REFERENCES portfolio_ledger_entries(entry_id);
ALTER TABLE portfolio_ledger_entries ADD COLUMN IF NOT EXISTS security_id TEXT;
ALTER TABLE portfolio_ledger_entries ADD COLUMN IF NOT EXISTS quantity TEXT;
ALTER TABLE portfolio_ledger_entries ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
ALTER TABLE portfolio_ledger_entries ADD COLUMN IF NOT EXISTS correlation_id TEXT;
ALTER TABLE portfolio_ledger_entries DROP CONSTRAINT IF EXISTS portfolio_ledger_entries_entry_type_check;
ALTER TABLE portfolio_ledger_entries ADD CONSTRAINT portfolio_ledger_entries_entry_type_check CHECK (entry_type IN ('OPENING', 'BUY', 'SELL', 'FEE', 'DIVIDEND', 'SPLIT', 'REVERSAL'));
CREATE UNIQUE INDEX IF NOT EXISTS portfolio_ledger_one_reversal_idx ON portfolio_ledger_entries (reversal_of_entry_id) WHERE reversal_of_entry_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS portfolio_ledger_idempotency_idx ON portfolio_ledger_entries (portfolio_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  account_id TEXT NOT NULL,
  as_of TIMESTAMPTZ NOT NULL,
  cash TEXT NOT NULL CHECK (cash ~ '^-?[0-9]+(\.[0-9]{1,8})?$'),
  positions JSONB NOT NULL,
  ledger_version INTEGER NOT NULL CHECK (ledger_version > 0),
  source_ref TEXT NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS portfolio_snapshots_latest_idx ON portfolio_snapshots (portfolio_id, ledger_version DESC);
CREATE UNIQUE INDEX IF NOT EXISTS portfolio_snapshots_version_idx ON portfolio_snapshots (portfolio_id, ledger_version);
ALTER TABLE portfolio_ledger_entries DROP CONSTRAINT IF EXISTS portfolio_ledger_entries_amount_check;
ALTER TABLE portfolio_ledger_entries ADD CONSTRAINT portfolio_ledger_entries_amount_check CHECK (amount ~ '^-?[0-9]+(\.[0-9]{1,8})?$');
ALTER TABLE portfolio_snapshots DROP CONSTRAINT IF EXISTS portfolio_snapshots_cash_check;
ALTER TABLE portfolio_snapshots ADD CONSTRAINT portfolio_snapshots_cash_check CHECK (cash ~ '^-?[0-9]+(\.[0-9]{1,8})?$');

CREATE TABLE IF NOT EXISTS portfolio_snapshot_idempotency (
  portfolio_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  snapshot_id TEXT NOT NULL REFERENCES portfolio_snapshots(snapshot_id),
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (portfolio_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS portfolio_valuations (
  valuation_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  portfolio_snapshot_id TEXT NOT NULL REFERENCES portfolio_snapshots(snapshot_id),
  ledger_version INTEGER NOT NULL,
  market_data_version TEXT NOT NULL,
  as_of TIMESTAMPTZ NOT NULL,
  market_value TEXT NOT NULL CHECK (market_value ~ '^-?[0-9]+(\.[0-9]{1,8})?$'),
  total_equity TEXT NOT NULL CHECK (total_equity ~ '^-?[0-9]+(\.[0-9]{1,8})?$'),
  payload JSONB NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (portfolio_snapshot_id, market_data_version, as_of)
);
CREATE INDEX IF NOT EXISTS portfolio_valuations_latest_idx ON portfolio_valuations (portfolio_id, as_of DESC);
