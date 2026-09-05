# 阶段10验收

- [ ] 所有核心Workflow及版本测试通过。
- [x] 数据到人工成交/持仓的E2E通过。
- [ ] 风险复核、硬风控和人工审批不可绕过。
- [ ] 修改建议一定重新复核和风控。
- [x] 重复、迟到、重启和恢复无重复副作用。
- [ ] 每日0～2个组合调仓批次、第二批reason、长期HOLD和暂停规则正确。
- [ ] 多Leg一次审批/风控/批次、预算并发和失败释放语义正确。
- [ ] 五类日频与盘中联合回放可复现，并完成成本后差异和尾部风险评审。
- [x] UNKNOWN和对账差异失败关闭。
- [ ] 自动交易Feature Flag仍关闭。
- [ ] Runbook和审计导出可由其他人员执行。

## 历史人工验收结论（仅针对所列基线）

- 状态：**PASS**
- 验收环境：Ubuntu 服务器（Temporal、Worker、PostgreSQL、NATS、容器）
- 验收日期：2026-09-05
- 验收依据：按 `06-ubuntu-e2e-verification.md` 完成工作流顺序与幂等、投资决策门控、人工审批、预算批次、成交状态、Feature Flag 和故障恢复检查。
- 验收代码基线：`a6a3a31`
- 备注：自动交易开关保持关闭，后续阶段仍需遵守人工审批和回放门禁。

## 当前实现证据

- Temporal 基础契约提交：`91a2fb4`；日频量化工作流：`10a4691`；新闻工作流：`37aad02`；盯盘工作流：`835bfd1`；市场状态工作流：`46931c1`。
- 投资决策工作流提交：`3be2a74`；人工审批工作流：`ff441d5`；调仓执行工作流：`5bd2333`；可靠性策略：`da30ea0`。
- Mac 本地 ESLint、TypeScript 和 29 项工作流单元测试通过。
- 已覆盖幂等 Activity、Artifact 引用、门控与 HOLD 短路、人工 Signal、预算释放、UNKNOWN 成交和安全 Feature Flag。
- 当前整改提交的REAL_E2E尚未验收，必须完成 `06-ubuntu-e2e-verification.md` 并记录 Temporal/NATS/数据库/Worker 证据。

## 当前整改提交的验收范围

[整改记录](../../architecture/architecture-remediation-2026-09-05.md)为本次变更证据入口。历史人工PASS仅对应历史基线；本次未签署本阶段REAL_E2E/RELEASE。全部Workflow导出、显式demo模式、真实Activity绑定和接受不确定时保留预算；拒绝以Fake结果代替真实Temporal恢复。

- [x] 补齐当前提交、镜像、迁移、契约版本与报告路径。
- [x] 完成本阶段新增真实场景；授权、资金、幂等和恢复任一失败判FAIL。
- [x] 记录风险、回滚目标和签署人，不以新增文档替代运行验证。

## 2026-09-05 P1 REAL_E2E 验收记录

- 提交：`e8c6342`（P1修复回归测试提交待合并）；本地镜像由该工作区构建，数据库迁移沿用治理、执行和组合风险现有迁移。
- 环境：macOS 本机 Docker Desktop，PostgreSQL、NATS、Temporal、治理服务、组合风险服务、交易执行服务和真实 Temporal Rebalance Worker。
- 工作流：`e2e-workflow-1788607435529`，Task Queue `stock-rebalance-v1`，Temporal 状态 `Completed`，History length `29`。
- 执行批次：`rebalance-e2e-workflow-1788607435529`，Intent 状态 `FILLED`；成交事件通过 Execution Outbox 发布并由 Portfolio Inbox 去重接收。
- 账本：组合 `e2e-portfolio-1788607435529` 从 ledger version 1 更新到 version 2，持仓 `SSE:600000=10`，现金 `99000`。
- 资源：`resource-1788607435529` 最终状态 `SETTLED`；预算、授权、执行内容 Hash 和资源引用一致。
- 自动化：workflow-orchestration 39 tests、trade-execution 43 tests 通过；5 个集成测试按测试环境标记跳过。
- 新增回归覆盖：Outbox 不重复包装事件信封、资源预留推进 `DISPATCHING`、成交 `fillPrice` 映射及真实 Activity 幂等键。
- 风险与回滚：自动交易 Feature Flag 保持关闭；回滚目标为 `e8c6342` 的父提交，保留数据库账本、Inbox、Outbox 和 UNKNOWN 状态，不删除或重放生产委托。
- 签署：自动检查执行者 Codex；人工发布签署人：待指定。该记录只证明隔离本地 REAL_E2E，不代表生产 RELEASE。
