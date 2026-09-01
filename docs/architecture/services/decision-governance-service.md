# decision-governance-service

## 1. 定位

管理投资建议从创建、复核、硬风控、人工审批到关闭的完整生命周期，是 Agent 输出与交易执行之间的治理边界。

从第一阶段起作为独立NestJS微服务项目和Docker镜像部署。`platform-api-service`只提供BFF入口，不能持有或直接修改TradeProposal、频率预算和审批状态。

## 2. 核心职责

- 决策触发门控。
- 接收并保存主 Agent 的结构化建议。
- 检查证据完整性和数据新鲜度。
- 按decisionId和proposalVersion关联不可变RiskReviewResult。
- 调用 portfolio-risk-service 进行硬风控。
- 管理人工审批、拒绝、修改和过期。
- 管理每日组合调仓预算、预算预留和冷却时间。
- 生成可交给 execution-service 的已批准组合调仓指令草稿。
- 保存完整决策审计链。

## 3. 决策触发门控

主 Agent 在MonitorPolicy到期或事件触发时“检查”不等于生成建议。即使P0/P1/P2分别按10/20/30分钟评估，也只有满足以下一项或多项才运行：

- 新的每日量化快照已发布。
- 持仓或候选股发生重大新闻事件。
- market-monitor-service产生HIGH或CRITICAL异常，或盯盘Agent输出REASSESS/RISK_ESCALATION。
- market-regime-service发布显著状态变化，或market-state-agent建议重新评估。
- 当前持仓风险阈值发生变化。
- 人工主动请求重新分析。

同时必须满足：

- 当前没有相同输入版本的有效建议。
- 未进入全局暂停状态。
- 达到冷却时间。
- 数据新鲜度满足策略要求。
- 当日决策预算尚未耗尽。

相同anomalyEventId和相同输入快照版本只能触发一个有效决策流程，重复事件由幂等键合并。

## 4. 建议状态机

    DRAFT
      -> AGENT_REVIEWED
      -> RISK_REVIEW_PENDING
      -> RISK_REVIEWED
      -> HARD_RISK_PASSED
      -> PENDING_HUMAN_APPROVAL
      -> APPROVED
      -> BUDGET_RESERVED
      -> SENT_TO_EXECUTION
      -> EXECUTED

分支状态：

    REJECTED
    EXPIRED
    SUPERSEDED
    CANCELLED
    EXECUTION_FAILED
    BUDGET_RELEASED
    REVISION_REQUIRED
    REVIEW_BLOCKED

风险复核分支：

    PASS -> RISK_REVIEWED
    PASS_WITH_CONDITIONS -> REVISION_REQUIRED -> 新proposalVersion
    REJECT -> REJECTED
    INSUFFICIENT_EVIDENCE -> REVIEW_BLOCKED

状态变化必须由明确命令触发并写审计，不允许直接更新数据库状态字段。

DecisionBudgetReservation是独立状态对象；`BUDGET_RESERVED`只表示已取得有效预留，不表示执行已接受。执行接受前失败进入`BUDGET_RELEASED`并关闭本次发送尝试；执行接受后预留转CONSUMED，Proposal进入`SENT_TO_EXECUTION`。

## 5. 组合级TradeProposal契约

至少包含：

- decisionId、proposalVersion、portfolioId、strategyId。
- proposalAction：HOLD或REBALANCE。
- rebalanceReason：DAILY_TARGET、INTRADAY_RISK_REDUCTION或EXECUTION_CORRECTION。
- targetPortfolioVersion和`legs[]`；每个Leg包含legId、symbol、exchange、BUY/SELL及targetWeight或建议数量。
- validFrom、expiresAt。
- confidence。
- reasons、risks、assumptions。
- evidenceIds。
- quantSnapshotId、strategySnapshotIds、可选ensembleStrategySnapshotId、newsSnapshotId、marketRegimeSnapshotId、portfolioSnapshotId和anomalyEventIds。
- agentRunId。RiskReviewResult单独保存并通过decisionId和proposalVersion关联。
- promptVersion、model metadata。

治理服务只接受引用生产时为`ACTIVE`且不可变的策略快照。StrategyVersion后续停用不重写历史建议，但在创建新版本、重新复核或审批前必须重新校验当前可用性，并保存当时的StrategyVersion、参数Hash、代码/镜像Digest和成本模型版本。

HOLD也应保存，但`legs`必须为空，不进入交易审批和当日组合调仓批次计数。REBALANCE至少包含一个Leg，风险复核和硬风控必须基于完整Leg集合，禁止把同一目标组合拆成多个单票Proposal规避批次或组合风险。

## 6. 风险复核结果治理

- 只有RiskReviewResult.verdict为PASS的当前proposalVersion可以进入硬风控。
- PASS_WITH_CONDITIONS不能由治理服务直接篡改建议；应创建修订请求，由主Agent或人工形成新proposalVersion，然后重新执行风险复核。
- REJECT关闭当前建议版本，但保留人工发起全新建议或请求新数据分析的能力。
- INSUFFICIENT_EVIDENCE进入REVIEW_BLOCKED，等待新快照、证据补齐或人工取消，禁止超时后自动放行。
- RiskReviewResult过期、引用的证据版本变化或持仓快照变化时，旧复核结果失效。
- 多模型复核冲突由agent-runtime-service按已发布规则确定性合并；治理服务只接受合并后的结构化结果并保存所有reviewerAgentRunIds。
- 风险复核只能提出语义建议；最终仓位上限、交易次数和回撤限制以portfolio-risk-service的RiskEvaluation为准。
- 每次修订递增proposalVersion并记录parentProposalVersion；超过已发布的maxRiskReviewRevisions后进入REVIEW_BLOCKED，避免Agent无限修订循环。

## 7. 人工审批

审批动作：

- approve：接受建议。
- reject：拒绝并填写原因。
- modify：调整数量或目标权重后重新风控。
- request-refresh：要求使用新数据重新分析。

批准前再次检查：

- 建议是否过期。
- 持仓快照是否变化。
- 风险策略是否变化。
- 最新行情是否超过允许偏差。
- 当日组合调仓预算是否仍可原子预留。

修改建议后必须生成修订版本，重新经过风险复核和硬风控，不能沿用旧RiskReviewResult或RiskEvaluation的PASS结果。

## 8. API

- POST /internal/v1/decisions
- GET /api/v1/decisions
- GET /api/v1/decisions/{decisionId}
- POST /api/v1/decisions/{decisionId}/approve
- POST /api/v1/decisions/{decisionId}/reject
- POST /api/v1/decisions/{decisionId}/modify
- POST /api/v1/decisions/{decisionId}/request-refresh
- POST /internal/v1/decisions/{decisionId}/risk-result
- POST /internal/v1/decisions/{decisionId}/execution-result
- GET /api/v1/decision-budget/{portfolioId}
- POST /internal/v1/decision-budget/reservations
- POST /internal/v1/decision-budget/reservations/{reservationId}/consume
- POST /internal/v1/decision-budget/reservations/{reservationId}/release

risk-result写入必须同时校验proposalVersion、reviewId和幂等键。迟到的旧版本结果只保存审计，不推动当前状态机。

## 9. 组合调仓频率治理

- `maxDailyRebalanceBatches`是硬上限，默认2，允许实际为0；`maxDailyTradeBatches`不再作为新契约字段。
- 上限和第二批reason来自portfolio-risk-service的有效RiskPolicy/RiskEvaluation；治理服务只保存绑定policyVersion的预算投影并执行原子用量控制，不能自行提高上限。
- maxRiskReviewRevisions是单次decision的复核修订上限，建议默认2；它不属于交易频次指标。
- weeklyTradeTarget 是观察指标，不强制满足。
- 连续数周无交易属于合法状态。
- 一个组合级Proposal可以包含多个Leg；执行服务把它原子转换为一个RebalanceBatch和多个OrderIntent。
- 人工批准后、调用执行前，治理服务以`portfolioId + tradingDate`为并发隔离键原子创建`DecisionBudgetReservation`。没有有效预留不得请求执行。
- 调用execution-service前预留转为DISPATCHING；执行服务原子接受RebalanceBatch时转为CONSUMED。只有执行明确确认未接受批次时才转为RELEASED；超时、响应丢失或结果不确定时保持DISPATCHING并按幂等键查询。
- RebalanceBatch接受后，即使部分成交、撤销、过期、人工重报或最终失败也不释放额度；同一幂等键重试不重复计数。
- Governance与Execution各自在本地事务内原子更新，不使用跨服务分布式事务；DISPATCHING预留依靠查询和事件恢复收敛。
- 第一批通常使用DAILY_TARGET；第二批默认只允许INTRADAY_RISK_REDUCTION或EXECUTION_CORRECTION。其他原因必须由版本化策略和RiskPolicy显式开放，并引用通过联合回放与Shadow门禁的证据。
- 拒绝、过期、HOLD和执行接受前的整体失败不计入真实调仓批次，但单独统计模型建议与预留失败频率。

## 10. 审计

每个 decisionId 形成完整时间线：

- 触发原因。
- 使用的全部快照和证据。
- 主 Agent 输出。
- 风险Agent结构化输出、参与模型、分歧和合并规则。
- 硬风控输入和结果。
- 人工操作人和理由。
- 指令、成交与对账结果。
- 预算预留、消费或释放，以及RebalanceBatch和全部Leg/OrderIntent。
- 后续绩效归因。

## 11. 可靠性与安全

- 审批接口使用强认证、幂等键和乐观锁。
- 同一建议只能存在一个有效审批结果。
- APPROVED 到发送执行之间再次校验版本。
- 所有过期时间由服务端计算。
- 外部系统故障时保持 PENDING 或转 FAILED，禁止推断成功。
- 风险复核超时、证据不足或结果无法通过Schema校验时进入REVIEW_BLOCKED，不得跳过该步骤。

## 12. 后续扩展

- 双人审批和按金额分级审批。
- 多策略冲突合并。
- 自动批准低风险小额交易，但仍经过硬风控。
- 影子决策和 A/B 策略比较。
- 决策后归因，比较预期与实际影响。
- 紧急全局 Kill Switch 和只减仓模式。

## 13. 验收标准

- Agent 输出不能直接进入 execution-service。
- 修改后的建议一定重新风控。
- 重复审批不会产生多个执行指令。
- 可以完整回放任意历史决策的状态变化和依据。
- 有条件通过一定产生新proposalVersion并重新复核，旧版本结果不能用于放行。
- 风险复核与硬风控任一层失败都不能默认进入人工批准或执行。
- 每个组合每天第3个RebalanceBatch被拒绝；同批次多Leg、部分成交和重报不重复计数。
- 预算预留并发安全，执行接受前失败可释放，接受后不得通过取消或失败恢复额度。
- 执行接受响应丢失时不会释放额度或创建新批次，查询恢复后状态收敛。
