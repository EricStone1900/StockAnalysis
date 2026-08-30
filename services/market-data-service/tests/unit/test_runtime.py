from market_data.runtime import endpoint_reachable


def test_unreachable_endpoint_is_reported() -> None:
    assert not endpoint_reachable("nats://127.0.0.1:1")
