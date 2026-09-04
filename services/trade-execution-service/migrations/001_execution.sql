CREATE TABLE IF NOT EXISTS rebalance_batches (
  rebalance_batch_id TEXT PRIMARY KEY,
  decision_id TEXT NOT NULL,
  proposal_version INTEGER NOT NULL,
  approval_id TEXT NOT NULL,
  risk_evaluation_id TEXT NOT NULL,
  budget_reservation_id TEXT NOT NULL,
  target_portfolio_version INTEGER NOT NULL,
  valid_until TIMESTAMPTZ NOT NULL,
  content_hash TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS order_intents (
  intent_id TEXT PRIMARY KEY,
  rebalance_batch_id TEXT NOT NULL REFERENCES rebalance_batches(rebalance_batch_id),
  leg_id TEXT NOT NULL,
  security_id TEXT NOT NULL,
  side TEXT NOT NULL CHECK (side IN ('BUY','SELL')),
  quantity TEXT NOT NULL,
  status TEXT NOT NULL,
  payload JSONB NOT NULL,
  UNIQUE (rebalance_batch_id, leg_id)
);
CREATE TABLE IF NOT EXISTS execution_fills (
  fill_id TEXT PRIMARY KEY,
  intent_id TEXT NOT NULL REFERENCES order_intents(intent_id),
  filled_quantity TEXT NOT NULL,
  fill_price TEXT NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  payload JSONB NOT NULL
);
