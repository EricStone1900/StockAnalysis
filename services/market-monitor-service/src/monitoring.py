"""批量快照、Watchlist和5分钟封闭Bar的确定性实现。"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, Field


class Quote(BaseModel):
    security_id: str
    timestamp: AwareDatetime
    price: float = Field(gt=0)
    volume: float = Field(ge=0)
    amount: float = Field(ge=0)
    trading_status: Literal["ACTIVE", "SUSPENDED"] = "ACTIVE"


class ClosedBar(BaseModel):
    security_id: str
    window_start: AwareDatetime
    window_end: AwareDatetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    quality: Literal["PASS", "WARN", "FAIL"]
    source_event_ids: list[str]


class RuleVersion(BaseModel):
    version: str
    price_jump_pct: float = Field(gt=0)
    volume_multiplier: float = Field(gt=1)


class SnapshotQuality(BaseModel):
    source: str
    schema_version: str
    quote_age_seconds: float = Field(ge=0)
    coverage: float = Field(ge=0, le=1)
    provider_available: bool

    def gate(self, *, max_age_seconds: float = 180, min_coverage: float = 1) -> Literal["PASS", "STALE", "FAIL"]:
        if not self.provider_available or self.coverage < min_coverage:
            return "FAIL"
        if self.quote_age_seconds > max_age_seconds:
            return "STALE"
        return "PASS"


class MarketAnomalyEvent(BaseModel):
    event_id: str
    security_id: str
    window_start: AwareDatetime
    rule_version: str
    severity: Literal["WATCH", "CRITICAL"]
    reason_codes: tuple[str, ...]
    evidence_ids: tuple[str, ...]


class AnomalyDeduplicator:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def accept(self, event: MarketAnomalyEvent) -> bool:
        if event.event_id in self._seen:
            return False
        self._seen.add(event.event_id)
        return True


class WatchlistEntry(BaseModel):
    security_id: str
    tier: Literal["P0", "P1", "P2"]


class Watchlist(BaseModel):
    version: str
    entries: list[WatchlistEntry]

    def validate_capacity(self, max_symbols: int = 50) -> None:
        if len({entry.security_id for entry in self.entries}) > max_symbols:
            raise ValueError(f"watchlist exceeds {max_symbols} symbols")


class MonitorPolicy(BaseModel):
    version: str
    mode: Literal["FREE_TIERED_10_20_30"] = "FREE_TIERED_10_20_30"
    intervals_minutes: dict[str, int] = {"P0": 10, "P1": 20, "P2": 30}
    max_symbols: int = 50

    def validate_for_watchlist(self, watchlist: Watchlist) -> None:
        watchlist.validate_capacity(self.max_symbols)
        if self.intervals_minutes != {"P0": 10, "P1": 20, "P2": 30}:
            raise ValueError("FREE_TIERED_10_20_30 intervals are fixed")


def due_tiers(policy: MonitorPolicy, last_evaluation: datetime, now: datetime) -> tuple[str, ...]:
    if last_evaluation.tzinfo is None or now.tzinfo is None:
        raise ValueError("evaluation timestamps must include timezone")
    elapsed = (now.astimezone(UTC) - last_evaluation.astimezone(UTC)).total_seconds() / 60
    return tuple(tier for tier in ("P0", "P1", "P2") if elapsed >= policy.intervals_minutes[tier])


def detect_anomaly(previous: ClosedBar, current: ClosedBar, rule: RuleVersion, baseline_volume: float) -> MarketAnomalyEvent | None:
    reasons: list[str] = []
    if previous.close > 0 and abs(current.close / previous.close - 1) >= rule.price_jump_pct:
        reasons.append("PRICE_JUMP")
    if baseline_volume > 0 and current.volume >= baseline_volume * rule.volume_multiplier:
        reasons.append("VOLUME_SURGE")
    if not reasons or current.quality == "FAIL":
        return None
    severity: Literal["WATCH", "CRITICAL"] = "CRITICAL" if "PRICE_JUMP" in reasons else "WATCH"
    return MarketAnomalyEvent(
        event_id=f"anomaly:{current.security_id}:{current.window_start.isoformat()}:{rule.version}",
        security_id=current.security_id, window_start=current.window_start, rule_version=rule.version,
        severity=severity, reason_codes=tuple(reasons), evidence_ids=tuple(current.source_event_ids),
    )


def aggregate_closed_bars(quotes: list[Quote], now: datetime) -> list[ClosedBar]:
    if now.tzinfo is None:
        raise ValueError("now must include timezone")
    groups: dict[tuple[str, datetime], list[Quote]] = defaultdict(list)
    for quote in quotes:
        stamp = quote.timestamp.astimezone(ZoneInfo("Asia/Shanghai"))
        minute = stamp.replace(second=0, microsecond=0)
        start = minute - timedelta(minutes=minute.minute % 5)
        end = start + timedelta(minutes=5)
        if end <= now.astimezone(ZoneInfo("Asia/Shanghai")) and _is_trading_window(start, end):
            groups[(quote.security_id, start)].append(quote)
    bars: list[ClosedBar] = []
    for (security_id, start), values in sorted(groups.items()):
        ordered = sorted(values, key=lambda value: value.timestamp)
        prices = [value.price for value in ordered]
        quality: Literal["PASS", "WARN"] = "WARN" if any(value.trading_status == "SUSPENDED" for value in ordered) else "PASS"
        bars.append(ClosedBar(
            security_id=security_id, window_start=start, window_end=start + timedelta(minutes=5),
            open=prices[0], high=max(prices), low=min(prices), close=prices[-1],
            volume=sum(value.volume for value in ordered), amount=sum(value.amount for value in ordered),
            quality=quality, source_event_ids=[f"quote:{value.timestamp.isoformat()}" for value in ordered],
        ))
    return bars


def _is_trading_window(start: datetime, end: datetime) -> bool:
    """首版交易时段：09:30-11:30、13:00-15:00；不跨越午休。"""
    morning = start.hour == 9 and start.minute >= 30 or start.hour == 10 or start.hour == 11 and end.minute <= 30
    afternoon = start.hour in (13, 14) and end.hour <= 15
    return morning or afternoon
