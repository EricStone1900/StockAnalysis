"""候选 Artifact 不可变存储和供应链门禁。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Protocol, cast

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


class S3ArtifactStore:
    """MinIO/S3不可变对象适配器；密钥由调用方从Secret文件读取。"""

    def __init__(self, endpoint_url: str, bucket: str, access_key: str, secret_key: str, client: Any | None = None) -> None:
        if not bucket or not endpoint_url.startswith(("http://", "https://")):
            raise ValueError("S3 endpoint and bucket are required")
        if client is None:
            import boto3  # type: ignore[import-untyped]

            client = boto3.client("s3", endpoint_url=endpoint_url, aws_access_key_id=access_key, aws_secret_access_key=secret_key)
        self._client: Any = client
        self._bucket = bucket

    def put_immutable(self, uri: str, content: bytes, expected_hash: str) -> None:
        key = _object_key(uri)
        actual = sha256(content).hexdigest()
        if actual != expected_hash:
            raise ValueError("artifact content hash mismatch")
        try:
            head = self._client.head_object(Bucket=self._bucket, Key=key)
        except Exception as error:
            if _error_code(error) != "404":
                raise
            self._client.put_object(Bucket=self._bucket, Key=key, Body=content, Metadata={"sha256": expected_hash})
            return
        if str(head.get("Metadata", {}).get("sha256", "")) != expected_hash:
            raise ValueError("artifact URI already contains different content")

    def read_verified(self, uri: str, expected_hash: str) -> bytes:
        key = _object_key(uri)
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        content = cast(bytes, response["Body"].read())
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


def _object_key(uri: str) -> str:
    if "://" not in uri:
        raise ValueError("artifact URI must be object-store URI")
    key = uri.split("://", 1)[1].split("/", 1)[-1]
    if not key or key.startswith("/") or ".." in key.split("/"):
        raise ValueError("invalid artifact object key")
    return key


def _error_code(error: Exception) -> str:
    response = getattr(error, "response", {})
    return str(response.get("Error", {}).get("Code", ""))
