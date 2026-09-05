CREATE TABLE IF NOT EXISTS portfolio_resource_reservations (
  reservation_id TEXT PRIMARY KEY,
  portfolio_id TEXT NOT NULL,
  ledger_version INTEGER NOT NULL,
  decision_id TEXT NOT NULL,
  proposal_version INTEGER NOT NULL,
  risk_evaluation_id TEXT NOT NULL,
  risk_policy_version TEXT NOT NULL,
  execution_content_hash TEXT NOT NULL,
  reserved_cash TEXT NOT NULL,
  reserved_sells JSONB NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('RESERVED', 'DISPATCHING', 'IN_FLIGHT', 'UNKNOWN', 'SETTLED', 'RELEASED')),
  request_hash TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (portfolio_id, idempotency_key)
);
CREATE UNIQUE INDEX IF NOT EXISTS portfolio_one_active_resource_reservation_idx
  ON portfolio_resource_reservations (portfolio_id)
  WHERE status NOT IN ('SETTLED', 'RELEASED');
