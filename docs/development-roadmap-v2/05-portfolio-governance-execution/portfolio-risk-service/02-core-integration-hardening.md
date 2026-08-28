# Portfolio 05-02 核心能力、集成与强化

## 实施步骤

1. 实现成交入账、现金、费用、公司行动、估值和不可变PortfolioSnapshot。
2. 实现版本化RiskPolicy：单股、行业、总仓位、现金、换手、每日交易批次、回撤和暂停规则。
3. `evaluate(proposal, portfolioSnapshot, marketSnapshot, policy)`返回PASS/REJECT及逐条RuleResult。
4. 每日最多1～2批是硬上限；周交易1～2次只是指标；HOLD不计批次。
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

- 第3个交易批次、超仓、回撤、陈旧价格和全局暂停拒绝。
- RiskPolicy变化使旧RiskEvaluation失效。
- 市场数据超时、重复Fill事件和并发入账。

