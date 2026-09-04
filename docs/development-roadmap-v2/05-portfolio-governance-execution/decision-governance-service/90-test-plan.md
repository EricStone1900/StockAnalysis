# decision-governance-service测试计划

- Proposal状态机和所有非法跃迁。
- proposalVersion不可变、parent关联和内容Hash。
- PASS、CONDITIONAL、REJECT、INSUFFICIENT四类风险复核。
- RiskEvaluation版本、新鲜度和失效。
- approve/reject/modify/refresh/expire及RBAC。
- 每日0～2批、第二批reason、预算原子预留/消费/释放、修订上限、暂停和只观察。
- 多Leg Proposal、目标组合版本、拆单规避和内容Hash变化。
- 重复、乱序和迟到事件。
- Agent、Risk、Execution Fake Contract Test。
- PostgreSQL 迁移、Outbox 幂等写入、领取租约、NATS 发布确认和失败重试。

关键不变量：任何路径都不能绕过当前Proposal的风险复核、硬风控、人工批准和预算预留；并发流程不能超用批次额度。
