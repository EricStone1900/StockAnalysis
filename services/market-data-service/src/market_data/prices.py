from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PricePoint(BaseModel):
    model_config = ConfigDict(frozen=True)
    security_id: str
    close: Decimal = Field(gt=0, decimal_places=8)
    as_of: date
    data_version: str = Field(min_length=1)


class VersionedPriceStore:
    """价格读取端口的最小实现；未写入的版本/日期必须返回 None。"""

    def __init__(self) -> None:
        self._prices: dict[tuple[str, str, date], PricePoint] = {}

    def put(self, price: PricePoint) -> None:
        self._prices[(price.security_id, price.data_version, price.as_of)] = price

    def get(self, security_id: str, data_version: str, as_of: date) -> PricePoint | None:
        return self._prices.get((security_id, data_version, as_of))
