from hashlib import sha256

import pytest

from src.research_automation.artifact_store import InMemoryArtifactStore, SupplyChainGate


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
