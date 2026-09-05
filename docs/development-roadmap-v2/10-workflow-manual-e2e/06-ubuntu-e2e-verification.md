# 阶段10 Ubuntu 人工验收步骤

本步骤验证 Temporal 工作流、人工审批、组合调仓和可靠性门禁。必须在 Ubuntu 容器环境执行；Mac 单元测试不能替代真实 Worker、Temporal Signal 和故障恢复。

## 1. 固定代码并检查依赖

```sh
git clone https://github.com/EricStone1900/StockAnalysis.git
cd StockAnalysis
git checkout <待验收CommitSHA>
corepack enable
pnpm install --frozen-lockfile
pnpm --filter @stock/workflow-orchestration-service lint
pnpm --filter @stock/workflow-orchestration-service typecheck
pnpm --filter @stock/workflow-orchestration-service test
```

记录 Commit SHA、Node、pnpm、Docker、Compose 和 Temporal CLI 版本。

## 2. 启动 Temporal、数据库、NATS 与 Worker

```sh
docker compose -f infra/compose/docker-compose.yml up -d postgres nats temporal
export WORKFLOW_GLOBAL_PAUSED=false
export WORKFLOW_OBSERVE_ONLY=true
export WORKFLOW_AGENT_ENABLED=false
export WORKFLOW_EXECUTION_ENABLED=false
pnpm --filter @stock/workflow-orchestration-service dev
```

确认 Temporal 服务健康、Worker 已连接 `stock-workflows-v1` Task Queue，且 Worker 重启不会创建重复 Activity 结果。

## 3. 验证工作流顺序与幂等

使用固定 `workflowId`、`runId`、`correlationId` 和幂等键分别运行 DailyQuant、NewsAnalysis、MarketMonitor 和 MarketRegime。检查每一步只保存 Artifact 引用，不把新闻正文、Tick、Prompt 或回测大对象写入 History。重复相同 Workflow/Activity 请求，结果必须一致且不得重复写入。

## 4. 验证投资决策门控

构造以下场景并记录结果：

- 门控失败：直接 `BLOCKED`，不调用 Agent；
- 主决策 `HOLD`：不进入风险复核、预算预留或审批；
- `REBALANCE`：依次通过专业证据、主决策、风险复核和硬风控后才进入人工审批；
- 证据过期、Provider 失败、风险拒绝或硬风控失败：不得生成可审批建议。

## 5. 验证人工审批与调仓执行

通过 Temporal Signal 分别发送批准、拒绝、修改、刷新和超时场景。每个 Signal 必须带原因和幂等键，重复 Signal 不得重复记录。批准后验证预算预留、单个组合 RebalanceBatch、多腿 OrderIntent 和成交回填；拒绝、修改、刷新和超时不得创建订单。

验证第二批仅允许 `INTRADAY_RISK_REDUCTION` 或 `EXECUTION_CORRECTION`；第三批和 `DAILY_TARGET` 第二批必须拒绝。批次创建失败释放预算，已接受后的成交 `UNKNOWN` 必须进入人工处理，禁止自动重下。

## 6. 验证可靠性与故障恢复

逐项切换 Feature Flag：全局暂停、只观察、Agent 禁用、执行禁用。暂停或禁用时应阻止对应路径。重启 Worker、Temporal、NATS 和数据库，确认 Workflow 可恢复、幂等键不变、已接受批次不释放预算。检查阻塞队列、失败日志和审计时间线完整且不含 Secret。

## 7. 验收记录与回滚

保存 Workflow ID、Run ID、Activity ID、Task Queue、Signal、容器日志、Temporal 查询结果、数据库/NATS 状态、Artifact Hash、镜像摘要和验收人。任何时间语义、幂等、预算、T+1、证据、权限或恢复失败均判定 FAIL；回滚到上一已验证 Commit，保持 `WORKFLOW_OBSERVE_ONLY=true` 和 `WORKFLOW_EXECUTION_ENABLED=false`。
