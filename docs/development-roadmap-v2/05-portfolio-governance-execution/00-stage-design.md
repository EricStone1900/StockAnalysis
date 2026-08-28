# 阶段05：组合、决策治理与人工执行基础

## 目标

依次独立完成三个有强业务约束的微服务，再用Fake Agent和Fake行情验证它们的同步命令链。三个服务保持独立数据库和发布周期。

## 顺序

1. [portfolio-risk-service计划](./portfolio-risk-service/00-service-plan.md)。
2. [decision-governance-service计划](./decision-governance-service/00-service-plan.md)。
3. [trade-execution-service计划](./trade-execution-service/00-service-plan.md)。
4. [三服务契约集成](./04-stage-integration.md)。
5. [阶段测试](./90-stage-test-plan.md)与[阶段验收](./99-stage-acceptance.md)。

## 关键边界

- portfolio-risk拥有Ledger、PortfolioSnapshot、RiskPolicy和RiskEvaluation。
- decision-governance拥有TradeProposal、Review Link、Approval和决策预算。
- trade-execution拥有OrderIntent、Order、Fill和Reconciliation。
- Governance不能伪造Risk PASS；Execution不能自行创建未批准建议；Portfolio不能直接下单。

本阶段不接真实Agent、Temporal或券商，使用Fixture和Fake Client形成确定性基础。

