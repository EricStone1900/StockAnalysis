CREATE TABLE IF NOT EXISTS source_policies (
  policy_version TEXT PRIMARY KEY,
  primary_source TEXT NOT NULL,
  policy_document_uri TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS raw_artifacts (
  raw_artifact_hash CHAR(64) PRIMARY KEY,
  source TEXT NOT NULL,
  source_record_id TEXT NOT NULL,
  source_version TEXT NOT NULL,
  source_release_tag TEXT,
  raw_artifact_uri TEXT NOT NULL UNIQUE,
  license_ref TEXT NOT NULL,
  source_policy_version TEXT NOT NULL REFERENCES source_policies(policy_version),
  ingested_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS financial_facts (
  security_id TEXT NOT NULL REFERENCES securities(security_id),
  fact_type TEXT NOT NULL,
  period_end DATE NOT NULL,
  value NUMERIC NOT NULL,
  announced_at TIMESTAMPTZ NOT NULL,
  available_at TIMESTAMPTZ NOT NULL,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  revision_reason TEXT,
  supersedes_revision INTEGER,
  raw_artifact_hash CHAR(64) NOT NULL REFERENCES raw_artifacts(raw_artifact_hash),
  PRIMARY KEY (security_id, fact_type, period_end, revision),
  CHECK (available_at >= announced_at),
  CHECK (
    (revision = 1 AND revision_reason IS NULL AND supersedes_revision IS NULL)
    OR (revision > 1 AND revision_reason IS NOT NULL AND supersedes_revision = revision - 1)
  )
);

CREATE TABLE IF NOT EXISTS field_provenance (
  provenance_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_key TEXT NOT NULL,
  field_name TEXT NOT NULL,
  source TEXT NOT NULL,
  source_record_id TEXT NOT NULL,
  raw_artifact_hash CHAR(64) NOT NULL REFERENCES raw_artifacts(raw_artifact_hash),
  source_version TEXT NOT NULL,
  source_policy_version TEXT NOT NULL REFERENCES source_policies(policy_version),
  role TEXT NOT NULL CHECK (role IN ('PRIMARY', 'SUPPLEMENT', 'VERIFIED')),
  UNIQUE (entity_type, entity_key, field_name, raw_artifact_hash)
);

CREATE TABLE IF NOT EXISTS reconciliation_results (
  reconciliation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  policy_version TEXT NOT NULL REFERENCES source_policies(policy_version),
  entity_type TEXT NOT NULL,
  entity_key TEXT NOT NULL,
  field_name TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('PRIMARY_ONLY', 'SUPPLEMENTED', 'VERIFIED', 'QUARANTINED')),
  reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
