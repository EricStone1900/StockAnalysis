# Portfolio 05-02 核心能力、集成与强化

## 实施步骤

1. 实现成交入账、现金、费用、公司行动、估值和不可变PortfolioSnapshot。
2. 实现版本化RiskPolicy：单股、行业、总仓位、现金、换手、`maxDailyRebalanceBatches`、`allowedSecondBatchReasons`、回撤和暂停规则。
3. `evaluate(proposal, portfolioSnapshot, decisionBudgetSnapshot, marketSnapshot, policy)`一次评估完整Leg集合，返回PASS/REJECT、逐Leg结果和组合before/projectedAfter。
4. 每日允许0～2批是硬上限；周交易1～2次只是指标；HOLD不计批次。最终并发预留由decision-governance执行。
5. 接market-data生成Client；故障时明确STALE或失败关闭。
6. 发布PortfolioSnapshot和RiskEvaluation事件，写入Outbox。

```ts
interface RiskRuleResult {
  ruleId: string;
  policyVersion: string;
  verdict: 'PASS' | 'REJECT';
  actual: string;
  limit: string;
  reasonCode: string;
}
```

## 强化测试

- 第3个组合调仓批次、非法第二批reason、超仓、回撤、陈旧价格和全局暂停拒绝。
- RiskPolicy变化使旧RiskEvaluation失效。
- 市场数据超时、重复Fill事件和并发入账。
- 任一Leg变化使旧评估失效；全部Leg单独合法但组合后超限时整体拒绝。
