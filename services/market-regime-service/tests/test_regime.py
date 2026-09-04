import pytest

from src.regime import FeatureInput, RegimeDefinition, RegimeStateMachine, classify


def features(**changes: object) -> FeatureInput:
    value: dict[str, object] = {"as_of": "2026-09-04T00:00:00Z", "dimensions": {"trend": 0.2, "breadth": 0.5, "volatility": 0.2, "liquidity": 0.5}, "data_version": "d1", "feature_version": "f1", "quality": "PASS", "evidence_ids": ["e1"]}
    value.update(changes)
    return FeatureInput.model_validate(value)


def test_classification_is_deterministic_and_versioned() -> None:
    snapshot = classify(features(), RegimeDefinition(version="r1"))
    assert snapshot.overall_regime == "RISK_ON"
    assert snapshot.snapshot_id.endswith(":r1")


def test_fail_quality_does_not_publish_regime() -> None:
    with pytest.raises(ValueError, match="FAIL"):
        classify(features(quality="FAIL"), RegimeDefinition(version="r1"))


def test_state_machine_holds_short_transition_and_marks_failure_stale() -> None:
    definition = RegimeDefinition(version="r1")
    machine = RegimeStateMachine(minimum_duration_minutes=30)
    first = machine.evaluate(features(), definition)
    changed = features(as_of="2026-09-04T00:10:00Z", dimensions={"trend": -0.8, "breadth": 0.1, "volatility": 0.2, "liquidity": 0.2})
    assert machine.evaluate(changed, definition).snapshot_id == first.snapshot_id
    stale = machine.evaluate(features(as_of="2026-09-04T01:00:00Z", quality="FAIL"), definition)
    assert stale.freshness == "STALE"
    assert stale.quality == "FAIL"
