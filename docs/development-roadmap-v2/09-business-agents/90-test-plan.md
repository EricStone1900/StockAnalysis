# 阶段09测试计划

- 六个Agent的输入/输出Schema、证据、新鲜度和权限。
- 专业Agent领域边界与禁止Tool。
- 主Agent策略共识、冲突、HOLD和成本解释。
- 风险Agent独立证据判断、反方情景和四类结论。
- DeepSeek/Claude跨模型分歧合并。
- Prompt注入、幻觉证据、超时、限流、上下文超限和Provider全故障。
- AgentRun、Context Manifest、ModelRun、ToolCall和Artifact审计。
- NATS重复任务和多部署故障隔离。

所有BUY/SELL输出必须能从evidenceIds重建；失败时默认阻塞而不是放行。

