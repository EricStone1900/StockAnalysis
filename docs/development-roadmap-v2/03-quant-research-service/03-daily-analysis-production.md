# 03-03 每日分析生产闭环

## 实施步骤

1. 建立DailyQuantRun状态机：QUEUED、RUNNING、VALIDATING、READY、FAILED。
2. 输入固定DataVersion、UniverseVersion、FactorSetVersion、ModelVersion和PortfolioSnapshot引用。
3. 生成候选股、持仓股分析、排名、信号、质量摘要和evidenceIds。
4. 使用临时Artifact构建，Schema、数量、Hash和质量校验完成后原子发布DailyAnalysisSnapshot。
5. 发布`stock.quant.daily-analysis.published.v1`；失败保存原因并继续提供上一READY快照且标记stale。

```python
def publish_snapshot(run: DailyQuantRun) -> DailyAnalysisSnapshot:
    assert run.status == "VALIDATING"
    validate_no_future_data(run)
    validate_artifact_hashes(run)
    return repository.publish_atomically(run)
```

## 测试

- DataVersion重复事件只启动一次Run。
- 部分股票计算失败不能发布半快照。
- 旧快照降级必须显式isStale和validUntil。
- 持仓股即使不在新候选池也有分析。

