import pytest

from src.main import build_ingestion_service


def test_without_storage_environment_uses_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("NEWS_INTELLIGENCE_DATABASE_URL", "MINIO_ENDPOINT", "MINIO_ACCESS_KEY", "MINIO_SECRET_KEY", "MINIO_SECRET_KEY_FILE", "ARTIFACT_BUCKET"):
        monkeypatch.delenv(name, raising=False)
    assert build_ingestion_service().__class__.__name__ == "NewsIngestionService"


def test_partial_storage_environment_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEWS_INTELLIGENCE_DATABASE_URL", "postgresql://example.invalid/news")
    with pytest.raises(RuntimeError, match="incomplete"):
        build_ingestion_service()
