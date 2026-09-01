# 03-03 每日分析生产闭环

## 实施步骤

1. 建立DailyQuantRun状态机：QUEUED、RUNNING、VALIDATING、READY、FAILED。
2. 输入固定DataVersion、UniverseVersion、FactorSetVersion、ModelVersion和PortfolioSnapshot引用。
3. 生成候选股、持仓股分析、排名、信号、质量摘要和evidenceIds。
4. 使用临时Artifact构建，Schema、数量、Hash和质量校验完成后原子发布DailyAnalysisSnapshot。
5. 发布`stock.quant.daily-analysis.published.v1`；失败保存原因并继续提供上一READY快照且标记stale。

## 当前实现

- `src/quant_research/daily_analysis.py`提供`DailyQuantRun`状态模型、输入版本绑定、候选/持仓分析、质量摘要和不可变`DailyAnalysisSnapshot`。
- `DailyAnalysisService.start`按`run_id`幂等启动；同一ID绑定不同日期或输入版本时拒绝，避免重复事件产生多个运行。
- `publish`先进入`VALIDATING`，对候选和持仓按证券代码稳定排序，计算规范内容Hash，再通过`publish_atomically`写入完整快照；发布成功后才进入`READY`并发送`stock.quant.daily-analysis.published.v1`。
- `fail`只记录失败原因，不覆盖仓储中的上一份快照；调用方应继续返回上一份快照并标记`isStale/validUntil`。
- 当前为内存仓储和事件端口，供Mac Fixture验证使用；PostgreSQL、Outbox和真实消息总线属于后续组件集成。

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

专项测试位于`tests/unit/test_daily_analysis.py`，覆盖幂等、排序、Hash、事件、失败保旧、FAIL质量和非UTC输入。
