"""阶段03应用服务；协调已验证输入与领域规则。"""

from datetime import datetime

from quant_research.adapters.qlib import QlibCloseGapIndexAdapter
from quant_research.domain import (
    CloseGapHandlingPolicy,
    CloseGapResolution,
    MarketDataVersionRef,
    ResearchRunManifest,
    build_run_manifest,
    resolve_close_gaps,
)


class CloseGapMaskService:
    def __init__(self, adapter: QlibCloseGapIndexAdapter) -> None:
        self._adapter = adapter

    def create_mask(
        self,
        run_id: str,
        data_version: MarketDataVersionRef,
        policy: CloseGapHandlingPolicy,
        generated_at: datetime,
    ) -> tuple[CloseGapResolution, ResearchRunManifest]:
        gaps = self._adapter.load_gaps(data_version)
        resolution = resolve_close_gaps(data_version, policy, gaps, generated_at)
        return resolution, build_run_manifest(run_id, resolution)
