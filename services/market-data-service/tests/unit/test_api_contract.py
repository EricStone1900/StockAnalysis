import asyncio

import pytest
from fastapi import HTTPException, Request

import main


def test_openapi_exposes_stage_two_public_contracts() -> None:
    paths = main.app.openapi()["paths"]
    assert "/api/v1/securities" in paths
    assert "/api/v1/securities/{symbol}" in paths
    assert "/api/v1/securities/{symbol}/status" in paths
    assert "/api/v1/calendars/{market}" in paths
    assert "/api/v1/data-versions" in paths
    assert "/api/v1/data-versions/latest" in paths
    assert "/api/v1/prices/{symbol}" in paths
    assert "Idempotency-Key" in {item["name"] for item in paths["/api/v1/data-versions"]["post"]["parameters"]}
    assert "/internal/v1/jobs/import-investment-data" in paths
    assert {item["name"] for item in paths["/internal/v1/jobs/import-investment-data"]["post"]["parameters"]} == {
        "Idempotency-Key",
        "X-Import-Token",
    }
    assert "/internal/v1/jobs/enrich-baostock-status" in paths
    assert {item["name"] for item in paths["/internal/v1/jobs/enrich-baostock-status"]["post"]["parameters"]} == {
        "Idempotency-Key",
        "X-Import-Token",
    }


def test_import_task_is_disabled_without_configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKET_DATA_IMPORT_TOKEN", raising=False)
    with pytest.raises(HTTPException, match="not enabled") as error:
        main.require_import_token("not-configured")
    assert error.value.status_code == 503


def test_import_task_rejects_wrong_token_before_download(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARKET_DATA_IMPORT_TOKEN", "expected-token")
    with pytest.raises(HTTPException, match="invalid import token") as error:
        main.require_import_token("wrong-token")
    assert error.value.status_code == 403


def test_status_enrichment_task_is_disabled_without_configured_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MARKET_DATA_IMPORT_TOKEN", raising=False)
    with pytest.raises(HTTPException, match="not enabled") as error:
        main.require_import_token("not-configured")
    assert error.value.status_code == 503


@pytest.mark.parametrize(
    ("path", "token", "expected_status"),
    (
        ("/internal/v1/jobs/import-investment-data", None, 503),
        ("/internal/v1/jobs/enrich-baostock-status", None, 503),
        ("/internal/v1/jobs/import-investment-data", "wrong-token", 403),
        ("/internal/v1/jobs/enrich-baostock-status", "wrong-token", 403),
    ),
)
def test_internal_tasks_authorize_before_validating_body(
    monkeypatch: pytest.MonkeyPatch, path: str, token: str | None, expected_status: int
) -> None:
    if token is None:
        monkeypatch.delenv("MARKET_DATA_IMPORT_TOKEN", raising=False)
        submitted_token = "not-configured"
    else:
        monkeypatch.setenv("MARKET_DATA_IMPORT_TOKEN", "expected-token")
        submitted_token = token

    async def body_must_not_be_read() -> dict[str, object]:
        raise AssertionError("request body must not be read before authorization")

    raw_request = Request({"type": "http", "method": "POST", "path": path, "headers": []}, body_must_not_be_read)
    handler = main.import_investment_data if path.endswith("import-investment-data") else main.enrich_baostock_status

    with pytest.raises(HTTPException) as error:
        asyncio.run(handler(raw_request, "authorization-order-test", submitted_token))
    assert error.value.status_code == expected_status
