# workflow-orchestration-service

Temporal 负责时间、顺序、重试和人工等待；领域事实、数据库写入、模型调用与交易执行均由各自服务的 Activity 调用完成。

本地检查：

```sh
pnpm --filter @stock/workflow-orchestration-service lint
pnpm --filter @stock/workflow-orchestration-service typecheck
pnpm --filter @stock/workflow-orchestration-service test
```

Worker 使用 `stock-workflows-v1` Task Queue。每个 Activity 都必须接收 `workflowId`、`runId`、`correlationId` 和 `idempotencyKey`，只返回小结果或 Artifact 引用。
