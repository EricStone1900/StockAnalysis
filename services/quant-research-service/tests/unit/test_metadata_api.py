from fastapi.testclient import TestClient

from main import app, metadata_repository


def test_metadata_api_is_read_only_and_returns_not_found() -> None:
    client = TestClient(app)
    missing = client.get("/api/v1/runs/missing-run")
    assert missing.status_code == 404
    assert client.post("/api/v1/runs/missing-run").status_code == 405
    assert client.get("/api/v1/daily-analysis-snapshots/missing").status_code == 404
    assert client.get("/api/v1/daily-analysis-snapshots/latest").status_code == 404
    assert client.post("/api/v1/daily-analysis-snapshots/missing").status_code == 405


def test_readiness_reports_metadata_query_capability() -> None:
    response = TestClient(app).get("/ready")
    assert response.status_code == 200
    assert response.json()["capabilities"]["metadata_query"] == "S3_POSTGRES_OR_IN_MEMORY"
    assert metadata_repository is not None


def test_strategy_api_is_read_only() -> None:
    client = TestClient(app)
    assert client.get("/api/v1/strategies/no-rebalance/v1").status_code == 404
    assert client.get("/api/v1/strategy-snapshots/missing").status_code == 404
    assert client.get("/api/v1/strategy-runs/missing").status_code == 404
    assert client.post("/api/v1/strategies/no-rebalance/v1").status_code == 405
    assert client.post("/api/v1/strategy-snapshots/missing").status_code == 405
    assert client.post("/api/v1/strategy-runs/missing").status_code == 405


def test_openapi_exposes_only_strategy_read_endpoints() -> None:
    paths = app.openapi()["paths"]
    assert "/api/v1/strategies/{strategy_id}/{version}" in paths
    assert "/api/v1/strategy-snapshots/{snapshot_id}" in paths
    assert "/api/v1/strategy-runs/{run_id}" in paths
    assert "/api/v1/daily-analysis-snapshots/{snapshot_id}" in paths
    assert "/api/v1/daily-analysis-snapshots/latest" in paths
    assert not any("orders" in path or "trade-proposals" in path for path in paths)
