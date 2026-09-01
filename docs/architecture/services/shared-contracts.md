# shared-contracts

## 1. 定位

定义所有服务共同使用的稳定数据契约、错误结构、版本规则和所有权。它不是微服务，而是契约源。

推荐在主工程建立：

    packages/contracts
    contracts/openapi
    contracts/asyncapi
    contracts/schemas

OpenAPI和JSON Schema作为跨语言事实来源，生成TypeScript和Python类型。手写类型只能作为生成器输入或领域内部类型，不能在多个服务复制维护。

## 2. 通用事件信封

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

消费者必须用Inbox按`eventId + consumerName`幂等；eventVersion用于Schema演进，aggregateVersion用于同一业务对象的顺序检查。完整发布、重放和Subject规则见[event-driven-architecture](./event-driven-architecture.md)。

## 3. 通用请求上下文

    interface RequestContext {
      requestId: string;
      correlationId: string;
      actorId?: string;
      sourceService: string;
      requestedAt: string;
    }

内部服务不得信任客户端传入的actor权限，只能传递已验证身份声明。

## 4. 数据新鲜度和来源

    interface DataFreshness {
      asOf: string;
      availableAt: string;
      latestExpectedAt?: string;
      isStale: boolean;
      staleReason?: string;
    }

    interface ProvenanceRef {
      evidenceId: string;
      source: string;
      sourceRecordId?: string;
      artifactUri?: string;
      dataVersion: string;
      contentHash?: string;
    }

所有进入投资决策的数据必须有DataFreshness和至少一个ProvenanceRef或不可变快照引用。

## 5. 异步任务契约

    interface JobAccepted {
      runId: string;
      status: 'QUEUED';
      submittedAt: string;
      idempotencyKey: string;
    }

    type JobStatus =
      | 'QUEUED'
      | 'RUNNING'
      | 'SUCCEEDED'
      | 'FAILED'
      | 'CANCELLED';

    interface JobResultRef {
      runId: string;
      status: JobStatus;
      progress?: number;
      resultRef?: string;
      error?: ErrorEnvelope;
      updatedAt: string;
    }

## 6. 错误契约

    interface ErrorEnvelope {
      code: string;
      message: string;
      retryable: boolean;
      category:
        | 'VALIDATION'
        | 'NOT_FOUND'
        | 'CONFLICT'
        | 'DATA_QUALITY'
        | 'DEPENDENCY'
        | 'RATE_LIMIT'
        | 'TIMEOUT'
        | 'INTERNAL';
      correlationId: string;
      details?: Record<string, unknown>;
    }

message面向调用方可读但不得包含密钥、SQL、模型原始私密输入或供应商凭据。

## 7. MarketDataEvent和MarketBar

MarketDataEvent用于Adapter到监控Worker的内部流：

- symbol、exchange、eventTime、receivedAt。
- eventKind：TICK、QUOTE、TRADE、STATUS。
- price、volume、amount和可选盘口字段。
- tradingStatus、limitStatus。
- source、sourceSequence、dataVersion。

MarketBar包含：

- symbol、timeframe、windowStart、windowEnd。
- open、high、low、close、volume、amount。
- previousClose、vwap。
- adjustment、tradingStatus。
- source、dataVersion、freshness。

## 8. MarketAnomalyEvent

    interface MarketAnomalyEvent {
      eventId: string;
      eventVersion: number;
      symbol: string;
      detectedAt: string;
      windowStart: string;
      windowEnd: string;
      type: string;
      severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
      ruleHits: Array<{
        ruleId: string;
        ruleVersion: string;
        observedValue?: number;
        threshold?: number;
      }>;
      observedFeatures: Record<string, number | string | null>;
      marketDataVersion: string;
      watchlistVersion: string;
      detectorVersion: string;
      riverModelVersion?: string;
      portfolioSnapshotId?: string;
      freshness: DataFreshness;
      evidenceIds: string[];
    }

## 9. 量化分析快照

DailyAnalysisSnapshot必须包含：

- snapshotId、runId、asOfDate、dataCutoffAt、publishedAt。
- status、isStale。
- universeVersion、factorSetVersion、modelVersion、dataVersion。
- selectedStocks、heldStocks。
- provenance和qualitySummary。

StockAnalysis必须包含symbol、score、rank、percentile、signal、factorContributions、riskFlags和evidenceIds。

### 9.1 日频策略快照

DailyStrategySnapshot必须包含：

- snapshotId、runId、strategyId、strategyVersion、parameterSetId。
- asOfDate、dataCutoffAt、publishedAt、validUntil。
- dataVersion、universeVersion、factorSetVersion、modelVersion和costModelVersion。
- portfolioSnapshotId和可选marketRegimeSnapshotId。
- rebalanceDecision：NO_REBALANCE、REBALANCE_CANDIDATE或RISK_REDUCTION。
- currentWeights、targetWeights和proposedChanges。
- expectedTurnover、estimatedTransactionCost和estimatedSlippage。
- evaluationSummaryRef、reasonCodes、warnings、evidenceIds、freshness和contentHash。

策略快照是确定性候选组合，不是TradeProposal、Approval或OrderIntent。只有ACTIVE StrategyVersion可以发布生产快照。

## 10. 市场状态快照

MarketRegimeSnapshot必须包含：

- snapshotId、asOf、frequency、publishedAt。
- overallRegime：RISK_ON、NEUTRAL、RISK_OFF、STRESS。
- regimeConfidence、previousRegime、changeDetected、transitionReason。
- trend、breadth、volatility、liquidity维度分数。
- benchmarkStates和industryStates。
- dataVersion、featureVersion、regimeDefinitionVersion。
- riverModelVersion或researchModelVersion。
- freshness、qualitySummary和evidenceIds。

MarketRegimeAssessment必须包含：

- regimeSnapshotId、interpretation。
- suggestedRiskBias：NORMAL、CONSERVATIVE、DEFENSIVE。
- allowNewPositions建议值。
- preferredIndustries、avoidedIndustries。
- portfolioImplications、risks、evidenceIds、validUntil、agentRunId。

Assessment属于Agent建议，不能直接修改RiskPolicy或订单。

## 11. 新闻契约

NewsEventCandidate包含：

- candidateId、newsIds、clusterVersion。
- representativeTitle、contentRefs。
- candidateSymbols和实体关联置信度。
- sourceSummary、publishedAtRange、freshness。

FinancialNewsEvent包含：

- eventId、candidateId、newsIds、eventType。
- affectedSymbols、relevance、impactDirection、impactMagnitude、impactHorizon。
- noveltyScore、sourceReliability、confidence。
- summary、reasoning、evidenceIds。
- analyzedAt、provider、modelId、promptVersion。

## 12. Agent输出契约

MarketMonitorAssessment：

- anomalyEventId。
- assessment：IGNORE、WATCH、REASSESS、RISK_ESCALATION。
- explanation、risks、evidenceIds。
- confidence、validUntil。
- agentRunId、modelRunMetadata。

TradeProposal是组合级建议，不是单只股票订单：

```ts
interface RebalanceLeg {
  legId: string;
  symbol: string;
  exchange: string;
  side: 'BUY' | 'SELL';
  targetWeight?: string;
  quantity?: string;
  reasonCodes: string[];
}

interface TradeProposal {
  decisionId: string;
  proposalVersion: number;
  portfolioId: string;
  strategyId: string;
  proposalAction: 'HOLD' | 'REBALANCE';
  rebalanceReason?:
    | 'DAILY_TARGET'
    | 'INTRADAY_RISK_REDUCTION'
    | 'EXECUTION_CORRECTION';
  targetPortfolioVersion?: string;
  legs: RebalanceLeg[];
  validFrom: string;
  expiresAt: string;
  confidence: number;
  reasons: string[];
  risks: string[];
  assumptions: string[];
  evidenceIds: string[];
  quantSnapshotId: string;
  newsSnapshotId?: string;
  portfolioSnapshotId: string;
  strategySnapshotIds: string[];
  ensembleStrategySnapshotId?: string;
  marketRegimeSnapshotId?: string;
  anomalyEventIds: string[];
  agentRunId: string;
}
```

`HOLD`的`legs`必须为空且不进入审批或预算预留；`REBALANCE`必须至少包含一个Leg。每个策略快照引用必须能解析到当时为ACTIVE的不可变StrategyVersion和评估记录。风险复核通过decisionId和proposalVersion关联，不回写并修改原TradeProposal。

## 13. 风险复核契约

    interface RiskReviewEvidencePacket {
      packetId: string;
      decisionId: string;
      proposalVersion: number;
      generatedAt: string;
      proposal: TradeProposal;
      evidenceRefs: ProvenanceRef[];
      snapshotRefs: Array<{
        snapshotType: string;
        snapshotId: string;
        dataVersion: string;
        asOf: string;
        freshness: DataFreshness;
      }>;
      portfolioSnapshotId: string;
      unresolvedEvidenceIds: string[];
      contentHash: string;
    }

    interface RiskReviewResult {
      reviewId: string;
      decisionId: string;
      proposalVersion: number;
      evidencePacketId: string;
      evidencePacketHash: string;
      reviewedAt: string;
      validUntil: string;
      verdict:
        | 'PASS'
        | 'PASS_WITH_CONDITIONS'
        | 'REJECT'
        | 'INSUFFICIENT_EVIDENCE';
      riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
      confidence: number;
      summary: string;
      verifiedClaims: Array<{
        claim: string;
        evidenceIds: string[];
      }>;
      unsupportedClaims: string[];
      conflictingEvidence: string[];
      missingEvidence: string[];
      downsideScenarios: Array<{
        scenario: string;
        probability: 'LOW' | 'MEDIUM' | 'HIGH';
        expectedImpact: string;
        evidenceIds: string[];
      }>;
      recommendedChanges?: {
        maxPositionWeight?: number;
        entryCondition?: string;
        exitCondition?: string;
        observationUntil?: string;
      };
      reasonCodes: string[];
      evidenceIds: string[];
      reviewerAgentRunIds: string[];
      requiresHumanAttention: boolean;
      freshness: DataFreshness;
    }

约束：

- RiskReviewResult是独立不可变对象，不修改TradeProposal。
- RiskReviewEvidencePacket按contentHash不可变；复核过程中出现的新证据必须生成新packet和新proposalVersion。
- PASS只允许进入确定性硬风控，不表示批准交易。
- PASS_WITH_CONDITIONS必须形成新的proposalVersion并重新复核。
- INSUFFICIENT_EVIDENCE不能被调用方解释为PASS。
- recommendedChanges是语义建议，不得覆盖RiskPolicy或RiskEvaluation给出的合法上限。
- 多模型复核时reviewerAgentRunIds记录所有参与运行，最终结果记录确定性合并后的verdict。

## 14. 风控和执行契约

RiskEvaluation针对整个组合级TradeProposal计算，包含：

- evaluationId、decisionId、proposalVersion、portfolioSnapshotId、targetPortfolioVersion。
- riskPolicyVersion、evaluatedAt、expiresAt。
- result：PASS、REJECT、REQUIRES_REVIEW。
- violatedRules、legResults、beforeMetrics、projectedAfterMetrics。
- maximumAllowedQuantities或maximumAllowedWeights。

DecisionBudgetReservation包含：

- reservationId、portfolioId、tradingDate、sequence、decisionId、proposalVersion。
- maxDailyRebalanceBatches、riskPolicyVersion。
- status：RESERVED、DISPATCHING、CONSUMED、RELEASED、EXPIRED。
- reservedAt、expiresAt、consumedAt、releasedAt、idempotencyKey。

DecisionBudgetSnapshot包含：

- budgetSnapshotId、portfolioId、tradingDate、asOf。
- maxDailyRebalanceBatches、reservedBatches、consumedBatches和remainingBatches。
- allowedSecondBatchReasons、riskPolicyVersion和contentHash。

DecisionBudgetSnapshot用于组合级RiskEvaluation的当时输入，但不承担并发放行；最终额度必须由decision-governance-service原子预留。`maxDailyRebalanceBatches`、`allowedSecondBatchReasons`和`riskPolicyVersion`只能来自portfolio-risk-service发布的有效RiskPolicy结果，Governance只拥有用量、预留和状态，不得自行修改政策值。

RebalanceBatch包含：

- rebalanceBatchId、portfolioId、tradingDate、sequence和reason。
- decisionId、proposalVersion、approvalId、riskEvaluationId、budgetReservationId。
- targetPortfolioVersion、orderIntentIds、acceptedAt、contentHash和idempotencyKey。
- status：ACCEPTED、IN_PROGRESS、PARTIALLY_FILLED、COMPLETED、CANCELLED、EXPIRED、FAILED、UNKNOWN。

OrderIntent包含：

- orderIntentId、rebalanceBatchId、legId、decisionId、proposalVersion、riskEvaluationId。
- accountId、symbol、side、quantity、orderType、limitPrice。
- validUntil、status、idempotencyKey。

同一`rebalanceBatchId`下的多个OrderIntent、部分成交、撤单重报和相同幂等键重试只计一个调仓批次。调用执行前预留转为DISPATCHING，执行服务原子接受RebalanceBatch后转为CONSUMED；只有执行服务明确确认未接受批次时才允许RELEASED。超时或响应丢失时保持DISPATCHING并按幂等键查询，不得推断失败。

Fill包含：

- fillId、orderId、brokerExecutionId。
- symbol、side、quantity、price、fees、executedAt。
- source、receivedAt。

## 15. 事实来源

| 业务对象 | 唯一写入方 |
|---|---|
| Security、MarketBar、DataVersion | market-data-service |
| MarketAnomalyEvent | market-monitor-service |
| MarketRegimeSnapshot | market-regime-service |
| Factor、Model、Strategy、DailyAnalysisSnapshot、DailyStrategySnapshot | quant-research-service |
| ResearchExperiment、CandidateArtifact、PromotionRequest | research-automation-service |
| NewsItem、FinancialNewsEvent | news-intelligence-service |
| AgentRun、ModelRun、AgentAssessment | 对应agent-service部署 |
| RiskReviewResult与Proposal关联 | decision-governance-service；模型运行明细由risk-review-agent拥有 |
| PortfolioSnapshot、RiskEvaluation | portfolio-risk-service |
| TradeProposal、Approval、DecisionBudgetReservation、DecisionBudgetSnapshot | decision-governance-service |
| RebalanceBatch、OrderIntent、Order、Fill | trade-execution-service |
| Workflow状态 | Temporal |

其他服务只能通过API、事件或Artifact读取，不能跨Schema直接写入。

## 16. Schema演进

- 新增可选字段属于兼容变更。
- 删除、重命名、改变语义或收窄枚举属于破坏性变更。
- 破坏性事件变更发布新的Subject Major版本，同时支持新旧Consumer并行迁移。
- API通过/v1、/v2版本化；数据库内部版本不能代替API版本。
- Schema变更必须有Consumer Contract Test。

## 17. 金额和数值

- 金额、价格、数量和费率使用Decimal语义，JSON使用字符串或明确精度协议。
- 百分比统一定义为0～1还是0～100，项目内只能选一种；推荐0～1。
- 时间使用ISO 8601带时区。
- 股票标识采用symbol + exchange，不依赖展示名称。
- 所有排名注明股票池版本和方向。

## 18. 通用运维端点

每个HTTP服务至少提供：

- GET /health/live
- GET /health/ready
- GET /metrics
- GET /internal/v1/version

version结果包含serviceVersion、gitCommit、buildTime、contractVersion和启用的关键配置版本。
