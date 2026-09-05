# 阶段10测试计划

- Temporal Unit、Time Skipping、Replay和Worker升级测试。
- DailyQuant、News、Monitor、Regime、Decision和Approval全部分支。
- Agent/Provider失败、服务超时、NATS停止和数据库恢复。
- Proposal修改、风险修订上限、旧结果和持仓变化。
- 人工批准/拒绝/刷新/超时和RBAC。
- DecisionBudgetReservation、RebalanceBatch、OrderIntent[]、Fill[]、Portfolio和Reconciliation完整链路。
- 重复Signal、重复命令、重复事件、重复Fill和浏览器重试。
- 每日0～2个组合调仓批次、第二批reason、长期HOLD、全局暂停和只观察模式。
- 多Leg原子接受、并发预算竞争、接受前释放、接受后不释放和同批不重复计数。
- 纯日频、盘中延迟、风险减仓、最多两批和NO_REBALANCE五类联合历史回放。
- PIT、A股T+1、涨跌停、停牌、费用、滑点、部分成交和迟到分钟数据。

必须完成历史Workflow Replay、日频与盘中联合回放和一次端到端灾难恢复演练。

## 当前本机验证记录（Mac）

- Temporal Activity 契约、DailyQuant、NewsAnalysis、MarketMonitor、MarketRegime、InvestmentDecision、HumanApproval 和 RebalanceExecution 工作流切片已实现。
- 已覆盖 Activity 幂等、Artifact 引用、门控阻塞、HOLD 短路、风险复核、硬风控、人工 Signal、预算释放、UNKNOWN 成交和第二批限制。
- 工作流服务 ESLint、TypeScript 和 `git diff --check` 通过；当前单元测试 29 项通过。
- 可靠性策略已覆盖全局暂停、只观察、Agent 禁用、执行禁用、重试上限和阻塞运维动作。
- 尚待 Ubuntu/Temporal 人工验收：真实 Worker、Schedule、Signal、重启恢复、NATS/数据库故障和人工交易 E2E。
