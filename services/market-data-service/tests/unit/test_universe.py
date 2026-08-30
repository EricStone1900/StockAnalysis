from market_data.domain import Exchange, SecurityId
from market_data.universe import is_stage03_cn_a_equity


def test_stage03_equity_universe_keeps_only_shenzhen_and_shanghai_a_shares() -> None:
    assert is_stage03_cn_a_equity(SecurityId(exchange=Exchange.SSE, symbol="600000"))
    assert is_stage03_cn_a_equity(SecurityId(exchange=Exchange.SZSE, symbol="000001"))
    assert not is_stage03_cn_a_equity(SecurityId(exchange=Exchange.SSE, symbol="000852"))
    assert not is_stage03_cn_a_equity(SecurityId(exchange=Exchange.SZSE, symbol="399001"))
    assert not is_stage03_cn_a_equity(SecurityId(exchange=Exchange.BSE, symbol="430047"))
