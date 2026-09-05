# 阶段09测试计划

- 六个Agent的输入/输出Schema、证据、新鲜度和权限。
- 专业Agent领域边界与禁止Tool。
- 主Agent策略共识、冲突、HOLD、组合级多Leg建议和成本解释。
- 风险Agent独立证据判断、反方情景和四类结论。
- DeepSeek/Claude跨模型分歧合并。
- Prompt注入、幻觉证据、超时、限流、上下文超限和Provider全故障。
- AgentRun、Context Manifest、ModelRun、ToolCall和Artifact审计。
- NATS重复任务和多部署故障隔离。

所有RebalanceLeg必须能从evidenceIds和目标组合版本重建；失败时默认阻塞而不是放行。

## 当前本机验证记录（Mac）

- 四个专业 Agent Fake 契约、主决策 Agent、风险复核 Agent 与 Golden 评估均已实现。
- Agent 服务 ESLint、TypeScript 和 `git diff --check` 通过。
- 当前单元测试：34 项通过；PostgreSQL 仓储集成测试 1 项因未配置数据库跳过。
- Golden Fixture：6 个 Agent 各 10 个，共 60 个；覆盖提示注入、证据冲突、过期数据、风险拒绝、幻觉证据、多股票组合和盘中风险减仓。
- 尚待 Ubuntu 人工验收：真实六部署、NATS/Temporal 入口、Provider 配置、权限隔离、容器恢复和故障日志脱敏。
