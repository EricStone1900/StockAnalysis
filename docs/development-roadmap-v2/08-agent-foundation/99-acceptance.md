# 阶段08验收

- [ ] 通用Kernel与Fake Agent纵向闭环通过。
- [ ] DeepSeek、OpenAI兼容和Claude Adapter契约通过。
- [ ] 模型切换不修改Agent业务定义。
- [ ] Tool最小权限和Prompt版本治理通过。
- [ ] Memory M0、Context Manifest和Hash通过。
- [ ] 六个配置隔离部署通过。
- [ ] 所有失败路径结构化且不会默认放行。
- [ ] 尚未实现具体业务Agent Prompt。

## 当前实现证据

- 已实现提交：`586e96e`、`a57e5bd`、`8c0806a`、`4fd0ca9`、`f4465f0`、`5a2e0d6`、`c7211a3`。
- Mac Agent 单元测试 11 项、PostgreSQL 集成测试 1 项通过；ESLint、TypeScript 和 Compose 配置检查通过。
- 已覆盖 Kernel 结构化输出、Tool 预算、三入口幂等、Provider 降级、Tool/Prompt 白名单、Context Hash、Memory M0、Agent ID 隔离和 AgentRun 恢复。
- 尚待人工验收：真实六部署、NATS/Temporal、服务账号权限、Provider 全部失败时的 BLOCKED、日志脱敏和 Ubuntu 故障恢复。

## 人工验收结论

- 状态：**PASS**
- 验收环境：Ubuntu 服务器（容器、PostgreSQL、NATS、Temporal）
- 验收日期：2026-09-05
- 验收依据：按 `05-ubuntu-e2e-verification.md` 完成代码固定、服务启动、HTTP 幂等、六部署隔离、失败路径、消息入口与恢复检查。
- 验收提交：`d9a2c29`
- 备注：具体业务 Agent Prompt 仍属于后续阶段范围，不影响阶段08基础设施验收。
