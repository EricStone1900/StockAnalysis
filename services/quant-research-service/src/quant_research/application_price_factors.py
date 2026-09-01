"""真实Qlib价格读取、空洞掩码与Fixture因子计算的最小纵向闭环。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

from quant_research.adapters.factor_engine import (
    DailyPriceBar,
    FixturePriceFactorAdapter,
    PriceFactorMatrix,
)
from quant_research.adapters.qlib import QlibCloseGapIndexAdapter
from quant_research.domain import (
    CloseGapHandlingPolicy,
    CloseGapResolution,
    MarketDataVersionRef,
    ResearchRunManifest,
    build_run_manifest,
    resolve_close_gaps,
)


class PriceBarReader(Protocol):
    def load_bars(
        self, instruments: Sequence[str], start_date: date, end_date: date
    ) -> tuple[DailyPriceBar, ...]: ...


class QlibMaskedPriceFactorService:
    def __init__(
        self,
        bar_reader: PriceBarReader,
        close_gap_adapter: QlibCloseGapIndexAdapter,
        calculator: FixturePriceFactorAdapter | None = None,
    ) -> None:
        self._bar_reader = bar_reader
        self._close_gap_adapter = close_gap_adapter
        self._calculator = calculator or FixturePriceFactorAdapter()

    def calculate(
        self,
        run_id: str,
        data_version: MarketDataVersionRef,
        policy: CloseGapHandlingPolicy,
        instruments: Sequence[str],
        start_date: date,
        end_date: date,
        generated_at: datetime,
        resolution: CloseGapResolution | None = None,
    ) -> tuple[PriceFactorMatrix, CloseGapResolution, ResearchRunManifest]:
        if resolution is None:
            gaps = self._close_gap_adapter.load_gaps(data_version)
            resolution = resolve_close_gaps(data_version, policy, gaps, generated_at)
        if resolution.data_version != data_version or resolution.policy != policy:
            raise ValueError("precomputed close-gap resolution does not match the requested inputs")
        bars = self._bar_reader.load_bars(instruments, start_date, end_date)
        matrix = self._calculator.calculate(data_version.version_id, bars, resolution.entries)
        return matrix, resolution, build_run_manifest(run_id, resolution)
