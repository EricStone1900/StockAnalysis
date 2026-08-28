# 09-03 风险复核Agent

## 实施步骤

1. 构建不可变RiskReviewEvidencePacket，包含ProposalVersion、快照、证据、Portfolio风险和contentHash。
2. 复核阶段固定为：独立阅读证据、验证主张、对照Proposal、构建反方/下行情景、输出结论。
3. 输出PASS、PASS_WITH_CONDITIONS、REJECT或INSUFFICIENT_EVIDENCE。
4. 默认使用与主Agent不同的Claude Profile；高风险可运行第二Reviewer并确定性合并。
5. 检查策略状态、新鲜度、成本、滑点、换手、容量、Regime适配、NO_TRADE基线和证据反例。
6. 风险Agent只给语义复核；最终仓位、批次和回撤由portfolio-risk确定性执行。

```ts
interface RiskReviewResult {
  decisionId: string;
  proposalVersion: number;
  evidencePacketHash: string;
  verdict: 'PASS' | 'PASS_WITH_CONDITIONS' | 'REJECT' | 'INSUFFICIENT_EVIDENCE';
  riskLevel: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  counterThesis: string[];
  evidenceIds: string[];
  validUntil: string;
}
```

## 测试

旧Packet、证据缺失、模型冲突、所有Provider失败、条件修订和主建议确认偏差。

