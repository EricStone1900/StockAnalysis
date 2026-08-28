# Regime 06-01 特征和Snapshot最小切片

## 实施步骤

1. 建立RegimeDefinition、FeatureSetVersion、MarketRegimeSnapshot和Transition。
2. 从market-data API/Artifact读取指数、个股和行业数据，计算Trend、Breadth、Volatility和Liquidity。
3. 最小Use Case为“固定历史日生成NEUTRAL快照及四维分数”。
4. 特征保存公式、窗口、DataVersion、availableAt和质量摘要。
5. 行业状态使用统一行业分类版本，不能用当前分类回填历史。

```python
class RegimeDimensions(BaseModel):
    trend: Decimal
    breadth: Decimal
    volatility: Decimal
    liquidity: Decimal
```

## 测试

- 固定数据结果确定一致。
- 缺少市场宽度时质量FAIL而非LLM补全。
- 历史行业分类和指数成分无未来泄漏。

