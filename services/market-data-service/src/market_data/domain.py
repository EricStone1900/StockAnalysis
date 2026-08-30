from __future__ import annotations

from datetime import date, time
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Exchange(StrEnum):
    SSE = "SSE"
    SZSE = "SZSE"
    BSE = "BSE"


class SecurityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DELISTED = "DELISTED"


class SecurityId(BaseModel, frozen=True):
    market: str = "CN_A"
    exchange: Exchange
    symbol: str = Field(pattern=r"^[0-9]{6}$")


class Security(BaseModel):
    security_id: SecurityId
    name: str
    status: SecurityStatus = SecurityStatus.ACTIVE
    version: int = Field(default=1, ge=1)


class TradingSession(BaseModel, frozen=True):
    start: time
    end: time


class TradingCalendar(BaseModel):
    market: str = "CN_A"
    trading_days: set[date] = Field(default_factory=set)
    holidays: set[date] = Field(default_factory=set)

    @field_validator("market")
    @classmethod
    def cn_a_only(cls, value: str) -> str:
        if value != "CN_A":
            raise ValueError("only CN_A is supported in v1")
        return value

    def is_trading_day(self, day: date) -> bool:
        return day in self.trading_days and day not in self.holidays

    def sessions(self, day: date) -> list[TradingSession]:
        if not self.is_trading_day(day):
            return []
        return [
            TradingSession(start=time(9, 30), end=time(11, 30)),
            TradingSession(start=time(13, 0), end=time(15, 0)),
        ]
