import json
from datetime import UTC, datetime
from hashlib import sha256

import pytest

from quant_research.adapters.qlib import (
    ArtifactIntegrityError,
    InMemoryVerifiedArtifactReader,
    QlibCloseGapIndexAdapter,
)
from quant_research.application import CloseGapMaskService
from quant_research.domain import (
    ArtifactRef,
    CloseGapHandlingPolicy,
    DataQualityStatus,
    MarketDataVersionRef,
)


def reference(uri: str, content: bytes) -> ArtifactRef:
    return ArtifactRef(uri=uri, sha256=sha256(content).hexdigest())


def setup_service(index_archive_hash: str | None = None) -> tuple[CloseGapMaskService, MarketDataVersionRef, CloseGapHandlingPolicy]:
    archive = b"original qlib archive bytes; close values are never opened by this slice"
    archive_ref = reference("minio://artifacts/data-version.tar.gz", archive)
    index = json.dumps(
        {
            "archive_hash": index_archive_hash or archive_ref.sha256,
            "gaps": [
                {"symbol": "sz000001", "trading_day": "2020-01-03"},
                {"symbol": "bj430047", "trading_day": "2020-01-02"},
                {"symbol": "sh600000", "trading_day": "2020-01-02"},
            ],
        },
        separators=(",", ":"),
    ).encode()
    index_ref = reference("minio://artifacts/close-gap-index.json", index)
    policy_content = b'{"policyVersion":"v1-assume-suspension-on-read"}'
    policy_ref = reference("minio://artifacts/close-gap-policy.json", policy_content)
    reader = InMemoryVerifiedArtifactReader({archive_ref.uri: archive, index_ref.uri: index})
    version = MarketDataVersionRef(
        version_id="cn-a-fixture-v1",
        artifact=archive_ref,
        close_gap_index=index_ref,
        quality_status=DataQualityStatus.WARN,
        source_release_tag="fixture-2026-08-30",
        source_policy_version="v1-close-gap-fast",
    )
    policy = CloseGapHandlingPolicy(
        policy_version="v1-assume-suspension-on-read",
        artifact=policy_ref,
        applicable_universe_version="cn-a-main-board-v1",
        approval_reference="ADR-003-01",
        acknowledged_by="research-operator",
        approved_at=datetime(2026, 8, 30, tzinfo=UTC),
    )
    return CloseGapMaskService(QlibCloseGapIndexAdapter(reader)), version, policy


def test_verified_fixture_becomes_warn_candidate_mask_and_manifest() -> None:
    service, version, policy = setup_service()
    resolution, manifest = service.create_mask("run-fixture-001", version, policy, datetime(2026, 8, 30, tzinfo=UTC))

    assert [(entry.security_id, entry.status) for entry in resolution.entries] == [
        ("sh600000", "SUSPENSION_ASSUMED"),
        ("sz000001", "SUSPENSION_ASSUMED"),
    ]
    assert manifest.quality_status is DataQualityStatus.WARN
    assert manifest.snapshot_eligibility == "CANDIDATE_ONLY"
    assert manifest.close_gap_index.sha256 == version.close_gap_index.sha256
    assert manifest.suspension_mask_hash == resolution.canonical_content_hash


def test_index_with_different_parent_archive_is_rejected() -> None:
    service, version, policy = setup_service(index_archive_hash="f" * 64)
    with pytest.raises(ArtifactIntegrityError, match="does not belong"):
        service.create_mask("run-fixture-002", version, policy, datetime(2026, 8, 30, tzinfo=UTC))


def test_artifact_hash_mismatch_is_rejected_before_parsing() -> None:
    service, version, policy = setup_service()
    bad_version = version.model_copy(update={"artifact": ArtifactRef(uri=version.artifact.uri, sha256="0" * 64)})
    with pytest.raises(ArtifactIntegrityError, match="hash mismatch"):
        service.create_mask("run-fixture-003", bad_version, policy, datetime(2026, 8, 30, tzinfo=UTC))
