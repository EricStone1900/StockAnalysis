import pytest
from fastapi import HTTPException

from src.main import analyze_candidate, create_candidate


def news_item() -> dict[str, object]:
    return {
        "news_id": "n-api-1", "source_id": "official", "canonical_url": "https://example.test/1",
        "title": "星河科技发布公告", "language": "zh-CN", "published_at": "2026-09-04T01:00:00Z",
        "collected_at": "2026-09-04T01:01:00Z", "available_at": "2026-09-04T01:01:00Z",
        "source_reliability": 1, "content_hash": "a" * 64,
        "evidence": {"uri": "s3://artifacts/news/a.txt", "content_hash": "a" * 64, "license_policy_id": "v1"},
    }


def test_candidate_and_analysis_api_are_idempotent() -> None:
    candidate = create_candidate({
        "newsItem": news_item(), "entities": [{"symbol": "SSE:1", "name": "星河科技"}],
    })["candidate"]
    first = analyze_candidate({"candidate": candidate, "agentRunId": "api-run-1"})
    repeated = analyze_candidate({"candidate": candidate, "agentRunId": "api-run-1"})
    assert first["event"] == repeated["event"]


def test_analysis_api_rejects_missing_run_id() -> None:
    with pytest.raises(HTTPException) as error:
        analyze_candidate({"candidate": {}})
    assert error.value.status_code == 400
