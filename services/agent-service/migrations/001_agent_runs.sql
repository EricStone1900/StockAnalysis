CREATE TABLE IF NOT EXISTS agent_runs (
  correlation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE,
  definition_id TEXT NOT NULL,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
