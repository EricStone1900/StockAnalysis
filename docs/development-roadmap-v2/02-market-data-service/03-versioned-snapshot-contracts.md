# 02-03 DataVersion、快照、API与事件

## 实施步骤

1. 将一次完整发布建模为`DataVersion` Aggregate，状态为BUILDING、VALIDATING、READY、FAILED、SUPERSEDED。
2. 保存数据范围、来源版本、Artifact Hash、质量摘要、availableAt和contentHash。
3. 使用临时版本构建，全部校验通过后原子切换READY；禁止覆盖旧版本。
4. 实现按version/asOf查询Security、Calendar、Bar和FinancialFact的OpenAPI。
5. 发布`stock.market-data.data-version.published.v1`，事件只包含版本、范围、质量和Artifact引用。
6. 提供Qlib所需的不可变Parquet数据视图，不让Qlib直接查询生产表。

```python
class DataVersionStatus(StrEnum):
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"
```

## 测试

- 发布中进程崩溃，旧READY版本仍可读。
- 重复发布请求保持幂等。
- 事件重复消费不会触发多个下游版本。
- Artifact Hash错误阻止READY。

