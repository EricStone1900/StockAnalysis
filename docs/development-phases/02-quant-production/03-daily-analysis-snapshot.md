# 02-03 每日分析快照与API

## 目标

每天对生产股票池和当前持仓运行推理，原子发布DailyAnalysisSnapshot。

## 实施步骤

### 1. 任务输入

```python
class DailyAnalysisRequest(BaseModel):
    as_of_date: date
    data_version: str
    portfolio_snapshot_id: str | None
    idempotency_key: str
```

任务开始时解析ACTIVE factorSet和modelVersion，之后即使配置变化也不能静默切换。

### 2. 股票分析结构

```python
class StockAnalysis(BaseModel):
    symbol: str
    score: float
    rank: int
    percentile: float
    signal: Literal["POSITIVE", "NEUTRAL", "NEGATIVE"]
    factor_contributions: list[FactorContribution]
    risk_flags: list[str]
    evidence_ids: list[str]
```

候选股与持仓股都要分析；持仓股不能因为未进入当日Top N而丢失。

### 3. 原子发布

```python
with repository.transaction():
    snapshot = repository.insert_immutable_snapshot(result)
    repository.compare_and_set_latest(snapshot.snapshot_id)
```

先将大文件写入临时Artifact，校验完成后再注册不可变URI。

### 4. API

```text
POST /internal/v1/runs/daily-analysis
GET  /api/v1/snapshots/latest
GET  /api/v1/snapshots/{asOfDate}
GET  /api/v1/stocks/{symbol}/analysis
GET  /api/v1/runs/{runId}
```

### 5. 失败语义

新任务失败时latest保持上一份READY；API返回`isStale=true`和失败原因，不复制旧快照伪装成当天新结果。

## 测试案例

1. 同一幂等键只产生一个快照。
2. 持仓股不在候选股中仍有分析。
3. 计算中断不改变latest。
4. 因子贡献合计和模型分数在容差内一致。
5. API明确返回dataCutoffAt和所有版本。

## 完成条件

- 每日任务可由Temporal或手工触发。
- 快照完整、不可变且可追溯。
- 失败时调用方能识别旧数据。
