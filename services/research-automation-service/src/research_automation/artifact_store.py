"""候选 Artifact 不可变存储和供应链门禁。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from .artifacts import CandidateArtifact


class ArtifactStore(Protocol):
    def put_immutable(self, uri: str, content: bytes, expected_hash: str) -> None: ...
    def read_verified(self, uri: str, expected_hash: str) -> bytes: ...


class InMemoryArtifactStore:
    """测试用内容寻址存储；生产实现应替换为受限MinIO/S3 Adapter。"""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def put_immutable(self, uri: str, content: bytes, expected_hash: str) -> None:
        actual = sha256(content).hexdigest()
        if actual != expected_hash:
            raise ValueError("artifact content hash mismatch")
        existing = self._objects.get(uri)
        if existing is not None and existing != content:
            raise ValueError("artifact URI already contains different content")
        self._objects[uri] = content

    def read_verified(self, uri: str, expected_hash: str) -> bytes:
        content = self._objects.get(uri)
        if content is None:
            raise FileNotFoundError(uri)
        if sha256(content).hexdigest() != expected_hash:
            raise ValueError("artifact content hash mismatch")
        return content


class CandidateArtifactPublisher:
    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    def publish(self, candidate: CandidateArtifact, manifest: dict[str, object]) -> None:
        payload = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        self._store.put_immutable(candidate.artifact_uri, payload, candidate.artifact_hash)


@dataclass(frozen=True)
class SupplyChainReport:
    dependencies: tuple[str, ...]
    licenses: tuple[str, ...]
    vulnerabilities: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.vulnerabilities


class SupplyChainGate:
    def __init__(self, allowed_dependencies: frozenset[str], allowed_licenses: frozenset[str]) -> None:
        self._allowed_dependencies = allowed_dependencies
        self._allowed_licenses = allowed_licenses

    def inspect(self, dependencies: tuple[str, ...], licenses: tuple[str, ...], vulnerabilities: tuple[str, ...]) -> SupplyChainReport:
        unknown_dependencies = sorted(set(dependencies) - self._allowed_dependencies)
        forbidden_licenses = sorted(set(licenses) - self._allowed_licenses)
        findings = tuple(vulnerabilities) + tuple(f"dependency:{item}" for item in unknown_dependencies) + tuple(f"license:{item}" for item in forbidden_licenses)
        report = SupplyChainReport(tuple(dependencies), tuple(licenses), findings)
        if not report.passed:
            raise ValueError("supply chain gate failed: " + ",".join(report.vulnerabilities))
        return report
