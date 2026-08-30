from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from .domain import SecurityId
from .lineage import FieldProvenance


class RawArtifact(BaseModel):
    source: str
    source_record_id: str
    source_version: str
    source_release_tag: str | None = None
    raw_artifact_uri: str
    raw_artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    license_ref: str
    source_policy_version: str
    ingested_at: datetime

    @property
    def content_hash(self) -> str:
        """兼容Qlib Artifact生成代码；值始终是原始Artifact的SHA-256。"""
        return self.raw_artifact_hash


class DailyBar(BaseModel):
    security_id: SecurityId
    trading_day: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal
    available_at: datetime
    artifact: RawArtifact
    field_provenance: tuple[FieldProvenance, ...] = ()


class FinancialFact(BaseModel):
    security_id: SecurityId
    fact_type: str
    period_end: date
    value: Decimal
    announced_at: datetime
    available_at: datetime
    revision: int = Field(ge=1)
    revision_reason: str | None = None
    supersedes_revision: int | None = Field(default=None, ge=1)
    artifact: RawArtifact
    field_provenance: tuple[FieldProvenance, ...] = ()

    @model_validator(mode="after")
    def validate_revision_chain(self) -> "FinancialFact":
        if self.available_at < self.announced_at:
            raise ValueError("available_at must not be earlier than announced_at")
        if self.revision == 1 and (self.revision_reason is not None or self.supersedes_revision is not None):
            raise ValueError("initial financial fact must not supersede another revision")
        if self.revision > 1 and (not self.revision_reason or self.supersedes_revision != self.revision - 1):
            raise ValueError("corrected financial fact must identify the previous revision and reason")
        return self


class CorporateAction(BaseModel):
    security_id: SecurityId
    action_type: str
    ex_date: date
    available_at: datetime
    adjustment_factor: Decimal
    artifact: RawArtifact
    field_provenance: tuple[FieldProvenance, ...] = ()


def visible_actions(actions: list[CorporateAction], as_of: datetime) -> list[CorporateAction]:
    return [action for action in actions if action.available_at <= as_of]


def point_in_time_facts(facts: list[FinancialFact], as_of: datetime) -> list[FinancialFact]:
    latest: dict[tuple[SecurityId, str, date], FinancialFact] = {}
    for fact in facts:
        if fact.available_at > as_of:
            continue
        key = (fact.security_id, fact.fact_type, fact.period_end)
        current = latest.get(key)
        if current is None or (fact.available_at, fact.revision) > (current.available_at, current.revision):
            latest[key] = fact
    return list(latest.values())
