# decision-governance-service开发计划

## 目标与边界

建立TradeProposal版本、风险复核链接、硬风控链接、人工审批和交易频率治理状态机。领域基线见[决策治理设计](../../../architecture/services/decision-governance-service.md)。

## 内部阶段

1. [骨架与Proposal最小切片](./01-scaffold-minimum-slice.md)。
2. [复核、风控、审批和强化](./02-core-integration-hardening.md)。
3. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

本阶段用Fake Agent结果和Fake Risk Client，不接模型和Temporal。

