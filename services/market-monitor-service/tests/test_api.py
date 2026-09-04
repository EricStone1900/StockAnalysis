from src.main import evaluate_anomaly
from src.monitoring import ClosedBar, RuleVersion


def payload() -> dict[str, object]:
    previous = ClosedBar(security_id="SSE:9", window_start="2026-09-04T01:30:00Z", window_end="2026-09-04T01:35:00Z", open=100, high=100, low=100, close=100, volume=10, amount=1000, quality="PASS", source_event_ids=["p"])
    current = ClosedBar(security_id="SSE:9", window_start="2026-09-04T01:35:00Z", window_end="2026-09-04T01:40:00Z", open=110, high=110, low=110, close=110, volume=30, amount=3300, quality="PASS", source_event_ids=["c"])
    return {"previous": previous, "current": current, "rule": RuleVersion(version="api-r1", price_jump_pct=0.05, volume_multiplier=2), "baselineVolume": 10}


def test_anomaly_api_deduplicates_event() -> None:
    first = evaluate_anomaly(payload())
    repeated = evaluate_anomaly(payload())
    assert first["published"] is True
    assert repeated["published"] is False
    assert repeated["reason"] == "DUPLICATE"
