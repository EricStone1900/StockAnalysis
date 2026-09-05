CREATE TABLE IF NOT EXISTS portfolio_execution_inbox (
  event_id TEXT PRIMARY KEY,
  subject TEXT NOT NULL,
  received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
