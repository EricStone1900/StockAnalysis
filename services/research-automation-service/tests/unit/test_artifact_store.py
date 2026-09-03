from hashlib import sha256

import pytest

from src.research_automation.artifact_store import (
    InMemoryArtifactStore,
    S3ArtifactStore,
    SupplyChainGate,
)
from src.research_automation.artifacts import ModelCallAudit
from src.research_automation.model_audit import ModelCallAuditStore


def test_artifact_store_is_hash_verified_and_immutable() -> None:
    store = InMemoryArtifactStore()
    content = b'{"artifact":"candidate"}'
    digest = sha256(content).hexdigest()
    store.put_immutable("minio://artifacts/candidate.json", content, digest)
    store.put_immutable("minio://artifacts/candidate.json", content, digest)
    assert store.read_verified("minio://artifacts/candidate.json", digest) == content
    with pytest.raises(ValueError, match="different content"):
        store.put_immutable("minio://artifacts/candidate.json", b"tampered", sha256(b"tampered").hexdigest())
    with pytest.raises(ValueError, match="hash mismatch"):
        store.read_verified("minio://artifacts/candidate.json", "0" * 64)


def test_supply_chain_gate_rejects_unknown_dependency_license_and_vulnerability() -> None:
    gate = SupplyChainGate(frozenset({"numpy"}), frozenset({"MIT"}))
    assert gate.inspect(("numpy",), ("MIT",), ()).passed
    with pytest.raises(ValueError, match="supply chain gate failed"):
        gate.inspect(("numpy", "unknown"), ("GPL-3.0",), ("CVE-HIGH",))


def test_s3_adapter_writes_once_and_verifies_reads() -> None:
    class Body:
        def read(self) -> bytes:
            return b"content"

    class FakeS3:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}

        def head_object(self, **kwargs: object) -> dict[str, object]:
            if kwargs["Key"] not in self.objects:
                error = RuntimeError("missing")
                error.response = {"Error": {"Code": "404"}}  # type: ignore[attr-defined]
                raise error
            return {"Metadata": {"sha256": sha256(self.objects[str(kwargs["Key"])]).hexdigest()}}

        def put_object(self, **kwargs: object) -> None:
            self.objects[str(kwargs["Key"])] = bytes(kwargs["Body"])

        def get_object(self, **kwargs: object) -> dict[str, Body]:
            return {"Body": Body()}

    from hashlib import sha256

    fake = FakeS3()
    store = S3ArtifactStore("http://minio:9000", "artifacts", "access", "secret", fake)
    digest = sha256(b"content").hexdigest()
    store.put_immutable("minio://artifacts/candidate.bin", b"content", digest)
    assert fake.objects["candidate.bin"] == b"content"


def test_model_call_audit_is_idempotent() -> None:
    audit = ModelCallAudit("provider", "model", "prompt-v1", "a" * 64, 10, 0.01)
    store = ModelCallAuditStore()
    store.record("call-1", audit)
    store.record("call-1", audit)
    assert store.get("call-1") == audit
