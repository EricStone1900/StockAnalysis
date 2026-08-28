# 阶段00验收

## 人工验收步骤

1. 阅读[阶段总设计](./00-stage-design.md)与[详细实施计划](./04-detailed-implementation-plan.md)，确认没有提前实施业务服务或基础设施。
2. 审阅[服务目录](./05-service-catalog-baseline.md)，抽查 `PortfolioSnapshot`、`TradeProposal`、`Order/Fill`：每项均只有一个写入 Owner，且平台服务不拥有可写副本。
3. 审阅[依赖与通信基线](./06-dependency-communication-baseline.md)，沿每日研究、盘中监控和低频决策链路逐跳检查：不存在环路，REST/NATS/Temporal 各自职责清晰。
4. 审阅[共享语义](./07-shared-semantics-contract-baseline.md)，确认 `SecurityId`、Decimal、UTC/`Asia/Shanghai`、交易日、`DataVersion`、`availableAt` 与历史回放规则可直接用于阶段 01 契约实现。
5. 打开[ADR 登记](../../architecture/adr/ADR-001-018-register.md)，逐项确认状态。ADR-002、003、004、015、016 必须为 `ACCEPTED`；其余未决项必须有责任人、阻塞范围和后续决策时间。
6. 按[测试计划](./90-test-plan.md)核对 T00-01 至 T00-13 的证据。出现 P0/P1、所有权冲突、未知共享概念或未通过硬门禁时，立即判定 FAIL。
7. 确认遗留项均不影响阶段 01 的边界、契约或基础设施选择；否则将其转为 ADR 阻塞项并停止进入下一阶段。

## 验收清单

- [ ] 服务目录和 Owner 已冻结。
- [ ] Database/User、REST、事件与 Workflow 边界明确。
- [ ] 依赖图无循环，平台服务无领域事实写入权。
- [ ] `SecurityId`、Decimal、时区、交易日、`DataVersion` 和 `availableAt` 规则明确。
- [ ] ADR-002、003、004、015、016 已确认，其余 ADR 有可追溯状态。
- [ ] T00-01 至 T00-13 均有 PASS 证据，且无未解决 P0/P1。
- [ ] 阶段 01 不依赖未定义的共享概念。

## 验收记录

```text
阶段/服务：阶段 00：架构与开发基线
代码提交：
契约版本：v1 草案
测试命令/审查记录：
测试报告：
覆盖的风险场景：
未完成项：
已知风险：
回滚方案：恢复到上一版架构文档；未创建运行时资源
验收人/日期：
结论：PASS | CONDITIONAL_PASS | FAIL
```

`CONDITIONAL_PASS` 不适用于事实所有权、时间语义、幂等、权限、ADR 硬门禁或依赖环；这些问题只能判定 `FAIL`。
