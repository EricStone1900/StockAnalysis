# 10-02 领域工作流

## 实现顺序

1. `DailyQuantAnalysisWorkflow`：等待DataVersion，运行量化和ACTIVE策略，发布快照。
2. `NewsAnalysisWorkflow`：采集、Candidate、新闻Agent和事件回写。
3. `MarketMonitorWorkflow`：开盘前检查；仅中高异常调用Agent并按需重评估。
4. `MarketRegimeWorkflow`：生成Snapshot，显著变化时调用市场状态Agent。
5. `InvestmentDecisionWorkflow`：门控、专业证据、主Agent、治理、风险Agent、硬风控。
6. `HumanApprovalWorkflow`：等待批准、拒绝、修改、刷新或超时。
7. `RebalanceExecutionWorkflow`：批准后预留批次预算，原子创建RebalanceBatch和OrderIntent[]，根据接受结果消费或释放预留。

决策门控检查交易日、冷却、事件严重度、快照新鲜度、开放Proposal和全局暂停。MonitorPolicy的P0/P1/P2按10/20/30分钟到期检查不表示调用模型或产生交易；只有中高异常、新证据或人工请求才进入决策链。

PASS_WITH_CONDITIONS最多修订`maxRiskReviewRevisions`次，超过后REVIEW_BLOCKED。

HOLD不进入审批和组合调仓批次。Workflow重试必须复用同一reservationId、rebalanceBatchId和幂等键；第二批默认只允许INTRADAY_RISK_REDUCTION或EXECUTION_CORRECTION。

## 测试

- 每条分支、超时、Signal重复、Schedule错过和Continue-as-new。
- 无新证据时不重复调用主Agent。
- HOLD不进入审批和组合调仓批次。
- 并发争抢最后一个额度、执行接受前失败释放、接受后失败不释放。
