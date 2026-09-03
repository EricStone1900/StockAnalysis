"""research 与 quant 的最小 Promotion 契约；不共享数据库模型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .promotion import PromotionGateResult, PromotionRequest


@dataclass(frozen=True)
class PromotionSubmission:
    request_id: str
    candidate_content_hash: str
    data_version_id: str
    artifact_uri: str
    artifact_hash: str
    manifest_hash: str


@dataclass(frozen=True)
class QuantReproductionResponse:
    request_id: str
    reproduced: bool
    gates: PromotionGateResult
    reproduction_hash: str


class QuantPromotionPort(Protocol):
    def reproduce(self, submission: PromotionSubmission) -> QuantReproductionResponse: ...


class ResearchPromotionClient:
    """将候选提交给 quant 复验；没有 activate 方法。"""

    def __init__(self, port: QuantPromotionPort) -> None:
        self._port = port

    def submit_for_reproduction(self, request: PromotionRequest) -> QuantReproductionResponse:
        candidate = request.result.candidate
        return self._port.reproduce(PromotionSubmission(
            request.request_id,
            request.result.content_hash,
            candidate.manifest.data_version_id,
            candidate.artifact_uri,
            candidate.artifact_hash,
            candidate.manifest.content_hash,
        ))

    def activate(self, _request_id: str) -> None:
        raise PermissionError("research identity cannot activate quant production versions")
