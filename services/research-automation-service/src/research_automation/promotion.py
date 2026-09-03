"""PromotionRequest 与 quant 生产隔离。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum

from .reproducibility import ResearchResultManifest


class PromotionStatus(StrEnum):
    REQUESTED = "REQUESTED"
    REPRODUCED = "REPRODUCED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class PromotionGateResult:
    pit_passed: bool
    out_of_sample: bool
    cost_passed: bool
    correlation_passed: bool
    sensitivity_passed: bool
    security_passed: bool

    @property
    def passed(self) -> bool:
        return all((self.pit_passed, self.out_of_sample, self.cost_passed, self.correlation_passed, self.sensitivity_passed, self.security_passed))


@dataclass(frozen=True)
class PromotionRequest:
    request_id: str
    result: ResearchResultManifest
    risks: tuple[str, ...]
    status: PromotionStatus
    created_at: datetime
    reproduction: PromotionGateResult | None = None
    rejection_reason: str | None = None


class PromotionRequestService:
    """候选提交服务；没有激活或修改生产Registry的方法。"""

    def __init__(self) -> None:
        self._requests: dict[str, PromotionRequest] = {}
        self._idempotency: dict[str, tuple[str, str]] = {}

    def submit(self, request_id: str, idempotency_key: str, result: ResearchResultManifest, risks: tuple[str, ...], now: datetime) -> PromotionRequest:
        _require_utc(now)
        if not request_id.strip() or not idempotency_key.strip():
            raise ValueError("request_id and idempotency_key are required")
        fingerprint = result.content_hash
        existing = self._idempotency.get(idempotency_key)
        if existing is not None:
            if existing != (request_id, fingerprint):
                raise ValueError("idempotency key is already bound to different content")
            return self._requests[request_id]
        if request_id in self._requests:
            raise ValueError("request_id already exists")
        request = PromotionRequest(request_id, result, tuple(sorted(set(risks))), PromotionStatus.REQUESTED, now)
        self._requests[request_id] = request
        self._idempotency[idempotency_key] = (request_id, fingerprint)
        return request

    def reproduce(self, request_id: str, verifier: Callable[[ResearchResultManifest], PromotionGateResult]) -> PromotionRequest:
        request = self._require(request_id)
        if request.status is not PromotionStatus.REQUESTED:
            raise ValueError("only requested promotion can be reproduced")
        gates = verifier(request.result)
        if not gates.passed:
            updated = replace(request, status=PromotionStatus.REJECTED, reproduction=gates, rejection_reason="promotion gates failed")
        else:
            updated = replace(request, status=PromotionStatus.REPRODUCED, reproduction=gates)
        self._requests[request_id] = updated
        return updated

    def approve(self, request_id: str) -> None:
        raise PermissionError("research service cannot approve or activate production versions")

    def get(self, request_id: str) -> PromotionRequest | None:
        return self._requests.get(request_id)

    def _require(self, request_id: str) -> PromotionRequest:
        request = self.get(request_id)
        if request is None:
            raise KeyError(request_id)
        return request


def _require_utc(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamps must use UTC")
