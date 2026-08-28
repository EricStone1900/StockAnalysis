# 05-04 三服务契约集成

## 目标

使用Fake Proposal和Fake人工操作验证三服务真实API/Event链，但不接Agent和Temporal。

```text
Fake Proposal
  -> decision-governance DRAFT
  -> Fake RiskReview PASS
  -> portfolio-risk RiskEvaluation
  -> Human Approval API
  -> trade-execution OrderIntent
  -> Manual Fill
  -> portfolio-risk Ledger/Snapshot
```

## 实施步骤

1. 所有同步调用使用生成Client；所有事实传播使用NATS和Inbox。
2. 为每一步保存correlationId，并建立跨服务审计查询Fixture。
3. 人工修改Proposal后验证旧Risk和Approval不能复用。
4. Fill入账后生成新PortfolioSnapshot，使未执行旧建议失效。
5. 加入依赖故障、重试、重复和迟到场景。

## 完成条件

上述链路可重复运行且无跨库访问；任何失败都不能静默创建READY OrderIntent。

