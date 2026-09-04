# Outbox 配置与 Ubuntu 验证

## 当前默认行为

Portfolio 服务默认不启动 Outbox Worker。当前阶段已完成事件落库、领取和生命周期骨架，但尚未绑定生产消息总线；未配置 Publisher 时服务启动不会尝试发送事件。

## Ubuntu 验证前置

在 Ubuntu 服务器上准备 PostgreSQL，并设置组合服务数据库连接：

```sh
export PORTFOLIO_DATABASE_URL='postgresql://portfolio_risk:<password>@127.0.0.1:5433/portfolio_risk'
```

不要把真实密码写入仓库、日志或提交记录。执行迁移并确认表存在：

```sh
cd "$STOCK_ROOT/services/portfolio-risk-service"
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm exec tsx -e "import { readFile } from 'node:fs/promises'; import { Client } from 'pg'; const c=new Client({connectionString:process.env.PORTFOLIO_DATABASE_URL}); await c.connect(); await c.query(await readFile('migrations/001_portfolio_ledger.sql','utf8')); const r=await c.query(\"select to_regclass('portfolio_risk_evaluations'), to_regclass('portfolio_outbox_events')\"); console.log(r.rows[0]); await c.end();"
```

预期两个表名均返回非空值。

## 事件落库与幂等

```sh
PORTFOLIO_DATABASE_URL="$PORTFOLIO_DATABASE_URL" COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm test:integration
```

重点确认风险评估集成测试通过。同一 `proposal_id + policy_version` 重复评估只能保留一条评估记录和一条 Outbox 事件。

## 发布 Worker 验证

当前版本不启用真实发布器。后续接入消息总线后，必须显式配置启用，并人工验证：成功发布后写入 `published_at`；发布失败不写入 `published_at`；租约到期后可以再次领取；发布失败不阻塞健康检查或组合账本写入。
