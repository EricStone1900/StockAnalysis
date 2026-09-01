from main import live


def test_live() -> None:
    assert live() == {"status": "UP"}
