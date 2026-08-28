# portfolio-risk-service开发计划

## 目标与边界

建立组合账本、持仓快照和确定性硬风控。领域基线见[Portfolio Risk设计](../../../architecture/services/portfolio-risk-service.md)。

## 内部阶段

1. [骨架与最小组合切片](./01-scaffold-minimum-slice.md)。
2. [账本、估值、RiskPolicy和集成强化](./02-core-integration-hardening.md)。
3. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 禁止事项

- 不保存TradeProposal、Approval或Order事实。
- 不调用LLM判断硬限制。
- 不根据每周交易目标强制买卖。
- 风控不可用时新增和加仓必须失败关闭。

