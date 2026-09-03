"""研究结果 Manifest 与独立复算门禁。"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256

from .artifacts import CandidateArtifact, ReproducibilityManifest
from .provider import CandidateProposal


@dataclass(frozen=True)
class ResearchResultManifest:
    experiment_id: str
    run_id: str
    candidate: CandidateArtifact
    proposal: CandidateProposal
    metrics: Mapping[str, float]
    manifest: ReproducibilityManifest

    @property
    def content_hash(self) -> str:
        value = {
            "experimentId": self.experiment_id,
            "runId": self.run_id,
            "candidateHash": self.candidate.content_hash,
            "proposal": self.proposal.model_dump(mode="json"),
            "metrics": dict(sorted(self.metrics.items())),
            "reproducibilityHash": self.manifest.content_hash,
        }
        return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class IndependentReproducer:
    """在独立计算器中复算候选指标并比较确定性结果。"""

    def reproduce(
        self,
        result: ResearchResultManifest,
        calculator: Callable[[ReproducibilityManifest], Mapping[str, float]],
    ) -> None:
        calculated = dict(calculator(result.manifest))
        expected = dict(result.metrics)
        if calculated != expected:
            raise ValueError("independent reproduction metrics mismatch")


def manifest_payload(result: ResearchResultManifest) -> dict[str, object]:
    return {
        "experimentId": result.experiment_id,
        "runId": result.run_id,
        "candidateArtifactId": result.candidate.artifact_id,
        "candidateArtifactUri": result.candidate.artifact_uri,
        "candidateArtifactHash": result.candidate.artifact_hash,
        "candidateContentHash": result.candidate.content_hash,
        "proposal": result.proposal.model_dump(mode="json"),
        "metrics": dict(sorted(result.metrics.items())),
        "reproducibilityManifestHash": result.manifest.content_hash,
        "contentHash": result.content_hash,
    }
