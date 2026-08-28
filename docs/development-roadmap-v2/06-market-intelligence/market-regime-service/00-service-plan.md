# market-regime-service开发计划

## 目标

用确定性指标和状态机判断市场、指数和行业环境。领域基线见[市场状态服务设计](../../../architecture/services/market-regime-service.md)。

## 内部阶段

1. [特征和Snapshot最小切片](./01-scaffold-features.md)。
2. [状态机、回放和强化](./02-core-integration-hardening.md)。
3. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

LLM只在阶段09解释Snapshot，不能计算或改写Regime事实。

