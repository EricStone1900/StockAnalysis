# 07-02 Regime评分、迟滞和状态机

## 目标

把特征映射为RISK_ON、NEUTRAL、RISK_OFF或STRESS，并避免频繁抖动。

## 实施步骤

### 1. 维度评分

```python
score = (
    weights.trend * trend_score
    + weights.breadth * breadth_score
    + weights.volatility * volatility_score
    + weights.liquidity * liquidity_score
)
```

权重、标准化方式和阈值组成RegimeDefinitionVersion。

### 2. 状态机

```python
def next_regime(current: Regime, score: float, confirms: int, hard_event: bool) -> Regime:
    if hard_event:
        return Regime.STRESS
    if current == Regime.RISK_ON and score < EXIT_RISK_ON and confirms >= MIN_CONFIRM:
        return Regime.NEUTRAL
    # 其他状态转换显式实现
    return current
```

进入与退出阈值不同，形成迟滞；从STRESS恢复使用更严格确认窗口。

### 3. 行业状态

行业映射为LEADING、IMPROVING、WEAKENING、LAGGING，保存相对基准和状态持续时间。

### 4. 数据质量

- FAIL：不发布新状态。
- WARN：可发布但降低confidence。
- 极端硬事件：可快速降级并记录原因。

## 测试案例

1. 阈值附近来回波动不会每窗口切状态。
2. 连续确认达到要求后才转换。
3. STRESS恢复比普通转换严格。
4. FAIL沿用旧快照并标记过期。
5. 硬事件转换保存rule/evidence引用。

## 完成条件

- 所有转换路径有单元测试。
- 定义配置版本化且不可由Agent修改。
- 状态转换原因可读。

