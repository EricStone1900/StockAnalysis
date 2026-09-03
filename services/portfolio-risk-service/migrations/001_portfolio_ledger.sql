CREATE TABLE IF NOT EXISTS portfolio_ledger_entries (
  entry_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  entry_type TEXT NOT NULL CHECK (entry_type IN ('OPENING', 'BUY', 'SELL', 'FEE', 'DIVIDEND', 'REVERSAL')),
  amount TEXT NOT NULL CHECK (amount ~ '^-?[0-9]+(\.[0-9]{1,8})?$'),
  occurred_at TIMESTAMPTZ NOT NULL,
  available_at TIMESTAMPTZ NOT NULL CHECK (available_at >= occurred_at),
  source_ref TEXT NOT NULL,
  actor_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  reversal_of_entry_id TEXT REFERENCES portfolio_ledger_entries(entry_id),
  idempotency_key TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE portfolio_ledger_entries ADD COLUMN IF NOT EXISTS reversal_of_entry_id TEXT REFERENCES portfolio_ledger_entries(entry_id);
ALTER TABLE portfolio_ledger_entries ADD COLUMN IF NOT EXISTS idempotency_key TEXT;
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
