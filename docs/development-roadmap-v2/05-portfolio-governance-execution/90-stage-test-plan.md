# 阶段05集成测试计划

1. 正常Fake建议到人工Fill再到新PortfolioSnapshot。
2. 风险复核REJECT、证据不足和条件通过分支。
3. 硬风控拒绝超仓、第3批交易和回撤状态。
4. 人工拒绝、修改、刷新和过期。
5. 重复审批、重复Intent、重复Fill和重复事件。
6. 旧proposalVersion、RiskEvaluation或Approval迟到。
7. 任一服务停止、超时、恢复和Outbox重放。
8. 跨数据库写权限和越权API拒绝。

通过标准：失败路径无订单或重复账本副作用，审计可关联完整correlationId。

