# 阶段09：六个业务Agent

## 目标

在已验收Agent Kernel上依次实现四个专业Agent、主决策Agent和独立风险复核Agent。所有领域服务已稳定，Agent只读取结构化证据并输出建议。

## 顺序

1. [四个专业Agent](./01-specialist-agents.md)。
2. [主决策Agent](./02-main-decision-agent.md)。
3. [风险复核Agent](./03-risk-review-agent.md)。
4. [Golden Dataset与跨模型评估](./04-golden-evaluation.md)。
5. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

- Agent不能写领域数据库、运行量化/策略插件、修改RiskPolicy、批准建议或创建Order。
- 所有结论引用evidenceIds和validUntil。
- 主决策与风险复核逻辑、模型Profile、Tool权限和运行记录独立。

