"""模型与回测Artifact的只读完整性读取器。"""

from __future__ import annotations

from quant_research.adapters.qlib import ArtifactIntegrityError, VerifiedArtifactReader
from quant_research.baseline_model import LinearBaselineModel
from quant_research.domain import ArtifactRef
from quant_research.portfolio_backtest import PortfolioBacktestReport


class ResearchArtifactReader:
    """所有研究结果先经引用Hash校验，再解析为领域对象。"""

    def __init__(self, reader: VerifiedArtifactReader) -> None:
        self._reader = reader

    def load_model(self, artifact: ArtifactRef) -> LinearBaselineModel:
        content = self._reader.get_verified(artifact)
        try:
            return LinearBaselineModel.model_validate_json(content)
        except ValueError as error:
            raise ArtifactIntegrityError("model Artifact is not valid baseline-model JSON") from error

    def load_backtest(self, artifact: ArtifactRef) -> PortfolioBacktestReport:
        content = self._reader.get_verified(artifact)
        try:
            return PortfolioBacktestReport.model_validate_json(content)
        except ValueError as error:
            raise ArtifactIntegrityError("backtest Artifact is not valid portfolio-report JSON") from error
