# 阶段09 Ubuntu 人工验收步骤

本步骤用于验证阶段09在 Ubuntu 容器环境中的独立部署、消息入口、组合级建议和风险门禁。Mac 单元测试不能替代真实服务、NATS、Temporal 和权限检查。

## 1. 固定版本与基础检查

```sh
git clone https://github.com/EricStone1900/StockAnalysis.git
cd StockAnalysis
git checkout <待验收CommitSHA>
corepack enable
pnpm install --frozen-lockfile
pnpm --filter @stock/agent-service lint
pnpm --filter @stock/agent-service typecheck
pnpm --filter @stock/agent-service test
```

记录 Commit SHA、Node、pnpm、Docker 和 Compose 版本，确认依赖来自锁文件。

## 2. 启动六个独立 Agent 部署

为 `stock-analysis`、`financial-news`、`market-monitor`、`market-state`、`main-decision`、`risk-review` 分别配置独立的 `AGENT_ID`、Task Queue、NATS Durable Consumer、模型 Profile 和服务账号。逐个启动并检查：

```sh
docker compose -f infra/compose/docker-compose.yml up -d postgres nats temporal agent-service
docker compose -f infra/compose/docker-compose.yml ps
curl --fail http://127.0.0.1:3009/live
```

故意使用未知 `AGENT_ID`、共享 Queue 或共享 Durable Consumer 重启一个实例；服务必须拒绝启动，且其他 Agent 不受影响。

## 3. 专业 Agent 输入边界

分别投递合法的 DailyAnalysisSnapshot、NewsEventCandidate、MarketAnomalyEvent 和 MarketRegimeSnapshot Fixture。确认输出包含原始 `evidenceIds`、有效期和结构化 Schema。再投递快照外股票、过期/未来证据、新闻提示注入、连续 Tick、原始行情或 RiskPolicy 写请求，确认请求被拒绝且没有领域数据库写入。

## 4. 主决策组合级 Proposal

投递包含策略、新闻、异常、Regime、组合和专业评估的完整 Context Manifest。确认：

- `NO_REBALANCE` 只产生一个 `HOLD`，且 `legs=[]`；
- 再平衡只产生一个组合级 Proposal，所有 legs 与目标组合版本一致；
- 多股票目标不能拆成多个单票 Proposal；
- 任一策略过期、证据缺失、风险升级或 Provider 全失败时不得生成可用 BUY；
- 输出不创建 Approval、DecisionBudgetReservation、RebalanceBatch 或 OrderIntent。

## 5. 风险复核与跨模型门禁

使用完整且 Hash 正确的 `RiskReviewEvidencePacket` 验证 `PASS`。分别篡改 Hash、提高换手/成本/滑点、删除 leg 证据、模拟 Provider 不可用和让第二 Reviewer 返回 `REJECT`，确认结果分别为拒绝、证据不足或保守合并后的更高风险结论。风险复核不得修改原 Proposal。

## 6. Golden 回归与恢复

执行 60 个 Golden Fixture，确认结构化输出率、证据引用率、安全断言和 reasonCode 覆盖率均达门槛，任何失败都将 `releaseBlocked=true`。重复投递同一 `correlationId`/`eventId` 不得产生重复 AgentRun；重启 Agent、NATS 和 Temporal worker 后任务按策略恢复且不重复执行。

## 7. 记录与判定

保存测试输出、容器日志、镜像摘要、配置摘要、Golden 报告、迁移版本和验收人。硬风控、时间语义、证据、幂等、权限或恢复失败均判定 FAIL；通过后在 `99-acceptance.md` 记录 SHA、风险、回滚版本和签署人。
