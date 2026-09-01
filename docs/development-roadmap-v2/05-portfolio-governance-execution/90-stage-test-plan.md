# 阶段05集成测试计划

1. 正常多Leg Fake建议到一个RebalanceBatch、多个人工Fill再到新PortfolioSnapshot。
2. 风险复核REJECT、证据不足和条件通过分支。
3. 硬风控拒绝超仓、第3个组合调仓批次、非法第二批reason和回撤状态。
4. 人工拒绝、修改、刷新和过期。
5. 重复审批、重复Intent、重复Fill和重复事件。
6. 旧proposalVersion、RiskEvaluation或Approval迟到。
7. 任一服务停止、超时、恢复和Outbox重放。
8. 跨数据库写权限和越权API拒绝。
9. 预算并发预留、接受前整体失败释放、接受后取消不释放。
10. 同批次多Leg、部分成交、撤单重报和相同幂等键重试不重复计数。
11. 任一Leg违反T+1、涨跌停、停牌或使组合projectedAfter超限时，整个批次不能留下部分READY Intent。
12. 执行已接受但响应丢失时，预留保持DISPATCHING；按幂等键查询后收敛为CONSUMED，不释放或新建批次。

通过标准：失败路径无部分READY批次或重复账本副作用，审计可关联完整correlationId、reservationId和rebalanceBatchId。
