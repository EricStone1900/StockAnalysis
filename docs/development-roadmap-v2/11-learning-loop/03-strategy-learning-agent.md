# 11-03 交易复盘与策略学习Agent

## 定位

新增`strategy-learning-agent`作为研究侧部署，复用agent-service Kernel，但不进入盘中决策链。六个生产决策Agent保持不变。

## 实施步骤

1. 输入为已关闭Outcome窗口、Decision Memory、人工反馈、反例和当前StrategyVersion，不读取未来结果。
2. 单次复盘输出成功/失败归因、原假设验证、风险遗漏、人工修改影响和待观察问题。
3. 每周聚合复盘；满足最小样本、独立窗口和观点多样性后才能生成StrategyMemoryDraft。
4. 每月/季度可生成ResearchHypothesis或ExperimentRequest，交给research-automation-service。
5. Tool白名单只允许读Outcome/Memory/Strategy信息和创建草稿/实验请求；无Registry激活、Prompt发布、RiskPolicy或Order权限。
6. 结果必须同时列出支持样本和反例，声明真实/拒绝/HOLD/Shadow样本数量。

```ts
interface StrategyLearningDraft {
  title: string;
  hypothesis: string;
  applicability: { regimes: string[]; horizons: number[] };
  supportingDecisionIds: string[];
  counterexampleDecisionIds: string[];
  sampleBreakdown: Record<string, number>;
  proposedExperiment: object;
  status: 'DRAFT';
}
```

## 测试

- 单次Outcome不能发布经验。
- 小样本、无反例或样本混用必须输出证据不足。
- Agent不能修改ACTIVE策略或生产Prompt。

