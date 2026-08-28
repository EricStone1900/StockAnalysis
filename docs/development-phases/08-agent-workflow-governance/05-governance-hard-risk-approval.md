# 08-05 决策治理、硬风控和人工审批

## 目标

在独立`decision-governance-service`实现建议状态机、频率预算和人工审批，在独立`portfolio-risk-service`实现RiskPolicy与预交易硬风控，形成Agent与执行之间不可绕过的双服务边界。

## 实施步骤

### 1. 状态机

```ts
const transitions: Record<DecisionStatus, readonly DecisionStatus[]> = {
  DRAFT: ['AGENT_REVIEWED', 'CANCELLED'],
  AGENT_REVIEWED: ['RISK_REVIEW_PENDING'],
  RISK_REVIEW_PENDING: ['RISK_REVIEWED', 'REVISION_REQUIRED', 'REJECTED', 'REVIEW_BLOCKED'],
  RISK_REVIEWED: ['HARD_RISK_PASSED', 'REJECTED'],
  HARD_RISK_PASSED: ['PENDING_HUMAN_APPROVAL'],
  PENDING_HUMAN_APPROVAL: ['APPROVED', 'REJECTED', 'EXPIRED', 'REVISION_REQUIRED'],
  // 其余状态显式列出
};
```

platform-api Controller只能转发鉴权命令；decision-governance领域层验证状态转换、乐观锁并写Outbox和审计。

### 2. RiskPolicy

第一版至少包含：

- maxDailyTradeBatches。
- maxSinglePositionWeight、maxIndustryWeight、maxTotalExposure。
- maxDailyTurnover、minimumCashRatio。
- maxPortfolioDrawdown、maxSingleTradeLoss。
- minimumHoldingDays、cooldownMinutes。
- minimumDataFreshnessMinutes。

### 3. 规则接口

```ts
interface RiskRule {
  ruleId: string;
  version: string;
  evaluate(context: PreTradeContext): RiskRuleResult;
}
```

结果包括before/projectedAfter、违反原因和允许最大仓位。规则在portfolio-risk-service按稳定顺序执行并全部记录，不只返回第一条失败。

### 4. 预交易评估

绑定decisionId、proposalVersion、portfolioSnapshotId和riskPolicyVersion。任一版本变化使旧PASS失效。

```ts
if (context.executedTradeBatchesToday >= policy.maxDailyTradeBatches) {
  violations.push({ ruleId: 'MAX_DAILY_TRADE_BATCHES', status: 'REJECT' });
}
```

每周目标不进入硬规则。

### 5. 风险复核关联

只有当前proposalVersion的RiskReviewResult为PASS才能调用硬风控。迟到旧结果只保存审计，不推动状态。

### 6. 人工审批

审批前重新检查过期、持仓版本、RiskPolicy、行情偏差和当日批次。modify创建新proposalVersion，重新风险复核和硬风控。

### 7. 全局控制

实现`OBSERVE_ONLY`、`PAUSED`和未来`REDUCE_ONLY`。控制状态在模型和执行之外生效。

## 测试案例

1. 风险复核PASS但单股仓位超限时硬风控REJECT。
2. 第3个交易批次被拒绝。
3. 连续数周无交易不产生错误。
4. 人工修改仓位后旧RiskEvaluation失效。
5. 重复approve命令只产生一次状态变化。
6. RiskPolicy变更后旧PASS不能执行。
7. 风控模块异常时BUY默认拒绝。
8. OBSERVE_ONLY下可以生成HOLD/报告但不能创建可执行指令。

## 完成条件

- 风险规则同输入同版本结果一致。
- 所有状态变化通过命令和乐观锁。
- Agent输出无法直接访问execution模块。
- governance和portfolio-risk分别拥有独立Database/User，任何一方不得直接写另一方表。
- 人工审批页面能显示证据、风险复核和硬规则结果。
