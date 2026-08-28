# 08-03 主决策和风险复核Agent

## 目标

实现版本化TradeProposal生成和独立RiskReviewResult，确保模型建议不能直接进入执行。

## 实施步骤

### 1. 主决策输入包

```ts
interface DecisionEvidenceBundle {
  trigger: DecisionTrigger;
  quantSnapshotId: string;
  strategySnapshotIds: string[];
  ensembleStrategySnapshotId?: string;
  newsEventIds: string[];
  marketRegimeSnapshotId: string;
  anomalyEventIds: string[];
  portfolioSnapshotId: string;
  specialistAssessments: SpecialistAssessmentRef[];
  freshness: DataFreshness[];
}
```

ContextBuilder先确定性检查快照存在、版本一致和未过期；所有策略快照必须来自`ACTIVE` StrategyVersion，且其`asOf`、DataVersion、股票池版本和成本模型兼容。策略缺失或互相冲突不是自动买卖理由，应作为结构化证据进入HOLD或风险复核。

### 2. TradeProposal

```ts
const tradeProposalSchema = z.object({
  decisionId: z.string(),
  proposalVersion: z.number().int().positive(),
  portfolioId: z.string(),
  symbol: z.string(),
  action: z.enum(['BUY', 'SELL', 'HOLD']),
  targetWeight: z.number().min(0).max(1).optional(),
  confidence: z.number().min(0).max(1),
  reasons: z.array(z.string()).min(1),
  risks: z.array(z.string()),
  assumptions: z.array(z.string()),
  evidenceIds: z.array(z.string()).min(1),
  strategySnapshotIds: z.array(z.string()),
  ensembleStrategySnapshotId: z.string().optional(),
  validFrom: z.string().datetime({ offset: true }),
  expiresAt: z.string().datetime({ offset: true }),
});
```

HOLD也保存，但不进入交易审批和批次计数。

### 3. 不可变风险证据包

将Proposal、ProvenanceRef、快照引用、组合风险和无法解析证据生成`contentHash`。复核中发现新证据时创建新packet和proposalVersion。

### 4. 风险复核多阶段

```text
Validate evidence packet
  -> Independent assessment without main conclusion
  -> Compare proposal claims and evidence
  -> Build counter-thesis/downside scenarios
  -> Synthesize structured verdict
```

输出四种verdict：PASS、PASS_WITH_CONDITIONS、REJECT、INSUFFICIENT_EVIDENCE。

风险复核必须确定性检查策略版本状态、快照新鲜度、换手率、交易成本、滑点、容量、市场状态适配和NO_TRADE基线。LLM负责质疑解释与反方情景，不能替代这些硬校验。

### 5. 跨模型策略

- 主决策默认DeepSeek。
- 风险复核默认Claude。
- 高风险/大仓位/CRITICAL事件可运行第二复核。
- 冲突按`REJECT > INSUFFICIENT_EVIDENCE > PASS_WITH_CONDITIONS > PASS`合并，并要求人工关注。

### 6. 防止无限修订

`PASS_WITH_CONDITIONS`只能请求修订，不直接改Proposal。`maxRiskReviewRevisions`默认2，超过后REVIEW_BLOCKED。

## 测试案例

1. 缺失evidenceId产生INSUFFICIENT_EVIDENCE。
2. PASS仍不能直接创建OrderIntent。
3. 条件通过生成新proposalVersion。
4. 两模型PASS/REJECT合并为REJECT。
5. 旧EvidencePacket Hash不能复核新Proposal。
6. 连续第三次修订进入REVIEW_BLOCKED。
7. 所有风险Provider失败时BUY不放行。
8. TradeProposal引用`CANDIDATE`策略快照时返回INSUFFICIENT_EVIDENCE或REJECT。
9. 策略集合建议买入但NO_TRADE基线和成本后收益不支持时，不得默认PASS。
10. StrategyVersion激活状态、成本模型或快照内容在复核期间变化时，旧EvidencePacket失效。

## 完成条件

- 主建议和风险复核均为不可变对象。
- 复核模型与主模型可独立配置。
- 所有失败和分歧路径结构化、可测试、可审计。
