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
