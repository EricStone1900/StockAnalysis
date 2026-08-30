from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256


@dataclass(frozen=True)
class ProviderPolicy:
    provider: str
    license: str
    requests_per_minute: int
    timeout_seconds: float
    max_retries: int


@dataclass(frozen=True)
class FreshnessSlo:
    dataset: str
    max_delay: timedelta


DAILY_BAR_SLO = FreshnessSlo("daily_bar", timedelta(hours=18))
MINUTE_BAR_SLO = FreshnessSlo("minute_bar", timedelta(minutes=5))
FINANCIAL_FACT_SLO = FreshnessSlo("financial_fact", timedelta(hours=24))


def verify_artifact(content: bytes, expected_hash: str) -> bool:
    return sha256(content).hexdigest() == expected_hash


def is_stale(available_at: datetime, now: datetime, slo: FreshnessSlo) -> bool:
    return now - available_at > slo.max_delay


class SourceSelector:
    def __init__(self, primary: ProviderPolicy, fallback: ProviderPolicy) -> None:
        self.primary = primary
        self.fallback = fallback

    def select(self, primary_healthy: bool) -> tuple[ProviderPolicy, bool]:
        return (self.primary, False) if primary_healthy else (self.fallback, True)
