# 阶段11：交易复盘与策略学习闭环

## 目标

在人工交易事实稳定后，建立确定性Outcome、Decision Memory、受治理Strategy Memory和候选策略研究闭环，让系统逐步积累经验但不能在线自我修改生产规则。

领域基线见[Agent Memory设计](../../architecture/agent-memory-design.md)、[自动研究服务](../../architecture/services/research-automation-service.md)和[日频策略平台](../../architecture/services/daily-strategy-extension-design.md)。

## 顺序

1. [Outcome Evaluator](./01-outcome-evaluator.md)。
2. [Decision Memory投影与检索](./02-decision-memory.md)。
3. [交易复盘与策略学习Agent](./03-strategy-learning-agent.md)。
4. [候选实验、验证和晋升](./04-learning-promotion-loop.md)。
5. [测试](./90-test-plan.md)与[验收](./99-acceptance.md)。

## 边界

- 数值结果由确定性代码计算，LLM只解释和提出候选假设。
- 真实成交、人工拒绝、HOLD和Shadow样本必须分类型保存，不混合收益口径。
- Strategy Memory和候选策略不能自动成为ACTIVE。
- 单次盈利或亏损不得形成生产规则。


## 纵向交付依赖调整

依据[ADR-020](../../architecture/adr/ADR-020-execution-consistency-and-delivery-gates.md)，本阶段增强能力不阻塞M1只读分析与M2隔离人工闭环；本阶段自身S0～S6、数据与安全测试及签署要求不变。验收应验证未启用本阶段时依赖方明确降级，不能伪造新闻、市场状态或学习结果；生产启用仍需原有门禁。
