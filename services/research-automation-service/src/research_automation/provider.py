"""模型 Provider 边界、输出 Schema 和有限修复。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from .artifacts import ModelCallAudit
from .model_audit import ModelCallAuditStore


class CandidateProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_type: str = Field(pattern=r"^(factor|model|strategy)$")
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2000)
    support_evidence: list[str] = Field(min_length=1, max_length=20)
    counterexamples: list[str] = Field(min_length=1, max_length=20)
    failure_reasons: list[str] = Field(min_length=1, max_length=20)
    uncertainty: str = Field(min_length=1, max_length=1000)


@dataclass(frozen=True)
class ModelRequest:
    call_id: str
    provider: str
    model_id: str
    prompt_version: str
    input_hash: str
    prompt: str


@dataclass(frozen=True)
class ModelResponse:
    raw_output: str
    token_count: int
    cost: float


class ModelProvider(Protocol):
    def complete(self, request: ModelRequest) -> ModelResponse: ...


class ProviderAdapter:
    def __init__(self, provider: ModelProvider, audit_store: ModelCallAuditStore, max_output_bytes: int = 65536) -> None:
        self._provider = provider
        self._audit_store = audit_store
        self._max_output_bytes = max_output_bytes

    def generate_candidate(self, request: ModelRequest) -> CandidateProposal:
        response = self._provider.complete(request)
        if len(response.raw_output.encode()) > self._max_output_bytes:
            raise ValueError("model output exceeds configured size limit")
        if response.token_count < 0 or response.cost < 0:
            raise ValueError("model usage values cannot be negative")
        self._audit_store.record(
            request.call_id,
            ModelCallAudit(request.provider, request.model_id, request.prompt_version, request.input_hash, response.token_count, response.cost),
        )
        try:
            value = json.loads(response.raw_output)
            return CandidateProposal.model_validate(value)
        except (json.JSONDecodeError, ValueError, TypeError) as error:
            raise ValueError("model output failed candidate schema") from error


class FixedModelProvider:
    """本地确定性 Provider，仅用于契约测试。"""

    def __init__(self, output: str) -> None:
        self._output = output

    def complete(self, request: ModelRequest) -> ModelResponse:
        if not request.prompt.strip():
            raise ValueError("prompt is required")
        return ModelResponse(self._output, token_count=1, cost=0.0)
