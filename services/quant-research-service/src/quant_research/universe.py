"""历史股票池：只使用截至计算时点已经可得的证券状态。"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UniverseEligibilityInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    security_id: str = Field(min_length=1)
    listed_on: date
    delisted_on: date | None = None
    status_available_at: datetime
    is_st: bool
    is_suspended: bool
    average_daily_turnover: Decimal = Field(ge=0)

    @field_validator("status_available_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("status_available_at must use UTC")
        return value


class HistoricalUniverseDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    universe_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    as_of_date: date
    cutoff_at: datetime
    min_listed_days: int = Field(ge=0)
    min_average_daily_turnover: Decimal = Field(ge=0)
    exclude_st: bool = True
    exclude_suspended: bool = True
    exclude_bse: bool = True

    @field_validator("cutoff_at")
    @classmethod
    def require_utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("cutoff_at must use UTC")
        return value


class HistoricalUniverseSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    definition: HistoricalUniverseDefinition
    members: tuple[str, ...]
    canonical_content_hash: str


def build_historical_universe(
    definition: HistoricalUniverseDefinition,
    inputs: tuple[UniverseEligibilityInput, ...],
) -> HistoricalUniverseSnapshot:
    """构建无未来成分的股票池；晚于cutoff的状态记录不会参与判断。"""
    members = tuple(
        sorted(
            item.security_id
            for item in inputs
            if _is_eligible(definition, item)
        )
    )
    payload = {
        "definition": definition.model_dump(mode="json"),
        "members": members,
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str)
    return HistoricalUniverseSnapshot(
        definition=definition,
        members=members,
        canonical_content_hash=sha256(canonical.encode("utf-8")).hexdigest(),
    )


def _is_eligible(definition: HistoricalUniverseDefinition, item: UniverseEligibilityInput) -> bool:
    if item.status_available_at > definition.cutoff_at:
        return False
    if item.listed_on > definition.as_of_date:
        return False
    if (definition.as_of_date - item.listed_on).days < definition.min_listed_days:
        return False
    if item.delisted_on is not None and item.delisted_on <= definition.as_of_date:
        return False
    if definition.exclude_bse and _is_bse_security(item.security_id):
        return False
    if definition.exclude_st and item.is_st:
        return False
    if definition.exclude_suspended and item.is_suspended:
        return False
    return item.average_daily_turnover >= definition.min_average_daily_turnover


def _is_bse_security(security_id: str) -> bool:
    normalized = security_id.lower()
    return normalized.startswith("bj") or normalized.endswith(".bj")
