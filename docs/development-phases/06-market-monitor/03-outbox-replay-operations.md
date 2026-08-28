# 06-03 Outbox、历史回放和运行保障

## 目标

可靠发布MarketAnomalyEvent，并使用生产相同代码进行历史回放和恢复测试。

## 实施步骤

### 1. 事件和幂等键

```python
event_key = f"{symbol}:{anomaly_type}:{window_end.isoformat()}:{detector_version}"
```

在同一数据库事务中插入异常和Outbox。发布成功后标记Outbox，不删除业务事件。

### 2. 冷却

冷却键包含symbol、type和规则版本。CRITICAL硬事件可绕过普通冷却，但仍按eventId幂等。

### 3. 回放Runner

```python
for event in replay_source.iter_by_event_time():
    bars = aggregator.on_event(event)
    for bar in bars:
        detector.evaluate(bar, mode="REPLAY")
```

回放只替换输入和时钟，使用相同Aggregator、RuleEngine、SeverityCombiner和Schema。

### 4. Readiness

检查行情连接、Calendar、watchlist、规则版本和Outbox积压。行情断开时Liveness可正常，但Readiness失败并告警。

## 测试案例

1. Outbox发布进程崩溃后恢复且不丢事件。
2. 消费者收到重复事件可按eventId去重。
3. 回放与相同生产输入产生相同规则命中。
4. Redis丢失后关键事件仍能从持久数据恢复。
5. Gateway断开后不产生伪正常Bar。

## 完成条件

- HIGH/CRITICAL事件能可靠发布引用。
- 回放报告包含触发数、重复率和假阳性样本。
- 有行情断开、积压和状态恢复Runbook。
