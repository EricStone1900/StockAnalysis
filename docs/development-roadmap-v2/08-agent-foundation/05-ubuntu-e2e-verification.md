# 阶段08 Ubuntu 人工验收步骤

本文用于在 Ubuntu 服务器上验证阶段08的可运行性、隔离性和恢复能力。本机 Mac 验证不能替代其中的容器、NATS、Temporal 与权限检查。

## 1. 固定代码与依赖

```sh
git clone https://github.com/EricStone1900/StockAnalysis.git
cd StockAnalysis
git checkout <已验证的CommitSHA>
corepack enable
pnpm install --frozen-lockfile
pnpm --filter @stock/agent-service lint
pnpm --filter @stock/agent-service typecheck
pnpm --filter @stock/agent-service test
```

记录 Commit SHA、Node、pnpm、Docker 和 Compose 版本；依赖必须来自锁文件。

## 2. 启动数据库与 Agent 服务

```sh
docker compose -f infra/compose/docker-compose.yml up -d postgres
docker compose -f infra/compose/docker-compose.yml up -d agent-service
curl --fail http://127.0.0.1:3009/live
docker compose -f infra/compose/docker-compose.yml ps
```

确认 `agent_runtime` 数据库可连接，且 `agent_runs` 迁移已执行。服务健康检查和迁移成功是后续测试的前置条件。

## 3. HTTP 入口与幂等

向 `POST http://127.0.0.1:3009/internal/v1/agent-runs/fake-analysis` 发送合法 JSON，包含固定 `correlationId`、`agentId` 和上下文。使用同一请求重复发送两次，确认返回的 `runId`、输出和状态一致，数据库仅有一条对应 AgentRun；更换 `correlationId` 应生成新运行。

## 4. 六部署隔离

逐一检查六个允许的 `AGENT_ID`、独立 `taskQueue`、durable consumer 和服务账号。故意配置未知 Agent ID 或共享队列后重启，服务必须拒绝启动；单个部署停止不得影响其他部署。

## 5. 权限、证据与模型失败路径

验证未授权 Tool、副作用 Tool、未批准 Prompt，以及 `FUTURE`/`UNRESOLVED` Context Hash 均被拒绝。模拟主 Provider 超时、429、无效 JSON、成本超限，确认自动切换到兼容 Provider；全部 Provider 失败时必须返回结构化 `BLOCKED`/`FAILED`，不得默认放行。

## 6. NATS、Temporal 与恢复

通过批准的 subject/queue 投递一次任务，再投递相同 `eventId`，确认只产生一次 AgentRun。停止并重启 NATS、Agent 容器和 Temporal worker，确认任务按重试策略恢复且不会重复执行。检查日志不得出现 API key、数据库密码或完整敏感上下文。

## 7. 记录、失败处理与回滚

保存命令输出、容器日志、镜像摘要、迁移版本、配置摘要和验收人。任何硬风控、时间语义、数据质量、幂等、权限或恢复失败均判定 FAIL；保留日志后执行 `docker compose ... down`，回滚到上一已验证 SHA，禁止手工修改生产数据库。
