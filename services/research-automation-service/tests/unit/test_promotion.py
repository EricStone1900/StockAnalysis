from datetime import UTC, datetime

import pytest

from src.research_automation.artifacts import (
    CandidateArtifact,
    CandidateArtifactKind,
    ReproducibilityManifest,
)
from src.research_automation.promotion import (
    PromotionGateResult,
    PromotionRequestService,
    PromotionStatus,
)
from src.research_automation.provider import CandidateProposal
from src.research_automation.reproducibility import ResearchResultManifest


def _result() -> ResearchResultManifest:
    manifest = ReproducibilityManifest("dv-1", "a" * 64, "b" * 64, "sha256:image", "c" * 64, 7, "eval-v1")
    candidate = CandidateArtifact("candidate-1", CandidateArtifactKind.CODE, "minio://artifacts/candidate.py", "d" * 64, manifest, datetime(2026, 9, 3, tzinfo=UTC))
    proposal = CandidateProposal(candidate_type="factor", title="测试", summary="摘要", support_evidence=["e1"], counterexamples=["c1"], failure_reasons=["f1"], uncertainty="不确定")
    return ResearchResultManifest("experiment-1", "run-1", candidate, proposal, {"ic": 0.12}, manifest)


def _gates(passed: bool) -> PromotionGateResult:
    return PromotionGateResult(passed, passed, passed, passed, passed, passed)


def test_promotion_request_is_idempotent_and_reproduced_only() -> None:
    service = PromotionRequestService()
    now = datetime(2026, 9, 3, tzinfo=UTC)
    request = service.submit("promotion-1", "promotion-key-1", _result(), ("research-only",), now)
    assert service.submit("promotion-1", "promotion-key-1", _result(), (), now) == request
    reproduced = service.reproduce("promotion-1", lambda _result: _gates(True))
    assert reproduced.status is PromotionStatus.REPRODUCED
    with pytest.raises(PermissionError, match="cannot approve"):
        service.approve("promotion-1")


def test_failed_reproduction_rejects_and_hash_rebound_is_refused() -> None:
    service = PromotionRequestService()
    now = datetime(2026, 9, 3, tzinfo=UTC)
    service.submit("promotion-2", "promotion-key-2", _result(), (), now)
    rejected = service.reproduce("promotion-2", lambda _result: _gates(False))
    assert rejected.status is PromotionStatus.REJECTED
    with pytest.raises(ValueError, match="different content"):
        service.submit("promotion-3", "promotion-key-2", _result(), (), now)
