# workflow-orchestration-service

`pnpm dev`只启动HTTP健康服务，不启动Temporal Worker。Worker入口为`pnpm worker`，导出健康、量化、新闻、盯盘、市场状态、投资决策、人工审批和执行工作流。

当前Activity实现仍为Fake。只有显式设置`WORKFLOW_RUNTIME_MODE=demo`且`WORKFLOW_EXECUTION_ENABLED=false`、非production环境才允许Worker启动。真实模式会失败关闭，不能把demo运行签署为真实服务E2E。

执行工作流遇到接受响应不确定或接受后步骤失败返回UNKNOWN，不释放预算。仅权威返回明确未接受时释放。后续仍需实现真实Activity、按原幂等键查询恢复和持久化事件接入。

本地验证：`pnpm lint`、`pnpm typecheck`、`pnpm test`；单元测试包含实际工作流函数的异常路径，但不替代真实Temporal测试。
