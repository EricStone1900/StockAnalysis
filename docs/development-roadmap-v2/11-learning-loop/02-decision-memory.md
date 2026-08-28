# 11-02 Decision Memory投影与检索

## 实施步骤

1. 在agent-service先实现结构化DecisionMemoryProjection Worker；数据量扩大后才考虑独立部署。
2. 投影关联Proposal、风险复核、硬风控、人工反馈、Fill、Outcome、Regime和原证据引用。
3. 检索顺序固定为权限Scope、availableAt、状态/有效期、结构化过滤、相关性排序、Token裁剪。
4. 保存候选、排除原因、最终选择、MemoryPolicyVersion和Context Hash。
5. 投影可删除并由事件/API重建；它不是第二业务事实源。
6. 第一版使用PostgreSQL结构化查询，确有需要后再引入pgvector。

```ts
interface DecisionMemorySummary {
  memoryId: string;
  portfolioId: string;
  strategyId: string;
  symbol: string;
  decisionAsOf: string;
  availableAt: string;
  outcomeRefs: string[];
  evidenceIds: string[];
  status: 'ACTIVE' | 'SUPERSEDED' | 'INVALIDATED' | 'QUARANTINED';
}
```

## 测试

- 未来、跨Portfolio、失效、污染和Hash错误Memory被排除。
- 成功与失败/反例都有召回配额，防止确认偏差。
- 删除投影可重建相同contentHash。

