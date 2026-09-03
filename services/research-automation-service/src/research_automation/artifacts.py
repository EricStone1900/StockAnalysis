"""候选 Artifact 与可复现研究清单。"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256


class CandidateArtifactKind(StrEnum):
    CODE = "CODE"
    MODEL = "MODEL"
    EXPERIMENT_LOG = "EXPERIMENT_LOG"


@dataclass(frozen=True)
class ReproducibilityManifest:
    data_version_id: str
    data_artifact_hash: str
    dependency_lock_hash: str
    image_digest: str
    parameter_hash: str
    random_seed: int
    evaluation_protocol_version: str

    @property
    def content_hash(self) -> str:
        payload = {
            "dataVersionId": self.data_version_id,
            "dataArtifactHash": self.data_artifact_hash,
            "dependencyLockHash": self.dependency_lock_hash,
            "imageDigest": self.image_digest,
            "parameterHash": self.parameter_hash,
            "randomSeed": self.random_seed,
            "evaluationProtocolVersion": self.evaluation_protocol_version,
        }
        return _hash(payload)


@dataclass(frozen=True)
class CandidateArtifact:
    artifact_id: str
    kind: CandidateArtifactKind
    artifact_uri: str
    artifact_hash: str
    manifest: ReproducibilityManifest
    created_at: datetime

    def __post_init__(self) -> None:
        if len(self.artifact_hash) != 64 or not self.artifact_uri.startswith(("s3://", "minio://")):
            raise ValueError("candidate artifact must use an object-store URI and SHA-256")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() != UTC.utcoffset(self.created_at):
            raise ValueError("created_at must use UTC")

    @property
    def content_hash(self) -> str:
        return _hash({
            "artifactId": self.artifact_id,
            "kind": self.kind.value,
            "artifactUri": self.artifact_uri,
            "artifactHash": self.artifact_hash,
            "manifestHash": self.manifest.content_hash,
        })


@dataclass(frozen=True)
class ModelCallAudit:
    provider: str
    model_id: str
    prompt_version: str
    input_hash: str
    token_count: int
    cost: float

    def __post_init__(self) -> None:
        if self.token_count < 0 or self.cost < 0:
            raise ValueError("model token count and cost cannot be negative")


@dataclass(frozen=True)
class CodeScanFinding:
    rule: str
    line: int
    detail: str


class CandidateCodeScanner:
    """生成代码进入 Sandbox 前的静态拒绝规则。"""

    _rules: tuple[tuple[str, re.Pattern[str], str], ...] = (
        ("network", re.compile(r"\b(socket|requests|httpx|urllib|ftplib)\b"), "network access is forbidden"),
        ("process", re.compile(r"\b(subprocess|os\.system|os\.popen)\b"), "process spawning is forbidden"),
        ("secrets", re.compile(r"\b(os\.environ|secret|token|password)\b", re.IGNORECASE), "secret access is forbidden"),
        ("dynamic-code", re.compile(r"\b(eval|exec|compile)\s*\("), "dynamic code execution is forbidden"),
        ("dependency-install", re.compile(r"\b(pip|pip3)\s+install\b"), "runtime dependency installation is forbidden"),
    )

    def scan(self, source: str) -> tuple[CodeScanFinding, ...]:
        findings: list[CodeScanFinding] = []
        for number, line in enumerate(source.splitlines(), start=1):
            for rule, pattern, detail in self._rules:
                if pattern.search(line):
                    findings.append(CodeScanFinding(rule, number, detail))
        return tuple(findings)

    def require_safe(self, source: str) -> None:
        findings = self.scan(source)
        if findings:
            raise ValueError("candidate code failed security scan: " + ", ".join(f.rule for f in findings))


class FixedRDAGENTAdapter:
    """仅记录已生成候选的元数据，不调用外部模型。"""

    def __init__(self, scanner: CandidateCodeScanner | None = None) -> None:
        self._scanner = scanner or CandidateCodeScanner()

    def register_code_candidate(
        self,
        artifact_id: str,
        source: str,
        artifact_uri: str,
        artifact_hash: str,
        manifest: ReproducibilityManifest,
        created_at: datetime,
    ) -> CandidateArtifact:
        self._scanner.require_safe(source)
        return CandidateArtifact(artifact_id, CandidateArtifactKind.CODE, artifact_uri, artifact_hash, manifest, created_at)


def _hash(value: Mapping[str, object]) -> str:
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
