# Monitor 06-02 异常规则、River影子与强化

## 实施步骤

1. 实现价格跳变、成交量/额放大、波动、缺口、流动性和数据中断规则。
2. RuleVersion保存窗口、阈值、适用证券和生效时间；输出severity、reasonCodes和evidenceIds。
3. 建立事件去重、冷却、升级和恢复；无异常不发布Agent调用事件。
4. 使用历史回放标定阈值；River初期只输出shadowScore，不影响综合级别。
5. 累积标签并批准ModelVersion后，River才可参与确定性合并。
6. 实现Gateway断线、重连、补发、Lag和质量告警。

## 测试

- 无异常时不产生MarketAnomalyEvent。
- 同一异常窗口重复输入只触发一次。
- CRITICAL可跳过普通冷却但仍保持幂等。
- River漂移或不可用不阻断规则引擎。
- 行情中断发布数据质量告警，不发布“市场正常”。

