# 01-03 版本快照、API与验收

## 目标

实现DataVersion原子发布、历史查询API和Qlib输入Artifact。

## 实施步骤

### 1. 发布状态机

```text
BUILDING -> VALIDATING -> READY
                   └──> FAILED
```

发布伪代码：

```python
async def publish_version(run_id: str) -> DataVersion:
    artifact = await build_versioned_artifact(run_id)
    report = await quality_pipeline.evaluate(artifact)
    if report.status == "FAIL":
        return await mark_failed(run_id, report)
    version = await repository.insert_immutable_version(artifact, report)
    await repository.compare_and_set_latest(version.id)
    return version
```

`compare_and_set_latest`必须在事务中完成，不能让调用方看到正在写入的半成品。

### 2. 查询API

实现：

```text
GET /api/v1/securities/{symbol}
GET /api/v1/calendars/{market}
GET /api/v1/market/bars?symbols=&start=&end=&dataVersion=
GET /api/v1/fundamentals/{symbol}?decisionTime=
GET /api/v1/data-versions/latest
POST /internal/v1/jobs/sync-daily
GET /internal/v1/jobs/{runId}
```

未指定DataVersion的查询返回latest，同时明确返回实际版本。历史决策调用必须显式传版本。

### 3. Qlib Artifact

```text
s3://research-artifacts/qlib-data/{dataVersion}/
  calendars/
  instruments/
  features/
  manifest.json
```

`manifest.json`记录输入版本、行数、时间范围、Hash和构建代码版本。

### 4. 缓存

Redis只缓存latest查询。缓存键必须含DataVersion；历史版本不可因latest变化而返回错误内容。

## 验证

```bash
curl -X POST http://localhost:8001/internal/v1/jobs/sync-daily \
  -H 'Idempotency-Key: market-2026-08-27'
curl http://localhost:8001/api/v1/data-versions/latest
```

## 测试案例

1. 两个相同幂等键只产生一个任务。
2. 发布中查询仍返回上一份READY。
3. FAIL任务不改变latest。
4. 指定历史DataVersion结果不随新版本变化。
5. Qlib manifest Hash与实际文件一致。

## 完成条件

- API通过OpenAPI契约测试。
- Qlib Data Cache可由DataVersion重建。
- 任一历史版本可查询且不会被覆盖。
