# decision-governance-service测试计划

- Proposal状态机和所有非法跃迁。
- proposalVersion不可变、parent关联和内容Hash。
- PASS、CONDITIONAL、REJECT、INSUFFICIENT四类风险复核。
- RiskEvaluation版本、新鲜度和失效。
- approve/reject/modify/refresh/expire及RBAC。
- 每日批次、修订上限、暂停和只观察。
- 重复、乱序和迟到事件。
- Agent、Risk、Execution Fake Contract Test。

关键不变量：任何路径都不能绕过当前Proposal的风险复核、硬风控和人工批准。

