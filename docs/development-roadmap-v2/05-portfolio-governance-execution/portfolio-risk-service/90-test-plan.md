# portfolio-risk-service测试计划

- Ledger不可变、冲正、费用、现金和公司行动。
- PortfolioSnapshot原子性、估值和Decimal精度。
- RiskPolicy版本、单股/行业/总仓位/现金/换手/0～2批/第二批reason/回撤。
- 多Leg逐项结果、组合projectedAfter、T+1和整体原子拒绝。
- 并发expectedVersion、重复命令和重复Fill。
- 行情缺失、陈旧、超时和恢复。
- OpenAPI、Portfolio/Risk事件、Outbox/Inbox重放。
- API契约必须核对[05-01接口契约](./02-api-contract.md)：路径、字段、错误码、幂等和版本语义保持一致。
- 服务级集成测试需关闭并重新创建 Nest 应用后继续写入，确认数据库快照和 `ledgerVersion` 跨重启恢复。
- `/ready` 在数据库模式执行 `SELECT 1` 探测；数据库不可用必须显示 `DOWN`，内存模式显示 `NOT_CONFIGURED`，不可将依赖故障伪装为 `UP`。
- 应用关闭时必须触发连接池释放；测试环境为支持多实例恢复测试而禁用自动释放，生产环境不得禁用。
- 容器构建必须使用仓库根 `.dockerignore`，不得把 `node_modules`、`.venv`、缓存和本机凭据发送到构建上下文；镜像构建后需在 Ubuntu 启动并检查 `3002/live`、`3002/ready`。
- RBAC：Agent只读，Governance只调用evaluate，Execution只提交Fill事实。

必须包含长期HOLD、零交易、卖出降风险和新增仓位失败关闭场景。
