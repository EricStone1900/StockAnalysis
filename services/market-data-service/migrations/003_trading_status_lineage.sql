CREATE TABLE IF NOT EXISTS trading_status_facts (
  security_id TEXT NOT NULL REFERENCES securities(security_id),
  trading_day DATE NOT NULL,
  trading_status TEXT NOT NULL CHECK (trading_status IN ('TRADING', 'SUSPENDED', 'DELISTED', 'UNKNOWN')),
  is_st BOOLEAN,
  raw_tradestatus TEXT,
  raw_is_st TEXT,
  observed_at TIMESTAMPTZ NOT NULL,
  available_at TIMESTAMPTZ NOT NULL,
  raw_artifact_hash CHAR(64) NOT NULL REFERENCES raw_artifacts(raw_artifact_hash),
  PRIMARY KEY (security_id, trading_day, raw_artifact_hash),
  CHECK (available_at >= observed_at)
);

CREATE TABLE IF NOT EXISTS close_gap_reconciliations (
  reconciliation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  policy_version TEXT NOT NULL REFERENCES source_policies(policy_version),
  security_id TEXT NOT NULL REFERENCES securities(security_id),
  trading_day DATE NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('SUSPENSION_CONFIRMED', 'UNEXPLAINED_MISSING', 'STATUS_UNKNOWN', 'QUARANTINED')),
  reason TEXT NOT NULL,
  primary_raw_artifact_hash CHAR(64) NOT NULL REFERENCES raw_artifacts(raw_artifact_hash),
  status_raw_artifact_hash CHAR(64) REFERENCES raw_artifacts(raw_artifact_hash),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (policy_version, security_id, trading_day)
);
