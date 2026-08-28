# 06-01 行情Gateway、标准事件和Bar

## 目标

建立vn.py/供应商/轮询Adapter，将行情统一为MarketDataEvent并按事件时间聚合1分钟和5分钟Bar。

## 实施步骤

### 1. Gateway端口

```python
class MarketGateway(Protocol):
    async def connect(self) -> None: ...
    async def subscribe(self, symbols: list[SecurityId]) -> None: ...
    async def events(self) -> AsyncIterator[MarketDataEvent]: ...
```

vn.py对象只能存在于`gateways/vnpy_adapter.py`。

### 2. 标准事件

```python
class MarketDataEvent(BaseModel):
    symbol: str
    exchange: str
    event_time: datetime
    received_at: datetime
    event_kind: Literal["TICK", "QUOTE", "TRADE", "STATUS"]
    price: Decimal | None
    volume: Decimal | None
    source_sequence: str | None
    data_version: str
```

记录eventTime与receivedAt，用于检测延迟和乱序。

### 3. Bar聚合

窗口使用交易所本地时区和正式交易日历。午休不能生成横跨90分钟的普通5分钟Bar。

```python
bar = MarketBar(
    window_start=window.start,
    window_end=window.end,
    open=events[0].price,
    high=max(e.price for e in events),
    low=min(e.price for e in events),
    close=events[-1].price,
    volume=sum(e.volume or 0 for e in events),
)
```

### 4. Watchlist

P0持仓/待执行、P1候选、P2人工关注。每次加载保存watchlistVersion和来源快照ID。

## 测试案例

1. 乱序Tick在允许水位内正确聚合。
2. 超过水位的迟到事件记录但不篡改已发布Bar。
3. 午休、停牌和涨跌停状态正确。
4. 重复sourceSequence不重复计量。
5. 轮询和推送Adapter产生相同内部契约。

## 完成条件

- Gateway可替换。
- Bar可保存和回放。
- quoteAge和dataGap可计算。

