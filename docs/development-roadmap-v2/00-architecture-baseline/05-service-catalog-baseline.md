# 00-05 服务目录与事实所有权基线

## 规则

每项业务事实只能由一个服务写入；服务使用独立 Database/User；跨服务只能通过 REST、事件或只读投影访问。`禁止写入` 包含直接 SQL、共享 ORM Entity、BFF 缓存回写和 Agent Tool 绕过命令。

| 服务 | 限界上下文与唯一事实 Owner | 数据库 | 入站端口 | 出站端口 | 禁止写入 |
|---|---|---|---|---|---|
| market-data-service | Security、Calendar、MarketBar、FinancialFact、DataVersion | market_data | Adapter、REST | NATS 数据版本事件 | 分析、策略、持仓 |
| quant-research-service | Factor/Model/Strategy Registry、每日分析与策略快照 | quant_research | REST、数据版本事件 | NATS 快照/策略事件 | 原始行情、订单 |
| research-automation-service | 实验、候选代码、PromotionRequest | research_automation | REST、研究任务 | NATS 实验事件 | 生产 Registry、生产快照 |
| news-intelligence-service | 新闻证据、去重簇、FinancialNewsEvent | news_intelligence | Adapter、REST | NATS 新闻事件 | Security、建议、订单 |
| market-monitor-service | Watchlist、Bar、AnomalyEvent | market_monitor | 行情流、REST | NATS 异常事件 | 行情主事实、持仓 |
| market-regime-service | Regime 定义与 MarketRegimeSnapshot | market_regime | REST、数据版本事件 | NATS Regime 事件 | 行情主事实、RiskPolicy |
| portfolio-risk-service | Account、Ledger、PortfolioSnapshot、RiskPolicy、RiskEvaluation | portfolio_risk | REST、Fill 事件 | NATS 组合/风控事件 | Proposal、Approval、Order |
| decision-governance-service | 组合级TradeProposal、RiskReview关联、审批、DecisionBudgetReservation | decision_governance | REST、Agent/Risk事件 | NATS决策/预算事件 | Portfolio、Fill、Broker订单 |
| trade-execution-service | RebalanceBatch、OrderIntent、订单、人工Fill、对账结果 | trade_execution | 鉴权REST、审批/预算命令 | NATS批次/Fill事件 | Proposal、RiskPolicy、PortfolioSnapshot |
| platform-api-service | 无领域事实；仅认证、RBAC、请求审计和短生命周期查询缓存 | platform_api | Web REST/SSE | 生成 Client 调用 | 所有领域 Aggregate |
| workflow-orchestration-service | Workflow History、调度和人工等待状态 | temporal | Schedule、Signal、Activity | 受控 REST/事件 | 所有领域 Aggregate |
| agent-service | AgentRun、ModelRun、Assessment | agent_runtime | Tool、任务、事件 | NATS Assessment 事件 | Portfolio、Risk、Proposal、Order、Fill |

## 审查方式

1. 对每个事实在表中找到且仅找到一个 Owner。
2. 对每项出站事件核对 Owner 与事件主题的生产方一致。
3. 对平台服务抽查数据库设计，确认只保存本行列出的运行或审计数据。
4. 新服务、Aggregate 或投影加入前必须更新本表及 ADR-016；未更新即禁止合并。
