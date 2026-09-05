# trade-execution-service

当前提供人工批次、Intent、增量Fill和对账切片。启动为`pnpm dev`。PostgreSQL迁移为`migrations/001_execution.sql`，配置数据库后，应用服务使用单连接事务提交批次、全部Intent及Outbox，按数据库恢复状态。

执行写入口需要配置服务身份，使用运行环境中的`EXECUTION_SERVICE_TOKEN`（至少32字符），不要写入仓库或日志。身份校验不替代业务授权：当前权威授权适配器尚未接入，创建批次默认拒绝，不能仅凭调用方填写的审批ID创建READY。

`filledQuantity`表示本次增量成交数量；使用Decimal累计判断完成，超量成交拒绝。历史若使用累计回报，必须先审计与迁移，不能直接再次入账。

验证：`pnpm lint`、`pnpm typecheck`、`pnpm test`。事务专项位于`tests/integration/execution-transaction.spec.ts`，必须设置隔离数据库连接；使用随机独立Schema，结束后清理。未配置数据库的跳过不等于集成通过。

完整授权、资源预留和真实事件联调计划见[整改计划](../../docs/development-roadmap-v2/05-portfolio-governance-execution/07-execution-consistency-remediation.md)。
