# 11-04 候选实验、验证与晋升

## 实施步骤

1. StrategyLearningDraft经人工选择后创建ResearchExperiment，不直接改生产策略。
2. RD-Agent在Sandbox生成候选因子、参数、模型或Strategy Plugin。
3. quant-research独立复算PIT、样本外、Walk-forward、成本、换手、容量、Regime和相关性。
4. 使用Champion/Challenger：候选先历史回放，再Shadow；与NO_TRADE和当前ACTIVE策略比较。
5. 只有达到预先登记门槛且人工批准，才能创建/激活新StrategyVersion或StrategyMemoryVersion。
6. 发布后持续监控漂移、回撤、相对表现和失效条件；触发时SUSPEND或回滚，不在线调参。

```text
Outcomes -> Learning Draft -> Human Select
  -> RD-Agent Experiment -> Independent Quant Validation
  -> Challenger Shadow -> Human Approval
  -> ACTIVE Version -> Monitor/Suspend/Rollback
```

## 防偏差要求

- 训练、选择和最终验证样本隔离。
- 多重试验和数据窥探记录实验家族与预算。
- 不以胜率单指标晋升；必须包含收益、回撤、成本、容量和稳定性。
- 人工拒绝/HOLD的机会收益只作为反事实指标。

