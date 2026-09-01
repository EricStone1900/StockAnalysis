import io
from datetime import UTC, date, datetime
from hashlib import sha256

import pyarrow.parquet as pq
import pytest

from quant_research.adapters.factor_artifacts import (
    FactorArtifactPublisher,
    PublishedFactorEvidenceReader,
)
from quant_research.adapters.factor_engine import (
    FactorObservation,
    PriceFactorMatrix,
    canonical_price_factor_matrix_hash,
)
from quant_research.adapters.qlib import ArtifactIntegrityError, InMemoryVerifiedArtifactReader
from quant_research.domain import (
    ArtifactRef,
    CloseGapHandlingPolicy,
    DataQualityStatus,
    MarketDataVersionRef,
    ResearchRunManifest,
    build_run_manifest,
    resolve_close_gaps,
)


class FakeImmutableWriter:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_immutable(self, key: str, content: bytes) -> str:
        existing = self.objects.get(key)
        if existing is not None and existing != content:
            raise ValueError("immutable artifact key already contains different content")
        self.objects[key] = content
        return sha256(content).hexdigest()


def ref(uri: str, character: str) -> ArtifactRef:
    return ArtifactRef(uri=uri, sha256=character * 64)


def manifest() -> ResearchRunManifest:
    version = MarketDataVersionRef(
        version_id="cn-a-fixture-v1", artifact=ref("minio://artifacts/raw", "a"),
        close_gap_index=ref("minio://artifacts/gaps", "b"), quality_status=DataQualityStatus.WARN,
        source_release_tag="fixture", source_policy_version="v1-close-gap-fast",
    )
    policy = CloseGapHandlingPolicy(
        policy_version="v1-assume-suspension-on-read", artifact=ref("repo://policy", "c"),
        applicable_universe_version="cn-a-main-board-v1", approval_reference="ADR-003-04",
        acknowledged_by="operator", approved_at=datetime(2026, 8, 30, tzinfo=UTC),
    )
    return build_run_manifest("run-fixture-001", resolve_close_gaps(version, policy, (), datetime(2026, 8, 30, tzinfo=UTC)))


def test_factor_artifacts_are_sorted_immutable_and_enter_warn_manifest() -> None:
    matrix = PriceFactorMatrix(
        data_version_id="cn-a-fixture-v1",
        observations=(
            FactorObservation(security_id="sz000001", trading_day=date(2020, 1, 2), factor_id="price.momentum.2d", value="0.10000000"),
            FactorObservation(security_id="sh600000", trading_day=date(2020, 1, 2), factor_id="price.momentum.2d", value="0.20000000"),
        ),
        canonical_content_hash="d" * 64,
    )
    writer = FakeImmutableWriter()
    publisher = FactorArtifactPublisher(writer, "minio://artifacts")

    first = publisher.publish(matrix, manifest())
    second = publisher.publish(matrix, manifest())

    assert first.matrix_artifact == second.matrix_artifact
    assert first.manifest.quality_status is DataQualityStatus.WARN
    assert first.manifest.snapshot_eligibility == "CANDIDATE_ONLY"
    assert first.manifest.factor_matrix_canonical_content_hash == matrix.canonical_content_hash
    parquet_key = first.matrix_artifact.uri.removeprefix("minio://artifacts/")
    table = pq.read_table(io.BytesIO(writer.objects[parquet_key]))
    assert table.column("security_id").to_pylist() == ["sh600000", "sz000001"]


def test_candidate_evidence_is_rebuilt_from_verified_manifest_and_matrix() -> None:
    observations = (
        FactorObservation(
            security_id="sh600000", trading_day=date(2020, 1, 2), factor_id="price.momentum.2d", value="0.20000000"
        ),
    )
    matrix = PriceFactorMatrix(
        data_version_id="cn-a-fixture-v1",
        observations=observations,
        canonical_content_hash=canonical_price_factor_matrix_hash("cn-a-fixture-v1", observations),
    )
    writer = FakeImmutableWriter()
    published = FactorArtifactPublisher(writer, "minio://artifacts").publish(matrix, manifest())
    objects = {f"minio://artifacts/{key}": value for key, value in writer.objects.items()}
    evidence = PublishedFactorEvidenceReader(InMemoryVerifiedArtifactReader(objects)).load_candidate_evidence(
        published.manifest_artifact
    )

    assert evidence.matrix_factor_ids == ("price.momentum.2d",)
    assert evidence.run_manifest.factor_matrix_artifact == published.matrix_artifact

    tampered_manifest = published.manifest.model_copy(
        update={"factor_matrix_canonical_content_hash": "f" * 64}
    ).model_dump_json().encode()
    tampered_ref = ArtifactRef(uri="minio://artifacts/tampered.json", sha256=sha256(tampered_manifest).hexdigest())
    objects[tampered_ref.uri] = tampered_manifest
    with pytest.raises(ArtifactIntegrityError, match="canonical hash"):
        PublishedFactorEvidenceReader(InMemoryVerifiedArtifactReader(objects)).load_candidate_evidence(tampered_ref)
