CREATE TABLE IF NOT EXISTS strategy_metadata_records (
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (record_type, record_id)
);

CREATE TABLE IF NOT EXISTS strategy_outbox_events (
    event_id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    payload JSONB NOT NULL,
    published_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
