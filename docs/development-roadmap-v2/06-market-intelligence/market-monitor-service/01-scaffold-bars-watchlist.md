# Monitor 06-01 Gateway、Bar和Watchlist

## 实施步骤

1. 建立MarketGateway Port，先使用历史分钟Fixture，再选择vn.py或轮询Adapter。
2. 建立WatchlistVersion，来源包含候选股、持仓股和人工关注股。
3. 按交易所Calendar聚合5分钟OHLCV、成交额、VWAP和数据质量。
4. 处理集合竞价、午休、停牌、涨跌停、迟到和重复Tick/Bar。
5. 最小Use Case为“给定Watchlist和分钟Fixture发布一根已封闭5分钟Bar”。

```python
class ClosedBar(BaseModel):
    security_id: str
    window_start: AwareDatetime
    window_end: AwareDatetime
    ohlcv: Ohlcv
    quality: Literal["PASS", "WARN", "FAIL"]
    source_event_ids: list[str]
```

## 测试

- 午休不生成跨时段Bar。
- 重复、乱序数据结果稳定。
- 停牌不产生伪零波动正常信号。

