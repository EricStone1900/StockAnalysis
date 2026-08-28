# 阶段09：人工执行与端到端闭环总设计

## 目标

在独立`trade-execution-service`中把已批准建议转换为人工OrderIntent并记录提交、成交和撤销；由独立`portfolio-risk-service`消费确认成交、更新组合流水并完成日终对账。

## 开发边界

不调用券商下单API。只有人工确认的成交才能修改持仓事实。

## 实施要求

- OrderIntent、Fill和Ledger均使用不可变ID和幂等键。
- 订单状态不能跳跃，撤销不能删除已有成交。
- 组合从流水重建，对账差异不能自动覆盖事实。
- 全链路保留decisionId和riskEvaluationId。
- 两个服务使用独立Database/User，confirmed Fill通过NATS + Outbox/Inbox传递，重复事件只入账一次。

## 顺序文档

1. [OrderIntent和人工成交回填](./01-order-intent-manual-fill.md)
2. [组合流水和日终对账](./02-ledger-reconciliation.md)
3. [端到端测试与发布准备](./03-e2e-release-readiness.md)

## 阶段验收

- 只有APPROVED且RiskEvaluation有效的建议能创建READY指令。
- 重复提交和重复成交回填保持幂等。
- 持仓、现金和成交可以完整对账。
- 决策到成交形成完整时间线。
