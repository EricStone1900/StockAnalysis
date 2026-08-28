# 07-01 市场和行业特征计算

## 目标

从版本化市场数据计算趋势、宽度、波动、流动性和行业强弱特征。

## 实施步骤

### 1. 特征接口

```python
class RegimeFeatureCalculator(Protocol):
    feature_id: str
    version: str
    def calculate(self, window: MarketWindow) -> FeatureResult: ...
```

### 2. 第一版特征

- Trend：指数收益、均线位置、回撤。
- Breadth：上涨比例、新高/新低、均线上方比例、涨跌行业数。
- Volatility：实现波动、横截面离散度、同步下跌比例。
- Liquidity：成交额分位、换手、大小盘成交占比。
- Industry：行业相对收益和成交额变化。

### 3. 版本和缺失

```python
class FeatureResult(BaseModel):
    feature_id: str
    value: float | None
    quality: Literal["PASS", "WARN", "FAIL"]
    data_version: str
    feature_version: str
    evidence_ids: list[str]
```

资金流指标必须记录供应商和口径；不可把不同来源拼成同一连续序列。

### 4. 计算频率

日频正式特征收盘后计算；盘中按15～30分钟窗口。窗口未完整时不提前计算。

## 测试案例

1. 停牌股票不被简单归入下跌数。
2. 行业成分变化按历史成分计算。
3. 数据不足返回WARN/FAIL而非0。
4. 特征不读取窗口结束后的数据。
5. 不同供应商资金口径不会无记录混合。

## 完成条件

- 五个维度均有可解释特征。
- 每个值可追溯数据和公式版本。
- 日频和盘中使用统一契约。

