from src.monitoring import AnomalyDeduplicator, ClosedBar, RuleVersion, detect_anomaly


def bar(close: float, volume: float) -> ClosedBar:
    return ClosedBar(
        security_id="SSE:1", window_start="2026-09-04T01:30:00Z", window_end="2026-09-04T01:35:00Z",
        open=close, high=close, low=close, close=close, volume=volume, amount=close * volume,
        quality="PASS", source_event_ids=["q-1"],
    )


def test_rules_emit_deterministic_event_and_no_event_for_normal_bar() -> None:
    rule = RuleVersion(version="r1", price_jump_pct=0.05, volume_multiplier=2)
    event = detect_anomaly(bar(100, 10), bar(110, 30), rule, baseline_volume=10)
    assert event is not None
    assert event.severity == "CRITICAL"
    assert event.reason_codes == ("PRICE_JUMP", "VOLUME_SURGE")
    assert detect_anomaly(bar(100, 10), bar(101, 11), rule, baseline_volume=10) is None

    deduplicator = AnomalyDeduplicator()
    assert deduplicator.accept(event) is True
    assert deduplicator.accept(event) is False
