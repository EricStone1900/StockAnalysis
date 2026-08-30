import asyncio

import pytest

from market_data.outbox import OutboxRelay
from market_data.storage import ArtifactStore


class MissingObjectError(Exception):
    def __init__(self) -> None:
        self.response = {"Error": {"Code": "404"}}


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.put_calls = 0

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, dict[str, str]]:
        del Bucket
        if Key not in self.objects:
            raise MissingObjectError
        return {"Metadata": {"sha256": self.objects[Key][1]}}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, Metadata: dict[str, str]) -> None:
        del Bucket
        self.put_calls += 1
        self.objects[Key] = (Body, Metadata["sha256"])


def test_outbox_retries_after_timeout() -> None:
    calls = 0
    async def publish(_: str, __: bytes) -> None:
        nonlocal calls
        calls += 1
        if calls == 1: raise TimeoutError
    assert asyncio.run(OutboxRelay(publish).relay("stock.market-data.data-version.published.v1", b"{}"))
    assert calls == 2


def test_immutable_artifact_write_is_idempotent_and_rejects_overwrite() -> None:
    store = ArtifactStore("http://unused", "key", "secret", "artifacts")
    client = FakeS3Client()
    store.client = client

    first_hash = store.put_immutable("raw/test.bin", b"first")
    assert store.put_immutable("raw/test.bin", b"first") == first_hash
    assert client.put_calls == 1
    with pytest.raises(ValueError, match="different content"):
        store.put_immutable("raw/test.bin", b"replacement")
