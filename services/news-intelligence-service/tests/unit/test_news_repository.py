from hashlib import sha256

import pytest

from src.news_repository import MinioEvidenceStore, verify_evidence_content


class FakeS3Client:
    def __init__(self, existing_metadata: dict[str, str] | None = None) -> None:
        self.existing_metadata = existing_metadata
        self.put_calls: list[dict[str, object]] = []

    def head_object(self, **_: object) -> dict[str, object]:
        if self.existing_metadata is None:
            error = RuntimeError("not found")
            error.response = {"Error": {"Code": "404"}}  # type: ignore[attr-defined]
            raise error
        return {"Metadata": self.existing_metadata}

    def put_object(self, **kwargs: object) -> None:
        self.put_calls.append(kwargs)


def store_with_client(client: FakeS3Client) -> MinioEvidenceStore:
    store = MinioEvidenceStore.__new__(MinioEvidenceStore)
    store._bucket = "artifacts"  # type: ignore[attr-defined]
    store._client = client  # type: ignore[attr-defined]
    return store


def test_verify_evidence_content_rejects_mismatched_hash() -> None:
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_evidence_content(b"actual", "0" * 64)


def test_minio_put_is_idempotent_for_existing_immutable_object() -> None:
    content = "公告正文"
    digest = sha256(content.encode()).hexdigest()
    client = FakeS3Client({"sha256": digest})
    artifact = store_with_client(client).put(content, digest, "official-v1")
    assert artifact.uri == f"s3://artifacts/news/{digest}.txt"
    assert client.put_calls == []


def test_minio_put_rejects_different_content_at_existing_key() -> None:
    content = "公告正文"
    digest = sha256(content.encode()).hexdigest()
    client = FakeS3Client({"sha256": "f" * 64})
    with pytest.raises(ValueError, match="different content"):
        store_with_client(client).put(content, digest, "official-v1")


def test_minio_put_writes_hash_metadata_for_new_object() -> None:
    content = "新公告"
    digest = sha256(content.encode()).hexdigest()
    client = FakeS3Client()
    store_with_client(client).put(content, digest, "official-v1")
    assert client.put_calls[0]["Metadata"] == {"sha256": digest}
