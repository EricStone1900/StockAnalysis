CREATE TABLE IF NOT EXISTS research_promotion_requests (
    request_id TEXT PRIMARY KEY,
    content_hash CHAR(64) NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('REQUESTED', 'REPRODUCED', 'REJECTED')),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS research_promotion_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES research_promotion_requests(request_id),
    content_hash CHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
