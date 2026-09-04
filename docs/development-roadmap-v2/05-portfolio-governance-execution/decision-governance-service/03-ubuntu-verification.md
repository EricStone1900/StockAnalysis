# decision-governance-service Ubuntu 验证

## 1. 启动与迁移

```sh
cd "$STOCK_ROOT/services/decision-governance-service"
export DECISION_GOVERNANCE_DATABASE_URL='postgresql://decision_governance:<password>@127.0.0.1:5433/decision_governance'
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm test:integration
COREPACK_HOME="$STOCK_ROOT/.corepack" pnpm dev
```

检查：

```sh
curl --fail http://127.0.0.1:3003/live
curl --fail http://127.0.0.1:3003/ready
```

确认数据库迁移已创建 `trade_proposals`、`decision_budget_reservations` 和 `governance_outbox_events`。真实密码不得写入仓库或日志。

## 2. Proposal 流程

依次调用创建 Proposal、绑定 RiskReview、标记 Risk PASS 和人工审批接口。检查 Proposal 状态严格按以下顺序变化：

`DRAFT → RISK_REVIEWED → RISK_PASSED → APPROVED/REJECTED`

使用错误版本、非 PASS 评估或缺失审批信息时必须返回 400，旧版本不能被覆盖。

## 3. 调仓预算

同一组合同一交易日创建第一批应返回 `batchNumber=1`；第二批只有允许原因可以成功；第三批必须失败；`HOLD` 返回释放状态且不占用批次。重启服务后再次检查数据库，批次数不得归零。

## 4. Outbox 与 NATS

检查 `governance_outbox_events` 中事件主题、Proposal ID 和版本。接入真实 JetStream Publisher 后，成功发布必须写入 `published_at`；发布失败不得写入，30 秒租约到期后应可再次领取。重复事件 ID 不得产生重复记录。

## 5. 验收记录

记录 commit、镜像 digest、迁移版本、测试命令、API 响应和数据库查询结果。任一状态越权、预算超限、事件丢失或数据库不可用时判定 FAIL。
