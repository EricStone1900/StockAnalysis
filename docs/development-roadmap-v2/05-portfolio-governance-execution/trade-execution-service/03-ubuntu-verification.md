# trade-execution-service Ubuntu 验证

## 1. 启动与迁移

```sh
cd "$STOCK_ROOT/services/trade-execution-service"
export TRADE_EXECUTION_DATABASE_URL='postgresql://trade_execution:<password>@127.0.0.1:5433/trade_execution'
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm test:integration
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm dev
```

检查：

```sh
curl --fail http://127.0.0.1:3004/live
curl --fail http://127.0.0.1:3004/ready
```

确认迁移已创建 `rebalance_batches` 和 `order_intents`。密码不能写入仓库或日志。

## 2. 批次与 Intent 验证

使用已批准 Proposal、RiskEvaluation 和 BudgetReservation 引用调用批次接口。确认一次请求创建一个批次及全部 `READY` Intent；重复 `Idempotency-Key` 不得创建重复批次。

依次将 Intent 更新为 `SUBMITTED_MANUALLY`、`PARTIALLY_FILLED`、`FILLED`，非法跃迁和 `UNKNOWN` 自动重建必须失败。检查数据库中的状态与 API 返回一致。

## 3. 重启恢复

停止并重新创建服务容器，再查询原批次和 Intent。批次 ID、审批引用、Proposal 版本和 Intent 状态必须保持不变；不得因服务重启重新生成订单意图。

## 4. 验收记录

记录 commit、镜像 digest、迁移版本、测试命令、API 响应和数据库查询结果。未批准、过期批准、Hash 不匹配、部分写入或重启后状态丢失均判定 FAIL。
