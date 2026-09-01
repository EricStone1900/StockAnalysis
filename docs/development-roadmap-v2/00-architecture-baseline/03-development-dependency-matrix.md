# 00-03 开发依赖与Fake替代矩阵

## 目的

明确每个项目何时可以独立开发、依赖尚未完成时使用什么Fake，以及何时允许切换为真实集成。

| 项目 | 实现阶段 | 必须完成的上游 | 独立开发时替代 | 真实接入门禁 |
|---|---:|---|---|---|
| market-data-service | 02 | 工程基础 | CSV/Parquet Fixture | 自身99验收 |
| quant-research-service | 03 | market-data契约 | 固定DataVersion Artifact | market-data 99验收 |
| research-automation-service | 04 | quant契约 | Fake Promotion Receiver | quant 99验收 |
| portfolio-risk-service | 05 | Security/行情契约 | Fake Price/Security Client | market-data 99验收 |
| decision-governance-service | 05 | Risk/Agent契约 | Fake Risk与Fake Proposal | portfolio-risk 99验收 |
| trade-execution-service | 05 | Governance契约 | Fake Approval与Fake Broker | governance 99验收 |
| news-intelligence-service | 06 | Security契约 | Security Fixture、Fake Analyzer | market-data 99验收；真实Agent在09 |
| market-monitor-service | 06 | Calendar/Security | 历史分钟Fixture | market-data 99验收；真实Agent在09 |
| market-regime-service | 06 | DataVersion | 固定市场Fixture | market-data 99验收；真实Agent在09 |
| platform-api-service | 07 | 领域OpenAPI | Mock Servers | 各领域服务99验收 |
| agent-service | 08～09 | Tool契约 | Fake Provider、Fake Tools | 领域服务与Kernel分别验收 |
| workflow-orchestration-service | 10 | 全部命令契约 | Fake Activities | 阶段09验收 |
| React Web | 07/10 | Platform API | MSW Fixture | Platform API验收 |

## 顺序规则

- 默认按阶段编号顺序开发，适合个人开发和降低上下文切换。
- 多人团队可以在阶段02完成后并行准备阶段05/06的S0～S2，但不得接真实上游或跳过各自99验收。
- Fake必须实现同一个生成契约，禁止为联调创建未记录的临时字段。
- 切换Fake到真实实现只允许替换Adapter，不修改Domain规则。

## 契约冻结点

1. 阶段02冻结DataVersion、Security和Calendar v1。
2. 阶段03冻结DailyAnalysisSnapshot、DailyStrategySnapshot v1。
3. 阶段05冻结Portfolio、Risk、组合级Proposal、DecisionBudgetReservation、RebalanceBatch、Approval、OrderIntent和Fill v1。
4. 阶段06冻结NewsCandidate、AnomalyEvent和RegimeSnapshot v1。
5. 阶段08冻结AgentRun、ModelRun、Tool和Context Manifest v1。

冻结不表示永不变化；兼容增加走Minor版本，破坏性变化走新Major并保留迁移期。
