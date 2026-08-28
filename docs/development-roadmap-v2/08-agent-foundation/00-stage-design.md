# 阶段08：Agent基础框架

## 目标

先独立交付通用`agent-service` Kernel、多模型网关、Tool/Prompt Registry和Memory M0，再开发任何业务Agent。

领域基线见[Agent Runtime](../../architecture/services/agent-runtime-service.md)和[Agent Memory](../../architecture/agent-memory-design.md)。

## 顺序

1. [Agent Kernel与运行状态](./01-agent-kernel.md)。
2. [多模型网关](./02-model-gateway.md)。
3. [Tool、Prompt和Memory M0](./03-tools-prompts-memory.md)。
4. [同镜像多部署与生产强化](./04-deployment-hardening.md)。
5. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

本阶段只实现Fake示例Agent，不实现股票、新闻、盯盘、Regime、主决策或风险复核业务Prompt。

