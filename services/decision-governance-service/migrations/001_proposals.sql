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
