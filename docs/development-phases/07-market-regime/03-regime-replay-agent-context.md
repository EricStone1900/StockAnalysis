# 07-03 历史回放、快照和Agent上下文

## 目标

验证Regime定义、原子发布MarketRegimeSnapshot，并准备供阶段08 market-state-agent读取的上下文。

## 实施步骤

### 1. 历史回放

选择牛市、熊市、震荡和极端波动区间，统计状态持续时间、切换次数、后续收益/回撤和不同状态下因子表现。

ruptures只用于离线变化点参考：

```python
candidate_breaks = rpt.Pelt(model="rbf").fit(feature_matrix).predict(pen=penalty)
```

它不能直接成为实时生产触发器。

### 2. 快照发布

```python
snapshot = MarketRegimeSnapshot(
    snapshot_id=new_ulid(),
    overall_regime=regime,
    previous_regime=previous,
    change_detected=regime != previous,
    regime_definition_version=definition.version,
    evidence_ids=evidence_ids,
    freshness=freshness,
)
```

### 3. Agent上下文

提供只读端点：

```text
GET /api/v1/regimes/latest
GET /api/v1/regimes/{snapshotId}
GET /api/v1/regimes/industries/latest
```

Agent工具返回快照和组合上下文，不返回全市场原始矩阵。

### 4. 发布门禁

新定义先RESEARCH，再SHADOW，回放和人工批准后ACTIVE。

## 测试案例

1. 相同历史输入回放得到相同状态序列。
2. 新定义影子结果不改变latest生产快照。
3. 快照发布中查询返回旧READY。
4. Agent端点无法修改定义。
5. 状态变化事件只携带必要引用。

## 完成条件

- 至少一套ACTIVE可解释定义。
- 历史回放报告可复现。
- MarketRegimeSnapshot满足共享契约。
