# workflow-orchestration-service

## 1. 定位

基于 Temporal TypeScript SDK 的持久化工作流编排服务，负责“什么时候执行、按什么顺序执行、失败后如何恢复、何时等待人工输入”。

它不实现Agent推理和领域计算，只编排Activities和Signals。NATS JetStream可以启动或Signal工作流，但Temporal不是领域事件总线。

## 2. 核心工作流

### DailyQuantAnalysisWorkflow

    等待交易日和数据源就绪
      -> 更新并校验市场数据
      -> 启动 quant-research-service 每日任务
      -> 等待完成
      -> 验证并发布快照
      -> 运行ACTIVE日频策略并发布DailyStrategySnapshot
      -> 通知股票分析 Agent

### NewsAnalysisWorkflow

    定时或事件触发采集
      -> 新闻标准化和去重
      -> 结构化事件分析
      -> 针对候选股和持仓股生成摘要

### MarketMonitorWorkflow

    交易日前确保market-monitor-service就绪
      -> Worker按MonitorPolicy持续接收或批量轮询行情
      -> Worker本地聚合并运行异常检测
      -> Temporal只接收中高等级异常事件引用
      -> 调用盯盘 Agent
      -> 必要时触发决策工作流

Tick和完整分钟序列不能写入Temporal Workflow History；Temporal只编排Worker启停检查、异常后的Agent调用和后续决策。

### MarketRegimeWorkflow

    收盘后或盘中窗口完成
      -> 检查市场数据和宽度数据新鲜度
      -> 调用market-regime-service生成快照
      -> 状态未变化时仅保存快照
      -> 状态显著变化时调用market-state-agent
      -> 必要时触发组合风险和投资决策重评估

### InvestmentDecisionWorkflow

    决策触发门控
      -> 获取最新量化、ACTIVE日频策略、新闻、市场和持仓快照
      -> 调用主决策 Agent
      -> decision-governance-service创建DRAFT TradeProposal版本
      -> 构建并校验不可变RiskReviewEvidencePacket
      -> 调用风险复核 Agent
      -> PASS：调用硬风控
      -> PASS_WITH_CONDITIONS：生成修订请求并等待新proposalVersion
      -> REJECT：关闭当前建议版本
      -> INSUFFICIENT_EVIDENCE：等待数据刷新或人工处理
      -> 硬风控PASS后进入人工审批工作流
      -> 批准后原子预留DecisionBudgetReservation
      -> execution原子接受RebalanceBatch并创建OrderIntent[]
      -> 接受成功消费预留；接受前整体失败释放预留

风险复核的内部“独立证据判断、建议对照、反方情景、结果汇总”默认封装在一个risk-review Activity中。Temporal保存输入引用和结构化RiskReviewResult，不把模型的完整辩论文本或隐藏推理写入Workflow History。若未来使用LangGraph.js，只允许作为该Activity内部实现，不能替代Temporal持有业务生命周期。

PASS_WITH_CONDITIONS修订循环必须有`maxRiskReviewRevisions`上限，建议默认2次。超过上限转REVIEW_BLOCKED并请求人工处理，禁止Agent无限自我修改。

### HumanApprovalWorkflow

    等待人工 Signal
      -> 批准、拒绝、修改或超时
      -> 批准后创建交易指令草稿
      -> 当前阶段等待人工成交回填

## 3. Activities 边界

推荐 Activity 分类：

- market-data activities：数据同步、完整性验证、行情查询。
- market-regime activities：生成状态快照、读取状态、触发回放。
- quant activities：启动任务、查询状态、运行ACTIVE策略、读取分析/策略快照；不能在Workflow代码内加载插件。
- news activities：采集、分析、读取事件。
- agent activities：运行指定 Agent。
- risk-review activities：构建证据包、运行单模型或跨模型复核、确定性合并结构化结论。
- risk activities：硬风控评估。
- governance activities：创建建议、审批状态变更，以及预留、消费或释放组合调仓预算。
- execution activities：原子创建RebalanceBatch和OrderIntent[]、查询订单和对账。

Workflow 代码必须保持确定性，不在 Workflow 内直接使用当前时间、随机数、数据库客户端、HTTP 客户端或模型 SDK。

## 4. 调度建议

| 调度 | 规则 |
|---|---|
| 每日量化 | 交易日收盘后，并以数据源就绪为真正触发条件 |
| 新闻全量 | 每 12 小时，可由重大来源事件追加触发 |
| 盯盘 | Worker按版本化MonitorPolicy运行；免费首版每10分钟批量采样，P0/P1/P2分别每10/20/30分钟评估；Temporal负责开盘前检查和异常后流程 |
| 市场状态 | 日频收盘后；盘中15～30分钟或市场级异常触发 |
| 决策检查 | MonitorPolicy到期或事件触发；只有中高异常、新证据或人工请求才进入决策门控 |
| RD-Agent研究 | 每周、每月或人工触发research-automation-service |
| 模型重训 | 定期或漂移检测触发 |

周交易 1～2 次是策略目标，不是 Temporal 强制创建交易的调度。

## 5. 幂等与重试

- 每个 Activity 接收 runId、workflowId、correlationId。
- 写操作携带 Idempotency-Key。
- 读取和纯计算 Activity 可以重试。
- 模型调用仅在没有外部副作用时自动重试。
- 风险复核重试和Provider切换必须产生新的modelRunId；全部失败时返回阻塞结果，不能默认PASS。
- 创建建议、审批、订单等操作必须依靠服务端幂等，而不是仅依赖 Temporal。
- Workflow重试不得生成新的rebalanceBatchId或预算预留；同一decisionId、proposalVersion和批准结果必须复用稳定幂等键。
- 不可恢复的数据质量错误进入人工处理队列，不进行无限重试。

## 6. Task Queue

建议至少划分：

- orchestration-default
- quant-jobs
- news-jobs
- market-monitor-events
- market-regime-jobs
- agent-fast
- agent-reasoning
- agent-risk-review
- execution-critical

agent-risk-review队列承载风险复核Agent；portfolio-risk-service的同步硬风控仍走独立的确定性Activity和超时策略，不能与模型队列共用故障放行逻辑。

各Agent独立部署并绑定自己的队列；允许同一镜像复用实现，但不合并成一个Agent进程。Temporal Worker可按领域队列独立扩缩容。

## 6.1 与NATS的边界

- `DataVersionPublished`、`MarketAnomalyDetected`等领域事件先写入服务Outbox，再发布NATS。
- 轻量Event Starter校验Inbox幂等后启动或Signal指定Workflow。
- Workflow只记录事件ID、Aggregate版本和Artifact引用，通过Activity读取详情。
- Activity完成事件可供其他上下文订阅，但Workflow状态不能仅靠“猜测事件是否到达”推进；需要明确的Signal、查询或幂等命令结果。

## 7. 状态与可观测性

- Search Attributes 保存 market、asOf、strategyId、decisionId、status。
- 关键 Activity 记录输入版本，不记录明文密钥。
- Metrics 包含成功率、重试次数、队列延迟和工作流总时长。
- 失败告警必须链接 runId 和业务快照。

## 8. 后续扩展

- 多市场时为每个市场建立独立交易日历和 Schedule。
- 多组合时以 portfolioId 作为工作流隔离键。
- 自动交易阶段增加订单状态长工作流和对账补偿。
- 增加策略回放工作流，用历史快照重现当时决策。
- 阶段10增加日频策略、分钟异常、批次预算、A股执行限制和成本后的联合回放；阶段12使用Paper/Shadow继续验证。
- 增加风险复核影子模型和模型分歧评估，但影子结果不改变生产状态机。
- 增加灾难恢复和跨区域 Worker，但避免同一 Schedule 重复触发。

## 9. 验收标准

- Worker 重启后工作流可以继续。
- 人工审批可以等待数小时或数天，不占用线程。
- 每日任务重复触发不会发布两份相同版本快照。
- 工作流历史可以解释每一步使用的输入版本和结果。
- PASS_WITH_CONDITIONS、REJECT和INSUFFICIENT_EVIDENCE都有明确状态分支，不会落入默认放行路径。
- 同一组合级Proposal的多Leg只创建一个RebalanceBatch；第3批、预算竞争和接受失败释放均可确定性重放。
