CREATE TABLE IF NOT EXISTS research_experiments (
    experiment_id TEXT PRIMARY KEY,
    input_hash CHAR(64) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS research_experiment_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES research_experiments(experiment_id),
    input_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS research_experiment_outbox (
    event_id TEXT PRIMARY KEY,
    experiment_id TEXT NOT NULL REFERENCES research_experiments(experiment_id),
    subject TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS research_experiment_outbox_pending_idx
    ON research_experiment_outbox (created_at, event_id)
    WHERE published_at IS NULL;
