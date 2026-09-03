from datetime import UTC, datetime

import pytest

from src.research_automation.artifacts import (
    CandidateArtifactKind,
    CandidateCodeScanner,
    FixedRDAGENTAdapter,
    ReproducibilityManifest,
)


def _manifest() -> ReproducibilityManifest:
    return ReproducibilityManifest("dv-1", "a" * 64, "b" * 64, "sha256:image", "c" * 64, 7, "eval-v1")


def test_manifest_and_candidate_hash_are_deterministic() -> None:
    adapter = FixedRDAGENTAdapter()
    candidate = adapter.register_code_candidate(
        "candidate-1", "print('ok')", "minio://artifacts/candidate-1.py", "d" * 64, _manifest(), datetime(2026, 9, 3, tzinfo=UTC)
    )
    assert candidate.kind is CandidateArtifactKind.CODE
    assert candidate.content_hash == candidate.content_hash


def test_scanner_rejects_network_process_secrets_and_dynamic_code() -> None:
    findings = CandidateCodeScanner().scan("import requests\nimport subprocess\nprint(os.environ['TOKEN'])\neval('1')")
    assert {finding.rule for finding in findings} == {"network", "process", "secrets", "dynamic-code"}
    with pytest.raises(ValueError, match="security scan"):
        FixedRDAGENTAdapter().register_code_candidate(
            "candidate-unsafe", "import socket", "s3://artifacts/unsafe.py", "e" * 64, _manifest(), datetime(2026, 9, 3, tzinfo=UTC)
        )


def test_manifest_changes_when_seed_or_image_changes() -> None:
    original = _manifest()
    changed = ReproducibilityManifest(original.data_version_id, original.data_artifact_hash, original.dependency_lock_hash, "sha256:other", original.parameter_hash, original.random_seed, original.evaluation_protocol_version)
    assert original.content_hash != changed.content_hash
