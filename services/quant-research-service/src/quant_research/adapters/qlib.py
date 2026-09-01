"""Qlib 数据 Adapter；只读取阶段02发布且通过Hash校验的对象。"""

from collections.abc import Mapping
from datetime import date
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from quant_research.domain import ArtifactRef, CloseGap, MarketDataVersionRef


class VerifiedArtifactReader(Protocol):
    def get_verified(self, artifact: ArtifactRef) -> bytes: ...


class ArtifactIntegrityError(ValueError):
    """对象内容、引用Hash或父归档关系不匹配。"""


class InMemoryVerifiedArtifactReader:
    """仅供Fixture与单元测试使用，生产实现将在后续组件集成步骤注入。"""

    def __init__(self, objects: Mapping[str, bytes]) -> None:
        self._objects = dict(objects)

    def get_verified(self, artifact: ArtifactRef) -> bytes:
        try:
            content = self._objects[artifact.uri]
        except KeyError as error:
            raise ArtifactIntegrityError(f"artifact not found: {artifact.uri}") from error
        if sha256(content).hexdigest() != artifact.sha256:
            raise ArtifactIntegrityError(f"artifact hash mismatch: {artifact.uri}")
        return content


class _CloseGapWireEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    trading_day: date


class _CloseGapIndexWire(BaseModel):
    model_config = ConfigDict(frozen=True)

    archive_hash: str
    gaps: tuple[_CloseGapWireEntry, ...]


class QlibCloseGapIndexAdapter:
    """将阶段02的close-gap-index转换为领域空洞；不打开或改写价格序列。"""

    def __init__(self, reader: VerifiedArtifactReader) -> None:
        self._reader = reader

    def load_gaps(self, data_version: MarketDataVersionRef) -> tuple[CloseGap, ...]:
        self._reader.get_verified(data_version.artifact)
        index_content = self._reader.get_verified(data_version.close_gap_index)
        try:
            index = _CloseGapIndexWire.model_validate_json(index_content)
        except ValueError as error:
            raise ArtifactIntegrityError("close-gap index is not valid JSON") from error
        if index.archive_hash != data_version.artifact.sha256:
            raise ArtifactIntegrityError("close-gap index does not belong to DataVersion artifact")
        return tuple(CloseGap(security_id=gap.symbol, trading_day=gap.trading_day) for gap in index.gaps)
