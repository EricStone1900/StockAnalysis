# 02-02 因子评价、模型和回测

## 目标

实现因子质量指标、模型训练/推理、交易成本后回测和可复现记录。

## 实施步骤

### 1. 因子评价

输出至少包含：IC、RankIC、ICIR、覆盖率、换手率、分层收益、衰减和与ACTIVE因子相关性。

```python
def rank_ic(factor: pd.Series, future_return: pd.Series) -> float:
    aligned = pd.concat([factor, future_return], axis=1).dropna()
    return float(aligned.corr(method="spearman").iloc[0, 1])
```

`future_return`只用于研究评价，不能作为当前时点特征进入模型。

### 2. Model Registry

```python
class ModelVersion(BaseModel):
    model_id: str
    version: str
    factor_set_version: str
    train_range: DateRange
    validation_range: DateRange
    test_range: DateRange
    artifact_uri: str
    artifact_hash: str
    status: Literal["CANDIDATE", "APPROVED", "ACTIVE", "DEPRECATED"]
```

训练和推理分开，生产推理只加载ACTIVE模型Artifact。

### 3. 回测

第一版至少实现：

- 固定调仓频率。
- 交易成本、印花税和滑点。
- T+1和最小交易单位近似约束。
- 基准收益、最大回撤、年化、波动和换手率。
- Walk-forward或滚动样本外评估。

### 4. 可复现Manifest

```json
{
  "dataVersion": "...",
  "universeVersion": "...",
  "factorSetVersion": "...",
  "modelVersion": "...",
  "strategyConfigHash": "...",
  "codeCommit": "...",
  "randomSeed": 42
}
```

## 测试案例

1. 打乱未来收益后IC接近随机基线。
2. 成本后收益不高于忽略成本的结果。
3. 不同随机种子被Manifest记录。
4. 测试区间不与训练区间重叠。
5. 模型Artifact Hash不匹配时拒绝推理。

## 完成条件

- 任一回测可按Manifest重新运行。
- 模型状态和Artifact一一对应。
- 所有核心指标有单元测试和边界测试。

