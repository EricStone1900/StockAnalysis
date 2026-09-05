# workflow-orchestration-service

Temporal 负责时间、顺序、重试和人工等待；领域事实、数据库写入、模型调用与交易执行均由各自服务的 Activity 调用完成。

本地检查：

```sh
pnpm --filter @stock/workflow-orchestration-service lint
pnpm --filter @stock/workflow-orchestration-service typecheck
pnpm --filter @stock/workflow-orchestration-service test
```

Worker 使用 `stock-workflows-v1` Task Queue。每个 Activity 都必须接收 `workflowId`、`runId`、`correlationId` 和 `idempotencyKey`，只返回小结果或 Artifact 引用。

可靠性默认配置为只观察模式，Agent 和交易执行均关闭。必须显式设置 `WORKFLOW_AGENT_ENABLED=true`、`WORKFLOW_EXECUTION_ENABLED=true` 才能放行对应路径；任何 `WORKFLOW_GLOBAL_PAUSED=true` 都会阻断全部 Workflow。
