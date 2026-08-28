# 08-04 Temporal核心工作流

## 目标

用Temporal实现可靠调度、依赖顺序、Activity重试、事件触发和人工等待。

## 实施步骤

### 1. Task Queue

```ts
export const queues = {
  orchestration: 'orchestration-default',
  quant: 'quant-jobs',
  news: 'news-jobs',
  monitor: 'market-monitor-events',
  regime: 'market-regime-jobs',
  stockAnalysisAgent: 'agent-stock-analysis',
  financialNewsAgent: 'agent-financial-news',
  marketMonitorAgent: 'agent-market-monitor',
  marketStateAgent: 'agent-market-state',
  mainDecisionAgent: 'agent-main-decision',
  riskReviewAgent: 'agent-risk-review',
  execution: 'execution-critical',
} as const;
```

六个Agent容器各自只轮询一个专属队列。非Agent领域Worker也按限界上下文绑定队列，不把全部任务合并到一个进程。

### 2. Activity错误分类

```ts
class ActivityDependencyError extends Error {
  constructor(message: string, readonly retryable: boolean) { super(message); }
}
```

数据质量FAIL不可无限重试；网络超时可指数退避；写操作依靠服务端幂等。

### 3. DailyQuantAnalysisWorkflow

```ts
export async function dailyQuantAnalysis(input: DailyInput) {
  const data = await marketActivities.ensureDailyData(input.date);
  const run = await quantActivities.startDailyAnalysis({ ...input, dataVersion: data.id });
  const snapshot = await quantActivities.waitForSnapshot(run.runId);
  await agentActivities.runStockAnalysis(snapshot.snapshotId);
  return snapshot;
}
```

Workflow不直接使用HTTP、数据库或模型SDK。

### 4. 新闻、盯盘和Regime流程

- News：定时采集，NATS重大事件可启动或Signal Workflow。
- Monitor：NATS Event Starter通过Inbox去重后Signal Workflow；Temporal只收eventId，不收Tick和完整Bar。
- Regime：日频/盘中窗口，状态显著变化才调用Agent和重评估。

### 5. InvestmentDecisionWorkflow

```ts
const proposal = await decisionActivities.createProposal(evidenceBundle);
const review = await riskAgentActivities.review(proposal);

switch (review.verdict) {
  case 'PASS': return await hardRiskAndApproval(proposal, review);
  case 'PASS_WITH_CONDITIONS': return await requestBoundedRevision(proposal, review);
  case 'REJECT': return await governanceActivities.reject(proposal, review.reviewId);
  case 'INSUFFICIENT_EVIDENCE': return await governanceActivities.block(proposal, review.reviewId);
}
```

### 6. HumanApprovalWorkflow

使用Signal接收approve/reject/modify/request-refresh并设置服务端超时。修改生成新版本并重新复核和硬风控。

### 7. 幂等和Search Attributes

Workflow ID包含market、portfolioId和业务幂等键。保存decisionId、strategyId、asOf和status为Search Attributes。

## 测试案例

1. Worker在Activity中途重启后流程继续。
2. 同一事件重复Signal不创建两个决策。
3. Workflow replay不发生非确定性错误。
4. 模型Activity重试产生新modelRunId。
5. 人工审批等待数天不占线程。
6. Tick数据未写入Workflow History。
7. revision达到上限后结束自动循环。

## 完成条件

- 五类核心Workflow均有Temporal测试环境测试。
- Workflow History只保存小型引用和结构化结果。
- 所有写Activity有业务幂等键。
