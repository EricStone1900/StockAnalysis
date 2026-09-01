import json
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256

from quant_research.adapters.factor_engine import DailyPriceBar
from quant_research.adapters.qlib import InMemoryVerifiedArtifactReader, QlibCloseGapIndexAdapter
from quant_research.application_price_factors import QlibMaskedPriceFactorService
from quant_research.domain import (
    ArtifactRef,
    CloseGapHandlingPolicy,
    DataQualityStatus,
    MarketDataVersionRef,
)


class FakeBarReader:
    def load_bars(self, instruments: list[str], start_date: date, end_date: date) -> tuple[DailyPriceBar, ...]:
        return (
            DailyPriceBar(security_id="sh600000", trading_day=date(2020, 1, 1), close=Decimal(10), turnover=Decimal(100)),
            DailyPriceBar(security_id="sh600000", trading_day=date(2020, 1, 2), close=Decimal(11), turnover=Decimal(110)),
            DailyPriceBar(security_id="sh600000", trading_day=date(2020, 1, 3), close=Decimal(12), turnover=Decimal(120)),
        )


def ref(uri: str, content: bytes) -> ArtifactRef:
    return ArtifactRef(uri=uri, sha256=sha256(content).hexdigest())


def test_real_price_flow_applies_index_mask_and_keeps_warn_manifest() -> None:
    archive = b"verified qlib artifact"
    archive_ref = ref("minio://artifacts/archive", archive)
    index = json.dumps(
        {"archive_hash": archive_ref.sha256, "gaps": [{"symbol": "sh600000", "trading_day": "2020-01-02"}]}
    ).encode()
    index_ref = ref("minio://artifacts/gaps", index)
    version = MarketDataVersionRef(
        version_id="cn-a-fixture-v1", artifact=archive_ref, close_gap_index=index_ref,
        quality_status=DataQualityStatus.WARN, source_release_tag="fixture", source_policy_version="v1-close-gap-fast",
    )
    policy = CloseGapHandlingPolicy(
        policy_version="v1-assume-suspension-on-read", artifact=ref("repo://policy", b"policy"),
        applicable_universe_version="cn-a-main-board-v1", approval_reference="ADR-003-03",
        acknowledged_by="research-operator", approved_at=datetime(2026, 8, 30, tzinfo=UTC),
    )
    service = QlibMaskedPriceFactorService(
        FakeBarReader(),
        QlibCloseGapIndexAdapter(InMemoryVerifiedArtifactReader({archive_ref.uri: archive, index_ref.uri: index})),
    )

    matrix, resolution, manifest = service.calculate(
        "run-001", version, policy, ["SH600000"], date(2020, 1, 1), date(2020, 1, 3), datetime(2026, 8, 30, tzinfo=UTC)
    )

    assert len(resolution.entries) == 1
    assert matrix.observations == ()
    assert manifest.quality_status is DataQualityStatus.WARN
    assert manifest.snapshot_eligibility == "CANDIDATE_ONLY"


def test_precomputed_resolution_must_match_requested_inputs() -> None:
    archive = b"verified qlib artifact"
    archive_ref = ref("minio://artifacts/archive-precomputed", archive)
    index = json.dumps(
        {"archive_hash": archive_ref.sha256, "gaps": [{"symbol": "sh600000", "trading_day": "2020-01-02"}]}
    ).encode()
    index_ref = ref("minio://artifacts/gaps-precomputed", index)
    version = MarketDataVersionRef(
        version_id="cn-a-fixture-precomputed", artifact=archive_ref, close_gap_index=index_ref,
        quality_status=DataQualityStatus.WARN, source_release_tag="fixture", source_policy_version="v1-close-gap-fast",
    )
    policy = CloseGapHandlingPolicy(
        policy_version="v1-assume-suspension-on-read", artifact=ref("repo://policy-precomputed", b"policy"),
        applicable_universe_version="cn-a-main-board-v1", approval_reference="ADR-003-03",
        acknowledged_by="research-operator", approved_at=datetime(2026, 8, 30, tzinfo=UTC),
    )
    adapter = QlibCloseGapIndexAdapter(InMemoryVerifiedArtifactReader({archive_ref.uri: archive, index_ref.uri: index}))
    service = QlibMaskedPriceFactorService(FakeBarReader(), adapter)
    _, resolution, _ = service.calculate(
        "run-precomputed", version, policy, ["SH600000"], date(2020, 1, 1), date(2020, 1, 3), datetime(2026, 8, 30, tzinfo=UTC)
    )

    replacement = version.model_copy(update={"version_id": "another-version"})
    try:
        service.calculate(
            "run-precomputed-invalid", replacement, policy, ["SH600000"], date(2020, 1, 1), date(2020, 1, 3),
            datetime(2026, 8, 30, tzinfo=UTC), resolution=resolution,
        )
    except ValueError as error:
        assert "does not match" in str(error)
    else:
        raise AssertionError("precomputed resolution with different DataVersion must fail")
