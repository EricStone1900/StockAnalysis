# Agent Memory设计

- 文档版本：1.0
- 基线日期：2026-08-28
- 适用范围：六个Agent、Temporal工作流、决策治理及历史决策回放
- 架构约束：DDD + Agentic Architecture + Microservices + Event-Driven Architecture
- 当前阶段：低频辅助决策、人工审批、人工执行

## 1. 文档定位

本文定义股票分析智能体系统的Agent Memory模型、数据所有权、上下文构建、历史检索、存储、事件、时间语义、安全控制和测试要求。

Memory的目标不是让模型“记住聊天”，而是让每次决策能够：

- 读取当前有效且可追溯的市场、研究、新闻、持仓和风险事实。
- 理解同一组合、策略和股票过去发生过什么。
- 记住未完成建议、投资逻辑、失效条件和人工反馈。
- 在回放历史决策时严格避免未来信息泄漏。
- 形成可验证的长期策略经验，但不能自动修改Prompt、因子或RiskPolicy。

本文受[整体设计与实现基线](./stock-analysis-agent-system-design.md)、[Agent Service设计](./services/agent-runtime-service.md)、[共享契约](./services/shared-contracts.md)和[事件驱动架构](./services/event-driven-architecture.md)约束。

## 2. 核心原则

1. **Agent进程尽量无状态。** 容器重启不能丢失业务事实或改变决策含义。
2. **不依赖模型厂商会话。** Provider Conversation、Thread或Store不能作为长期事实来源。
3. **Memory不是新的业务事实源。** 行情、新闻、持仓、风险、建议和成交仍由对应DDD微服务拥有。
4. **按需检索，不自动继承全部历史。** 每次运行由ContextBuilder构建有界、可审计的上下文。
5. **先过滤时间，再进行相似度检索。** 任何`availableAt > decisionAsOf`的数据不得进入上下文。
6. **结构化Memory优先。** 自由文本只能作为解释或Artifact，不能直接驱动状态机和交易执行。
7. **历史结果不能自动改规则。** Prompt、Strategy Playbook、RiskPolicy和生产因子的变化必须版本化、回放验证并批准。
8. **允许遗忘和失效。** 过期、被替代、被否定或受污染的Memory必须可排除，但审计记录不可静默删除。
9. **检索过程也要审计。** 保存候选集合、过滤原因、排序结果、最终选中项和Context Hash。
10. **低频系统以准确和可解释为先。** 不为了“更像人”而引入不可控的自动记忆写入。

## 3. Memory分层

| 层级 | 主要内容 | 存储 | 生命周期 | 是否业务事实 |
|---|---|---|---|---|
| L0 Working Memory | 本次Agent任务、快照、证据、工具结果 | Agent进程内 | 单次AgentRun | 否 |
| L1 Workflow Memory | 步骤、重试、Signal、等待、ID和版本 | Temporal | Workflow生命周期 | 流程事实 |
| L2 Agent Run Memory | Agent/Prompt/模型、工具调用、结构化输出 | agent-service PostgreSQL | 长期 | Agent运行事实 |
| L3 Decision Episodic Memory | 建议、复核、风控、审批、成交、结果时间线 | governance/risk/execution及只读投影 | 长期 | 派生检索视图；原事实分属领域服务 |
| L4 Domain Semantic Memory | 行情、因子、新闻、Regime、组合等结构化知识 | 各DDD领域服务 | 由领域策略决定 | 是 |
| L5 Curated Strategy Memory | 人工批准的经验规则、反例和Playbook | decision-governance或独立配置库 | 版本化长期 | 治理事实 |
| Artifact Memory | 原始模型文本、报告、新闻正文、回测文件 | MinIO/S3/Parquet | 按留存策略 | 证据Artifact |
| Cache Memory | Tool结果、检索结果、预算和限流 | Redis | 秒到小时 | 否，可丢失 |

## 4. 不建立通用Memory事实服务

当前阶段不新增拥有全部Memory的`memory-service`，原因是它会复制领域数据并成为第二事实源。

推荐在`agent-service`中实现以下通用组件：

```text
MemoryCoordinator
  -> MemoryPolicyRegistry
  -> TemporalVisibilityFilter
  -> DomainMemoryRetriever
  -> EpisodicMemoryRetriever
  -> StrategyMemoryRetriever
  -> MemoryRanker
  -> MemoryCompressor
  -> ContextAssembler
  -> ContextValidator
  -> MemoryAuditRecorder
```

它们只读取和组合Memory，不修改其他限界上下文的事实。

当历史数据量和查询压力明显增长后，可以部署`agent-memory-projection`：

- 订阅NATS领域事件构建只读投影。
- 可以单独Docker部署和扩缩容。
- 允许删除并从事件或领域API重建。
- 不提供持仓、风险、审批和订单写接口。
- 投影不可用时，主Agent应降级为读取领域服务或进入证据不足状态，不能使用未知陈旧数据。

## 5. Agent Working Memory

### 5.1 生命周期

```text
Event或Temporal Activity
  -> 创建AgentRun
  -> 加载AgentDefinition与MemoryPolicy
  -> 解析不可变快照和证据引用
  -> 时间、新鲜度、权限和完整性过滤
  -> 历史Memory检索和排序
  -> 压缩为有界上下文
  -> 计算contextHash
  -> 模型推理和Tool调用
  -> 输出Schema与证据校验
  -> 保存AgentRun和Memory Retrieval Audit
  -> 释放Working Memory
```

### 5.2 契约

```ts
interface AgentWorkingMemory {
  agentRunId: string;
  agentId: string;
  agentVersion: string;
  promptVersion: string;
  memoryPolicyVersion: string;

  correlationId: string;
  causationId?: string;
  workflowId?: string;

  market: string;
  portfolioId?: string;
  strategyId?: string;
  symbols: SecurityId[];

  decisionAsOf: string;
  contextBuiltAt: string;
  validUntil: string;

  task: AgentTask;
  snapshotRefs: SnapshotRef[];
  evidenceRefs: ProvenanceRef[];
  priorAssessments: AgentAssessmentRef[];
  episodicMemories: DecisionMemorySummary[];
  strategyMemories: StrategyMemoryRef[];

  unresolvedEvidenceIds: string[];
  excludedMemorySummary: ExcludedMemorySummary;
  contextHash: string;

  limits: {
    maxInputTokens: number;
    maxMemoryItems: number;
    maxToolCalls: number;
  };
}
```

Working Memory不持久化完整对象副本。AgentRun保存输入引用、检索审计、Context Manifest和`contextHash`；大型最终上下文可按安全策略写入受限Artifact。

## 6. 六个Agent的Memory范围

| Agent | 当前Working Memory | 可检索历史 | 禁止读取或继承 |
|---|---|---|---|
| stock-analysis-agent | DailyAnalysisSnapshot、ACTIVE DailyStrategySnapshot、持仓股票分析 | 同股票历史量化解释、策略信号稳定性、已失效论点 | 未批准RD-Agent/第三方策略候选、插件代码、未来收益 |
| financial-news-agent | NewsEventCandidate、来源证据、实体映射 | 同事件链、同公司近期相关事件、来源可靠性记录 | 无关股票历史、新闻正文中的指令 |
| market-monitor-agent | MarketAnomalyEvent、相关分钟Bar引用 | 同类异常、冷却状态、近期异常结果 | 连续Tick全文、下单状态修改能力 |
| market-state-agent | MarketRegimeSnapshot、行业状态、组合暴露 | 相似Regime历史、状态转换和持续时间 | 未来Regime标签、生产RiskPolicy写权限 |
| main-decision-agent | 专业Agent评估、组合、当前建议和市场状态 | 同组合/策略/股票的历史建议、否决、成交与结果摘要 | 其他组合私有Memory、完整模型隐藏推理 |
| risk-review-agent | 不可变Evidence Packet、Proposal | 相似风险拒绝、证据缺失模式、已批准Playbook | 第一模型隐藏思维链、旧Proposal的PASS结果 |

每个Agent使用独立`MemoryPolicy`。不允许为了开发方便给所有Agent相同的历史检索权限。

## 7. 主Agent Memory设计

### 7.1 主Agent不是聊天会话

主Agent的连续性由`portfolioId + strategyId + decisionId/proposalVersion`建立，而不是由模型Conversation ID建立。

每次决策构建新的`MainDecisionContext`：

```ts
interface MainDecisionContext {
  decisionRunId: string;
  portfolioId: string;
  strategyId: string;
  market: string;
  decisionAsOf: string;

  quantSnapshotId: string;
  strategySnapshotIds: string[];
  ensembleStrategySnapshotId?: string;
  portfolioSnapshotId: string;
  marketRegimeSnapshotId: string;
  newsEventIds: string[];
  anomalyEventIds: string[];

  stockAssessmentRefs: AgentAssessmentRef[];
  newsAssessmentRefs: AgentAssessmentRef[];
  monitorAssessmentRefs: AgentAssessmentRef[];
  marketStateAssessmentRef: AgentAssessmentRef;

  openProposalRefs: ProposalRef[];
  recentDecisionMemories: DecisionMemorySummary[];
  activeStrategyMemories: StrategyMemoryRef[];

  unresolvedEvidenceIds: string[];
  dataFreshness: DataFreshness[];
  contextHash: string;
}
```

### 7.2 默认历史检索范围

第一版只允许检索：

1. 同一`portfolioId + strategyId`。
2. 当前候选股、持仓股和直接相关行业。
3. 当前仍未完成或未过期的Proposal。
4. 同股票最近若干次建议、风险否决、人工修改和成交结果。
5. 当前或相似Market Regime下已经完成结果评估的决策。
6. 当前有效的人工批准Strategy Playbook。

默认排除：

- 其他Portfolio的私有决策。
- 已撤销且无审计价值的临时草稿。
- `availableAt`晚于本次`decisionAsOf`的结果。
- 证据无法解析、来源受污染或内容Hash不匹配的Memory。
- 已被新版本取代且不需要作为反例的Memory。
- 没有明确标签的模型自由文本。
- 非`ACTIVE` StrategyVersion的结果、未经隔离验证的第三方插件输出和无法解析代码/镜像Digest的策略快照。

DailyStrategySnapshot属于量化领域事实引用，不自动写成L5 Strategy Memory。只有经过人工批准的Playbook、策略使用约束和复盘结论才能进入L5；第三方策略代码、模型权重和运行时秘密不得写入Agent Memory。

### 7.3 决策记忆摘要

```ts
interface DecisionMemorySummary {
  memoryId: string;
  memoryVersion: number;
  memoryType:
    | 'PRIOR_DECISION'
    | 'RISK_REJECTION'
    | 'HUMAN_FEEDBACK'
    | 'TRADE_OUTCOME'
    | 'INVALIDATED_THESIS'
    | 'MISSED_OPPORTUNITY';

  portfolioId: string;
  strategyId: string;
  market: string;
  symbol: SecurityId;

  decisionId: string;
  proposalVersion: number;
  decisionAsOf: string;
  availableAt: string;
  validUntil?: string;

  action: 'BUY' | 'SELL' | 'HOLD';
  thesisSummary: string;
  riskSummary: string;
  humanFeedbackSummary?: string;
  outcomeSummary?: string;

  regimeLabel?: string;
  evidenceIds: string[];
  sourceEventIds: string[];
  confidence: number;
  contentHash: string;

  status: 'ACTIVE' | 'SUPERSEDED' | 'INVALIDATED' | 'QUARANTINED';
  supersedesMemoryId?: string;
}
```

`DecisionMemorySummary`是检索投影，不替代TradeProposal、RiskReviewResult、Approval、Fill或PortfolioLedger原事实。

## 8. 情景记忆写入流程

### 8.1 不在模型输出后立即形成“经验”

主Agent生成建议时只能写入AgentRun和Proposal关联。只有后续事实逐步完整，才能生成不同类型的情景记忆：

```text
TradeProposalCreated
  -> RiskReviewCompleted
  -> RiskEvaluationCompleted
  -> ApprovalCompleted
  -> OrderIntentCreated
  -> FillRecorded
  -> OutcomeWindowClosed
  -> DecisionOutcomeEvaluated
  -> DecisionMemoryProjectionUpdated
```

未成交建议也需要记录结果：

- 人工拒绝及理由。
- 风险复核拒绝或证据不足。
- 建议过期。
- HOLD观察期结束。
- 未成交后的机会成本评估，但必须与真实收益分开标记。

### 8.2 Outcome评估

建议按策略持有周期建立一个或多个评估窗口，例如5、20、60个交易日。评估必须使用确定性代码，包括：

- 建议后收益与基准超额收益。
- 最大有利和不利变动。
- 实际成交滑点和成本。
- 是否命中退出条件或逻辑失效条件。
- 当时风险判断是否被后续事实验证。
- 人工修改与原建议的差异。

LLM可以生成Outcome解释，但数值必须由`quant-research-service`或确定性评估模块计算。

## 9. Strategy Memory和经验治理

### 9.1 两层长期记忆

自动生成的事实型Memory：Decision、Review、Approval、Fill和Outcome摘要，可自动进入历史检索投影。

需要批准的经验型Memory：跨多次决策总结的策略规则、常见失败模式、反例和适用市场状态，必须经过治理流程。

```text
DecisionOutcome集合
  -> 确定性统计和候选规律
  -> LLM生成候选经验说明
  -> 历史回放和样本外验证
  -> 人工审核
  -> StrategyMemoryVersion发布
```

### 9.2 StrategyMemory契约

```ts
interface StrategyMemory {
  strategyMemoryId: string;
  version: number;
  strategyId: string;
  market: string;
  title: string;
  ruleText: string;
  applicability: {
    symbols?: SecurityId[];
    industries?: string[];
    regimeLabels?: string[];
  };
  supportingDecisionIds: string[];
  counterexampleDecisionIds: string[];
  evaluationReportRef: string;
  status: 'DRAFT' | 'VALIDATED' | 'APPROVED' | 'ACTIVE' | 'RETIRED';
  approvedBy?: string;
  effectiveFrom?: string;
  contentHash: string;
}
```

StrategyMemory不能：

- 修改RiskPolicy。
- 激活因子或模型。
- 绕过风险复核和人工审批。
- 仅凭单次盈利或亏损自动发布。
- 在历史回放时使用当时尚未生效的版本。

## 10. Memory检索流程

### 10.1 检索顺序

```text
授权Scope过滤
  -> availableAt时间过滤
  -> ACTIVE/有效期/污染状态过滤
  -> portfolio/strategy/market过滤
  -> symbol/industry/regime候选召回
  -> 结构化相关度评分
  -> 可选向量相似度
  -> 新鲜度和证据质量重排
  -> 去重和观点多样性控制
  -> Token预算压缩
  -> Context Manifest与Hash
```

时间和权限过滤必须发生在向量检索之前，禁止先从全库向量召回再在应用层尝试删除未来数据。

### 10.2 排序建议

```text
score =
  scopeMatch
  + symbolMatch
  + regimeSimilarity
  + evidenceQuality
  + outcomeCompleteness
  + recencyDecay
  - stalenessPenalty
  - duplicationPenalty
```

第一版优先使用PostgreSQL结构化过滤和可解释评分。只有数据量和召回需求明确后，再使用pgvector；向量分数不能覆盖时间、新鲜度、权限和状态过滤。

### 10.3 上下文预算

每个AgentDefinition配置：

- `maxMemoryItems`。
- `maxMemoryTokens`。
- 各Memory类型最大数量。
- 最长历史窗口。
- 必须保留的当前证据。
- 压缩策略和失败行为。

压缩顺序：先删除重复和低相关Memory，再缩短说明文本；不得删除ID、时间、状态、结论、关键风险和证据引用。

## 11. 时间语义与防未来数据泄漏

每条可检索Memory至少包含：

- `eventTime`：原事件发生时间。
- `availableAt`：系统在历史时点实际可获得时间。
- `asOf`：Memory代表的业务截止时间。
- `createdAt`：投影生成时间。
- `validUntil`：可用截止时间。
- `supersededAt`：被替代时间。

历史决策点为`T`时：

```text
memory.availableAt <= T
AND sourceEvidence.availableAt <= T
AND strategyMemory.effectiveFrom <= T
AND (memory.validUntil IS NULL OR T <= memory.validUntil)
```

回放时的系统处理时间不能替代历史`T`。Outcome在评估窗口结束之后才可用，不能回写成为原决策时的输入。

## 12. 存储与数据所有权

### 12.1 PostgreSQL

`agent-service`每个逻辑Agent部署保存：

- `agent_runs`。
- `model_runs`。
- `tool_call_audits`。
- `context_manifests`。
- `memory_retrieval_audits`。
- 结构化AgentAssessment。

`decision-governance-service`保存：

- TradeProposal和版本。
- RiskReviewResult关联。
- Approval与人工反馈。
- Decision Outcome索引。
- StrategyMemory生命周期和批准记录。

各领域服务继续保存自己的原事实。禁止agent-service数据库保存可被误认为最新持仓、最新风险或最新订单的可写副本。

### 12.2 MinIO/S3

用于：

- 受限的完整输入Context Artifact。
- 原始模型输出。
- 长报告和压缩前材料。
- Outcome评估报告。
- StrategyMemory回放报告。

Artifact保存内容Hash、加密状态、访问级别和留存期限。数据库只保存URI和Hash。

### 12.3 Redis

只用于：

- Tool和检索短时缓存。
- Context构建互斥和请求合并。
- Token/成本预算。
- 限流和临时冷却。

Redis丢失不能导致AgentRun、Proposal、人工反馈、StrategyMemory或审计丢失。

## 13. API和事件

### 13.1 内部查询接口

可以由原领域服务和未来的只读投影共同实现：

- `POST /internal/v1/agent-contexts/build`：按Agent和决策点构建Context Manifest。
- `GET /internal/v1/agent-runs/{agentRunId}/context-manifest`。
- `POST /internal/v1/decision-memories/search`：结构化历史检索。
- `GET /internal/v1/decisions/{decisionId}/timeline`。
- `GET /internal/v1/strategy-memories/active?strategyId=&asOf=`。
- `POST /internal/v1/strategy-memories/{id}/approve`：治理命令，不开放给Agent身份。
- `POST /internal/v1/memories/{id}/quarantine`：人工隔离污染Memory。

所有查询必须带`decisionAsOf`、调用Agent身份和Scope。不能用服务端当前时间隐式替代决策时间。

### 13.2 订阅事件

- `stock.quant.daily-analysis.published.v1`。
- `stock.news.financial-event.published.v1`。
- `stock.monitor.market-anomaly.detected.v1`。
- `stock.regime.market-regime.changed.v1`。
- `stock.portfolio.snapshot.changed.v1`。
- `stock.agent.assessment.completed.v1`。
- `stock.decision.proposal.created.v1`。
- `stock.decision.risk-review.completed.v1`。
- `stock.risk.evaluation.completed.v1`。
- `stock.decision.approval.completed.v1`。
- `stock.execution.fill.recorded.v1`。

### 13.3 新增事件

- `stock.decision.outcome.evaluated.v1`：确定性结果评估完成。
- `stock.memory.decision-projection.updated.v1`：只读决策Memory投影更新。
- `stock.memory.strategy-memory.published.v1`：批准的StrategyMemory版本发布。
- `stock.memory.entry.quarantined.v1`：污染或错误Memory被隔离。

事件使用Outbox/Inbox，重复投递不能生成重复Memory版本。

## 14. Context Manifest与审计

每次Agent运行保存：

```ts
interface ContextManifest {
  contextManifestId: string;
  agentRunId: string;
  agentId: string;
  decisionAsOf: string;
  memoryPolicyVersion: string;

  selectedSnapshotRefs: SnapshotRef[];
  selectedEvidenceIds: string[];
  selectedMemoryIds: string[];
  excludedMemoryCountsByReason: Record<string, number>;

  tokenEstimate: number;
  contextHash: string;
  builtAt: string;
}
```

至少记录以下排除原因：

- `FUTURE_AVAILABLE_AT`。
- `EXPIRED`。
- `SUPERSEDED`。
- `QUARANTINED`。
- `SCOPE_MISMATCH`。
- `PERMISSION_DENIED`。
- `LOW_RELEVANCE`。
- `TOKEN_BUDGET`。
- `UNRESOLVED_EVIDENCE`。

不得要求或保存模型隐藏思维链。保存结构化结论、引用、可审计说明和原始输出Artifact即可。

## 15. Memory写入和权限

| 操作 | 允许主体 |
|---|---|
| 写AgentRun、Context Manifest | 对应agent-service部署 |
| 写领域事实 | 对应DDD领域服务 |
| 生成Decision Memory投影 | 受控Projection Worker |
| 写Outcome数值 | 确定性Outcome Evaluator |
| 生成StrategyMemory草稿 | 研究任务或授权Agent |
| 批准/发布StrategyMemory | 人工治理角色 |
| Quarantine错误Memory | 管理员或治理角色 |
| 修改RiskPolicy | portfolio-risk授权角色；Memory组件无权操作 |

外部新闻、网页和研报只能作为不可信证据，不能直接创建ACTIVE StrategyMemory或改变MemoryPolicy。

## 16. 失效、纠错与遗忘

Memory不做无审计的物理覆盖：

- 新版本通过`supersedesMemoryId`替代旧版本。
- 事实错误标记`INVALIDATED`并关联纠错证据。
- 疑似Prompt注入、错误实体映射或污染内容标记`QUARANTINED`。
- 过期Memory保留审计但不进入正常检索。
- 删除受版权、隐私或数据许可约束的Artifact时，保留最小删除审计和Hash，不保留受限原文。

建议留存策略：

| 数据 | 推荐策略 |
|---|---|
| AgentRun结构化元数据 | 长期，与决策审计周期一致 |
| 完整模型输入输出Artifact | 分级加密，按合规和成本设置期限 |
| DecisionMemorySummary | 长期，可从原事件重建 |
| Redis缓存 | 分钟到小时 |
| 未采用候选StrategyMemory | 定期归档 |
| 已发布StrategyMemory | 永久保留版本与批准记录 |

具体期限必须通过ADR确定，不能把推荐值当成法律或数据许可结论。

## 17. 失败与降级

- 当前领域快照无法读取：返回`INSUFFICIENT_EVIDENCE`或阻塞，不用历史Memory替代当前事实。
- 历史Memory检索失败：允许在MemoryPolicy明确时不带历史继续，但必须标记`memoryDegraded=true`；高风险建议可配置为阻塞。
- Memory投影滞后：根据Lag阈值改读领域服务或阻塞，不能静默使用旧投影。
- pgvector不可用：退化为结构化检索，不影响事实读取。
- Artifact无法校验Hash：排除并告警。
- Context超过Token预算：执行确定性裁剪；仍超限时失败，不随机截断关键证据。
- 模型Provider切换：使用相同Context Manifest，生成新的modelRunId。

## 18. 安全风险与控制

| 风险 | 控制 |
|---|---|
| 未来数据泄漏 | availableAt先过滤、历史时钟、回放测试 |
| Memory投毒 | 来源许可、Schema、内容Hash、Quarantine、人工治理 |
| 确认偏差 | 检索反例、风险拒绝和相反结果，设置观点多样性 |
| 错误自我强化 | 单次Outcome不能自动形成ACTIVE经验 |
| Prompt膨胀 | 类型配额、Token预算、确定性压缩 |
| 跨组合泄漏 | portfolio/strategy Scope和RBAC |
| Provider锁定 | 不使用厂商会话作为事实来源 |
| 敏感信息泄漏 | Tool最小权限、Artifact加密、日志脱敏 |
| 旧PASS误用 | proposalVersion、validUntil和Context Hash绑定 |

## 19. 测试要求

### 19.1 单元测试

1. 时间过滤排除`availableAt > decisionAsOf`。
2. Scope过滤阻止跨Portfolio和跨Strategy读取。
3. SUPERSEDED、INVALIDATED和QUARANTINED不进入正常上下文。
4. 排序结果在相同输入和版本下确定一致。
5. Token裁剪不删除必要证据、版本和风险字段。
6. Context Hash对相同Manifest稳定。

### 19.2 集成与事件测试

1. 同一Outcome事件重复10次只生成一个Memory版本。
2. Outbox发布前进程崩溃，恢复后仍能更新投影。
3. Projection删除后可由事件重建并得到相同内容Hash。
4. Redis清空后长期Memory和业务状态不丢失。
5. Artifact Hash不匹配时Memory被排除并告警。

### 19.3 Agent测试

1. 主Agent没有历史Memory时仍能基于当前证据运行。
2. 历史检索降级必须出现在AgentRun审计中。
3. 历史失败案例和成功案例都能被召回，避免只检索支持当前观点的Memory。
4. 新闻中的恶意指令不能创建StrategyMemory或扩大Tool权限。
5. risk-review-agent不能读取主Agent隐藏思维链。
6. 模型切换时复用相同Context Manifest但产生新modelRunId。

### 19.4 历史回放测试

选择历史决策点`T`：

- Context中所有证据和Memory的`availableAt <= T`。
- 当时未发布的StrategyMemory版本不可见。
- 后续收益和人工复盘不出现在原决策上下文。
- 使用相同MemoryPolicy、Prompt、数据和模型Fixture时可重建相同Context Hash。

## 20. 监控指标

- Context构建耗时和失败率。
- 各Memory类型召回数量和排除数量。
- `FUTURE_AVAILABLE_AT`过滤数量。
- Memory Projection Lag。
- Context Token使用量和裁剪率。
- unresolvedEvidence数量。
- Artifact Hash失败数量。
- `memoryDegraded`运行数量。
- 不同Agent的历史Memory命中率。
- StrategyMemory被引用、人工否决和退役次数。
- 相似历史检索后的决策校准变化；只能用于评估，不能自动放宽风险。

## 21. 推荐实现顺序

### M0：无历史检索的安全基线

- 实现AgentRun、ModelRun、Context Manifest和Context Hash。
- Working Memory只包含当前不可变快照和证据。
- 禁用Provider长期Conversation。
- 完成时间、新鲜度和证据校验。

### M1：结构化情景记忆

- 建立Decision Timeline查询。
- 实现DecisionMemorySummary投影。
- 按portfolio/strategy/symbol进行结构化检索。
- 实现人工反馈、风险拒绝和失效论点Memory。

### M2：结果闭环

- 实现确定性DecisionOutcome评估。
- 建立5/20/60交易日等策略化窗口。
- 将Outcome事件接入Memory投影。
- 完成历史回放和未来数据泄漏测试。

### M3：受治理策略经验

- 建立StrategyMemory草稿、验证、批准、发布和退役状态机。
- 部署研究侧`strategy-learning-agent`，只允许读取已关闭Outcome窗口、生成StrategyMemory草稿和ResearchExperiment请求；无生产版本激活权限。
- 增加反例检索和观点多样性。
- 建立Playbook回放与人工管理页面。

### M4：规模化检索

- 只有结构化查询不足时引入pgvector。
- 部署可重建`agent-memory-projection`。
- 增加冷热分层、归档和更精细的留存策略。

M0应在阶段08实现Agent Kernel时完成；M1可以随阶段08～09完成；M2在人工成交闭环后实现；M3、M4不得阻塞第一版人工辅助系统上线。

## 22. 验收标准

- Agent容器重启不丢失长期Memory或业务事实。
- 不使用模型厂商Conversation作为唯一上下文来源。
- 每次AgentRun都有可重建的Context Manifest和Context Hash。
- 主Agent只能读取授权Portfolio、Strategy、Market和Symbol范围的Memory。
- 历史回放不存在未来数据和未来StrategyMemory泄漏。
- Redis和Memory Projection丢失不影响原始业务事实，并可以重建。
- DecisionMemory不能覆盖TradeProposal、RiskReview、RiskEvaluation、Approval或Fill原事实。
- 过期、失效、被替代和受污染Memory不会进入正常上下文。
- 历史经验不能自动修改Prompt、生产因子、RiskPolicy或交易权限。
- Memory组件降级、证据不足或Hash失败不会静默放行交易。
