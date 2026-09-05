# 事件驱动架构

## 1. 定位

NATS JetStream用于在限界上下文之间传播已经发生的领域事实；Temporal负责跨步骤业务流程；REST/OpenAPI负责需要立即确认结果的查询和命令。三者组合使用，不互相替代。

## 2. 选择NATS JetStream的理由

- Node.js和Python客户端成熟，适合当前双语言技术栈。
- 支持持久化、消费者确认、重放和按Subject路由。
- 运维体量适合初期团队，同时保留未来迁移Kafka的契约边界。

不得依赖“恰好一次”假设。系统统一采用至少一次投递、幂等消费和可重放设计。

## 3. 事件命名与Envelope

Subject格式：

```text
stock.<bounded-context>.<aggregate-or-topic>.<past-tense-event>.v<major>
```

示例：`stock.quant.daily-analysis.published.v1`。

统一Envelope至少包含：

```ts
import type { DomainEventEnvelope } from '@stock/contracts';
type DomainEvent<T extends Record<string, unknown>> = Omit<DomainEventEnvelope, 'payload'> & { payload: T };
```

Payload包含业务必要字段和不可变Artifact引用，不包含新闻全文、Tick流、因子矩阵或模型二进制。

## 4. 初始事件目录

| Subject | Owner | 典型消费者 |
|---|---|---|
| `stock.market-data.data-version.published.v1` | market-data | quant、research-automation、workflow |
| `stock.quant.daily-analysis.published.v1` | quant-research | stock-analysis-agent、workflow |
| `stock.strategy.daily-strategy.published.v1` | quant-research | stock-analysis/main/risk-review agents、workflow |
| `stock.strategy.strategy-version.activated.v1` | quant-research | workflow、platform-api、audit |
| `stock.research.experiment.completed.v1` | research-automation | research UI、quant-research |
| `stock.news.financial-event.published.v1` | news-intelligence | financial-news/main/risk-review agents |
| `stock.monitor.market-anomaly.detected.v1` | market-monitor | market-monitor-agent、workflow |
| `stock.regime.market-regime.changed.v1` | market-regime | market-state-agent、workflow、risk |
| `stock.portfolio.snapshot.changed.v1` | portfolio-risk | main/risk-review agents、platform-api |
| `stock.agent.assessment.completed.v1` | agent-service部署 | workflow、decision-governance |
| `stock.decision.proposal.created.v1` | decision-governance | workflow、platform-api |
| `stock.decision.risk-review.completed.v1` | decision-governance | workflow、platform-api |
| `stock.risk.evaluation.completed.v1` | portfolio-risk | governance、workflow |
| `stock.decision.approval.completed.v1` | decision-governance | workflow、trade-execution |
| `stock.decision.rebalance-budget.changed.v1` | decision-governance | workflow、trade-execution、audit |
| `stock.execution.rebalance-batch.accepted.v1` | trade-execution | governance、workflow、platform-api、audit |
| `stock.execution.rebalance-batch.completed.v1` | trade-execution | governance、portfolio-risk、platform-api、audit |
| `stock.execution.fill.recorded.v1` | trade-execution | portfolio-risk、governance、audit |

AsyncAPI文件位于`packages/contracts/asyncapi/`，Payload Schema引用`packages/contracts/schemas/`。新增或破坏性变更必须先更新契约和兼容性测试。

## 5. Outbox、Inbox与顺序

生产方在同一数据库事务内写Aggregate和`outbox_events`，Relay异步发布NATS并记录发布时间。消费者在同一数据库事务中写`eventId + consumerName`的Inbox记录及业务修改；事务提交后才ACK。重复已提交事件直接确认，未提交记录不能用作已处理证明。

- 不假设网络投递顺序或全局顺序；消费者按版本拒绝旧投影覆盖新投影。
- v1的`aggregateId/aggregateVersion`为兼容性可选字段，必须成对出现。只有生产者保证连续版本且消费者订阅完整聚合事件时，才以缺口触发重建；否则通过权威快照对账，禁止无限等待不存在的版本。
- `schemaVersion`是契约版本，不能用作聚合版本；`availableAt`是业务可见时间，不能用重投时间覆盖。
- Handler的外部副作用必须有业务幂等键。
- Dead Letter Stream保留原事件、失败分类、重试次数和追踪信息。

## 6. Stream和Consumer建议

初期按保留策略划分，而不是为每个Subject创建Stream：

- `STOCK_FACTS`：行情版本、量化、新闻、Regime、组合和成交；长期保留。
- `STOCK_SIGNALS`：异常和Agent评估；按审计周期保留。
- `STOCK_OPERATIONS`：非敏感运维事件；短期保留。

每个逻辑Agent使用独立Durable Consumer，例如`financial-news-agent-v1`。升级时新旧Consumer可并存回放；完成验证后再停旧版本。

## 7. 事件、命令和Workflow边界

适合事件：快照已发布、新闻已识别、异常已检测、成交已确认。

不适合事件替代的操作：预交易硬风控、批准/拒绝、原子预留调仓预算、创建RebalanceBatch和OrderIntent[]、修改RiskPolicy。它们使用鉴权同步命令并立即返回确定结果，由Temporal记录长流程状态。预算或批次事实事件用于审计、投影和恢复，不能代替同步命令结果；响应不确定时必须按幂等键查询权威服务。

NATS事件可以启动或Signal Temporal Workflow；Workflow History只保存小型ID和摘要，再通过Activity读取Artifact，禁止写入Tick或大型模型上下文。

## 8. 安全与可观测性

- 按服务账户限制Publish/Subscribe Subject权限。
- 敏感字段不进入Event Payload；URI使用短时授权或由服务端解析。
- Envelope传递`traceId`，OpenTelemetry串联HTTP、Temporal、NATS和模型调用。
- 监控发布延迟、Consumer Lag、Redelivery、DLQ、Outbox积压和Inbox重复率。

## 9. 验收测试

- 同一事件重复投递10次，业务状态只改变一次。
- 服务在数据库提交后、NATS发布前崩溃，重启后Outbox仍能完成发布。
- Consumer在处理后、Ack前崩溃，重投不产生重复建议、成交或通知。
- 从指定Sequence回放可以重建只读投影，不触发真实外部副作用。
- 新旧Minor Schema能并行消费；破坏性变更使用新Subject Major版本。
