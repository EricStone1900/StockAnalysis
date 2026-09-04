# Portfolio 05-02 核心能力、集成与强化

## 当前实现

已完成成交入账的领域最小切片：`BUY`、`SELL` 与独立 `FEE` 流水均不可变，使用最多 8 位小数的定点 Decimal 运算计算现金和持仓；卖超可用持仓会拒绝。成交必须以既有期初快照为基础，并继续使用 `expectedVersion` 与幂等键。

已将确认成交以单一 PostgreSQL 事务写入：成交、可选费用、下一版快照与快照幂等记录要么全部提交、要么全部回滚；内部接口为`POST /internal/v1/reconciliation/apply-confirmed-fill`。现金分红同样以事务写入`DIVIDEND`流水和快照，接口为`POST /internal/v1/reconciliation/apply-cash-dividend`。拆股、送股等改变持仓数量的公司行动、行情估值、风险策略、市场数据生成 Client、Outbox 事件仍属于本阶段后续步骤。

拆股/送股比例调整已支持`numerator/denominator`正整数比例并生成`SPLIT`流水：只调整目标证券的数量和可用数量，不改变现金；同样以 PostgreSQL 事务写入流水、快照与幂等记录，接口为`POST /internal/v1/reconciliation/apply-stock-split`。

估值领域切片已支持以`marketDataVersion`、价格`asOf`和持仓快照版本计算持仓市值与总权益；任一持仓缺价、价格非正或超过最大允许陈旧时间均失败关闭。估值结果已落入不可变`portfolio_valuations`，以快照、行情版本和时间唯一约束防止重复。市场数据生成 Client 仍等待上游价格契约补齐。

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
