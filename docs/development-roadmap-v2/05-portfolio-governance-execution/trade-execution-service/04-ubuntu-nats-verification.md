# trade-execution-service Ubuntu 与 NATS 验收

## 1. 启动服务

```sh
cd "$STOCK_ROOT/services/trade-execution-service"
export TRADE_EXECUTION_DATABASE_URL='postgresql://trade_execution:<password>@127.0.0.1:5433/trade_execution'
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm test:integration
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm dev
```

检查 `3004/live` 和 `3004/ready` 均成功，确认迁移创建 `rebalance_batches`、`order_intents`、`execution_fills`、`reconciliation_cases` 和 `execution_outbox_events`。

## 2. 执行链路

提交包含 `decisionId`、`approvalId`、`riskEvaluationId`、`budgetReservationId` 和有效期的批准批次。确认一次请求创建一个批次及全部 `READY` Intent；重复幂等键不得重复创建。

将 Intent 更新为 `SUBMITTED_MANUALLY`，提交部分和完全成交，检查 `execution_fills`、Intent 状态及审计 Outbox 同步变化。未知订单、过期批准和 Hash 不匹配必须失败。

## 3. 对账处理

创建 `OPEN` 对账差异，人工标记 `RESOLVED` 或 `IGNORED`，确认理由、时间和状态均写入数据库。已关闭差异不可再次修改。

## 4. NATS 发布与恢复

接入 JetStream Publisher 后订阅以下 subject：

- `stock.trade-execution.rebalance-batch.created.v1`
- `stock.trade-execution.fill.recorded.v1`
- `stock.trade-execution.reconciliation.opened.v1`

发布成功必须写入 `published_at`；发布失败不确认，租约到期后可重试。重启服务后批次、成交、对账差异和未发布事件均应保持。

## 5. 验收记录

记录 commit、镜像 digest、迁移版本、测试命令、API 响应、SQL 查询和 NATS 消息。任何未经批准的执行、部分写入、成交丢失或事件丢失均判定 FAIL。
