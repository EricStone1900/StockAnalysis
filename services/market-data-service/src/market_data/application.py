from datetime import date

from .domain import Security, SecurityId, SecurityStatus, TradingCalendar
from .versioning import VersionRegistry


class DuplicateSecurityError(ValueError):
    pass


class MarketDataService:
    def __init__(self) -> None:
        self._securities: dict[str, Security] = {}
        self._idempotency: dict[str, Security] = {}
        self.outbox: list[dict[str, str]] = []
        self.calendar = TradingCalendar(trading_days={date(2026, 8, 28)})
        self.versions = VersionRegistry()

    def register_security(self, security: Security, idempotency_key: str) -> Security:
        if idempotency_key in self._idempotency:
            return self._idempotency[idempotency_key]
        key = self._key(security.security_id)
        if key in self._securities:
            raise DuplicateSecurityError(key)
        self._securities[key] = security
        self._idempotency[idempotency_key] = security
        self.outbox.append({"type": "stock.market-data.security.registered.v1", "securityId": key})
        return security

    def update_status(self, security_id: SecurityId, status: SecurityStatus) -> Security:
        key = self._key(security_id)
        current = self._securities[key]
        updated = current.model_copy(update={"status": status})
        self._securities[key] = updated
        self.outbox.append({"type": "stock.market-data.security.status-changed.v1", "securityId": key})
        return updated

    def get_security(self, symbol: str) -> Security | None:
        return next((item for item in self._securities.values() if item.security_id.symbol == symbol), None)

    @staticmethod
    def _key(security_id: SecurityId) -> str:
        return f"{security_id.exchange}:{security_id.symbol}"
