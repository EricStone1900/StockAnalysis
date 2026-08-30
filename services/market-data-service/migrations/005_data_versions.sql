-- DataVersion 元数据持久化；行情大对象仍只通过 Artifact URI/Hash 引用。
CREATE TABLE IF NOT EXISTS data_versions (
  version_id TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('BUILDING', 'VALIDATING', 'READY', 'FAILED', 'SUPERSEDED')),
  scope TEXT NOT NULL,
  source_version TEXT NOT NULL,
  source_release_tag TEXT,
  source_policy_version TEXT NOT NULL,
  source_manifest_hash CHAR(64),
  artifact_uri TEXT NOT NULL,
  artifact_hash CHAR(64) NOT NULL,
  quality_report_uri TEXT,
  close_gap_index_uri TEXT,
  close_gap_index_hash CHAR(64),
  quality_status TEXT NOT NULL CHECK (quality_status IN ('PASS', 'WARN', 'FAIL')),
  available_at TIMESTAMPTZ NOT NULL,
  content_hash CHAR(64) NOT NULL,
  parent_version_id TEXT REFERENCES data_versions(version_id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (close_gap_index_uri IS NULL OR close_gap_index_hash IS NOT NULL),
  CHECK (close_gap_index_hash IS NULL OR close_gap_index_uri IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS data_versions_release_idx
  ON data_versions (source_release_tag, available_at);
