# 阶段06：盘中市场监控总设计

## 目标

在独立`services/market-monitor-service`中实现交易时段Worker，对持仓、候选和关注股票生成1/5分钟Bar、确定性异常和版本化MarketAnomalyEvent。

## 开发边界

Worker不调用LLM、不下单、不修改持仓和风险策略。Agent解释在阶段08接入。

## 实施要求

- 聚合和规则以事件时间为准。
- 生产与回放使用相同检测代码。
- 硬事件优先于River模型分数。
- 行情断开必须失败可见，不能输出伪正常结论。
- Worker和可选查询API使用同一服务镜像的不同命令、独立Database/User和NATS Outbox。

## 顺序文档

1. [行情Gateway、标准事件和Bar](./01-market-gateway-bars.md)
2. [异常规则、严重度和River影子模型](./02-anomaly-rules-river.md)
3. [Outbox、历史回放和运行保障](./03-outbox-replay-operations.md)

## 阶段验收

- 交易时段、午休、停牌和数据中断处理正确。
- 相同事件不重复发布。
- 无异常不产生后续模型任务。
- Worker重启后恢复watchlist、规则版本和冷却状态。
