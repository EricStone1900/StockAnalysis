# 00-06 依赖与通信基线

## 编译依赖矩阵

所有服务可依赖本服务 Domain/Application、`packages/contracts` 的生成类型和通用可观测性/配置包；不得依赖其他服务的 Domain、ORM Entity、迁移或 Adapter。阶段 01 用架构测试执行该规则。

| 调用方 | 允许的跨边界编译依赖 | 禁止依赖 |
|---|---|---|
| 任意领域服务 | OpenAPI/AsyncAPI 生成 Client、共享契约 | 其他服务源码与数据库模型 |
| platform-api-service | 各服务 OpenAPI Client | 领域服务 Repository/Entity |
| workflow-orchestration-service | 命令 DTO、Activity 接口 | 领域 Aggregate/数据库 |
| agent-service | Tool DTO、输出 Schema | 任何领域数据库/ORM |

## 同步 REST 矩阵

| 场景 | 调用方 → Owner | 结果要求 |
|---|---|---|
| 查询快照和只读事实 | 平台、Agent、Workflow → 领域服务 | 明确 Freshness 与 Provenance |
| 硬风控评估 | Governance/Workflow → portfolio-risk | 即时允许或拒绝，不能只发事件 |
| 批准、拒绝与创建 OrderIntent | Workflow/平台 → Governance/Execution | 鉴权、幂等、版本冲突可见 |
| 人工 Fill 回填 | 执行入口 → trade-execution | 返回唯一处理结果与关联 ID |

## 异步事件矩阵

NATS JetStream 只发布已发生的事实，Subject 使用 `stock.<context>.<topic>.<past-tense>.v<major>`。消费者不得以事件替代审批、硬风控或下单命令。

| 生产方 | 领域事实 | 典型消费者 |
|---|---|---|
| market-data | DataVersionPublished | quant、research、workflow |
| quant-research | DailyAnalysis/StrategyPublished | Agent、workflow |
| news、monitor、regime | News/Anomaly/Regime 事件 | Agent、workflow、risk |
| portfolio-risk | PortfolioSnapshotChanged、RiskEvaluationCompleted | Agent、governance、workflow |
| decision-governance | Proposal/RiskReview/ApprovalCompleted | workflow、platform、execution |
| trade-execution | FillRecorded | portfolio-risk、governance、audit |

## Temporal 与人工矩阵

Temporal 编排每日研究、事件触发重评估、审批等待、超时和补偿；History 只保存 ID 与摘要。人工仅通过已鉴权命令审批、拒绝、修改建议、录入 Fill 和签署验收。Workflow 不拥有领域事实，也不能通过重试绕过服务拒绝。

## 无环检查

每日链路为 `market-data → quant-research → agent → decision-governance → trade-execution → portfolio-risk`；事件反馈只更新 Owner 的投影或启动新流程，不能形成同步回调环。发现双向需求时，优先使用只读查询投影；需要跨步骤协调时使用 Temporal Process Manager。
