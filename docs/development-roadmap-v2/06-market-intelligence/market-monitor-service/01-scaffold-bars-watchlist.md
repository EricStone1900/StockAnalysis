# Monitor 06-01 Gateway、Bar和Watchlist

## 实施步骤

1. 建立MarketGateway Port，先使用历史分钟Fixture，再选择vn.py或轮询Adapter；轮询Adapter必须支持一次获取批量快照和本地按SecurityId过滤，禁止逐股循环请求。
2. 建立WatchlistVersion和版本化MonitorPolicy，来源包含候选股、持仓股和人工关注股；`FREE_TIERED_10_20_30`默认拒绝超过50支的活跃集合，P0/P1/P2分别固定10/20/30分钟评估，80支需显式稳定性准入，100支仅在压力测试配置可用。
3. 按交易所Calendar每10分钟调度一次批量快照，并聚合5分钟OHLCV、成交额、VWAP、`quoteAgeSeconds`、覆盖率和数据质量；到期的P0/P1/P2复用相同快照，禁止增加逐层上游请求。
4. 处理集合竞价、午休、停牌、涨跌停、迟到和重复Tick/Bar；计划窗口后120秒未完成、行情超过180秒、覆盖不足或字段无效时失败关闭。
5. 最小Use Case为“给定含P0/P1/P2的50支Watchlist和分钟Fixture，在一个10分钟计划窗口内发布两根已封闭5分钟Bar，并仅对到期层级进行评估或明确质量失败”。

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
- 一次批量响应只保留Watchlist证券；100支测试不得产生100次上游请求。
- P0/P1/P2分别在10/20/30分钟到期时评估，P1/P2不得为到期额外请求行情。
- 陈旧、缺失或覆盖不足只能产生质量告警，不得生成正常异常结论。
