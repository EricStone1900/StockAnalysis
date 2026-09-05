# 阶段08测试计划

- Kernel生命周期、Tool循环、Schema修复、预算、取消和审计。
- 三类Provider契约、能力路由、切换、限流和成本。
- Tool Registry权限、Prompt Registry版本和Context Hash。
- 时间、新鲜度、证据解析和Prompt注入。
- HTTP、NATS和Temporal三种入口幂等。
- 六部署权限、Task Queue、Consumer和故障隔离。
- Security：无领域数据库写权限、无交易Secret、日志脱敏。
- Recovery：进程/Provider/NATS/Artifact故障。

## 本机验证记录（Mac）

- Agent 服务单元测试：11 项通过，覆盖 Kernel、入口幂等、模型降级、Tool/Prompt/Memory、部署隔离和 PostgreSQL 仓储。
- AgentRun PostgreSQL 集成测试：1 项通过，验证迁移、按 `correlationId` 幂等保存和恢复。
- Agent 服务 ESLint、TypeScript 与 `git diff --check` 通过。
- 真实 NATS、Temporal、Provider 和 Artifact 恢复仍需在 Ubuntu 环境人工验收。
