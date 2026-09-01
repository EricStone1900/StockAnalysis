# 09-04 Golden Dataset与跨模型评估

## 实施步骤

1. 每个专业Agent建立至少10～20个版本化Fixture；主决策和风险复核覆盖完整组合情景。
2. Fixture包含输入快照、允许证据、禁止推断、期望Schema、关键reasonCode和安全断言。
3. 评估结构化有效率、证据引用率、遗漏风险、过度交易、校准、稳定性和成本。
4. 同一Context Manifest分别运行DeepSeek、OpenAI兼容模型和Claude；比较但不要求自然语言相同。
5. Prompt或模型升级必须对固定Golden集回归；P0安全退化阻止发布。

## 必含场景

- 新闻Prompt注入、证据冲突、过期数据。
- 量化看多但Regime/成本不支持。
- 异常行情最终HOLD。
- 连续数周无交易。
- 主AgentBUY而风险AgentREJECT。
- 模型幻觉不存在evidenceId。
- 一次多股票目标组合只形成一个Proposal；拆票规避每日批次必须失败。
- 盘中异常允许风险减仓但不产生第二批新Alpha调仓。

评估结果保存AgentVersion、PromptVersion、ModelProfile和FixtureVersion。
