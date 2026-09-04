# 阶段05本机 API 闭环验证

本步骤在 Mac Docker Desktop 上验证 Proposal、预算、执行和组合账本闭环；不连接真实 Agent、券商或生产账户。

## 1. 启动依赖

```sh
export DECISION_GOVERNANCE_DATABASE_URL='postgresql://<治理用户>:<密码>@postgres:5432/decision_governance'
export TRADE_EXECUTION_DATABASE_URL='postgresql://<执行用户>:<密码>@postgres:5432/trade_execution'
docker compose -f infra/compose/docker-compose.yml up -d postgres nats \
  decision-governance-service trade-execution-service portfolio-risk-service
```

确认 `3002`、`3003`、`3004` 的 `/live` 和 `/ready` 均返回 `status=UP`。

## 2. 治理到执行

按以下顺序调用治理 API：

1. `POST /api/v1/proposals` 创建 `REBALANCE` Proposal（先按规范计算 `contentHash`）。
2. `POST /api/v1/proposals/{proposalId}/versions/1/risk-review`，提交 `PASS`。
3. `POST /api/v1/proposals/{proposalId}/versions/1/risk-pass`。
4. `POST /api/v1/proposals/{proposalId}/versions/1/approval`，提交人工 `APPROVED`。
5. `POST /api/v1/proposals/{proposalId}/budget-reservations`，确认返回 `RESERVED`。
6. 调用 `POST .../{reservationId}/dispatching`，确认返回 `DISPATCHING`。
7. 调用执行 `POST /api/v1/execution/batches`，提交全部 Leg；确认一次生成一个批次和全部 `READY` Intent。
8. 使用相同 `idempotencyKey` 重试第 7 步，响应应复用原批次，不增加数据库记录。
9. 执行 `POST .../{reservationId}/consume`，确认返回 `CONSUMED`；消费后不得再释放。

## 3. 人工成交到账

1. 将每个 Intent 状态改为 `SUBMITTED_MANUALLY`。
2. 调用执行成交接口记录 `Fill`，确认完整成交变为 `FILLED`。
3. 调用 `POST /internal/v1/reconciliation/apply-confirmed-fill`，必须携带匹配的 `Idempotency-Key`、`X-Actor-Id` 和 `X-Correlation-Id`。
4. 查询组合最新快照，确认 `ledgerVersion` 递增、持仓和现金按成交价及费用计算。
5. 重复第 3 步，确认仍返回首次快照且版本不再递增。

## 4. 通过标准

- 全链路事件和日志可用同一 `correlationId` 关联。
- 任一失败不会留下部分 `READY Intent`。
- 预算状态严格遵循 `RESERVED → DISPATCHING → CONSUMED`；未接受批次才允许 `RELEASED`。
- 重复 Proposal、批次、事件和成交均无重复副作用。
- 本机通过后，再按各服务 `03/04-ubuntu-verification.md` 在 Ubuntu 执行真实 NATS/PostgreSQL 验收。
