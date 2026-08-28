# 09-03 端到端测试与发布准备

## 目标

验证从每日数据到人工成交的完整链路，并形成第一版可日常使用的发布门禁。

## E2E场景

### 场景A：正常买入

```text
DataVersion READY
 -> DailyAnalysisSnapshot
 -> 新闻/Regime上下文
 -> 主Agent BUY
 -> 风险复核 PASS
 -> 硬风控 PASS
 -> 人工批准
 -> OrderIntent READY
 -> 人工Fill
 -> PortfolioSnapshot更新
```

断言每一步引用同一decisionId/correlationId和正确版本。

### 场景B：长期HOLD

连续模拟多个交易日，主Agent均HOLD。断言没有审批、OrderIntent和“补交易”，但建议和证据被审计。

### 场景C：安全拒绝

风险复核PASS，但硬风控因每日批次或仓位拒绝。断言不能人工强行approve进入执行；需要新版本或策略发布。

### 场景D：故障恢复

在模型Activity、Outbox发布和成交应用前后分别停止Worker，恢复后断言无重复建议、订单或流水。

## 发布检查

- 备份和恢复演练。
- Temporal、业务DB、MinIO备份隔离。
- 所有Feature Flag默认人工模式。
- 告警和Runbook可用。
- 生产密钥不在镜像和日志中。
- 关键Dashboard显示freshness和系统状态。

## 验证命令示例

```bash
pnpm test
python -m pytest
pnpm test:e2e
pnpm test:contracts
```

具体脚本名称以仓库实现为准，但根README必须提供一条完整验证命令。

## 完成条件

- 所有关键E2E场景自动化或有明确人工步骤和证据。
- 未解决的P0/P1问题为0。
- 经过一段只观察运行后再开始记录真实人工交易。
