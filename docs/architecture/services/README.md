# 股票分析智能体系统：服务设计索引

本目录是各限界上下文和平台能力的详细设计入口。顶层约束以[整体设计与实现基线](../stock-analysis-agent-system-design.md)为准，事件规范见[事件驱动架构](./event-driven-architecture.md)，当前开发顺序和验收门禁见[开发路线V2](../../development-roadmap-v2/README.md)；旧版[分阶段开发指南](../../development-phases/README.md)仅作代码示例参考。

## 1. 拆分结论

系统采用DDD + Agentic Architecture + Microservices + Event-Driven Architecture：

- 按限界上下文拆微服务，不按Controller、类或Agent数量机械拆分。
- 行情、研究、新闻、持仓风险、决策治理和交易执行拥有各自业务事实；Agent只拥有推理运行记录和结构化判断。
- 所有基础服务均是Monorepo中的独立项目，拥有独立Dockerfile、数据库、API/事件契约、迁移和测试，可单独构建与部署。
- 六个Agent复用一个`agent-service`工程和镜像，使用不同配置部署为六个独立容器，不复制六套Kernel代码。
- NATS JetStream传播领域事件，Temporal编排长流程，REST/OpenAPI处理需要即时答复的查询与命令。
- 当前为低频辅助决策：每天最多1～2个交易批次，允许长期不交易，人工审批和人工执行是不可绕过的边界。

## 2. 独立微服务项目

### 2.1 业务限界上下文

| 服务设计 | 主要技术 | 事实所有权与用途 |
|---|---|---|
| [market-data-service](./market-data-service.md) | FastAPI、Polars、Parquet | 证券、交易日历、行情、财务PIT、DataVersion |
| [quant-research-service](./quant-research-service.md) | FastAPI、Qlib、Strategy Plugin SDK | 已批准因子、模型、日频策略、回测和每日快照 |
| [research-automation-service](./research-automation-service.md) | FastAPI、RD-Agent、隔离Sandbox | 自动研究实验、候选代码与Promotion Request，不写生产Registry |
| [news-intelligence-service](./news-intelligence-service.md) | FastAPI、FinNLP、RSSHub/合规数据源 | 新闻证据、去重、实体关联、金融新闻事件 |
| [market-monitor-service](./market-monitor-worker.md) | vn.py、River、规则引擎 | Watchlist、分钟聚合、异常事件；文档保留worker文件名 |
| [market-regime-service](./market-regime-service.md) | FastAPI、Qlib/River/ruptures | 指数、宽度、波动、行业和市场状态快照 |
| [portfolio-risk-service](./portfolio-risk-service.md) | NestJS、PostgreSQL | 账户、成交账本、持仓投影、RiskPolicy和硬风控 |
| [decision-governance-service](./decision-governance-service.md) | NestJS、PostgreSQL | TradeProposal、复核关联、频率预算、批准状态机和审计 |
| [trade-execution-service](./trade-execution-service.md) | NestJS、Broker Adapter | OrderIntent、人工成交、Paper/Shadow、订单和对账 |

### 2.2 平台服务

| 服务设计 | 主要技术 | 职责 |
|---|---|---|
| [platform-api-service](./platform-api-service.md) | NestJS、Fastify | BFF、认证、RBAC、聚合查询、配置入口和SSE |
| [workflow-orchestration-service](./workflow-orchestration-service.md) | Temporal TypeScript SDK | Schedule、Workflow、Activity、Signal、人工等待和补偿 |
| [agent-service](./agent-runtime-service.md) | TypeScript、Vercel AI SDK、Zod | 通用Agent Kernel、多模型路由、工具授权；六个配置化部署 |

### 2.3 跨服务规范

- [shared-contracts](./shared-contracts.md)：同步DTO、事件Envelope、核心对象与事实来源。
- [event-driven-architecture](./event-driven-architecture.md)：NATS Subject、Outbox/Inbox、重放、幂等和AsyncAPI。
- [agent-memory-design](../agent-memory-design.md)：Working Memory、主Agent情景记忆、历史检索、Outcome和Strategy Memory。
- [daily-strategy-extension-design](./daily-strategy-extension-design.md)：Strategy Registry、Plugin SDK、第三方隔离执行和日频策略快照。
- [implementation-checklist](./implementation-checklist.md)：实施与发布检查清单。

## 3. Agent与基础服务关系

| Agent部署 | 主要读取 | 主要产出 |
|---|---|---|
| `stock-analysis-agent` | DailyAnalysisSnapshot、PortfolioSnapshot | StockAnalysisAssessment |
| `financial-news-agent` | NewsEventCandidate、Security、证据正文引用 | FinancialNewsEvent |
| `market-monitor-agent` | MarketAnomalyEvent、相关分钟Bar引用 | MarketMonitorAssessment |
| `market-state-agent` | MarketRegimeSnapshot、组合暴露 | MarketRegimeAssessment |
| `main-decision-agent` | 全部专业评估、持仓、风险数据 | TradeProposalDraft；不能创建订单 |
| `risk-review-agent` | Proposal、独立证据包、RiskPolicy摘要 | RiskReviewResult；不能通过语义判断放宽硬风控 |

Agent通过只读Tool查询服务快照，通过Temporal Activity执行受控步骤，通过事件发布完成事实。任何Agent不得跨库写入、直接修改持仓、批准建议或向券商下单。

## 4. 混合集成规则

| 场景 | 机制 | 原因 |
|---|---|---|
| 快照发布、新闻识别、异常发生、成交记录 | NATS JetStream领域事件 | 一对多传播、持久化、可重放 |
| 每日分析、决策、审批等待和执行链路 | Temporal Workflow | 长流程状态、超时、重试、Signal和补偿 |
| 查询快照、硬风控、创建OrderIntent | REST/OpenAPI | 调用方必须获得明确即时结果 |
| 大型因子矩阵、新闻全文、模型文件 | MinIO/S3/Parquet引用 | 避免大消息和重复复制 |

每个写服务使用Transactional Outbox；每个消费者持久化Inbox/Event ID。事件至少一次投递，因此Handler必须幂等。Temporal不是事件总线，NATS也不替代需要确定结果的业务命令。

## 5. Docker部署约束

本地通过Compose Profile启动，生产可平移到Kubernetes或其他容器平台：

```text
infra   -> postgres, temporal, nats, redis, minio, observability
domain  -> nine domain services
agents  -> workflow-orchestration + six agent containers
web     -> platform-api + React web
full    -> all profiles
```

- 每个服务目录有`Dockerfile`、`.dockerignore`、健康检查、非root用户和资源限制。
- 本地允许共用一个PostgreSQL容器，但每个服务必须使用独立Database/User；禁止共享表和跨库写入。
- 容器间通过服务名、OpenAPI生成Client和NATS Subject通信，不引用对方源代码中的Domain Entity。
- 数据库迁移由服务自身镜像执行；发布时必须兼容滚动升级和事件版本并存。
- API、Worker可来自同一服务镜像的不同启动命令，但它们仍属于同一个限界上下文。

## 6. 三条核心链路

### 6.1 每日研究

```text
Temporal Schedule
  -> market-data-service发布DataVersion
  -> quant-research-service运行ACTIVE因子与模型
  -> 运行ACTIVE日频策略
  -> 发布DailyAnalysisSnapshot和DailyStrategySnapshot
  -> stock-analysis-agent生成解释
```

`research-automation-service`是旁路研究通道，只产生候选和Promotion Request；人工批准并由`quant-research-service`验证后，下一版本才可进入生产。

### 6.2 盘中监控

```text
market-data/gateway -> market-monitor-service规则与River
  -> MarketAnomalyEvent -> market-monitor-agent
  -> 必要时Signal决策Workflow
```

盯盘默认按1分钟输入、5分钟聚合，可按异常自适应加密；它不是每5分钟要求主Agent交易。

### 6.3 低频决策

```text
专业Agent结果 + PortfolioSnapshot + MarketRegimeSnapshot
  -> main-decision-agent
  -> risk-review-agent
  -> portfolio-risk-service硬风控
  -> decision-governance-service频率预算与人工批准
  -> trade-execution-service人工OrderIntent/Fill
  -> portfolio-risk-service更新账本投影
```

只有`PASS`且硬风控通过的建议才能进入审批；`NO_TRADE`是正常结果。每日1～2次是上限，不得实现为最低次数或强制交易目标。

## 7. 推荐开发顺序

1. 契约、NATS/Temporal/PostgreSQL/MinIO基础设施和服务模板。
2. `market-data-service`。
3. `quant-research-service`生产因子、模型与可扩展日频策略闭环。
4. `research-automation-service`隔离研究通道。
5. `portfolio-risk-service`、`platform-api-service`和只读Web。
6. `news-intelligence-service`、`market-monitor-service`、`market-regime-service`。
7. 通用`agent-service`及六个部署。
8. `workflow-orchestration-service`与`decision-governance-service`。
9. `trade-execution-service`人工模式与端到端回放。
10. Paper、Shadow和满足上线门槛后的白名单自动交易。

具体步骤与验证条件以[分阶段开发指南](../../development-phases/README.md)为准。
