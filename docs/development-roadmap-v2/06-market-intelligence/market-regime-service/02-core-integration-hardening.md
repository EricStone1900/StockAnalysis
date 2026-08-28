# Regime 06-02 状态机、回放与强化

## 实施步骤

1. 实现RISK_ON、NEUTRAL、RISK_OFF、STRESS确定性状态规则。
2. 实现进入/退出阈值、迟滞、最短持续窗口和极端事件快速降级。
3. 发布不可变MarketRegimeSnapshot；状态变化发布changed事件，未变化只发布快照事实。
4. 使用ruptures研究变化点，用Qlib评估不同Regime下策略表现；两者不能直接改变ACTIVE定义。
5. River状态模型先Shadow，验证漂移和稳定性后才能进入版本化定义。
6. 数据FAIL保留上一快照并显式stale，不能静默延长有效期。

## 测试

- 阈值附近不频繁抖动。
- STRESS快速进入且满足条件后受控退出。
- 数据失败、重复、迟到和版本变化。
- 历史回放能重建相同状态序列和Hash。

