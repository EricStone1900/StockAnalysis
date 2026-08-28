# trade-execution-service测试计划

- OrderIntent和ExecutionBatch状态机。
- Approval/Risk/Proposal引用和过期校验。
- 人工提交、部分/完全成交、费用、撤销和过期。
- Fill唯一性、重复事件和Portfolio入账。
- 日终对账全部差异类型。
- UNKNOWN、超时、进程崩溃、Outbox恢复和暂停。
- RBAC：Agent、Governance和普通用户不能伪造Fill。

阶段05不运行任何真实券商写操作。

