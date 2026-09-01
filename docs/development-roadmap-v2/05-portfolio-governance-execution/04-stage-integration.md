# 05-04 三服务契约集成

## 目标

使用Fake Proposal和Fake人工操作验证三服务真实API/Event链，但不接Agent和Temporal。

```text
Fake Proposal
  -> decision-governance DRAFT
  -> Fake RiskReview PASS
  -> portfolio-risk组合级RiskEvaluation
  -> Human Approval API
  -> decision-governance原子预留DecisionBudgetReservation
  -> trade-execution原子接受RebalanceBatch并创建OrderIntent[]
  -> 预留转CONSUMED
  -> Manual Fill[]
  -> portfolio-risk Ledger/Snapshot
```

## 实施步骤

1. 所有同步调用使用生成Client；所有事实传播使用NATS和Inbox。
2. 为每一步保存correlationId，并建立跨服务审计查询Fixture。
3. 人工修改Proposal后验证旧Risk和Approval不能复用。
4. Fill入账后生成新PortfolioSnapshot，使未执行旧建议失效。
5. 加入依赖故障、重试、重复和迟到场景。
6. 使用一个含多个Leg的Fake Proposal验证一次组合调仓只占一个批次；任一Leg在原子接受前失败时不留下部分READY Intent并释放预留。
7. 并发提交第二、第三批，验证预算按`portfolioId + tradingDate`原子串行化，第三批失败且不能通过拆分decisionId规避。
8. 模拟Execution提交成功但同步响应丢失：Governance保持DISPATCHING，通过查询或批次事件收敛为CONSUMED；禁止使用分布式事务或猜测失败。

## 完成条件

上述链路可重复运行且无跨库访问；任何失败都不能静默创建READY OrderIntent，预算预留、消费和释放均可审计。
