# 阶段06 Ubuntu 人工验收步骤

本文用于目标 Ubuntu 服务器的独立验收。Mac 本机测试通过不代表以下项目已通过。

## 1. 获取代码并准备环境

```sh
git clone https://github.com/EricStone1900/StockAnalysis.git
cd StockAnalysis
git checkout <待验收CommitSHA>
docker --version
docker compose version
```

确认 Docker Compose 可用，且磁盘至少预留 10GB。不要把生产密钥写入仓库或命令历史。

## 2. 准备配置

在 `infra/compose/.env` 或当前 Shell 中设置测试数据库 URL：

```sh
export NEWS_INTELLIGENCE_DATABASE_URL='postgresql://news_intelligence:<password>@postgres:5432/news_intelligence'
export DECISION_GOVERNANCE_DATABASE_URL='postgresql://decision_governance:<password>@postgres:5432/decision_governance'
export TRADE_EXECUTION_DATABASE_URL='postgresql://trade_execution:<password>@postgres:5432/trade_execution'
```

密码只从服务器 Secret 或密码管理器读取，不提交文件。先验证配置展开：

```sh
docker compose -f infra/compose/docker-compose.yml config --quiet
```

## 3. 启动并检查服务

```sh
docker compose -f infra/compose/docker-compose.yml up -d postgres minio nats
docker compose -f infra/compose/docker-compose.yml up -d news-intelligence-service market-monitor-service market-regime-service
docker compose -f infra/compose/docker-compose.yml ps
curl --fail http://127.0.0.1:3005/live
curl --fail http://127.0.0.1:3006/live
curl --fail http://127.0.0.1:3007/live
```

三服务均为 `running` 且健康检查通过后再继续；失败时保存 `docker compose logs --tail=200 <service>`。

## 4. 契约与边界验证

```sh
python3 scripts/stage06-contract-smoke.py
```

预期输出 `stage06 contract smoke: PASS`。随后分别调用新闻 Candidate、盯盘异常和 Regime classify 接口，确认响应包含版本、证据引用和时间字段；重复使用同一 `agentRunId` 或异常窗口不得产生第二条事实。

## 5. 质量与故障关闭

停止 MinIO 或模拟 Provider 不可用，确认新闻/行情不会返回伪正常结果；行情超过 180 秒、覆盖率不足或特征质量 `FAIL` 时必须返回 `STALE/FAIL`。恢复依赖后再次检查服务可用，但不得自动补写已失败窗口。

## 6. 容量与审计

使用 Fixture 执行 50 支 Watchlist 的连续窗口测试，确认每轮只产生一次批量请求，P0/P1/P2 复用快照；80 支只能在稳定性门禁通过后启用，100 支仅做压力测试。检查日志含 source、schema/adapter 版本、quality、quoteAgeSeconds 和 sourceChange，不含密钥或正文敏感信息。

## 7. 记录与回滚

记录 Commit SHA、镜像摘要、迁移版本、命令输出、失败窗口和人工签署人。验收失败时执行 `docker compose down`，保留日志；不得以跳过质量门禁或手工改库方式判定 PASS。
