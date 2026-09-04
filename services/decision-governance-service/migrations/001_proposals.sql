CREATE TABLE IF NOT EXISTS trade_proposals (
  proposal_id TEXT NOT NULL,
  proposal_version INTEGER NOT NULL CHECK (proposal_version > 0),
  proposal_kind TEXT NOT NULL CHECK (proposal_kind IN ('HOLD', 'REBALANCE')),
  state TEXT NOT NULL,
  agent_run_id TEXT NOT NULL,
  target_portfolio_version INTEGER NOT NULL CHECK (target_portfolio_version > 0),
  parent_proposal_version INTEGER,
  legs JSONB NOT NULL,
  evidence JSONB NOT NULL,
  content_hash TEXT NOT NULL,
  payload JSONB NOT NULL,
  risk_review JSONB,
  approval JSONB,
  idempotency_key TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (proposal_id, proposal_version),
  UNIQUE (idempotency_key),
  UNIQUE (proposal_id, content_hash)
);
ALTER TABLE trade_proposals ADD COLUMN IF NOT EXISTS risk_review JSONB;
ALTER TABLE trade_proposals ADD COLUMN IF NOT EXISTS approval JSONB;
CREATE INDEX IF NOT EXISTS trade_proposals_latest_idx ON trade_proposals (proposal_id, proposal_version DESC);

CREATE TABLE IF NOT EXISTS decision_budget_reservations (
  reservation_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  trading_date DATE NOT NULL,
  proposal_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  batch_number INTEGER NOT NULL CHECK (batch_number >= 0),
  status TEXT NOT NULL CHECK (status IN ('RESERVED', 'DISPATCHING', 'CONSUMED', 'RELEASED')),
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS decision_budget_active_batch_idx ON decision_budget_reservations (portfolio_id, trading_date, batch_number) WHERE status = 'RESERVED' AND batch_number > 0;

CREATE TABLE IF NOT EXISTS governance_outbox_events (
  event_id TEXT PRIMARY KEY,
  subject TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  available_at TIMESTAMPTZ NOT NULL,
  published_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS governance_outbox_pending_idx ON governance_outbox_events (available_at) WHERE published_at IS NULL;
