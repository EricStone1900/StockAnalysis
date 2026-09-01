CREATE TABLE IF NOT EXISTS daily_analysis_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
