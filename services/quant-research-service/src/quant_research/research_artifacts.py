"""模型与回测研究结果的不可变Artifact发布。"""

from __future__ import annotations

import json
import re
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from quant_research.baseline_model import LinearBaselineModel
from quant_research.domain import ArtifactRef
from quant_research.portfolio_backtest import PortfolioBacktestReport

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._-]+$")


class ResearchArtifactWriter(Protocol):
    def put_immutable(self, key: str, content: bytes) -> str: ...


class PublishedResearchArtifact(BaseModel):
    model_config = ConfigDict(frozen=True)

    artifact: ArtifactRef
    content_hash: str


class ResearchArtifactPublisher:
    """通过内容寻址键写入模型和回测结果；禁止覆盖不同内容。"""

    def __init__(self, writer: ResearchArtifactWriter, artifact_uri_prefix: str) -> None:
        self._writer = writer
        self._prefix = artifact_uri_prefix.rstrip("/")

    def publish_model(self, model: LinearBaselineModel) -> PublishedResearchArtifact:
        content = _canonical_json(model.model_dump(mode="json"))
        digest = sha256(content).hexdigest()
        key = f"quant-research/models/{model.model_id}/{model.model_version}/{digest}.json"
        _validate_segment(model.model_id)
        _validate_segment(model.model_version)
        stored = self._writer.put_immutable(key, content)
        return PublishedResearchArtifact(
            artifact=ArtifactRef(uri=f"{self._prefix}/{key}", sha256=stored),
            content_hash=model.canonical_content_hash,
        )

    def publish_backtest(
        self, run_id: str, report: PortfolioBacktestReport
    ) -> PublishedResearchArtifact:
        content = _canonical_json(report.model_dump(mode="json"))
        digest = sha256(content).hexdigest()
        _validate_segment(run_id)
        key = f"quant-research/backtests/{run_id}/{report.after_cost.canonical_content_hash}/{digest}.json"
        stored = self._writer.put_immutable(key, content)
        return PublishedResearchArtifact(
            artifact=ArtifactRef(uri=f"{self._prefix}/{key}", sha256=stored),
            content_hash=report.after_cost.canonical_content_hash,
        )


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _validate_segment(value: str) -> None:
    if not _SAFE_SEGMENT.fullmatch(value):
        raise ValueError("research artifact key segment contains unsupported characters")
