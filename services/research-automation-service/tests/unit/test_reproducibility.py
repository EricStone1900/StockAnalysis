from datetime import UTC, datetime

import pytest

from src.research_automation.artifacts import (
    CandidateArtifact,
    CandidateArtifactKind,
    ReproducibilityManifest,
)
from src.research_automation.provider import CandidateProposal
from src.research_automation.reproducibility import (
    IndependentReproducer,
    ResearchResultManifest,
    manifest_payload,
)


def _result() -> ResearchResultManifest:
    manifest = ReproducibilityManifest("dv-1", "a" * 64, "b" * 64, "sha256:image", "c" * 64, 7, "eval-v1")
    candidate = CandidateArtifact("candidate-1", CandidateArtifactKind.CODE, "minio://artifacts/candidate.py", "d" * 64, manifest, datetime(2026, 9, 3, tzinfo=UTC))
    proposal = CandidateProposal(candidate_type="factor", title="测试", summary="摘要", support_evidence=["e1"], counterexamples=["c1"], failure_reasons=["f1"], uncertainty="不确定")
    return ResearchResultManifest("experiment-1", "run-1", candidate, proposal, {"ic": 0.12}, manifest)


def test_manifest_binds_candidate_run_and_reproducibility_inputs() -> None:
    result = _result()
    payload = manifest_payload(result)
    assert payload["experimentId"] == "experiment-1"
    assert payload["candidateArtifactHash"] == "d" * 64
    assert payload["contentHash"] == result.content_hash


def test_independent_reproduction_requires_exact_metrics() -> None:
    result = _result()
    IndependentReproducer().reproduce(result, lambda _manifest: {"ic": 0.12})
    with pytest.raises(ValueError, match="metrics mismatch"):
        IndependentReproducer().reproduce(result, lambda _manifest: {"ic": 0.11})
