# portfolio-risk-service测试计划

- Ledger不可变、冲正、费用、现金和公司行动。
- PortfolioSnapshot原子性、估值和Decimal精度。
- RiskPolicy版本、单股/行业/总仓位/现金/换手/0～2批/第二批reason/回撤。
- 多Leg逐项结果、组合projectedAfter、T+1和整体原子拒绝。
- 并发expectedVersion、重复命令和重复Fill。
- 行情缺失、陈旧、超时和恢复。
- OpenAPI、Portfolio/Risk事件、Outbox/Inbox重放。
- API契约必须核对[05-01接口契约](./02-api-contract.md)：路径、字段、错误码、幂等和版本语义保持一致。
- RBAC：Agent只读，Governance只调用evaluate，Execution只提交Fill事实。

必须包含长期HOLD、零交易、卖出降风险和新增仓位失败关闭场景。
