from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from market_data.domain import Exchange, SecurityId
from market_data.lineage import FieldProvenance, ProvenanceRole
from market_data.pit import FinancialFact, RawArtifact
from market_data.reconciliation import (
    NumericFieldCandidate,
    ReconciliationPolicy,
    ReconciliationStatus,
    reconcile_numeric_field,
)


def provenance(source: str, role: ProvenanceRole = ProvenanceRole.PRIMARY) -> FieldProvenance:
    return FieldProvenance(
        field_name="pe_ttm",
        source=source,
        source_record_id="600000-2026-08-28",
        raw_artifact_hash="a" * 64,
        source_version="2026-08-28",
        source_policy_version="v1",
        role=role,
    )


def artifact() -> RawArtifact:
    return RawArtifact(
        source="cninfo",
        source_record_id="notice-1",
        source_version="2026-04-01",
        raw_artifact_uri="minio://artifacts/raw/cninfo/notice-1.pdf",
        raw_artifact_hash="b" * 64,
        license_ref="cninfo-disclosure",
        source_policy_version="v1",
        ingested_at=datetime.now(UTC),
    )


def test_supplement_only_fills_missing_primary_field() -> None:
    supplement = NumericFieldCandidate(field_name="pe_ttm", value=Decimal("12.3"), provenance=provenance("baostock"))
    result = reconcile_numeric_field(None, supplement, ReconciliationPolicy(policy_version="v1", primary_source="investment_data"))

    assert result.status is ReconciliationStatus.SUPPLEMENTED
    assert result.selected is not None
    assert result.selected.provenance.role is ProvenanceRole.SUPPLEMENT


def test_conflicting_sources_are_quarantined_instead_of_overwriting_primary() -> None:
    primary = NumericFieldCandidate(field_name="pe_ttm", value=Decimal("12.3"), provenance=provenance("investment_data"))
    supplement = NumericFieldCandidate(field_name="pe_ttm", value=Decimal("14.0"), provenance=provenance("baostock"))

    result = reconcile_numeric_field(primary, supplement, ReconciliationPolicy(policy_version="v1", primary_source="investment_data", relative_tolerance=Decimal("0.01")))

    assert result.status is ReconciliationStatus.QUARANTINED
    assert result.selected is None
    assert result.reason == "value_conflict"


def test_financial_correction_requires_revision_chain_and_reason() -> None:
    with pytest.raises(ValueError, match="previous revision"):
        FinancialFact(
            security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"),
            fact_type="revenue",
            period_end=date(2025, 12, 31),
            value=Decimal(120),
            announced_at=datetime(2026, 4, 1, tzinfo=UTC),
            available_at=datetime(2026, 4, 2, tzinfo=UTC),
            revision=2,
            artifact=artifact(),
        )
