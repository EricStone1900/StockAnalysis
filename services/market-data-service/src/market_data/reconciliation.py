from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from .lineage import FieldProvenance, ProvenanceRole


class ReconciliationStatus(StrEnum):
    PRIMARY_ONLY = "PRIMARY_ONLY"
    SUPPLEMENTED = "SUPPLEMENTED"
    VERIFIED = "VERIFIED"
    QUARANTINED = "QUARANTINED"


class ReconciliationPolicy(BaseModel):
    policy_version: str = Field(min_length=1)
    primary_source: str = Field(min_length=1)
    relative_tolerance: Decimal = Field(default=Decimal(0), ge=Decimal(0))


class NumericFieldCandidate(BaseModel):
    field_name: str = Field(min_length=1)
    value: Decimal
    provenance: FieldProvenance


class ReconciliationResult(BaseModel):
    status: ReconciliationStatus
    selected: NumericFieldCandidate | None
    reason: str | None = None


def reconcile_numeric_field(
    primary: NumericFieldCandidate | None,
    supplement: NumericFieldCandidate | None,
    policy: ReconciliationPolicy,
) -> ReconciliationResult:
    """只允许补缺；数值冲突必须隔离，禁止静默选取补充源。"""
    if primary is None and supplement is None:
        return ReconciliationResult(status=ReconciliationStatus.QUARANTINED, selected=None, reason="no_candidate")
    if primary is None:
        if supplement is None:
            raise AssertionError("unreachable")
        selected = supplement.model_copy(
            update={"provenance": supplement.provenance.model_copy(update={"role": ProvenanceRole.SUPPLEMENT})}
        )
        return ReconciliationResult(status=ReconciliationStatus.SUPPLEMENTED, selected=selected)
    if supplement is None:
        return ReconciliationResult(status=ReconciliationStatus.PRIMARY_ONLY, selected=primary)
    if primary.field_name != supplement.field_name:
        return ReconciliationResult(status=ReconciliationStatus.QUARANTINED, selected=None, reason="field_name_mismatch")
    if primary.provenance.source != policy.primary_source:
        return ReconciliationResult(status=ReconciliationStatus.QUARANTINED, selected=None, reason="unexpected_primary_source")

    scale = max(abs(primary.value), Decimal(1))
    difference = abs(primary.value - supplement.value) / scale
    if difference > policy.relative_tolerance:
        return ReconciliationResult(status=ReconciliationStatus.QUARANTINED, selected=None, reason="value_conflict")
    selected = primary.model_copy(
        update={"provenance": primary.provenance.model_copy(update={"role": ProvenanceRole.VERIFIED})}
    )
    return ReconciliationResult(status=ReconciliationStatus.VERIFIED, selected=selected)
