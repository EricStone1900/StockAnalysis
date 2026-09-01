# ADR-010：组合调仓批次与每日上限

- 状态：ACCEPTED
- 生效日期：2026-08-31
- 决策人：项目负责人
- 影响阶段：03、05、09、10、12

## 背景

系统使用日频因子、模型和策略生成目标组合，但交易日内可以根据执行条件、重大风险事件或首次执行偏差进行有限调整。业务约束是“每天最多调仓1～2次，允许不调仓”，不是“每天最多成交1～2只股票”或“每天必须交易”。

原设计使用`TradeProposal.symbol`和`maxDailyTradeBatches`表达该约束，无法明确表示一次组合调仓同时包含多只股票，也没有冻结部分成交、撤单重报、失败释放和并发占用的计数语义。

## 决策

1. 每个组合、每个A股交易日允许`0～2`个组合级`RebalanceBatch`，正式配置名为`maxDailyRebalanceBatches`，默认值为`2`。
2. `DAILY`表示每天评估，不表示每天调仓；`NO_REBALANCE`和`HOLD`均为正常结果，不占用调仓批次。
3. 一个`TradeProposal`描述一个组合级建议：顶层动作为`HOLD`或`REBALANCE`；`REBALANCE`通过多个`RebalanceLeg`表达各证券的买卖方向、目标权重或建议数量。
4. `decision-governance-service`拥有`DecisionBudgetReservation`，在批准结果送往执行前以`portfolioId + tradingDate`为并发隔离键原子预留额度。
5. `trade-execution-service`拥有`RebalanceBatch`。它原子接受已批准建议、预算预留和有效RiskEvaluation后，创建一个批次及其多个`OrderIntent`，并回写接受结果。
6. 调用执行前，预算预留从`RESERVED`转为`DISPATCHING`。执行服务成功接受批次时转为`CONSUMED`；执行服务明确确认未创建任何批次或`READY` OrderIntent时才允许`RELEASED`。请求超时、响应丢失或接受结果不确定时保持`DISPATCHING`，必须按稳定幂等键查询执行服务，禁止猜测失败后释放或创建新批次。
7. 批次一经接受，后续部分成交、撤销、过期、人工重报或同一幂等键重试均不释放且不重复计数。
8. 同一`rebalanceBatchId`下的多个证券、多个OrderIntent和多个Fill只算一次调仓。目标组合、建议内容或`rebalanceBatchId`变化才形成新的调仓批次。
9. 第一批通常来自`DAILY_TARGET`。第二批默认只允许`INTRADAY_RISK_REDUCTION`或`EXECUTION_CORRECTION`；使用第二批重新追逐Alpha必须由新的版本化策略和RiskPolicy明确允许，并先通过日频与盘中联合历史回放及Shadow门禁。
10. A股T+1、涨跌停、停牌、最小交易单位、费用、滑点和部分成交对每个Leg分别校验，但RiskEvaluation必须基于全部Leg计算组合`projectedAfter`，不能逐票通过后再假设组合整体安全。

## 所有权与流程

```text
DailyStrategySnapshot / 盘中重大事件
  -> 组合级TradeProposal(HOLD | REBALANCE, legs[])
  -> RiskReviewResult
  -> portfolio-risk组合级RiskEvaluation
  -> Human Approval
  -> decision-governance原子预留DecisionBudgetReservation
  -> trade-execution原子接受RebalanceBatch并创建OrderIntent[]
  -> 预留转已消耗
  -> Fill[] / Reconciliation
```

`quant-research-service`只发布候选目标组合和`proposedChanges`，不创建`TradeProposal`、预算预留、`RebalanceBatch`或订单。`market-monitor-service`只发布异常事实，不创建调仓。

“原子”仅指单个服务自己的数据库事务：Governance原子预留预算，Execution原子创建批次和全部Intent。跨服务不使用分布式事务；通过稳定幂等键、`DISPATCHING`中间态、同步查询、Outbox事件和恢复任务收敛。

## 联合验证

分钟异常规则自身在阶段06使用生产同代码进行历史回放；日频目标组合、盘中触发、批次预算、A股成交限制和成本后的联合收益回放在阶段10完成。阶段12继续用Paper和Shadow比较：

- 纯日频固定窗口调仓；
- 日频目标加盘中延迟执行；
- 日频目标加一次风险减仓；
- 每日最多两批的完整策略；
- `NO_REBALANCE`基准。

联合验证没有证明成本后改善时，盘中事件只能触发观察、人工复核或延迟执行，不能默认消耗第二批进行新Alpha调仓。

## 兼容性、迁移与回滚

- 阶段05共享契约尚未冻结，因此直接采用组合级`TradeProposal`和`maxDailyRebalanceBatches`，不保留新的生产`maxDailyTradeBatches`字段。
- 已有文档中的`maxDailyTradeBatches`视为旧候选名，应在进入阶段05前完成替换。
- `OrderIntent`继续保持单证券语义，但必须增加`rebalanceBatchId`和`legId`。
- 若后续需要回滚为单证券建议，可使用只含一个Leg的`TradeProposal`，无需改变批次和预算语义。

## 后果

- 优点：调仓次数、委托数和成交数不再混淆；多股票目标组合可以一次审批、一次风控、一次占用预算并保持审计完整。
- 代价：治理、风控和执行必须支持组合级原子校验、预算预留和父子状态聚合；阶段10必须新增联合历史回放。
- 禁止事项：不得用拆分多个decisionId、OrderIntent或券商委托规避每日批次上限。
