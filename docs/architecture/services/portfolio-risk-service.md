# portfolio-risk-service

## 1. 定位

持仓、现金、组合估值、风险暴露和确定性硬风控的事实来源。它接受交易建议进行规则评估，但不调用大模型，也不负责人工审批和订单执行。

从第一阶段起作为独立NestJS微服务项目和Docker镜像部署。可复用TypeScript风险规则包，但账户、成交账本、持仓投影和RiskPolicy数据库只能由本服务写入。

## 2. 核心职责

- 维护人工录入或券商同步的账户和持仓快照。
- 计算现金、市场价值、总权益、成本、已实现和未实现盈亏。
- 计算单股、行业、风格和市场暴露。
- 计算组合回撤、波动、集中度和流动性风险。
- 对交易建议执行预交易硬风控。
- 对成交结果执行交易后风险检查。
- 为 Agent 和前端提供不可变风险快照。

## 3. 不负责

- 根据新闻决定买卖。
- 用大模型动态修改风险阈值。
- 直接批准交易建议。
- 直接向券商发送订单。
- 使用未经确认的成交回报修改持仓。

## 4. 内部模块

    AccountRepository
    PortfolioLedger
    PositionValuation
    ExposureCalculator
    DrawdownCalculator
    RiskPolicyRegistry
    PreTradeRiskEvaluator
    PostTradeRiskEvaluator
    RiskSnapshotPublisher
    ReconciliationSupport

PortfolioLedger 采用流水账思路保存变动，PortfolioSnapshot 是从流水和行情计算出的不可变结果。

## 5. 核心数据模型

PortfolioSnapshot：

- portfolioSnapshotId、portfolioId、accountId、asOf。
- cash、marketValue、totalEquity。
- realizedPnl、unrealizedPnl、drawdown。
- positions。
- industryExposure、styleExposure、liquidityExposure。
- marketDataVersion、ledgerVersion。

RiskPolicy：

- maxSinglePositionWeight。
- maxIndustryWeight。
- maxTotalExposure。
- maxDailyTurnover。
- maxDailyTradeBatches。
- maxPortfolioDrawdown。
- maxSingleTradeLoss。
- minimumCashRatio。
- minimumHoldingDays。
- cooldownMinutes。
- minimumDataFreshnessMinutes。
- effectiveFrom、effectiveTo、version。

## 6. 预交易风控

输入为TradeProposal、当前PortfolioSnapshot和可选MarketRegimeSnapshot引用，输出：

- decisionId和proposalVersion。
- result：PASS、REJECT、REQUIRES_REVIEW。
- violatedRules。
- before 和 projectedAfter 风险指标。
- maximumAllowedQuantity 或 maximumAllowedWeight。
- riskPolicyVersion。
- evaluatedAt。

至少检查：

1. 每日交易批次是否超过 1～2 次上限。
2. 是否处于冷却时间。
3. 单股和行业仓位。
4. 总风险暴露和现金比例。
5. 组合回撤和止损状态。
6. 当前持仓是否满足 T+1 等卖出约束。
7. 数据是否过期。
8. 停牌、涨跌停和流动性风险。
9. 建议是否引用有效的持仓和行情版本。

市场状态可以触发更保守的已发布RiskPolicy分支，但不能由Agent文本临时修改数值阈值；评估结果记录marketRegimeSnapshotId和实际使用的riskPolicyVersion。

每周 1～2 次仅用于策略观察和报告，不作为强制最低交易次数。

## 7. API

- GET /api/v1/portfolios/{portfolioId}
- GET /api/v1/portfolios/{portfolioId}/snapshots/latest
- GET /api/v1/portfolios/{portfolioId}/risk/latest
- GET /api/v1/portfolios/{portfolioId}/positions
- GET /internal/v1/portfolios/{portfolioId}/monitor-context
- POST /api/v1/portfolios/{portfolioId}/manual-snapshots
- POST /internal/v1/risk/pre-trade-evaluations
- POST /internal/v1/risk/post-trade-evaluations
- POST /internal/v1/reconciliation/apply-confirmed-fill
- GET /api/v1/risk-policies/{policyId}

写接口必须携带 source、effectiveAt、idempotencyKey 和 operatorId。

## 8. 数据一致性

- 人工执行阶段以“人工确认成交记录”为持仓变更来源。
- 自动交易阶段以券商成交回报为来源，并通过日终对账纠正差异。
- 行情估值和持仓数量使用不同版本字段，不混为一体。
- 风控评估绑定具体decisionId、proposalVersion和portfolioSnapshotId；建议版本或持仓发生变化必须重新评估。
- 风险策略变更采用发布版本，不修改历史评估。

## 9. 可靠性和安全

- 风控服务不可用时默认禁止新增交易，而不是默认放行。
- 所有金额和数量使用 Decimal，避免浮点误差。
- 高风险策略变更需要双人或二次确认。
- 禁止 Agent 调用修改 RiskPolicy 的工具。
- 风控规则执行结果和输入快照永久可审计。

## 10. 后续扩展

- 多账户和多组合聚合风险。
- VaR、Expected Shortfall 和压力测试。
- 风格因子风险模型。
- 流动性和冲击成本模型。
- 实时盘中风险监控。
- 券商持仓自动同步和日终对账。
- 组合优化器，但最终输出仍需硬风控检查。

## 11. 验收标准

- 相同输入和相同 RiskPolicyVersion 产生相同结果。
- 持仓变化后旧风控通过结果不能继续用于执行。
- 新proposalVersion不能复用旧版本的RiskEvaluation。
- 风控服务故障不会导致交易默认放行。
- 每条违反规则都有稳定 ruleId 和可读说明。
