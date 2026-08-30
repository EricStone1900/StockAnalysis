from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from .domain import SecurityId
from .lineage import FieldProvenance
from .pit import RawArtifact


class TradingStatus(StrEnum):
    TRADING = "TRADING"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"
    UNKNOWN = "UNKNOWN"


class CloseGapReconciliationStatus(StrEnum):
    SUSPENSION_CONFIRMED = "SUSPENSION_CONFIRMED"
    SUSPENSION_ASSUMED = "SUSPENSION_ASSUMED"
    UNEXPLAINED_MISSING = "UNEXPLAINED_MISSING"
    STATUS_UNKNOWN = "STATUS_UNKNOWN"
    QUARANTINED = "QUARANTINED"


class StatusEnrichmentMode(StrEnum):
    """状态空洞处理模式；快速模式只能记录业务假设，不能伪造供应商证据。"""

    EXACT = "exact"
    FAST = "fast"


class TradingStatusFact(BaseModel):
    """状态补充事实；`available_at`绝不能早于实际抓取并固化的时间。"""

    security_id: SecurityId
    trading_day: date
    trading_status: TradingStatus
    is_st: bool | None = None
    raw_tradestatus: str | None = None
    raw_is_st: str | None = None
    observed_at: datetime
    available_at: datetime
    artifact: RawArtifact
    field_provenance: tuple[FieldProvenance, ...] = ()


class CloseGapReconciliation(BaseModel):
    security_id: SecurityId
    trading_day: date
    status: CloseGapReconciliationStatus
    reason: str
    primary_provenance: FieldProvenance
    status_provenance: FieldProvenance | None = None


class StatusEnrichmentQualityReport(BaseModel):
    parent_version_id: str = Field(min_length=1)
    close_gap_count: int = Field(ge=0)
    suspension_confirmed_count: int = Field(ge=0)
    suspension_assumed_count: int = Field(default=0, ge=0)
    unexplained_missing_count: int = Field(ge=0)
    status_unknown_count: int = Field(ge=0)
    quarantined_count: int = Field(ge=0)
    st_count: int = Field(ge=0)
    status_coverage: float = Field(ge=0, le=1)
    excluded_bse_gap_count: int = Field(default=0, ge=0)
    excluded_non_equity_gap_count: int = Field(default=0, ge=0)

    @property
    def classified_count(self) -> int:
        return (
            self.suspension_confirmed_count
            + self.suspension_assumed_count
            + self.unexplained_missing_count
            + self.status_unknown_count
            + self.quarantined_count
        )


def visible_trading_status(facts: list[TradingStatusFact], as_of: datetime) -> list[TradingStatusFact]:
    """仅暴露已落盘可用的状态证据，禁止将事后补录用于历史时点。"""
    return [fact for fact in facts if fact.available_at <= as_of]
