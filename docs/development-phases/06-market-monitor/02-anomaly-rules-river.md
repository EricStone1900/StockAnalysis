# 06-02 异常规则、严重度和River影子模型

## 目标

实现确定性异常规则、严重度合并和可选River在线影子评分。

## 实施步骤

### 1. 特征

实现return1m/5m、volumeRatio、rollingVolatility、VWAP偏离、指数/行业相对收益、日内回撤、止损距离和quoteAge。

### 2. 规则接口

```python
class AnomalyRule(Protocol):
    rule_id: str
    version: str
    def evaluate(self, context: FeatureContext) -> RuleHit | None: ...
```

示例：

```python
if context.quote_age_seconds > threshold:
    return RuleHit(rule_id="STALE_QUOTE", severity="HIGH", observed_value=context.quote_age_seconds)
```

第一版规则至少覆盖价格、成交量、波动、相对强弱、止损接近、交易状态和数据中断。

### 3. 严重度合并

硬事件给出最低严重等级，然后结合规则分、是否持仓、仓位和市场状态。模型分数不能降低硬事件等级。

### 4. River影子模式

```python
score = river_detector.score_one(features)
shadow_store.save(score=score, model_version=model.version)
```

初期只记录，不参与生产severity。完成回放评估和批准后再启用权重。

## 测试案例

1. STOP_LOSS_TRIGGERED不会被River低分降级。
2. STALE_QUOTE产生数据异常而非价格买卖信号。
3. 不同流动性股票使用各自历史阈值。
4. River冷启动不参与生产等级。
5. 规则版本变化产生新的detectorVersion。

## 完成条件

- 每条异常有ruleId、observedValue和threshold。
- 规则和River状态可版本化。
- 严重度逻辑完全可单测。

