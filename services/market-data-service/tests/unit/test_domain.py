from datetime import date

import pytest

from market_data.application import DuplicateSecurityError, MarketDataService
from market_data.domain import Exchange, Security, SecurityId


def test_idempotent_registration_emits_one_event() -> None:
    service = MarketDataService()
    security = Security(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), name="浦发银行")
    assert service.register_security(security, "key-1") == service.register_security(security, "key-1")
    assert len(service.outbox) == 1


def test_duplicate_registration_is_rejected() -> None:
    service = MarketDataService()
    security = Security(security_id=SecurityId(exchange=Exchange.SSE, symbol="600000"), name="浦发银行")
    service.register_security(security, "key-1")
    with pytest.raises(DuplicateSecurityError): service.register_security(security, "key-2")


def test_calendar_has_lunch_break_and_weekend_is_closed() -> None:
    service = MarketDataService()
    assert len(service.calendar.sessions(date(2026, 8, 28))) == 2
    assert not service.calendar.is_trading_day(date(2026, 8, 29))
