# 阶段05 Ubuntu 一体化验收

以下命令在 Ubuntu 项目目录执行。连接串、密码和 NATS 凭证只通过环境变量提供，不写入文件或日志。

## 1. 部署与健康检查

```sh
export DECISION_GOVERNANCE_DATABASE_URL='postgresql://<治理用户>:<密码>@postgres:5432/decision_governance'
export TRADE_EXECUTION_DATABASE_URL='postgresql://<执行用户>:<密码>@postgres:5432/trade_execution'
docker compose -f infra/compose/docker-compose.yml pull
docker compose -f infra/compose/docker-compose.yml up -d postgres nats \
  decision-governance-service trade-execution-service portfolio-risk-service
docker compose -f infra/compose/docker-compose.yml ps
```

确认三个服务均为 `healthy`，并分别请求 `3002/ready`、`3003/ready`、`3004/ready`。

## 2. 数据库与消息基础设施

```sh
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U decision_governance -d decision_governance -c '\dt'
docker compose -f infra/compose/docker-compose.yml exec -T postgres \
  psql -U trade_execution -d trade_execution -c '\dt'
curl --fail http://localhost:8222/varz
```

治理库必须有 `trade_proposals`、`decision_budget_reservations`、`governance_outbox_events`；执行库必须有 `rebalance_batches`、`order_intents`、`execution_fills`、`reconciliation_cases`、`execution_outbox_events`。

## 3. 闭环业务验收

使用 `05-local-api-e2e-verification.md` 的接口顺序执行：Proposal → 风险复核 PASS → 人工批准 → 预算 `RESERVED` → `DISPATCHING` → 执行批次及全部 `READY Intent` → `CONSUMED` → 人工提交/Fill → 组合确认成交。

每一步保存响应中的 `proposalVersion`、`budgetReservationId`、`rebalanceBatchId`、`ledgerVersion` 和 `correlationId`，用于审计关联。

## 4. 故障与幂等门禁

- 相同幂等键重复 Proposal、批次、Fill 和成交入账，不得增加记录或账本版本。
- 执行服务停止后恢复，Outbox 事件可重试且不重复发布副作用。
- 执行未接受时预算可 `RELEASED`；已 `CONSUMED` 时释放请求必须失败。
- 任何多 Leg 校验失败不得留下部分 `READY Intent`。

验收结束后记录镜像摘要、迁移版本、测试结果、风险与回滚方式，并在 `99-stage-acceptance.md` 登记最终人工签署。
