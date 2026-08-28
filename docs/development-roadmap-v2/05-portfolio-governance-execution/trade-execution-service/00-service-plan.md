# trade-execution-service开发计划

## 目标与边界

第一版只实现人工执行：从已批准建议创建OrderIntent，记录人工提交、成交、撤销和对账。领域基线见[交易执行设计](../../../architecture/services/trade-execution-service.md)。

## 内部阶段

1. [骨架与OrderIntent最小切片](./01-scaffold-minimum-slice.md)。
2. [人工Fill、对账和强化](./02-core-integration-hardening.md)。
3. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

当前禁止接生产券商交易接口；Broker Port只提供Fake实现。

