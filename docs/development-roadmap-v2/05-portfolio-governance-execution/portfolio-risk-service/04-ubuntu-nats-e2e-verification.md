# Ubuntu PostgreSQL + NATS JetStream 端到端验收

## 1. 启动依赖

在仓库根目录执行：

```sh
cd "$STOCK_ROOT"
./scripts/infra-up.sh
docker compose -f infra/compose/docker-compose.yml ps postgres nats
```

确认 PostgreSQL 与 NATS 状态为 `running`。组合服务使用独立数据库，不得复用其他服务账号。

## 2. 迁移并启动组合服务

```sh
export PORTFOLIO_DATABASE_URL='postgresql://portfolio_risk:<password>@127.0.0.1:5433/portfolio_risk'
cd "$STOCK_ROOT/services/portfolio-risk-service"
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm test:integration
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm dev
```

另开终端检查：

```sh
curl --fail http://127.0.0.1:3002/live
curl --fail http://127.0.0.1:3002/ready
```

`ready` 必须显示 PostgreSQL 为 `UP`；NATS 未绑定到启动组合根时，不得伪装成已发布。

## 3. 检查评估事件

调用风险评估接口后，在 PostgreSQL 中检查：

```sql
select evaluation_id, proposal_id, policy_version, verdict
from portfolio_risk_evaluations order by created_at desc limit 5;

select event_id, subject, published_at
from portfolio_outbox_events order by created_at desc limit 5;
```

评估记录和 Outbox 事件必须同时出现，subject 必须为 `stock.portfolio-risk.risk-evaluation.created.v1`。

## 4. JetStream 验收

当部署层已注入 NATS Client 并启用 Worker 后，使用 NATS CLI 或既有订阅工具订阅上述 subject。再次提交相同提案，数据库只能保留一条评估和一条 Outbox 事件；成功收到消息后该事件的 `published_at` 应非空。

临时停止订阅端或令 Publisher 返回错误，确认 `published_at` 保持为空；等待 30 秒租约到期后再次启动订阅端，事件应可重新领取并最终标记发布。失败期间 `/ready` 和账本写入必须保持可用。

## 5. 验收记录

记录 Git commit、镜像 digest、迁移版本、测试命令和 SQL 查询结果。若无法保留服务器证据，至少由人工确认上述检查项并记录通过时间与签署人。
