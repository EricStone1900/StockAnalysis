# 股票分析智能体系统整体设计与实现基线

- 文档版本：2.0
- 架构方向：DDD + Agentic Architecture + Microservices + Event-Driven Architecture
- 当前阶段：低频投资辅助决策、人工审批、人工执行
- 基线日期：2026-08-28
- 文档状态：实施基线；架构变更必须通过ADR

## 1. 文档定位

本文档是系统的顶层架构事实来源，用于指导微服务拆分、Agent协作、事件契约、工程目录、Docker部署和开发顺序。

- 领域细节见[服务设计索引](./services/README.md)。
- 人工开发顺序和阶段门禁以[开发路线V2](../development-roadmap-v2/README.md)为准；旧版[分阶段开发指南](../development-phases/README.md)仅保留为领域实现示例。
- 数据结构以[共享契约](./services/shared-contracts.md)为准。
- Agent上下文、历史检索和长期经验以[Agent Memory设计](./agent-memory-design.md)为准。
- 日频策略、第三方插件和策略快照以[可扩展日频策略平台设计](./services/daily-strategy-extension-design.md)为准。

当前目标：

- 面向A股的低频分析和辅助决策。
- 主Agent加五个专业Agent，共六个Agent。
- 阶段11可增加一个研究侧`strategy-learning-agent`用于复盘和生成候选实验；它不进入生产决策链，因此生产交易Agent仍为六个。
- 每天最多1～2个真实交易批次。
- 每周1～2次是观察目标，不是最低交易要求。
- 允许连续数周或2～3个月不交易。
- 第一阶段由用户人工批准、人工下单并回填成交。
- 后续依次扩展Paper、Shadow和小资金白名单自动交易。

## 2. 对新架构要求的判断

### 2.1 合理部分

- 基础能力做成独立微服务，可以在多个Agent之间复用，也便于单独测试、升级和Docker部署。
- DDD适合明确行情、研究、新闻、持仓、风险、决策和执行的事实所有权。
- Agentic Architecture适合把不同证据交给专业Agent解释，再由主Agent汇总、风险Agent质疑。
- EDA适合传播“快照已经发布”“重大新闻已识别”“异常已发生”等领域事实。

### 2.2 必须修正的部分

1. **以Agent为中心不等于Agent拥有业务事实。** Agent是推理和建议中心；行情、持仓、风险、订单等事实仍由DDD领域服务拥有。
2. **不按技术模块无限拆服务。** 只有具有独立语言、规则、数据所有权和发布节奏的限界上下文才成为微服务。
3. **不建议第一阶段拆成多个Git仓库。** 推荐一个Monorepo内包含独立微服务项目；每个项目有独立Dockerfile、数据库、API和发布版本。团队扩大后再拆仓库。
4. **六个Agent不需要六套重复代码。** 使用一个通用`agent-service`项目和镜像，通过`AGENT_ID`、Prompt和Task Queue配置部署成六个逻辑Agent服务。
5. **EDA不能替代所有同步调用。** 领域事实异步发布；预交易硬风控、审批命令、创建OrderIntent等需要立即确认结果的操作使用同步API并由Temporal编排。
6. **Docker化不自动等于微服务。** 必须同时做到数据库所有权、契约版本、独立部署、故障隔离和禁止跨库写入。

## 3. 四个架构方向的落地规则

### 3.1 DDD

- 每个微服务对应一个限界上下文。
- 服务内部按Domain、Application、Ports、Adapters组织。
- Aggregate通过命令改变状态并产生Domain Event。
- 每类事实只有一个写入服务。
- 跨服务只传DTO、事件和Artifact引用，不共享ORM Entity。

### 3.2 Agentic Architecture

- 专业Agent从领域服务读取结构化证据。
- 主Agent生成TradeProposal，不直接下单。
- 风险复核Agent使用独立证据包和不同模型质疑建议。
- Agent输出通过Schema、证据、新鲜度和权限校验。
- Agent服务尽量无状态；运行记录写自己的数据库或Artifact。

### 3.3 Microservices

- 每个服务项目可独立构建镜像、运行迁移、健康检查和发布。
- 本地可共用一个PostgreSQL实例，但每个服务使用独立Database/User；禁止共享表。
- 每个服务独立拥有OpenAPI、AsyncAPI、Dockerfile和测试。
- 主项目通过生成Client、事件订阅和Temporal Activity调用基础服务。

### 3.4 Event-Driven Architecture

- NATS JetStream作为轻量持久化领域事件总线。
- 每个写服务使用Transactional Outbox。
- 每个消费者使用Inbox/Event ID保证幂等。
- 投递语义按“至少一次”设计，业务代码不得假设只收到一次。
- AsyncAPI和JSON Schema是事件契约源。
- 大型行情、新闻全文和模型上下文不放入消息，只传不可变引用。

## 4. 总体架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                         React Web                               │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTPS / SSE
                    ┌──────────▼──────────┐
                    │ platform-api-service │
                    │ BFF/Auth/Query/Config│
                    └──────┬────────┬─────┘
                           │        │ Temporal command/status
                           │   ┌────▼────────────────────┐
                           │   │workflow-orchestration   │
                           │   │Temporal Process Manager │
                           │   └──────┬──────────────────┘
                           │          │ Activities / Signals
┌──────────────────────────▼──────────▼────────────────────────────┐
│                  Agentic Decision Layer                         │
│ stock-analysis │ financial-news │ market-monitor │ market-state │
│                  main-decision │ risk-review                    │
│       one agent-service project, six isolated deployments       │
└──────────┬──────────┬──────────┬──────────┬──────────┬──────────┘
           │ REST Query/Command               │ Domain Events
┌──────────▼──────────────────────────────────▼────────────────────┐
│                    DDD Domain Services                          │
│ market-data │ quant-research │ research-automation │ news        │
│ market-monitor │ market-regime │ portfolio-risk │ governance    │
│ trade-execution                                                 │
└──────────┬──────────────────────────────────┬────────────────────┘
           │ Outbox                            │ Publish/Subscribe
           └────────────────┬──────────────────┘
                    ┌───────▼────────┐
                    │ NATS JetStream │
                    │ Domain Events  │
                    └───────┬────────┘
                            │
┌───────────────────────────▼─────────────────────────────────────┐
│ PostgreSQL per service │ Temporal DB │ Redis │ MinIO/S3         │
│ Parquet/Qlib Cache │ optional TimescaleDB │ OpenTelemetry       │
└─────────────────────────────────────────────────────────────────┘
```

## 5. DDD限界上下文与微服务项目

### 5.1 业务微服务

| 微服务项目 | 限界上下文与事实所有权 | 主要调用方 |
|---|---|---|
| `market-data-service` | Security、Calendar、MarketBar、FinancialFact、DataVersion | 量化、新闻、盯盘、Regime、组合估值 |
| `quant-research-service` | Factor/Model/Strategy Registry、Backtest、DailyAnalysisSnapshot、DailyStrategySnapshot | 股票分析Agent、主Agent、风险Agent |
| `research-automation-service` | RD-Agent实验、候选代码、Experiment Artifact、Promotion Request | quant-research-service、研究管理页面 |
| `news-intelligence-service` | NewsItem、NewsEventCandidate、FinancialNewsEvent | 新闻Agent、主Agent、风险Agent |
| `market-monitor-service` | Watchlist、分钟Bar、规则版本、MarketAnomalyEvent | 盯盘Agent、Workflow、风险Agent |
| `market-regime-service` | RegimeDefinition、MarketRegimeSnapshot | 市场状态Agent、主Agent、风险和硬风控 |
| `portfolio-risk-service` | Account、Ledger、PortfolioSnapshot、RiskPolicy、RiskEvaluation | 主Agent、风险Agent、治理、执行 |
| `decision-governance-service` | TradeProposal、Review Link、Approval、决策预算和状态机 | Workflow、Web、execution |
| `trade-execution-service` | OrderIntent、Order、Fill、Reconciliation | Web、治理、portfolio-risk |

`portfolio-risk-service`当前保留为一个限界上下文，因为组合投影与预交易风险需要强一致输入。未来多账户或独立风控发布节奏出现后，再拆成`portfolio-service`和`risk-control-service`。

### 5.2 平台微服务

| 项目 | 职责 |
|---|---|
| `platform-api-service` | React BFF、认证、RBAC、聚合查询、配置入口、SSE |
| `workflow-orchestration-service` | Temporal Workflow、Schedule、Activity和人工等待 |
| `agent-service` | 通用Agent Kernel、Model Gateway、Tool Registry和单个Agent运行入口 |

### 5.3 Agent逻辑服务

以下六个容器使用同一`agent-service`镜像，但具有独立`AGENT_ID`、Prompt、模型Profile、Tool白名单、NATS Durable Consumer和Temporal Task Queue：

| 部署名 | 输入 | 输出事件/结果 |
|---|---|---|
| `stock-analysis-agent` | DailyAnalysisSnapshot、ACTIVE策略快照、持仓 | StockAnalysisAssessment |
| `financial-news-agent` | NewsEventCandidate、证据 | FinancialNewsEvent |
| `market-monitor-agent` | MarketAnomalyEvent | MarketMonitorAssessment |
| `market-state-agent` | MarketRegimeSnapshot、组合上下文 | MarketRegimeAssessment |
| `main-decision-agent` | 全部专业分析、组合和风险数据 | TradeProposalDraft |
| `risk-review-agent` | TradeProposal、RiskReviewEvidencePacket | RiskReviewResult |

建议独立部署的原因是权限、模型、扩缩容和失败策略不同；不建议复制六套Agent Kernel代码。

## 6. 服务内部DDD结构

每个Node/Python服务都遵循类似结构：

```text
src/
  domain/                 # Entity、Value Object、Aggregate、Domain Service/Event
  application/            # Use Case、Command/Query Handler、事务边界
  ports/
    inbound/              # HTTP/Event/Temporal调用端口
    outbound/             # Repository、Event Publisher、其他服务Client端口
  adapters/
    inbound/http/         # FastAPI/NestJS Controller
    inbound/events/       # NATS JetStream Consumer
    outbound/persistence/ # PostgreSQL/Parquet/MinIO
    outbound/events/      # Outbox与NATS Publisher
    outbound/clients/     # 生成的OpenAPI Client
  bootstrap/              # DI、配置、健康检查和启动入口
```

依赖方向：

```text
Adapters -> Application -> Domain
                 ↑
               Ports
```

Domain层不能依赖FastAPI、NestJS、NATS、Temporal、Qlib或数据库SDK。Qlib、vn.py等第三方框架位于Adapter或专用Application Service边界。

## 7. Agent Service设计

### 7.1 AgentDefinition

```ts
interface AgentDefinition<I, O> {
  agentId: string;
  agentVersion: string;
  promptVersion: string;
  modelProfile: ModelProfile;
  inputSchema: ZodType<I>;
  outputSchema: ZodType<O>;
  allowedTools: readonly string[];
  subscribedEvents: readonly string[];
  taskQueue: string;
  limits: AgentLimits;
}
```

### 7.2 Agent运行链

```text
Event/Temporal Activity
  -> Input and freshness validation
  -> ContextBuilder resolves immutable references
  -> Tool authorization
  -> ModelRouter selects DeepSeek/Claude/other provider
  -> Structured generation
  -> Zod and evidence validation
  -> AgentRun persistence
  -> result event or synchronous Activity result
```

### 7.3 多模型

- 股票、市场和主决策默认使用DeepSeek推理模型。
- 新闻初筛和异常解释可使用快速模型。
- 风险复核默认使用Claude，DeepSeek作为备用或第二意见。
- 业务Agent只绑定逻辑Profile，不绑定具体模型名称。
- Claude使用Anthropic Adapter，OpenAI格式模型使用Generic OpenAI Compatible Adapter。

### 7.4 Agent边界

- 不直接访问其他服务数据库。
- 不修改RiskPolicy。
- 不直接创建OrderIntent。
- 不接收未经版本化的全量原始行情。
- 不将模型自由文本直接写入决策状态机。

## 8. 事件驱动设计

### 8.1 基础设施分工

| 能力 | 技术 | 用途 |
|---|---|---|
| 领域事件 | NATS JetStream | 持久化发布、至少一次投递、重放和多消费者 |
| 长流程 | Temporal | 每日任务、Agent顺序、风险复核、人工等待和恢复 |
| 同步命令/查询 | REST/OpenAPI | 读取快照、硬风控、审批和创建执行指令 |
| 大型Artifact | MinIO/S3 | 原始数据、新闻全文、模型、回测和完整LLM审计内容 |

Temporal不是领域事件总线；NATS也不替代需要状态恢复和人工等待的Temporal Workflow。

### 8.2 事件命名

NATS Subject：

```text
stock.<bounded-context>.<aggregate>.<event>.v1
```

示例：

```text
stock.market-data.data-version.published.v1
stock.quant.daily-analysis.published.v1
stock.strategy.daily-strategy.published.v1
stock.strategy.ensemble-strategy.published.v1
stock.news.financial-event.published.v1
stock.monitor.market-anomaly.detected.v1
stock.regime.market-regime.changed.v1
stock.portfolio.snapshot.changed.v1
stock.agent.assessment.completed.v1
stock.decision.proposal.created.v1
stock.decision.risk-review.completed.v1
stock.risk.evaluation.completed.v1
stock.decision.approval.completed.v1
stock.execution.fill.recorded.v1
```

### 8.3 EventEnvelope

```ts
interface EventEnvelope<T> {
  eventId: string;
  eventType: string;
  eventVersion: number;
  occurredAt: string;
  publishedAt: string;
  producer: string;
  aggregateId: string;
  aggregateVersion: number;
  correlationId: string;
  causationId?: string;
  idempotencyKey: string;
  payload: T;
}
```

### 8.4 Outbox和Inbox

```text
Domain transaction
  -> update aggregate
  -> insert outbox row in same transaction
  -> relay publishes to JetStream
  -> consumer checks inbox(eventId)
  -> handle event
  -> record inbox and ACK
```

消费者处理失败不ACK，由JetStream重投。重投时Inbox确保业务副作用只执行一次。

### 8.5 事件与命令边界

适合事件：快照发布、异常发生、状态变化、成交确认。

必须同步确认或由Temporal发命令：

- 预交易RiskEvaluation。
- approve/reject/modify。
- 创建OrderIntent。
- 应用Confirmed Fill。
- 发布或修改RiskPolicy。

## 9. 核心业务流程

### 9.1 每日量化

```text
market-data publishes DataVersionPublished
  -> Temporal starts DailyQuantAnalysisWorkflow
  -> quant-research runs ACTIVE factors/model
  -> quant publishes DailyAnalysisSnapshotPublished
  -> quant runs ACTIVE daily strategies and publishes DailyStrategySnapshot
  -> stock-analysis-agent consumes reference
  -> AgentAssessmentCompleted
```

### 9.2 新闻

```text
news service collects/deduplicates/links entity
  -> NewsEventCandidateCreated
  -> financial-news-agent analyzes evidence
  -> result written back through idempotent command
  -> FinancialNewsEventPublished
```

### 9.3 盯盘

```text
market-monitor aggregates 1m/5m bars
  -> deterministic rules and optional River
  -> MarketAnomalyDetected
  -> market-monitor-agent
  -> REASSESS/RISK_ESCALATION triggers decision workflow
```

无异常不调用Agent；Tick和完整分钟序列不进入NATS业务事件或Temporal History。

### 9.4 市场状态

```text
market-regime calculates trend/breadth/volatility/liquidity
  -> MarketRegimeChanged when significant
  -> market-state-agent explains
  -> portfolio and decision reevaluation when needed
```

### 9.5 投资决策

```text
Decision trigger event
  -> Temporal collects immutable evidence references
  -> main-decision-agent
  -> decision-governance creates proposalVersion
  -> risk-review-agent
       PASS -> synchronous hard risk
       PASS_WITH_CONDITIONS -> bounded revision
       REJECT -> close current version
       INSUFFICIENT_EVIDENCE -> REVIEW_BLOCKED
  -> decision-governance waits human approval
  -> trade-execution creates manual OrderIntent
  -> confirmed Fill event
  -> portfolio-risk applies ledger and publishes new snapshot
```

每天最多1～2个交易批次由`portfolio-risk-service`确定性执行。HOLD、拒绝、过期和未审批不计入真实批次。

## 10. 数据与事实所有权

| 事实对象 | 唯一写入微服务 |
|---|---|
| Security、MarketBar、FinancialFact、DataVersion | market-data-service |
| Factor、Model、Strategy、Backtest、DailyAnalysisSnapshot、DailyStrategySnapshot | quant-research-service |
| Experiment、CandidateArtifact、PromotionRequest | research-automation-service |
| NewsItem、NewsEventCandidate、FinancialNewsEvent | news-intelligence-service |
| Watchlist、MonitorRule、MarketAnomalyEvent | market-monitor-service |
| RegimeDefinition、MarketRegimeSnapshot | market-regime-service |
| PortfolioLedger、PortfolioSnapshot、RiskPolicy、RiskEvaluation | portfolio-risk-service |
| TradeProposal、Approval、DecisionBudget | decision-governance-service |
| OrderIntent、Order、Fill、ReconciliationIssue | trade-execution-service |
| AgentRun、ModelRun、Agent输出 | 对应Agent部署的agent-service数据库 |
| Workflow状态 | Temporal |

规则：

- Database per Service，不共享表和ORM关系。
- 跨服务关联只保存ID和版本。
- 读模型可以订阅事件建立本地Projection，但不是原事实写入方。
- 金额和数量使用Decimal语义。
- 所有投资证据包含DataFreshness和ProvenanceRef。

## 11. 微服务项目目录

推荐Monorepo，但每个目录都是独立Docker微服务项目：

```text
StockAnalysis/
├── apps/
│   └── web/                              # React前端
├── services/
│   ├── platform-api-service/             # BFF、认证、聚合查询
│   ├── workflow-orchestration-service/   # Temporal Worker
│   ├── agent-service/                    # 通用镜像，部署六次
│   │   ├── agents/                       # 六个AgentDefinition和Prompt
│   │   ├── kernel/                       # Runner/Registry/Guardrail
│   │   └── model-gateway/                # DeepSeek/Claude/OpenAI兼容
│   ├── market-data-service/              # 数据、PIT和版本
│   ├── quant-research-service/           # Qlib生产因子、模型和回测
│   │   └── strategy_sdk/                 # 稳定插件契约和第三方策略Adapter
│   ├── research-automation-service/      # RD-Agent隔离研究
│   ├── news-intelligence-service/        # 新闻和事件
│   ├── market-monitor-service/           # vn.py、规则和River
│   ├── market-regime-service/            # 市场和行业状态
│   ├── portfolio-risk-service/           # 组合、流水和硬风控
│   ├── decision-governance-service/      # 建议、复核关联和审批
│   └── trade-execution-service/           # 人工/模拟/券商执行
├── packages/
│   ├── contracts-ts/                     # 生成的TypeScript契约
│   ├── agent-kernel-sdk/                 # Agent公共运行能力
│   ├── eventing-ts/                      # NATS/Outbox/Inbox公共适配器
│   ├── temporal-common/                  # Workflow/Activity公共约定
│   ├── observability/                    # 日志、Trace、Metrics
│   └── test-kit/                         # Fake Provider和契约Fixture
├── python/packages/
│   ├── contracts-py/                     # 生成的Pydantic契约
│   ├── eventing-py/                      # NATS/Outbox/Inbox
│   ├── market-core/                      # 时间、证券和Decimal语义
│   ├── snapshot-publisher/               # 不可变快照发布
│   └── observability-py/
├── contracts/
│   ├── openapi/                          # 同步API事实源
│   ├── asyncapi/                         # NATS事件事实源
│   ├── schemas/                          # JSON Schema
│   ├── examples/
│   └── compatibility/
├── deploy/
│   ├── compose/
│   │   ├── infrastructure.yml            # Postgres/NATS/Temporal/Redis/MinIO
│   │   ├── domain-services.yml           # 九个领域服务
│   │   ├── agent-services.yml            # 六个Agent容器
│   │   └── full-stack.yml
│   ├── docker/                           # 公共构建基础镜像
│   └── environments/                     # dev/test/prod配置模板
├── tests/
│   ├── contract/                         # OpenAPI/AsyncAPI消费者契约
│   ├── integration/
│   ├── e2e/
│   ├── replay/
│   ├── golden/
│   └── failure/
└── docs/
```

### 11.1 每个服务项目的最低结构

```text
service-name/
  src/
  tests/
  migrations/
  contracts/              # 服务拥有的API/事件片段
  Dockerfile
  compose.dev.yml
  .env.example
  README.md
  package.json|pyproject.toml
```

README必须列明：限界上下文、拥有的事实、同步API、发布/订阅事件、依赖、启动、迁移、测试和失败语义。

## 12. Docker部署

### 12.1 Compose Profile

```text
infra:    postgres instances, nats, temporal, redis, minio, otel
domain:   all deterministic domain services
agents:   six agent deployments
web:      platform-api and React
full:     all profiles
```

Agent部署示例：

```yaml
stock-analysis-agent:
  image: stock/agent-service:${APP_VERSION}
  environment:
    AGENT_ID: stock-analysis-agent
    TEMPORAL_TASK_QUEUE: agent-stock-analysis
    NATS_DURABLE_CONSUMER: stock-analysis-agent-v1

risk-review-agent:
  image: stock/agent-service:${APP_VERSION}
  environment:
    AGENT_ID: risk-review-agent
    MODEL_PROFILE: risk-review
    TEMPORAL_TASK_QUEUE: agent-risk-review
```

### 12.2 数据库

- 本地允许一个PostgreSQL容器创建多个Database/User。
- 生产可按风险和负载拆成多个实例。
- Temporal使用独立数据库。
- 服务凭据只允许访问自己的Database。
- MinIO Bucket按领域划分并设置最小权限。

### 12.3 不建议第一阶段引入

- Kubernetes和Service Mesh。
- Kafka集群。
- 多区域部署。
- 每个服务独立Git仓库。

Docker Compose足以完成当前低频人工模式；出现明确的可用性和扩缩容需求后再演进。

## 13. API、事件和一致性要求

- HTTP外部接口`/api/v1`，内部接口`/internal/v1`。
- 长任务返回202和runId。
- 写命令包含Idempotency-Key、actorId、correlationId和expectedVersion。
- 领域Aggregate使用乐观锁。
- 每个事件有eventId、eventVersion和producer。
- 事件Schema破坏性变更发布新的Subject Major版本，并支持新旧消费者并行迁移。
- 服务不能在数据库事务中同步等待NATS发布；先写Outbox。
- Eventual Consistency只用于可接受延迟的Projection和触发。
- 风控、审批和下单使用可确认命令，不允许“最终也许成功”的模糊状态。

## 14. 安全和可靠性

- 新闻和外部文本标记为不可信内容。
- RD-Agent在独立容器运行，无生产数据库、券商和交易密钥。
- 第三方策略在隔离Runner容器执行，无外网、生产数据库、模型和券商密钥。
- market-monitor只使用只读行情权限。
- Agent无RiskPolicy写权限和交易权限。
- trade-execution是唯一持有券商交易密钥的服务。
- 风控不可用时新增/加仓失败关闭。
- NATS消费者失败不ACK，重复投递必须幂等。
- UNKNOWN订单状态查询或人工处理，禁止自动重下单。
- 自动交易Feature Flag默认关闭。
- Kill Switch独立于Agent、NATS和Temporal生效。

## 15. 测试要求

每个微服务必须有：

- Domain单元测试。
- Application Use Case测试。
- Repository集成测试。
- OpenAPI Contract Test。
- AsyncAPI/Event Consumer Contract Test。
- Outbox/Inbox和重复事件测试。
- Docker镜像健康检查。
- 依赖超时和故障测试。

系统级必须覆盖：

1. DataVersion事件触发每日量化且重复事件不重复运行。
2. 新闻候选只被分析一次。
3. 无异常不调用盯盘Agent。
4. Regime变化触发重评估。
5. 主Agent建议被风险Agent或硬风控拒绝。
6. PASS_WITH_CONDITIONS产生新proposalVersion并有修订上限。
7. 每日第3个交易批次被拒绝。
8. Worker或NATS重启后不丢事件、不重复副作用。
9. 人工审批等待和过期正确。
10. Fill重复投递只入账一次。
11. HOLD持续数周不会触发强制交易。
12. 新增符合Plugin SDK的第三方日频策略不修改Agent、Workflow和治理状态机。
13. 第三方策略的网络、数据库、宿主文件和生产密钥访问被隔离并留下审计记录。
14. `CANDIDATE`或过期策略快照不能进入Agent上下文，策略版本变化使旧风险证据包失效。
15. 每日策略计算返回`NO_REBALANCE`时不创建TradeProposal或增加交易批次。

## 16. 推荐开发顺序

实施顺序以[开发路线V2](../development-roadmap-v2/README.md)的00～12阶段为唯一门禁来源：先冻结架构和搭建全部服务骨架，再逐个完成独立领域微服务，然后建设平台访问层、Agent基础、业务Agent、Temporal人工闭环、学习闭环以及Paper/Shadow和受控自动交易。

每个微服务必须按S0边界契约、S1骨架、S2最小纵向切片、S3核心领域、S4契约事件、S5生产强化和S6独立验收推进。基础服务先独立Docker部署并通过`90-test-plan.md`与`99-acceptance.md`，再允许Agent或Workflow接入。开发期间可使用Fake服务和固定Fixture，不允许通过跨库访问“临时联调”。

## 17. 顶层验收标准

- 每个限界上下文是独立Docker微服务项目。
- 每个服务拥有独立Database/User、API、事件、迁移和测试。
- 六个Agent使用同一Kernel代码但可独立部署、授权和扩缩容。
- 主项目只通过API、Temporal和NATS调用基础服务。
- NATS事件使用Outbox/Inbox并能重放。
- Agent不拥有行情、持仓、风险和订单事实。
- 硬风控、人工审批和执行边界不可绕过。
- 每天最多1～2个交易批次由确定性规则执行。
- 系统允许长期HOLD。
- 日频策略通过版本化Registry和Plugin SDK扩展，第三方代码默认隔离运行。
- 只有通过回测、安全、许可和人工审批并处于`ACTIVE`状态的策略快照能成为生产决策证据。
- 任一建议可追溯数据、事件、Agent、模型、Prompt、风险规则和人工操作。
- 任一服务故障不会静默放行交易。

## 18. 参考文档

- [服务设计索引](./services/README.md)
- [Agent Runtime](./services/agent-runtime-service.md)
- [工作流编排](./services/workflow-orchestration-service.md)
- [共享契约](./services/shared-contracts.md)
- [事件驱动架构](./services/event-driven-architecture.md)
- [自动研究服务](./services/research-automation-service.md)
- [Agent Memory设计](./agent-memory-design.md)
- [可扩展日频策略平台](./services/daily-strategy-extension-design.md)
- [实施清单](./services/implementation-checklist.md)
- [分阶段开发指南](../development-phases/README.md)
- [开发路线V2（当前实施门禁）](../development-roadmap-v2/README.md)
- [NATS JetStream](https://docs.nats.io/concepts/jetstream)
- [Temporal Workflow](https://docs.temporal.io/workflows)
- [AsyncAPI](https://www.asyncapi.com/docs)
